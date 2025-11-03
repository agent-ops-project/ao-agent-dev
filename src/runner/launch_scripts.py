# Wrapper script templates for launching user code with AST rewrites and environment setup.
# These templates use placeholders that will be replaced by develop_shim.py.


_SETUP_TRACING_SETUP = """import os
import sys
import runpy
import socket
import json
import traceback
from aco.common.logger import logger

project_root = {project_root}
packages_in_project_root = {packages_in_project_root}

# Add project root to path
# FIXME: This is a bit hacky so we are able to import the
# user's modules. I'm not sure this is needed but even if,
# it's probably not a good way to do this.
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Register taint functions in builtins so rewritten .pyc files can call them
import builtins
from aco.server.ast_transformer import (
    taint_fstring_join, taint_format_string, taint_percent_format, exec_func
)

builtins.taint_fstring_join = taint_fstring_join
builtins.taint_format_string = taint_format_string
builtins.taint_percent_format = taint_percent_format
builtins.exec_func = exec_func

# Add logging to check if .pyc files exist for user programs
import os
import glob
from aco.common.logger import logger

logger.info("[LaunchScripts] ✓ Taint functions registered in builtins")

# Log any .pyc files we can find for debugging
pyc_files = []
for root, dirs, files in os.walk(project_root):
    pyc_files.extend(glob.glob(os.path.join(root, "**", "*.pyc"), recursive=True))

if pyc_files:
    logger.info("[LaunchScripts] Found %d .pyc files in project:" % len(pyc_files))
    for pyc_file in pyc_files[:5]:  # Show first 5
        logger.info("[LaunchScripts]   %s" % pyc_file)
    if len(pyc_files) > 5:
        logger.info("[LaunchScripts]   ... and %d more" % (len(pyc_files) - 5))
else:
    logger.warning("[LaunchScripts] No .pyc files found in project root")

logger.info("[LaunchScripts] No longer using in-memory AST caching - relying on pre-compiled .pyc files")

# Connect to server and apply monkey patches if enabled via environment variable.
from aco.runner.context_manager import set_parent_session_id, set_server_connection
from aco.common.constants import HOST, PORT, SOCKET_TIMEOUT
from aco.runner.monkey_patching.apply_monkey_patches import apply_all_monkey_patches

if os.environ.get("AGENT_COPILOT_ENABLE_TRACING"):
    host = os.environ.get("AGENT_COPILOT_SERVER_HOST", HOST)
    port = int(os.environ.get("AGENT_COPILOT_SERVER_PORT", PORT))
    session_id = os.environ.get("AGENT_COPILOT_SESSION_ID")
    server_conn = None
    # try:
    # Connect to server, this will be the global server connection for the process.
    # We currently rely on the OS to close the connection when proc finishes.
    server_conn = socket.create_connection((host, port), timeout=SOCKET_TIMEOUT)

    # Handshake. For shim-runner, server doesn't send a response, just start running.
    handshake = {{
        "type": "hello",
        "role": "shim-runner",
        "script": os.path.basename(os.environ.get("_", "unknown")),
        "process_id": os.getpid(),
    }}
    server_conn.sendall((json.dumps(handshake) + "\\n").encode("utf-8"))

    # Register session_id and connection with context manager.
    set_parent_session_id(session_id)
    set_server_connection(server_conn)

    # except Exception as e:
    #     logger.error(f"Exception set up tracing:")
    #     traceback.print_exc()

    # Apply monkey patches.
    apply_all_monkey_patches()
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
