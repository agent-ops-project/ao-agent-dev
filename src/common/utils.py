import os
import inspect


def rel_path_to_abs(abs_file_path, rel_to_file):
    """
    Use __file__ as first argumante (abs_fil_path).
    Then use "agent-copilot/foo/bar.json" if your path is relative to the repo root.
    or just whatever if it's relative to the file (e.g., "../foo/bar.json")
    """
    # Normalize rel_to_file
    rel_to_file = os.path.normpath(rel_to_file)

    if rel_to_file.startswith("agent-copilot" + os.sep) or rel_to_file == "agent-copilot":
        # Assume project root is one of the parent directories containing "agent-copilot"
        current = abs_file_path
        while True:
            current = os.path.dirname(current)
            if os.path.basename(current) == "agent-copilot":
                project_root = current
                break
            if current == os.path.dirname(current):  # Reached filesystem root
                raise ValueError("Could not find 'agent-copilot' project root.")
        return os.path.abspath(os.path.join(project_root, os.path.relpath(rel_to_file, "agent-copilot")))
    else:
        # Treat as relative to the current file's directory
        return os.path.abspath(os.path.join(os.path.dirname(abs_file_path), rel_to_file))


def extract_key_args(fn, args, kwargs, key_names):
    """
    Robustly extract key arguments (by name) from a function call, handling positional, keyword, and default values.
    Returns a tuple of values for the requested key_names.
    """
    sig = inspect.signature(fn)
    try:
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
    except Exception as e:
        # Fallback: try to get from kwargs only
        return tuple(kwargs.get(k) for k in key_names)
    return tuple(bound.arguments.get(k) for k in key_names)
