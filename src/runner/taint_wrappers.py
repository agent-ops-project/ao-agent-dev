import io
import inspect
import sys


class TaintWrapper:
    """
    A unified wrapper for arbitrary objects that tracks taint origins.

    This class wraps any object and tracks taint information while delegating
    most operations to AST transformation via exec_func. The wrapper only
    implements operations that cannot be intercepted by AST transformation,
    such as implicit Python operations like __bool__, __iter__, and __hash__.

    Most explicit operations (+, -, [], len(), etc.) are handled by the
    AST transformer which rewrites them as exec_func calls.

    Attributes:
        obj: The wrapped object (never modified)
        _taint_origin (list): List of taint origin identifiers for this wrapper
    """

    def __init__(self, obj, taint_origin=None, enable_persistence=None, root_wrapper=None):
        object.__setattr__(self, "obj", obj)
        if taint_origin is None:
            object.__setattr__(self, "_taint_origin", [])
        elif isinstance(taint_origin, (int, str)):
            object.__setattr__(self, "_taint_origin", [taint_origin])
        elif isinstance(taint_origin, (list, set)):
            object.__setattr__(self, "_taint_origin", list(taint_origin))
        else:
            raise TypeError(f"Unsupported taint_origin type: {type(taint_origin)}")

        # Auto-detect file objects if enable_persistence not specified
        if enable_persistence is None:
            enable_persistence = isinstance(obj, io.IOBase)

        object.__setattr__(self, "_enable_persistence", enable_persistence)
        if enable_persistence:
            object.__setattr__(self, "_line_no", 0)  # Track current line for DB operations
            object.__setattr__(self, "_session_id", self._get_current_session_id())

        # Store reference to root wrapper (or self if this is the root)
        object.__setattr__(
            self, "_root_wrapper", root_wrapper if root_wrapper is not None else self
        )

    def _get_current_session_id(self):
        """Get the current session ID from environment or context"""
        import os

        return os.environ.get("AGENT_COPILOT_SESSION_ID", None)

    def _unwrap_args(self, *args):
        """Unwrap tainted arguments and collect taint origins."""
        origins = set(object.__getattribute__(self, "_taint_origin"))
        unwrapped = []
        for arg in args:
            origins.update(get_taint_origins(arg))
            unwrapped.append(untaint_if_needed(arg))
        return unwrapped, list(origins)

    def _unwrap_kwargs(self, kwargs):
        """Unwrap tainted kwargs and collect taint origins."""
        origins = set(object.__getattribute__(self, "_taint_origin"))
        unwrapped = {}
        for key, val in kwargs.items():
            origins.update(get_taint_origins(val))
            unwrapped[key] = untaint_if_needed(val)
        return unwrapped, list(origins)

    def bound_access(self, name, *args, **kwargs):
        """
        Unified handler for both method calls and attribute access.

        This method is used by __getattr__ via functools.partial to create
        bound access that preserves __self__ = self (TaintWrapper). This allows
        exec_func to extract taint from the root wrapper via the partial.

        Always returns raw results - exec_func handles all taint wrapping.

        Args:
            name: The name of the attribute/method to access on self.obj
            *args: Arguments for method calls (empty for attribute access)
            **kwargs: Keyword arguments for method calls (empty for attribute access)

        Returns:
            For method calls: The result of calling the method (raw)
            For attribute access: The attribute value (raw)
        """
        obj = object.__getattribute__(self, "obj")
        result = getattr(obj, name)

        if callable(result) and (args or kwargs):
            # It's a method call - execute it and return raw result
            return result(*args, **kwargs)
        else:
            # It's attribute access - return raw attribute
            return result

    def __getattr__(self, name):
        """Delegate attribute access to wrapped object."""
        if name in (
            "obj",
            "_taint_origin",
            "_enable_persistence",
            "_line_no",
            "_session_id",
            "_root_wrapper",
        ):
            return object.__getattribute__(self, name)

        # Always return unified partial that carries root wrapper reference
        # This allows exec_func to extract taint from the root wrapper
        from functools import partial

        return partial(self.bound_access, name)

    def __setattr__(self, name, value):
        """Unwrap value and set on wrapped object."""
        if name in (
            "obj",
            "_taint_origin",
            "_enable_persistence",
            "_line_no",
            "_session_id",
            "_root_wrapper",
        ):
            object.__setattr__(self, name, value)
        else:
            obj = object.__getattribute__(self, "obj")
            unwrapped_value = untaint_if_needed(value)
            setattr(obj, name, unwrapped_value)

    def __getitem__(self, key):
        """Get item from wrapped object and wrap result."""
        obj = object.__getattribute__(self, "obj")
        taint_origin = object.__getattribute__(self, "_taint_origin")
        root_wrapper = object.__getattribute__(self, "_root_wrapper")
        unwrapped_key = untaint_if_needed(key)
        result = obj[unwrapped_key]
        if taint_origin:
            return taint_wrap(result, taint_origin=taint_origin, root_wrapper=root_wrapper)
        return result

    def __setitem__(self, key, value):
        """Unwrap key and value, set on wrapped object."""
        obj = object.__getattribute__(self, "obj")
        unwrapped_key = untaint_if_needed(key)
        unwrapped_value = untaint_if_needed(value)
        obj[unwrapped_key] = unwrapped_value

    def __delitem__(self, key):
        """Delete item from wrapped object."""
        obj = object.__getattribute__(self, "obj")
        unwrapped_key = untaint_if_needed(key)
        del obj[unwrapped_key]

    def __call__(self, *args, **kwargs):
        """Unwrap args/kwargs, call wrapped object, wrap result."""
        obj = object.__getattribute__(self, "obj")
        root_wrapper = object.__getattribute__(self, "_root_wrapper")
        unwrapped_args, combined_origins = self._unwrap_args(*args)
        unwrapped_kwargs, kwargs_origins = self._unwrap_kwargs(kwargs)
        combined_origins = list(set(combined_origins) | set(kwargs_origins))

        result = obj(*unwrapped_args, **unwrapped_kwargs)

        if combined_origins:
            return taint_wrap(result, taint_origin=combined_origins, root_wrapper=root_wrapper)
        return result

    def __repr__(self):
        obj = object.__getattribute__(self, "obj")
        taint_origin = object.__getattribute__(self, "_taint_origin")
        return f"TaintWrapper({repr(obj)}, taint_origin={taint_origin})"

    def __str__(self):
        obj = object.__getattribute__(self, "obj")
        return str(obj)

    def __bool__(self):
        obj = object.__getattribute__(self, "obj")
        return bool(obj)

    def __iter__(self):
        obj = object.__getattribute__(self, "obj")
        taint_origin = object.__getattribute__(self, "_taint_origin")
        root_wrapper = object.__getattribute__(self, "_root_wrapper")
        for item in obj:
            if taint_origin:
                yield taint_wrap(item, taint_origin=taint_origin, root_wrapper=root_wrapper)
            else:
                yield item

    def __hash__(self):
        obj = object.__getattribute__(self, "obj")
        return hash(obj)

    def __len__(self):
        obj = object.__getattribute__(self, "obj")
        return len(obj)

    def __index__(self):
        """Allow TaintWrapper to be used as an index/slice."""
        obj = object.__getattribute__(self, "obj")
        return obj.__index__()

    def __reduce__(self):
        """For pickle/copy operations, return the wrapped object."""
        obj = object.__getattribute__(self, "obj")
        return (lambda x: x, (obj,))

    def __copy__(self):
        """For shallow copy, return wrapped object."""
        obj = object.__getattribute__(self, "obj")
        return obj

    def __deepcopy__(self, memo):
        """For deep copy, return wrapped object."""
        import copy

        obj = object.__getattribute__(self, "obj")
        return copy.deepcopy(obj, memo)

    def __enter__(self):
        """Support context manager protocol by delegating to wrapped object."""
        obj = object.__getattribute__(self, "obj")
        return obj.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support context manager protocol by delegating to wrapped object."""
        obj = object.__getattribute__(self, "obj")
        return obj.__exit__(exc_type, exc_val, exc_tb)

    # Make this object more transparent to type checkers
    @property
    def __class__(self):
        obj = object.__getattribute__(self, "obj")
        return obj.__class__

    @__class__.setter
    def __class__(self, value):
        obj = object.__getattribute__(self, "obj")
        obj.__class__ = value


def untaint_if_needed(val, _seen=None):
    """
    Recursively extract clean values from tainted objects.

    Args:
        val: The value to untaint
        _seen: Set to track visited objects (prevents circular references)

    Returns:
        The untainted version of the value
    """
    if _seen is None:
        _seen = set()

    obj_id = id(val)
    if obj_id in _seen:
        return val
    _seen.add(obj_id)

    # Handle TaintWrapper - return the wrapped object
    if isinstance(val, TaintWrapper):
        wrapped = object.__getattribute__(val, "obj")
        return untaint_if_needed(wrapped, _seen)

    # Handle nested data structures by creating clean copies ONLY if they contain taint
    if isinstance(val, dict):
        # Check if any values contain taint before creating a new dict
        tainted_keys = [k for k, v in val.items() if get_taint_origins(v)]
        if tainted_keys:
            return {k: untaint_if_needed(v, _seen) for k, v in val.items()}
        else:
            return val  # Return original dict if no taint
    elif isinstance(val, list):
        # Check if any items contain taint before creating a new list
        tainted_indices = [i for i, item in enumerate(val) if get_taint_origins(item)]
        if tainted_indices:
            return [untaint_if_needed(item, _seen) for item in val]
        else:
            return val  # Return original list if no taint
    elif isinstance(val, tuple):
        # Check if any items contain taint before creating a new tuple
        has_taint = any(get_taint_origins(item) for item in val)
        if has_taint:
            return tuple(untaint_if_needed(item, _seen) for item in val)
        else:
            return val  # Return original tuple if no taint
    elif isinstance(val, set):
        # Check if any items contain taint before creating a new set
        has_taint = any(get_taint_origins(item) for item in val)
        if has_taint:
            return {untaint_if_needed(item, _seen) for item in val}
        else:
            return val  # Return original set if no taint

    # For custom objects, check if they contain any tainted attributes
    # Only process objects that have a __dict__ (i.e., custom classes with attributes)
    if hasattr(val, "__dict__"):
        obj_dict = val.__dict__

        # Check each attribute for taint (including nested taint in collections)
        tainted_attrs = []
        for key, value in obj_dict.items():
            # Check if the value itself is wrapped OR contains tainted elements
            if get_taint_origins(value, _seen.copy()):
                tainted_attrs.append(key)

        if tainted_attrs:
            # Create a shallow copy and untaint all attributes
            import copy

            new_obj = copy.copy(val)
            for key, value in obj_dict.items():
                if key in tainted_attrs:
                    pass
                untainted_value = untaint_if_needed(value, _seen)
                setattr(new_obj, key, untainted_value)
            return new_obj
        else:
            return val  # Return original object if no taint

    # Return all other objects as-is (primitives, types, modules, etc.)
    return val


def is_wrapped(obj):
    """
    Check if an object has taint information.

    Args:
        obj: The object to check for taint

    Returns:
        True if the object has taint origins, False otherwise
    """
    try:
        # Use object.__getattribute__ to avoid triggering __getattr__ on proxy objects
        taint_origin = object.__getattribute__(obj, "_taint_origin")
        return bool(taint_origin)
    except AttributeError:
        return False


def get_taint_origins(val, _seen=None):
    """
    Extract all taint origins from a value and its nested structures.

    Args:
        val: The value to extract taint origins from
        _seen: Set to track visited objects (prevents circular references)

    Returns:
        List of taint origins found in the value
    """
    if _seen is None:
        _seen = set()

    obj_id = id(val)
    if obj_id in _seen:
        return []
    _seen.add(obj_id)

    # Check if object is TaintWrapper or has _taint_origin attribute
    try:
        taint_origin = object.__getattribute__(val, "_taint_origin")
        if taint_origin:
            return list(taint_origin) if isinstance(taint_origin, (list, set)) else [taint_origin]
    except AttributeError:
        pass

    # Check if object is a partial with root wrapper reference
    try:
        from functools import partial

        if isinstance(val, partial) and hasattr(val, "func") and hasattr(val.func, "__self__"):
            wrapper = val.func.__self__
            # Check if the wrapper has a root_wrapper reference
            if hasattr(wrapper, "_root_wrapper"):
                root_wrapper = object.__getattribute__(wrapper, "_root_wrapper")
                root_taint = object.__getattribute__(root_wrapper, "_taint_origin")
                if root_taint:
                    return list(root_taint) if isinstance(root_taint, (list, set)) else [root_taint]
            # Also check the immediate wrapper's taint
            elif hasattr(wrapper, "_taint_origin"):
                taint_origin = object.__getattribute__(wrapper, "_taint_origin")
                if taint_origin:
                    return (
                        list(taint_origin)
                        if isinstance(taint_origin, (list, set))
                        else [taint_origin]
                    )
    except (AttributeError, ImportError):
        pass

    # Recursively check nested data structures
    origins = set()

    if isinstance(val, (list, tuple, set)):
        for item in val:
            origins.update(get_taint_origins(item, _seen))
    elif isinstance(val, dict):
        for value in val.values():
            origins.update(get_taint_origins(value, _seen))

    return list(origins)


def taint_wrap(obj, taint_origin=[], root_wrapper=None):
    """
    Wrap an object with taint information.

    Args:
        obj: The object to wrap with taint information
        taint_origin: The taint origin(s) to assign to the wrapped object
        root_wrapper: Reference to the root wrapper (for nested wrapping)

    Returns:
        The wrapped object with taint information, or the original object if
        it shouldn't be wrapped
    """
    # Don't wrap objects that are already tainted
    if is_wrapped(obj):
        return obj

    # Don't wrap booleans or None
    if isinstance(obj, bool) or obj is None:
        return obj

    # Don't wrap types, functions, or modules
    if isinstance(obj, type) or inspect.isfunction(obj) or inspect.ismodule(obj):
        return obj

    # Don't wrap enums
    if hasattr(obj, "__class__"):
        import enum

        if isinstance(obj, enum.Enum):
            return obj

    # Special handling for file objects - enable persistence
    if isinstance(obj, io.IOBase):
        return TaintWrapper(
            obj, taint_origin=taint_origin, enable_persistence=True, root_wrapper=root_wrapper
        )

    # Wrap everything else with TaintWrapper
    # This includes: primitives (str, int, float), collections (list, dict, tuple),
    # and custom objects. TaintWrapper handles all of these transparently.
    return TaintWrapper(obj, taint_origin=taint_origin, root_wrapper=root_wrapper)
