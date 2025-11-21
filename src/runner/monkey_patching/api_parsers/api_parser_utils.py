from typing import Any


def _deep_serialize(obj: Any) -> Any:
    """Recursively serialize objects to JSON-compatible format."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, dict):
        return {k: _deep_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_deep_serialize(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        # Convert object to dict and recursively serialize
        result = {}
        for k, v in vars(obj).items():
            result[k] = _deep_serialize(v)
        return result
    else:
        return str(obj)
