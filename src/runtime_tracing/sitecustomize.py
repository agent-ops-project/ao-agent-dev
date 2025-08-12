import os
import socket
import json
import traceback
from agent_copilot.context_manager import set_session_id
from common.logger import logger
from common.constants import HOST, PORT, SOCKET_TIMEOUT
from runtime_tracing.apply_monkey_patches import apply_all_monkey_patches


def setup_tracing():
    """
    Set up runtime tracing if enabled via environment variable.
    """
    if not os.environ.get("AGENT_COPILOT_ENABLE_TRACING"):
        return
    host = os.environ.get("AGENT_COPILOT_SERVER_HOST", HOST)
    port = int(os.environ.get("AGENT_COPILOT_SERVER_PORT", PORT))
    session_id = os.environ.get("AGENT_COPILOT_SESSION_ID")
    server_conn = None
    try:
        server_conn = socket.create_connection((host, port), timeout=SOCKET_TIMEOUT)
    except Exception:
        return
    if server_conn:
        handshake = {
            "type": "hello",
            "role": "shim-runner",
            "script": os.path.basename(os.environ.get("_", "unknown")),
            "process_id": os.getpid(),
        }
        try:
            server_conn.sendall((json.dumps(handshake) + "\n").encode("utf-8"))
            # For shim-runner, server doesn't send a response, so don't wait for one
        except Exception:
            pass
        try:
            if session_id:
                set_session_id(session_id)
            else:
                logger.error(
                    f"sitecustomize: No session_id in environment, run will not be traced properly."
                )
            apply_all_monkey_patches(server_conn)
        except Exception as e:
            logger.error(f"Exception in sitecustomize.py patching: {e}")
            traceback.print_exc()
