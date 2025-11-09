"""
Test to confirm the subprocess issue with exec_func.

This test will:
1. Run the MCP server directly with Python (no aco-launch)
2. Show that exec_func is not available
3. Demonstrate the error you're seeing

Run with: python example_workflows/test_subprocess_issue.py
"""

import subprocess
import sys
import os
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent.parent


def test_direct_python_execution():
    """Test running the MCP server directly with Python (mimics subprocess behavior)."""
    
    print("=" * 60)
    print("Testing direct Python execution (no aco-launch)")
    print("=" * 60)
    
    # Path to the MCP server
    mcp_server_path = repo_root / "example_workflows/reasoning_mcp_server.py"
    
    if not mcp_server_path.exists():
        print(f"✗ MCP server not found: {mcp_server_path}")
        return
    
    # Set up environment
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    
    # Run with direct Python (no aco-launch)
    cmd = [sys.executable, str(mcp_server_path)]
    print(f"Running: {' '.join(cmd)}")
    print("(This should fail with exec_func not defined)")
    
    try:
        # Start the process
        process = subprocess.Popen(
            cmd,
            env=env,
            cwd=str(repo_root),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it a moment to start and potentially fail
        import time
        time.sleep(2)
        
        # Check if it's still running or failed
        returncode = process.poll()
        
        if returncode is not None:
            # Process has terminated
            stdout, stderr = process.communicate()
            print(f"\nReturn code: {returncode}")
            
            if stdout:
                print(f"\nSTDOUT:\n{stdout}")
                
            if stderr:
                print(f"\nSTDERR:\n{stderr}")
                
            if returncode != 0:
                print("✓ Process failed as expected (likely exec_func not available)")
                if "exec_func" in stderr:
                    print("✓ Confirmed: exec_func error found in stderr")
            else:
                print("⚠ Process terminated successfully")
        else:
            # Process is still running (waiting for input)
            print("⚠ Process is running (waiting for MCP input)")
            print("This means the import succeeded - exec_func might be available")
            
            # Terminate the process
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            
    except Exception as e:
        print(f"✗ Error running process: {e}")


def test_check_pyc_file():
    """Check if a .pyc file exists for the MCP server (indicating it was rewritten)."""
    
    print(f"\n{'=' * 60}")
    print("Checking for rewritten .pyc file")
    print("=" * 60)
    
    # Look for .pyc file
    mcp_server_path = repo_root / "example_workflows/reasoning_mcp_server.py"
    pyc_pattern = mcp_server_path.parent / "__pycache__" / f"{mcp_server_path.stem}.cpython-*.pyc"
    
    import glob
    pyc_files = glob.glob(str(pyc_pattern))
    
    if pyc_files:
        print(f"✓ Found .pyc file: {pyc_files[0]}")
        print("This indicates the file was processed by the file watcher")
        
        # Try to inspect the .pyc file
        pyc_file = pyc_files[0]
        stat = os.stat(pyc_file)
        print(f"  Size: {stat.st_size} bytes")
        print(f"  Modified: {stat.st_mtime}")
        
    else:
        print("✗ No .pyc file found")
        print("This means the file wasn't processed by the file watcher")


def test_with_simulated_rewriting():
    """Create a minimal test that simulates the rewriting issue."""
    
    print(f"\n{'=' * 60}")
    print("Testing simulated rewriting issue")
    print("=" * 60)
    
    # Create a minimal test script that uses exec_func
    test_script = '''
import sys

# Check if exec_func is available
print(f"exec_func in builtins: {hasattr(__builtins__, 'exec_func')}")
print(f"exec_func in globals: {'exec_func' in globals()}")

# Simulate what happens with a rewritten decorator
try:
    # This is what @mcp.tool() becomes after rewriting
    def dummy_mcp_tool():
        return lambda func: func
    
    # This will fail if exec_func is not available
    result = exec_func(dummy_mcp_tool, (), {})
    print("✓ exec_func call succeeded")
    
except NameError as e:
    print(f"✗ NameError as expected: {e}")
except Exception as e:
    print(f"✗ Other error: {e}")
'''
    
    # Write the test script
    test_file = repo_root / "example_workflows" / "temp_exec_func_test.py"
    with open(test_file, 'w') as f:
        f.write(test_script)
    
    try:
        # Run it with direct Python
        result = subprocess.run(
            [sys.executable, str(test_file)],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5
        )
        
        print("Direct Python execution:")
        print(result.stdout)
        if result.stderr:
            print(f"STDERR: {result.stderr}")
            
    finally:
        # Clean up
        if test_file.exists():
            test_file.unlink()


if __name__ == "__main__":
    print("Testing subprocess execution issue")
    print("This reproduces the problem where MCP servers run without exec_func")
    
    test_direct_python_execution()
    test_check_pyc_file() 
    test_with_simulated_rewriting()
    
    print(f"\n{'=' * 60}")
    print("DIAGNOSIS:")
    print("1. aco-launch injects exec_func into builtins")
    print("2. File watcher rewrites MCP server code to use exec_func")  
    print("3. MCP server runs as subprocess without aco-launch")
    print("4. Subprocess doesn't have exec_func -> NameError")
    print("=" * 60)