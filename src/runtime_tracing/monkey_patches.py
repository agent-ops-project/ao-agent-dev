import asyncio
import inspect
import json
import threading
import functools
import uuid
from runtime_tracing.cache_manager import CACHE
from common.logging_config import setup_logging
logger = setup_logging()
from common.utils import extract_key_args
from runtime_tracing.taint_wrappers import taint_wrap, get_origin_nodes


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

SESSION_ID = None

def set_session_id(session_id):
    """Set the global session ID for graph tracking."""
    global SESSION_ID
    SESSION_ID = session_id
    logger.info(f"Session ID set to: {SESSION_ID}")


# ===========================================================
# Graph tracking utilities
# ===========================================================

def _send_graph_node_and_edges(server_conn, node_id, input_obj, output, source_node_ids):
    """Send graph node and edge updates to the server."""
    # Send node
    node_msg = {
        "type": "addNode",
        "session_id": SESSION_ID,
        "node": {
            "id": node_id,
            "input": input_obj,
            "output": str(output),
            "border_color": "#00c542",
            "label": "Label"
        }
    }
    try:
        server_conn.sendall((json.dumps(node_msg) + "\n").encode("utf-8"))
    except Exception as e:
        logger.warning(f"Failed to send addNode: {e}")

    # Send edges for each source
    for src in source_node_ids:
        if src != node_id:
            edge_msg = {
                "type": "addEdge",
                "session_id": SESSION_ID,
                "edge": {"source": src, "target": node_id}
            }
            try:
                server_conn.sendall((json.dumps(edge_msg) + "\n").encode("utf-8"))
            except Exception as e:
                logger.warning(f"Failed to send addEdge: {e}")


def _extract_source_node_ids(taint):
    """Extract source node IDs from taint structure."""
    if isinstance(taint, list):
        # New taint structure: list of node IDs directly
        return [str(node_id) for node_id in taint if node_id is not None]
    if isinstance(taint, dict):
        # Check for new taint structure with origin_nodes
        if 'origin_nodes' in taint:
            return [str(node_id) for node_id in taint['origin_nodes'] if node_id is not None]
        # Check for old taint structure with node_id
        if 'node_id' in taint:
            return [str(taint['node_id'])]
        # Recursively check nested dicts
        ids = []
        for v in taint.values():
            ids.extend(_extract_source_node_ids(v))
        return ids
    if isinstance(taint, str):
        # Single node ID as string
        return [taint] if taint else []
    return []


def _taint_and_log_openai_result(result, input_obj, file_name, line_no, from_cache, server_conn, any_input_tainted, input_taint):
    """
    Shared logic for tainting, logging, and sending server messages for OpenAI LLM calls.
    Also constructs and sends LLM call graph updates.
    """
    node_id = str(uuid.uuid4())
    
    # Extract source node IDs from input taint
    source_node_ids = _extract_source_node_ids(input_taint)
    
    if any_input_tainted:
        logger.warning("OpenAI called with tainted input!")
    
    # Wrap output as new taint source
    result = taint_wrap(result, {'origin_nodes': [node_id]})

    # Get thread and task info
    thread_id = threading.get_ident()
    try:
        task_id = id(asyncio.current_task())
    except Exception:
        task_id = None

    # Send call message to server
    message = {
        "type": "call",
        "input": input_obj,
        "output": str(result),
        "file": file_name,
        "line": line_no,
        "thread": thread_id,
        "task": task_id,
        "from_cache": from_cache,
        "tainted": any_input_tainted,
        "taint_label": {'node_id': node_id, 'origin': f'{file_name}:{line_no}'},
        "node_id": node_id,
    }
    try:
        server_conn.sendall((json.dumps(message) + "\n").encode("utf-8"))
    except Exception:
        pass  # best-effort only

    # Send graph updates
    _send_graph_node_and_edges(server_conn, node_id, input_obj, result, source_node_ids)

    return result


