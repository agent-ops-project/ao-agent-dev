import os
import socket
import json
import traceback
from common.logging_config import setup_logging
logger = setup_logging()

def setup_tracing():
    """
    Set up runtime tracing if enabled via environment variable.
    """
    if not os.environ.get('AGENT_COPILOT_ENABLE_TRACING'):
        return
    host = os.environ.get('AGENT_COPILOT_SERVER_HOST', '127.0.0.1')
    port = int(os.environ.get('AGENT_COPILOT_SERVER_PORT', '5959'))
    server_conn = None
    try:
        server_conn = socket.create_connection((host, port), timeout=5)
    except Exception:
        return
    if server_conn:
        handshake = {
            "type": "hello",
            "role": "shim-runner",
            "script": os.path.basename(os.environ.get('_', 'unknown')),
            "process_id": os.getpid()
        }
        try:
            server_conn.sendall((json.dumps(handshake) + "\n").encode('utf-8'))
            file_obj = server_conn.makefile(mode='r')
            session_line = file_obj.readline()
            if session_line:
                try:
                    session_msg = json.loads(session_line.strip())
                    session_id = session_msg.get("session_id")
                except Exception:
                    pass
        except Exception:
            pass
        try:
            from runtime_tracing.apply_monkey_patches import apply_all_monkey_patches
            apply_all_monkey_patches(server_conn)
        except Exception as e:
            logger.error(f"Exception in sitecustomize.py patching: {e}")
            traceback.print_exc()

setup_tracing() 