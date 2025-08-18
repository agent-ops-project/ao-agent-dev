import os
import zipfile
import tempfile
import asyncio
import threading
import base64
from pathlib import Path
from common.logger import logger
from telemetry.client import supabase_client


# Patterns to exclude from code snapshots
EXCLUDE_PATTERNS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    ".venv",
    "venv",
    ".env",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
    "Thumbs.db",
    ".cache",
    "dist",
    "build",
    "*.egg-info",
    ".mypy_cache",
    ".coverage",
    "data",
}


def _should_exclude(path: Path, project_root: Path) -> bool:
    """Check if a path should be excluded from the snapshot."""
    relative_path = path.relative_to(project_root)

    # Check each part of the path
    for part in relative_path.parts:
        if part in EXCLUDE_PATTERNS:
            return True
        # Check wildcard patterns
        if part.endswith((".pyc", ".pyo")) or part.startswith("."):
            if part in EXCLUDE_PATTERNS:
                return True

    return False


def create_code_zip(project_root: str) -> bytes:
    """Create a zip file of the project code, excluding common artifacts."""
    project_path = Path(project_root)

    with tempfile.NamedTemporaryFile() as temp_file:
        with zipfile.ZipFile(temp_file.name, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in project_path.rglob("*"):
                if file_path.is_file() and not _should_exclude(file_path, project_path):
                    # Add file to zip with relative path
                    arcname = file_path.relative_to(project_path)
                    try:
                        zipf.write(file_path, arcname)
                    except (OSError, PermissionError) as e:
                        logger.debug(f"Skipping file {file_path}: {e}")

        # Read the zip data
        temp_file.seek(0)
        return temp_file.read()


def store_code_snapshot(user_id: str, project_root: str) -> bool:
    """Store a code snapshot synchronously."""
    if not supabase_client.is_available():
        logger.debug("Supabase not available, skipping code snapshot")
        return False

    try:
        # Create zip
        zip_data = create_code_zip(project_root)

        # Encode binary data as base64 for JSON transport
        zip_data_b64 = base64.b64encode(zip_data).decode("utf-8")

        # Debug the encoding
        logger.debug(f"Original zip size: {len(zip_data)} bytes")
        logger.debug(f"Base64 encoded size: {len(zip_data_b64)} chars")
        logger.debug(f"Base64 preview: {zip_data_b64[:50]}...")
        logger.debug(f"Base64 is valid text: {zip_data_b64.isprintable()}")

        # Store in Supabase
        supabase_client.client.table("code_snapshots").insert(
            {"user_id": user_id, "code_snapshot": zip_data_b64, "snapshot_size": len(zip_data)}
        ).execute()

        logger.info(f"Code snapshot stored successfully ({len(zip_data)} bytes)")
        return True

    except Exception as e:
        logger.error(f"Failed to store code snapshot: {e}")
        return False


async def store_code_snapshot_async(user_id: str, project_root: str) -> bool:
    """Store a code snapshot asynchronously in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, store_code_snapshot, user_id, project_root)


def store_code_snapshot_background(user_id: str, project_root: str) -> None:
    """Store a code snapshot in the background using threading."""

    def _background_task():
        store_code_snapshot(user_id, project_root)

    thread = threading.Thread(target=_background_task, daemon=True)
    thread.start()


if __name__ == "__main__":
    import tempfile
    import os

    print("Testing code snapshot functionality...")

    # Create a temporary test directory with some files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create some test files
        test_files = {
            "main.py": "print('hello world')",
            "README.md": "# Test Project",
            "src/utils.py": "def helper(): pass",
            ".env": "SECRET=123",  # Should be excluded
            "__pycache__/cache.pyc": "cached",  # Should be excluded
        }

        for file_path, content in test_files.items():
            full_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)

        print(f"Created test project in: {temp_dir}")
        print("Files created:", list(test_files.keys()))

        # Test zip creation
        print("\n1. Testing zip creation...")
        try:
            zip_data = create_code_zip(temp_dir)
            print(f"✅ Zip created successfully! Size: {len(zip_data)} bytes")
        except Exception as e:
            print(f"❌ Zip creation failed: {e}")
            exit(1)

        # Test snapshot storage
        print("\n2. Testing snapshot upload...")
        success = store_code_snapshot("test_user", temp_dir)
        if success:
            print("✅ Snapshot uploaded successfully!")
        else:
            print("❌ Snapshot upload failed (check Supabase connection)")

        # Test background upload
        print("\n3. Testing background upload...")
        store_code_snapshot_background("test_user", temp_dir)
        print("✅ Background upload started (check logs for completion)")
