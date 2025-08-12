import contextvars
from contextlib import contextmanager
import json
import socket
import threading
import os

from workflow_edits.cache_manager import CACHE
from workflow_edits.edit_manager import EDIT
from common.logger import logger

# Context variables to store the current session_id
current_session_id = contextvars.ContextVar("session_id", default=None)
parent_session_id = None


@contextmanager
def aco_launch(run_name="Workflow run"):
    """
    Context manager for launching runs with a specific name.

    Args:
        run_name (str): Name of the run to launch

    Usage:
        with aco_launch(run_name="my_eval"):
            # User code runs here
            result = some_function()
    """
    # Check if this run should be executed or not.
    # This is to support that some "sub-run" needs to be reran but not all.
    # TODO: I think this can have some weird side effects?
    logger.debug(
        f"Sub-run '{run_name}' starting in process {os.getpid()}, thread {threading.get_ident()}"
    )
    should_run, session_id = CACHE.should_run_subrun(parent_session_id, run_name)
    if not should_run:
        logger.debug(f"Sub-run '{run_name}' skipped - already executed")
        return

    print("executing", run_name)

    # Register with server as shim-control.
    shim_sock = socket.create_connection(("127.0.0.1", 5959))
    shim_file = shim_sock.makefile("rw")

    # Get rerun command from parent.
    parent_env = CACHE.get_parent_environment(parent_session_id)

    handshake = {
        "type": "hello",
        "role": "shim-control",
        "name": run_name,
        "parent_run": parent_session_id,
        "cwd": parent_env["cwd"],
        "command": parent_env["command"],
        "environment": json.loads(parent_env["environment"]),
    }
    shim_file.write(json.dumps(handshake) + "\n")
    shim_file.flush()

    response = json.loads(shim_file.readline().strip())

    if not session_id:
        session_id = response["session_id"]
    else:
        EDIT.mark_edit_applied(session_id)

    # Set session_id of this run.
    token = current_session_id.set(session_id)

    # Run user code
    try:
        yield run_name
    finally:
        # Clean up
        deregister_msg = {"type": "deregister", "session_id": session_id}
        shim_file.write(json.dumps(deregister_msg) + "\n")
        shim_file.flush()
        shim_sock.close()
        current_session_id.reset(token)


def get_session_id():
    sid = current_session_id.get()
    assert sid is not None
    return sid


def set_session_id(session_id):
    # Set session id of original develop run (called by sitecustomize.py).
    global parent_session_id, current_session_id
    parent_session_id = session_id
    current_session_id.set(session_id)
