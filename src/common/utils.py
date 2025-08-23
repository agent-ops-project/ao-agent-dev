import hashlib
import json
import os
from pathlib import Path
import threading
from typing import Optional, Union


def scan_user_py_files_and_modules(root_dir):
    """
    Scan a directory for all .py files and return:
      - user_py_files: set of absolute file paths
      - file_to_module: mapping from file path to module name (relative to root_dir)
    """
    user_py_files = set()
    file_to_module = dict()
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".py"):
                abs_path = os.path.abspath(os.path.join(dirpath, filename))
                user_py_files.add(abs_path)
                # Compute module name relative to root_dir
                rel_path = os.path.relpath(abs_path, root_dir)
                mod_name = rel_path[:-3].replace(os.sep, ".")  # strip .py, convert / to .
                if mod_name.endswith(".__init__"):
                    mod_name = mod_name[:-9]  # remove .__init__
                file_to_module[abs_path] = mod_name
    return user_py_files, file_to_module


# ==============================================================================
# Communication with server.
# ==============================================================================

# Global lock for thread-safe server communication
_server_lock = threading.Lock()


def send_to_server(msg):
    """Thread-safe send message to server (no response expected)."""
    from agent_copilot.context_manager import server_file

    if isinstance(msg, dict):
        msg = json.dumps(msg) + "\n"
    elif isinstance(msg, str) and msg[-1] != "\n":
        msg += "\n"
    with _server_lock:
        server_file.write(msg)
        server_file.flush()


def send_to_server_and_receive(msg):
    """Thread-safe send message to server and receive response."""
    from agent_copilot.context_manager import server_file

    if isinstance(msg, dict):
        msg = json.dumps(msg) + "\n"
    elif isinstance(msg, str) and msg[-1] != "\n":
        msg += "\n"
    with _server_lock:
        server_file.write(msg)
        server_file.flush()
        response = json.loads(server_file.readline().strip())
        return response


# ===============================================
# Helpers for writing attachments to disk.
# ===============================================
def stream_hash(stream):
    """Compute SHA-256 hash of a binary stream (reads full content into memory)."""
    content = stream.read()
    stream.seek(0)
    return hashlib.sha256(content).hexdigest()


def save_io_stream(stream, filename, dest_dir):
    """
    Save stream to dest_dir/filename. If filename already exists, find new unique one.
    """
    stream.seek(0)
    desired_path = os.path.join(dest_dir, filename)
    if not os.path.exists(desired_path):
        # No conflict, write directly
        with open(desired_path, "wb") as f:
            f.write(stream.read())
        stream.seek(0)
        return desired_path

    # Different content, find a unique name
    base, ext = os.path.splitext(filename)
    counter = 1
    while True:
        new_filename = f"{base}_{counter}{ext}"
        new_path = os.path.join(dest_dir, new_filename)
        if not os.path.exists(new_path):
            with open(new_path, "wb") as f:
                f.write(stream.read())
            stream.seek(0)
            return new_path

        counter += 1
