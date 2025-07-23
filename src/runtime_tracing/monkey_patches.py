import asyncio
import inspect
import json
import threading
import functools
import uuid
from workflow_edits.cache_manager import CACHE
from common.logger import logger
from workflow_edits.utils import extract_output_text, json_to_response
from runtime_tracing.taint_wrappers import get_taint_origins, taint_wrap
from openai import OpenAI
from openai.resources.responses import Responses
import openai


# ===========================================================
# Generic wrappers for caching and server notification
# ===========================================================

def notify_server_patch(fn, server_conn):
    """
    Wrap `fn` to cache results and notify server of calls.
    
    - On cache hit, returns stored result immediately
    - On cache miss, invokes `fn` and stores result
    - Cache keys include function inputs and caller location
    - Sends call details to server for monitoring
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        # Get caller location
        frame = inspect.currentframe()
        caller = frame and frame.f_back
        file_name = caller.f_code.co_filename
        line_no = caller.f_lineno

        # Check cache first
        cached_out = CACHE.get_output(file_name, line_no, fn, args, kwargs)
        if cached_out is not None:
            result = cached_out
        else:
            result = fn(*args, **kwargs)
            CACHE.cache_output(result, file_name, line_no, fn, args, kwargs)

        # Notify server
        thread_id = threading.get_ident()
        try:
            task_id = id(asyncio.current_task())
        except RuntimeError:
            task_id = None

        message = {
            "type": "call",
            "file": file_name,
            "line": line_no,
            "thread": thread_id,
            "task": task_id,
        }
        try:
            server_conn.sendall((json.dumps(message) + "\n").encode("utf-8"))
        except Exception:
            pass  # best-effort only

        return result

    return wrapper


def no_notify_patch(fn):
    """
    Wrap `fn` to cache results without server notification.
    
    - On cache hit, returns stored result immediately
    - On cache miss, invokes `fn` and stores result
    - Cache keys include function inputs and caller location
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        # Get caller location
        frame = inspect.currentframe()
        caller = frame and frame.f_back
        file_name = caller.f_code.co_filename
        line_no = caller.f_lineno

        # Check cache first
        cached_out = CACHE.get_output(file_name, line_no, fn, args, kwargs)
        if cached_out is not None:
            return cached_out
        
        # Run function and cache result
        result = fn(*args, **kwargs)
        CACHE.cache_output(result, file_name, line_no, fn, args, kwargs)
        return result
    
    return wrapper


# ===========================================================
# Session management
# ===========================================================

# Global session_id, set by set_session_id()
session_id = None

def set_session_id(sid):
    global session_id
    session_id = sid


# ===========================================================
# Graph tracking utilities
# ===========================================================

