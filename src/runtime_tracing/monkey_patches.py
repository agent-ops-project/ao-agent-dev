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
            "input": input,
            "output": extract_output_text(output_obj, api_type),
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
    assert NotImplementedError("openai v1 is not implemented")
    try:
        import openai
    except ImportError:
        return  # If openai isn't available, do nothing

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
        input_to_use, output_to_use, cached_node_id = CACHE.get_in_out(session_id, model, str(messages))
        from_cache = output_to_use is not None
        new_node_id = None
        if output_to_use is not None:
            result = output_to_use
        else:
            # Call real LLM with possibly edited input
            result = original_create(model=model, messages=messages) if input_to_use is None else original_create(model=model, messages=input_to_use)
            # Generate node ID for new result
            new_node_id = str(uuid.uuid4())
            CACHE.cache_output(session_id, model, str(messages if input_to_use is None else input_to_use), result, 'openai_v1', new_node_id)
        # Taint/graph logic
        def check_taint(val):
            if get_taint_origins(val):
                return get_taint_origins(val)
            if isinstance(val, (list, tuple)):
                return [check_taint(v) for v in val]
            if isinstance(val, dict):
                return {k: check_taint(v) for k, v in val.items()}
            return None
        input_obj = messages
        input_taint = check_taint(input_obj)
        any_input_tainted = bool(input_taint)
        # Get caller location
        frame = inspect.currentframe()
        caller = frame and frame.f_back
        file_name = caller.f_code.co_filename if caller else "unknown"
        line_no = caller.f_lineno if caller else 0
        
        # Use new_node_id for new results, cached_node_id for cached results
        node_id_to_use = new_node_id if not from_cache else cached_node_id
        return _taint_and_log_openai_result(result, file_name, line_no, from_cache, server_conn, any_input_tainted, input_taint, model, 'openai_v1', node_id_to_use, input_to_use=input_to_use)

    openai.ChatCompletion.create = patched_create

def v2_openai_patch(server_conn):
    # We need to patch `create` for every instance and cannot do it globally. 
    original_init = OpenAI.__init__

    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        original_create = self.responses.create

        def patched_create(*args, **kwargs):
            # Get model, input_text and LLM calls that produced them
            model = kwargs.get("model", args[0] if args else None)
            input = kwargs.get("input", args[1] if len(args) > 1 else None)
            taint_origins = get_taint_origins(input) + get_taint_origins(model)

            # Check if there's a cached / edited input/output
            input_to_use, output_to_use, node_id = CACHE.get_in_out(session_id, model, input)

            # Produce output
            if output_to_use is not None:
                # Use cached output. Convert json into OpenAI Response obj.
                result = json_to_response(output_to_use, "openai_v2")            
            else:
                # Call LLM
                new_kwargs = dict(kwargs)
                new_kwargs["input"] = input_to_use

                if len(args) == 1 and isinstance(args[0], Responses):
                    result = original_create(**new_kwargs)
                else:
                    result = original_create(*args, **new_kwargs)
                
                # Cache
                CACHE.cache_output(session_id, model, input_to_use, result, "openai_v2", node_id)

            # Send to server
            _send_graph_node_and_edges(server_conn=server_conn,
                                       node_id=node_id,
                                       input=input_to_use,
                                       output_obj=result,
                                       source_node_ids=taint_origins,
                                       model=model,
                                       api_type="openai_v2")

            # Wrap and return
            return taint_wrap(result, [node_id])
           
        self.responses.create = patched_create.__get__(self.responses, Responses)
    OpenAI.__init__ = new_init


# ===========================================================
# Patch function registry
# ===========================================================

CUSTOM_PATCH_FUNCTIONS = [
    v1_openai_patch,
    v2_openai_patch,
]
