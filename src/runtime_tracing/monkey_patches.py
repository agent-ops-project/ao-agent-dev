"""
Put all monkey patches here.

Have two general patch functions:
- notify_server_patch():
- no_notify_patch():
"""

import asyncio
import inspect
import json
import threading


def monkey_patch_llm_call(server_conn):
    """
    Monkey-patch agent_copilot.src.mock.call to intercept LLM calls.
    Sends call details (input, output, file, line, thread, task) to the server.
    """
    try:
        import agent_copilot.src.mock as ac_mock
    except ImportError:
        return  # If the module isn't available, do nothing
    original_call = getattr(ac_mock, "call", None)
    if original_call is None:
        return
    def patched_call(prompt: str) -> str:
        # Invoke the original LLM call (e.g., to get a response or raise an error)
        result = None
        error = None
        try:
            result = original_call(prompt)
        except Exception as e:
            error = e  # capture exception to report it, then re-raise
        # Gather call site info (filename and line number of the caller)
        frame = inspect.currentframe()
        caller = frame.f_back if frame else None
        file_name = caller.f_code.co_filename if caller else "<unknown>"
        line_no = caller.f_lineno if caller else -1
        # Identify thread and asyncio task
        thread_id = threading.get_ident()
        task_id = None
        try:
            task = asyncio.current_task()
        except RuntimeError:
            task = None
        if task:
            task_id = id(task)
        # Send the call details to the server
        message = {
            "type": "call",
            "input": prompt,
            "output": result if error is None else str(error),
            "file": file_name,
            "line": line_no,
            "thread": thread_id,
            "task": task_id
        }
        try:
            server_conn.sendall((json.dumps(message) + "\n").encode('utf-8'))
        except Exception:
            pass  # If sending fails (e.g., server down), skip
        if error:
            # Propagate the original exception after logging
            raise error
        return result
    ac_mock.call = patched_call
