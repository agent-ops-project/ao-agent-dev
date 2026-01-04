import inspect
from ao.runner.context_manager import get_session_id
from ao.common.constants import CERTAINTY_UNKNOWN
from ao.common.utils import send_to_server
from ao.common.logger import logger
from ao.runner.monkey_patching.api_parser import (
    get_model_name,
    func_kwargs_to_json_str,
    api_obj_to_json_str,
)

MAX_LABEL_LENGTH = 20
NO_LABEL = "No Label"


def sanitize_label(name: str) -> str:
    """
    Sanitize a model/tool name for display as a node label.
    - Take last part after "/" or ":"
    - Replace "_" with space
    - Return "No Label" if empty, malformed, or too long
    """
    if not name or name == "undefined":
        return NO_LABEL

    # Detect malformed input (XML tags or JSON)
    if "<" in name or "{" in name:
        logger.warning(f"[Label] Malformed name detected: {name[:50]}...")
        return NO_LABEL

    # Take last part after ":" or "/"
    if ":" in name:
        name = name.rsplit(":", 1)[-1]
    if "/" in name:
        name = name.rsplit("/", 1)[-1]

    # Replace underscores and hyphens with spaces, then title case
    name = name.replace("_", " ").replace("-", " ").title()

    # Too long means likely wrong
    if len(name) > MAX_LABEL_LENGTH:
        logger.warning(f"[Label] Name too long: {name[:50]}...")
        return NO_LABEL

    return name


# ===========================================================
# Generic wrappers for caching and server notification
# ===========================================================


def get_input_dict(func, *args, **kwargs):
    # Arguments are normalized to the function's parameter order.
    # func(a=5, b=2) and func(b=2, a=5) will result in same dict.

    # Try to get signature, handling "invalid method signature" error
    sig = None
    try:
        sig = inspect.signature(func)
    except ValueError as e:
        if "invalid method signature" in str(e):
            # This can happen with monkey-patched bound methods
            # Try to get the signature from the unbound method instead
            if hasattr(func, "__self__") and hasattr(func, "__func__"):
                try:
                    # Get the unbound function from the class
                    cls = func.__self__.__class__
                    func_name = func.__name__
                    unbound_func = getattr(cls, func_name)
                    sig = inspect.signature(unbound_func)

                    # For unbound methods, we need to include 'self' in the arguments
                    # when binding, so prepend the bound object as the first argument
                    args = (func.__self__,) + args
                except (AttributeError, TypeError):
                    # If we can't get the unbound signature, re-raise the original error
                    raise e
        else:
            # Re-raise other ValueError exceptions
            raise e

    if sig is None:
        raise ValueError("Could not obtain function signature")

    try:
        bound = sig.bind(*args, **kwargs)
    except TypeError:
        # Many APIs only accept kwargs
        bound = sig.bind(**kwargs)
    bound.apply_defaults()

    input_dict = {}
    for name, value in bound.arguments.items():
        if name == "self":
            continue
        param = sig.parameters[name]
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            input_dict.update(value)  # Flatten the captured extras
        else:
            input_dict[name] = value

    return input_dict


def send_graph_node_and_edges(node_id, input_dict, output_obj, source_node_ids, api_type):
    """Send graph node and edge updates to the server."""
    frame = inspect.currentframe()
    user_program_frame = inspect.getouterframes(frame)[2]
    line_no = user_program_frame.lineno
    file_name = user_program_frame.filename
    codeLocation = f"{file_name}:{line_no}"

    # Get strings to display in UI.
    input_string, attachments = func_kwargs_to_json_str(input_dict, api_type)
    output_string = api_obj_to_json_str(output_obj, api_type)
    model = get_model_name(input_dict, api_type)
    label = sanitize_label(model)

    # Send node
    node_msg = {
        "type": "add_node",
        "session_id": get_session_id(),
        "node": {
            "id": node_id,
            "input": input_string,
            "output": output_string,
            "border_color": CERTAINTY_UNKNOWN,
            "label": label,
            "codeLocation": codeLocation,
            "model": model,
            "attachments": attachments,
        },
        "incoming_edges": source_node_ids,
    }

    try:
        send_to_server(node_msg)
    except Exception as e:
        logger.error(f"Failed to send add_node: {e}")