# ===========================================================
# OpenAI API patches
# ===========================================================

def v1_openai_patch(server_conn):
    """
    Patch openai.ChatCompletion.create (v1/classic API) to track taint and send call details.
    """
    try:
        import openai
    except ImportError:
        return  # If openai isn't available, do nothing

    original_create = getattr(openai.ChatCompletion, "create", None)
    if original_create is None:
        return

    def patched_create(*args, **kwargs):
        # Get caller location
        frame = inspect.currentframe()
        caller = frame.f_back if frame else None
        file_name = caller.f_code.co_filename if caller else "<unknown>"
        line_no = caller.f_lineno if caller else -1

        # Check cache
        cached_out = CACHE.get_output(file_name, line_no, original_create, args, kwargs)
        from_cache = cached_out is not None
        if from_cache:
            result = cached_out
        else:
            result = original_create(*args, **kwargs)
            CACHE.cache_output(result, file_name, line_no, original_create, args, kwargs)

        # Check for taint in inputs
        def check_taint(val):
            if get_origin_nodes(val):
                return get_origin_nodes(val)
            if isinstance(val, (list, tuple)):
                return [check_taint(v) for v in val]
            if isinstance(val, dict):
                return {k: check_taint(v) for k, v in val.items()}
            return None
        
        input_obj = kwargs.get("messages", args[0] if args else None)
        input_taint = check_taint(input_obj)
        any_input_tainted = input_taint is not None and input_taint != {} and input_taint != []
        
        return _taint_and_log_openai_result(result, input_obj, file_name, line_no, from_cache, server_conn, any_input_tainted, input_taint)

    openai.ChatCompletion.create = patched_create


def v2_openai_patch(server_conn):
    """
    Patch OpenAI().responses.create (v2/client API) to track taint and send call details.
    """
    try:
        from openai import OpenAI
        from openai.resources.responses import Responses
    except ImportError:
        logger.warning("Could not import OpenAI or Responses for patching.")
        return

    original_init = OpenAI.__init__

    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        original_create = self.responses.create
        
        def patched_create(*args, **kwargs):
            # Get caller location
            frame = inspect.currentframe()
            caller = frame.f_back if frame else None
            file_name = caller.f_code.co_filename if caller else "<unknown>"
            line_no = caller.f_lineno if caller else -1

            # Extract cache key arguments
            cache_key_args = extract_key_args(original_create, args, kwargs, ["model", "input"])
            model, input_text = cache_key_args

            # Check cache
            cached_out = CACHE.get_output(file_name, line_no, original_create, cache_key_args, {})
            from_cache = cached_out is not None
            if from_cache:
                result = cached_out
            else:
                if len(args) == 1 and isinstance(args[0], Responses):
                    result = original_create(**kwargs)
                else:
                    result = original_create(*args, **kwargs)
                CACHE.cache_output(result, file_name, line_no, original_create, cache_key_args, {})

            # Check for taint in inputs
            def check_taint(val):
                if get_origin_nodes(val):
                    return get_origin_nodes(val)
                if isinstance(val, (list, tuple)):
                    return [check_taint(v) for v in val]
                if isinstance(val, dict):
                    return {k: check_taint(v) for k, v in val.items()}
                return None
            
            input_obj = kwargs.get("input", args[1] if len(args) > 1 else None)
            input_taint = check_taint(input_obj)
            any_input_tainted = input_taint is not None and input_taint != {} and input_taint != []
            
            return _taint_and_log_openai_result(result, input_obj, file_name, line_no, from_cache, server_conn, any_input_tainted, input_taint)
        
        self.responses.create = patched_create.__get__(self.responses, Responses)
    
    OpenAI.__init__ = new_init


# ===========================================================
# Patch function registry
# ===========================================================

CUSTOM_PATCH_FUNCTIONS = [
    v1_openai_patch,
    v2_openai_patch,
]
