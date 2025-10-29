# Wrapper script templates for launching user code with AST rewrites and environment setup.
# These templates use placeholders that will be replaced by develop_shim.py.


_SETUP_TRACING_SETUP = """import time
print(f"[LAUNCH] Wrapper script executing ({{time.time()}})")
_launch_start = time.time()
print(f"[LAUNCH] Script started ({{_launch_start}})")

import os
print(f"[LAUNCH] Imported os in {{time.time() - _launch_start:.4f}}s ({{time.time()}})")

import sys
print(f"[LAUNCH] Imported sys in {{time.time() - _launch_start:.4f}}s ({{time.time()}})")

import runpy
print(f"[LAUNCH] Imported runpy in {{time.time() - _launch_start:.4f}}s ({{time.time()}})")

import socket
print(f"[LAUNCH] Imported socket in {{time.time() - _launch_start:.4f}}s ({{time.time()}})")

import json
print(f"[LAUNCH] Imported json in {{time.time() - _launch_start:.4f}}s ({{time.time()}})")

import traceback
print(f"[LAUNCH] Imported traceback in {{time.time() - _launch_start:.4f}}s ({{time.time()}})")

from aco.common.logger import logger
print(f"[LAUNCH] Imported logger in {{time.time() - _launch_start:.4f}}s ({{time.time()}})")


project_root = {project_root}
packages_in_project_root = {packages_in_project_root}

# Add project root to path
# FIXME: This is a bit hacky so we are able to import the
# user's modules. I'm not sure this is needed but even if,
# it's probably not a good way to do this.
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set up AST rewriting for all user modules and register taint functions
print(f"[LAUNCH] About to import ast_rewriter ({{time.time() - _launch_start:.4f}}s total)")
from aco.runner.ast_rewriter import cache_rewritten_modules, install_rewrite_hook
print(f"[LAUNCH] Imported ast_rewriter in {{time.time() - _launch_start:.4f}}s ({{time.time()}})")

print(f"[LAUNCH] About to import scan_user_py_files_and_modules ({{time.time() - _launch_start:.4f}}s total)")
from aco.common.utils import scan_user_py_files_and_modules
print(f"[LAUNCH] Imported scan_user_py_files_and_modules in {{time.time() - _launch_start:.4f}}s ({{time.time()}})")

print(f"[LAUNCH] Starting file scan... ({{time.time()}})")
start_scan = time.time()
_, _, module_to_file = scan_user_py_files_and_modules(project_root)
for additional_package in packages_in_project_root:
    _, _, additional_package_module_to_file = scan_user_py_files_and_modules(additional_package)
    module_to_file = {{**module_to_file, **additional_package_module_to_file}}
print(f"[LAUNCH] File scan completed in {{time.time() - start_scan:.4f}}s ({{time.time()}})")

# Register taint functions in builtins FIRST
# This must happen before caching modules, since rewritten code will call these functions
print(f"[LAUNCH] Starting import of builtins and taint functions ({{time.time()}})")
start_import = time.time()
import builtins
from aco.runner.fstring_rewriter import (
    taint_fstring_join, taint_format_string, taint_percent_format, exec_func
)
print(f"[LAUNCH] Imports completed in {{time.time() - start_import:.4f}}s ({{time.time()}})")

print(f"[LAUNCH] Registering taint functions in builtins ({{time.time()}})")
start_register = time.time()
builtins.taint_fstring_join = taint_fstring_join
builtins.taint_format_string = taint_format_string
builtins.taint_percent_format = taint_percent_format
builtins.exec_func = exec_func
print(f"[LAUNCH] Taint functions registered in {{time.time() - start_register:.4f}}s ({{time.time()}})")

# Cache all user modules (rewrite + compile, but don't execute)
print(f"[LAUNCH] Starting cache_rewritten_modules... ({{time.time()}})")
start_cache = time.time()
cache_rewritten_modules(module_to_file)
print(f"[LAUNCH] cache_rewritten_modules completed in {{time.time() - start_cache:.4f}}s ({{time.time()}})")

# Install import hook to serve cached rewritten code
# Module-level code only runs when modules are actually imported
print(f"[LAUNCH] Installing rewrite hook... ({{time.time()}})")
start_hook = time.time()
install_rewrite_hook()
print(f"[LAUNCH] Rewrite hook installed in {{time.time() - start_hook:.4f}}s ({{time.time()}})")

# Connect to server and pply monkey patches if enabled via environment variable.
print(f"[LAUNCH] Starting imports for server connection... ({{time.time()}})")
start_server_imports = time.time()
from aco.runner.context_manager import set_parent_session_id, set_server_connection
from aco.common.constants import HOST, PORT, SOCKET_TIMEOUT
from aco.runner.monkey_patching.apply_monkey_patches import apply_all_monkey_patches
print(f"[LAUNCH] Server connection imports completed in {{time.time() - start_server_imports:.4f}}s ({{time.time()}})")

if os.environ.get("AGENT_COPILOT_ENABLE_TRACING"):
    host = os.environ.get("AGENT_COPILOT_SERVER_HOST", HOST)
    port = int(os.environ.get("AGENT_COPILOT_SERVER_PORT", PORT))
    session_id = os.environ.get("AGENT_COPILOT_SESSION_ID")
    server_conn = None
    # try:
    # Connect to server, this will be the global server connection for the process.
    # We currently rely on the OS to close the connection when proc finishes.
    print(f"[LAUNCH] Connecting to server... ({{time.time()}})")
    start_connect = time.time()
    server_conn = socket.create_connection((host, port), timeout=SOCKET_TIMEOUT)
    print(f"[LAUNCH] Server connection established in {{time.time() - start_connect:.4f}}s ({{time.time()}})")

    # Handshake. For shim-runner, server doesn't send a response, just start running.
    print(f"[LAUNCH] Sending handshake... ({{time.time()}})")
    start_handshake = time.time()
    handshake = {{
        "type": "hello",
        "role": "shim-runner",
        "script": os.path.basename(os.environ.get("_", "unknown")),
        "process_id": os.getpid(),
    }}
    server_conn.sendall((json.dumps(handshake) + "\\n").encode("utf-8"))
    print(f"[LAUNCH] Handshake sent in {{time.time() - start_handshake:.4f}}s ({{time.time()}})")

    # Register session_id and connection with context manager.
    print(f"[LAUNCH] Registering session and connection... ({{time.time()}})")
    start_register_session = time.time()
    set_parent_session_id(session_id)
    set_server_connection(server_conn)
    print(f"[LAUNCH] Session registered in {{time.time() - start_register_session:.4f}}s ({{time.time()}})")

    # except Exception as e:
    #     logger.error(f"Exception set up tracing:")
    #     traceback.print_exc()

    # Apply monkey patches.
    print(f"[LAUNCH] Starting apply_all_monkey_patches... ({{time.time()}})")
    start_patches = time.time()
    apply_all_monkey_patches()
    print(f"[LAUNCH] apply_all_monkey_patches completed in {{time.time() - start_patches:.4f}}s ({{time.time()}})")
"""


# Template for running a script as a module (when user runs: develop script.py)
SCRIPT_WRAPPER_TEMPLATE = (
    _SETUP_TRACING_SETUP
    + """
# Set up argv and run the module
module_name = os.path.abspath({module_name})
sys.argv = [{module_name}] + {script_args}
runpy.run_module({module_name}, run_name='__main__')
"""
)

# Template for running a module directly (when user runs: develop -m module)
MODULE_WRAPPER_TEMPLATE = (
    _SETUP_TRACING_SETUP
    + """
# Now run the module with proper resolution
sys.argv = [{module_name}] + {script_args}
runpy.run_module({module_name}, run_name='__main__')
"""
)