def _send_graph_node_and_edges(server_conn, 
                               node_id, 
                               input, 
                               output_obj, 
                               source_node_ids, 
                               model, 
                               api_type):
    """Send graph node and edge updates to the server."""
    # Get caller location
    frame = inspect.currentframe()
    caller = frame and frame.f_back
    file_name = caller.f_code.co_filename if caller else "unknown"
    line_no = caller.f_lineno if caller else 0
    codeLocation = f"{file_name}:{line_no}"

    # Send node
    node_msg = {
        "type": "addNode",
        "session_id": session_id,
        "node": {
            "id": node_id,
            "input": "None", #input,
            "output": "None", #extract_output_text(output_obj, api_type),
            "border_color": "#00c542", # TODO: Later based on certainty.
            "label": f"{model}", # TODO: Later label with LLM.
            "codeLocation": codeLocation,
            "model": model,
        }
    }

    try:
        server_conn.sendall((json.dumps(node_msg) + "\n").encode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to send addNode: {e}")

    # Send edges for each source
    for src in source_node_ids:
        if src != node_id:
            edge_msg = {
                "type": "addEdge",
                "session_id": session_id,
                "edge": {"source": src, "target": node_id}
            }
            try:
                server_conn.sendall((json.dumps(edge_msg) + "\n").encode("utf-8"))
            except Exception as e:
                logger.error(f"Failed to send addEdge: {e}")


# ===========================================================
# OpenAI API patches
# ===========================================================

def v1_openai_patch(server_conn):
    """
    Patch openai.ChatCompletion.create (v1/classic API) to use persistent cache and edits.
    """

    original_create = getattr(openai.ChatCompletion, "create", None)
    if original_create is None:
        return

    def patched_create(*args, **kwargs):
        # Extract model and messages
        model = kwargs.get("model", args[0] if args else None)
        messages = kwargs.get("messages", args[1] if len(args) > 1 else None)
        # Use get_raw if present
        if hasattr(model, 'get_raw'):
            model = model.get_raw()
        if hasattr(messages, 'get_raw'):
            messages = messages.get_raw()
        # Use persistent cache/edits
        input_to_use, output_to_use, node_id = CACHE.get_in_out(session_id, model, str(messages))

        # Taint origins: combine from input and model
        taint_origins = get_taint_origins(messages) + get_taint_origins(model)

        # Produce output
        if output_to_use is not None:
            # Use cached output (assume already in correct format)
            result = output_to_use
        else:
            # Call LLM with possibly edited input
            call_kwargs = dict(kwargs)
            call_kwargs["model"] = model
            call_kwargs["messages"] = input_to_use
            result = original_create(**call_kwargs)
            # Cache
            CACHE.cache_output(session_id, model, input_to_use, result, "openai_v1", node_id)

        # Send to server (graph node/edges)
        _send_graph_node_and_edges(
            server_conn=server_conn,
            node_id=node_id,
            input=input_to_use,
            output_obj=result,
            source_node_ids=taint_origins,
            model=model,
            api_type="openai_v1"
        )

        # Wrap and return
        return taint_wrap(result, [node_id])

    openai.ChatCompletion.create = patched_create

def patch_openai_responses_create(responses, server_conn):
    original_create = responses.create
    def patched_create(*args, **kwargs):
        model = kwargs.get("model", args[0] if args else [])
        input = kwargs.get("input", args[1] if len(args) > 1 else [])
        taint_origins = get_taint_origins(input) + get_taint_origins(model)
        # Check if there's a cached / edited input/output
        input_to_use, output_to_use, node_id = CACHE.get_in_out(session_id, model, input)
        if output_to_use is not None:
            result = json_to_response(output_to_use, "openai_v2")
        else:
            new_kwargs = dict(kwargs)
            new_kwargs["input"] = input_to_use
            if len(args) == 1 and isinstance(args[0], Responses):
                result = original_create(**new_kwargs)
            else:
                result = original_create(*args, **new_kwargs)
            CACHE.cache_output(session_id, model, input_to_use, result, "openai_v2", node_id)
        _send_graph_node_and_edges(server_conn=server_conn,
                                   node_id=node_id,
                                   input=input_to_use,
                                   output_obj=result,
                                   source_node_ids=taint_origins,
                                   model=model,
                                   api_type="openai_v2")
        return taint_wrap(result, [node_id])
    responses.create = patched_create.__get__(responses, Responses)

def patch_openai_beta_threads_runs_create_and_poll(runs, server_conn):
    original_create_and_poll = runs.create_and_poll
    def patched_create_and_poll(*args, **kwargs):
        print("patched_create_and_poll called with", args, kwargs)
        taint_origins = []
        for arg in args:
            taint_origins.extend(get_taint_origins(arg))
        for val in kwargs.values():
            taint_origins.extend(get_taint_origins(val))
        # Call original method with only keyword arguments
        result = original_create_and_poll(**kwargs)
        node_id = str(uuid.uuid4())
        _send_graph_node_and_edges(
            server_conn=server_conn,
            node_id=node_id,
            input=str(kwargs),
            output_obj=result,
            source_node_ids=taint_origins,
            model="beta_threads_run",
            api_type="openai_beta_runs"
        )
        return taint_wrap(result, [node_id])
    runs.create_and_poll = patched_create_and_poll.__get__(runs, type(original_create_and_poll))


def v2_openai_patch(server_conn):
    original_init = OpenAI.__init__
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        patch_openai_responses_create(self.responses, server_conn)
        patch_openai_beta_assistants_create(self.beta.assistants)
        patch_openai_beta_threads_create(self.beta.threads)
        patch_openai_beta_threads_runs_create_and_poll(self.beta.threads.runs, server_conn)
    OpenAI.__init__ = new_init


def patch_openai_beta_assistants_create(assistants_instance):
    """
    Patch the .create method of an OpenAI beta assistants instance to propagate taint origins from any input argument to the result.
    If no input is tainted, propagate an empty origin list.
    """
    original_create = assistants_instance.create

    def patched_create(*args, **kwargs):
        print("hello from patched_create")
        # Collect taint origins from all args and kwargs
        from runtime_tracing.taint_wrappers import get_taint_origins, taint_wrap
        taint_origins = set()
        for arg in args:
            taint_origins.update(get_taint_origins(arg))
        for val in kwargs.values():
            taint_origins.update(get_taint_origins(val))
        # Call the original method
        result = original_create(*args, **kwargs)
        # Propagate taint
        return taint_wrap(result, list(taint_origins))

    assistants_instance.create = patched_create


def patch_openai_beta_threads_create(threads_instance):
    """
    Patch the .create method of an OpenAI beta threads instance to propagate taint origins from any input argument to the result.
    If no input is tainted, propagate an empty origin list.
    """
    original_create = threads_instance.create

    def patched_create(*args, **kwargs):
        from runtime_tracing.taint_wrappers import get_taint_origins, taint_wrap
        taint_origins = set()
        for arg in args:
            taint_origins.update(get_taint_origins(arg))
        for val in kwargs.values():
            taint_origins.update(get_taint_origins(val))
        result = original_create(*args, **kwargs)
        return taint_wrap(result, list(taint_origins))

    threads_instance.create = patched_create


# ===========================================================
# Patch function registry
# ===========================================================

# Only include patch functions that can be called at global patch time (with server_conn as argument).
# Subclient patching must be done inside the OpenAI.__init__ patch (see v2_openai_patch).
CUSTOM_PATCH_FUNCTIONS = [
    v1_openai_patch,
    v2_openai_patch,
]

# Subclient patch functions (e.g., patch_openai_responses_create, patch_openai_beta_threads_runs_create_and_poll)
# are NOT included here and should only be called from within the OpenAI.__init__ patch.
