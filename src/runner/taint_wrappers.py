import io
import inspect
import threading
from typing import Any, Set
from types import ModuleType
from enum import Enum
from aco.server.database_manager import DB
from aco.common.logger import logger


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

    def __init__(self, obj, taint_origin=None, enable_persistence=None):
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

    def bound_method(self, method_name, *args, **kwargs):
        """
        Call a method on the wrapped object with the given arguments.

        This method retrieves the named method from self.obj and calls it with
        the provided arguments. It's used by __getattr__ via functools.partial
        to create bound methods that preserve __self__ = self (TaintWrapper).

        When exec_func receives a call like obj.method(args), it can extract taint
        from func.__self__ (which is self, the TaintWrapper) and combine it with
        taint from the arguments.

        Args:
            method_name: The name of the method to call on self.obj
            *args: Positional arguments to pass to the method
            **kwargs: Keyword arguments to pass to the method

        Returns:
            The result of calling the method on self.obj
        """
        obj = object.__getattribute__(self, "obj")
        method = getattr(obj, method_name)
        return method(*args, **kwargs)

    def __getattr__(self, name):
        """Delegate attribute access to wrapped object."""
        if name in ("obj", "_taint_origin", "_enable_persistence", "_line_no", "_session_id"):
            return object.__getattribute__(self, name)
        obj = object.__getattribute__(self, "obj")
        result = getattr(obj, name)

        # If it's callable (a method), return via partial to preserve __self__ = self
        # This allows exec_func to extract taint from the TaintWrapper
        if callable(result):
            from functools import partial

            return partial(self.bound_method, name)

        # For non-callable attributes, wrap with taint information
        taint_origin = object.__getattribute__(self, "_taint_origin")
        if taint_origin:
            return taint_wrap(result, taint_origin=taint_origin)
        return result

    def __setattr__(self, name, value):
        """Unwrap value and set on wrapped object."""
        if name in ("obj", "_taint_origin", "_enable_persistence", "_line_no", "_session_id"):
            object.__setattr__(self, name, value)
        else:
            obj = object.__getattribute__(self, "obj")
            unwrapped_value = untaint_if_needed(value)
            setattr(obj, name, unwrapped_value)

    def __getitem__(self, key):
        """Get item from wrapped object and wrap result."""
        obj = object.__getattribute__(self, "obj")
        taint_origin = object.__getattribute__(self, "_taint_origin")
        unwrapped_key = untaint_if_needed(key)
        result = obj[unwrapped_key]
        if taint_origin:
            return taint_wrap(result, taint_origin=taint_origin)
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
        unwrapped_args, combined_origins = self._unwrap_args(*args)
        unwrapped_kwargs, kwargs_origins = self._unwrap_kwargs(kwargs)
        combined_origins = list(set(combined_origins) | set(kwargs_origins))

        result = obj(*unwrapped_args, **unwrapped_kwargs)

        if combined_origins:
            return taint_wrap(result, taint_origin=combined_origins)
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
        return iter(obj)

    def __hash__(self):
        obj = object.__getattribute__(self, "obj")
        return hash(obj)

    def get_raw(self):
        """Return the wrapped object."""
        obj = object.__getattribute__(self, "obj")
        if hasattr(obj, "get_raw"):
            return obj.get_raw()
        return obj

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


# Utility functions
def safe_update_set(target_set: Set[Any], obj: Any) -> Set[Any]:
    """
    Safely update a set with items from an iterable, skipping unhashable items.

    This function attempts to add items from an iterable to a target set,
    gracefully handling TypeError exceptions that occur when trying to add
    unhashable items (like AST nodes, complex objects, etc.).

    Args:
        target_set: The set to update with new items
        obj: An iterable containing items to add to the set

    Returns:
        The updated target set

    Note:
        This function modifies the target_set in place and also returns it.
        Unhashable items are silently skipped to prevent crashes during
        taint origin extraction from complex nested objects.
    """
    try:
        target_set.update(set(obj))
    except TypeError:
        # Skip unhashable items like AST nodes, complex objects, etc.
        pass
    return target_set


def untaint_if_needed(val, _seen=None):
    """
    Recursively remove taint from objects and nested data structures.

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

    # Handle TaintWrapper wrapper - return the wrapped object directly
    if isinstance(val, TaintWrapper):
        wrapped = object.__getattribute__(val, "obj")
        # Mark wrapped object as seen to prevent it from being re-processed
        _seen.add(id(wrapped))
        if hasattr(wrapped, "get_raw"):
            return wrapped.get_raw()
        return wrapped

    # If object has get_raw method (tainted), use it
    if hasattr(val, "get_raw"):
        raw_val = val.get_raw()
        return untaint_if_needed(raw_val, _seen)

    # Handle nested data structures
    if isinstance(val, dict):
        return {k: untaint_if_needed(v, _seen) for k, v in val.items()}
    elif isinstance(val, (list, tuple)):
        result = [untaint_if_needed(item, _seen) for item in val]
        return tuple(result) if isinstance(val, tuple) else result
    elif isinstance(val, set):
        return {untaint_if_needed(item, _seen) for item in val}
    elif isinstance(val, Enum):
        return val
    elif isinstance(val, ModuleType):
        return val
    elif isinstance(
        val,
        (
            threading.Lock,
            threading._CRLock,
            threading.Condition,
            threading.Thread,
            threading.Semaphore,
            threading.BoundedSemaphore,
            threading.Event,
            threading.Barrier,
            threading.Timer,
            threading.local,
        ),
    ):
        return val  # Never modify threading primitives
    elif hasattr(val, "__dict__") and not isinstance(val, type):
        untainted = {}  # avoid mods while iterating over same thing
        for attr, value in val.__dict__.items():
            untainted[attr] = untaint_if_needed(value, _seen)
        for attr, value in untainted.items():
            val.__dict__[attr] = value
        return val
    elif hasattr(val, "__slots__"):
        # Handle objects with __slots__ (some objects have __slots__ but no __dict__).
        untainted = {}  # avoid mods while iterating over same thing
        for slot in val.__slots__:
            if hasattr(val, slot):
                untainted[slot] = untaint_if_needed(getattr(val, slot), _seen)
        for slot, value in untainted.items():
            try:
                setattr(val, slot, value)
            except Exception:
                logger.error(f"[TaintWrapper] error untainting {val}")
        return val

    # Return primitive types and other objects as-is
    return val


def is_tainted(obj):
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
        return bool(taint_origin) and bool(get_taint_origins(obj))
    except AttributeError:
        return False


def get_taint_origins(val, _seen=None, _depth=0, _max_depth=100):
    """
    Return a flat list of all taint origins for the input, including nested objects.

    Args:
        val: The value to extract taint origins from
        _seen: Set to track visited objects (prevents circular references)
        _depth: Current recursion depth
        _max_depth: Maximum recursion depth (default: 100)

    Returns:
        List of taint origins found in the value and its nested structures
    """
    if _depth > _max_depth:
        return []

    if _seen is None:
        _seen = set()

    obj_id = id(val)
    if obj_id in _seen:
        return []
    _seen.add(obj_id)

    # Check if object has direct taint
    # Use object.__getattribute__ to avoid triggering __getattr__ on proxy objects
    try:
        taint_origin = object.__getattribute__(val, "_taint_origin")
        if taint_origin is not None:
            if not isinstance(taint_origin, (list, set)):
                taint_origin = [taint_origin]
            return list(taint_origin)
    except AttributeError:
        # Object doesn't have _taint_origin, continue with other checks
        pass

    # Handle nested data structures
    origins = set()

    if isinstance(val, (list, tuple, set)):
        for v in val:
            origins = safe_update_set(origins, get_taint_origins(v, _seen, _depth + 1, _max_depth))
    elif isinstance(val, dict):
        # Create a list of values to avoid dictionary changed size during iteration
        for v in list(val.values()):
            origins = safe_update_set(origins, get_taint_origins(v, _seen, _depth + 1, _max_depth))
    elif isinstance(val, Enum):
        return origins
    elif hasattr(val, "__dict__") and not isinstance(val, type):
        # Handle custom objects with attributes
        # Create a list of items to avoid dictionary changed size during iteration
        for attr_name, attr_val in list(val.__dict__.items()):
            if attr_name.startswith("_"):
                continue
            origins = safe_update_set(
                origins, get_taint_origins(attr_val, _seen, _depth + 1, _max_depth)
            )
    elif hasattr(val, "__slots__"):
        # Handle objects with __slots__
        for slot in val.__slots__:
            try:
                # Use object.__getattribute__ to avoid triggering __getattr__ on proxy objects
                slot_val = object.__getattribute__(val, slot)
                origins = safe_update_set(
                    origins, get_taint_origins(slot_val, _seen, _depth + 1, _max_depth)
                )
            except AttributeError:
                # Slot doesn't exist on this instance, skip it
                continue

    return list(origins)




def taint_wrap(
    obj, taint_origin=None, inplace=False, _seen=None, _depth: int = 0, _max_depth: int = 10
):
    """
    Recursively wrap an object and its nested structures with taint information.

    This function takes any object and wraps it with the unified TaintWrapper
    while preserving the original structure. It handles nested data structures
    like lists, dictionaries, and custom objects.

    Args:
        obj: The object to wrap with taint information
        taint_origin: The taint origin(s) to assign to the wrapped object
        inplace: Should the object be modified inplace (if possible)
        _seen: Set to track visited objects (prevents circular references)
        _depth: Keep track of depth to avoid to deep recursion

    Returns:
        The wrapped object with taint information, or the original object if
        no appropriate tainted wrapper exists
    """
    if _depth > _max_depth:
        return obj

    # Handle primitive types that should be wrapped individually
    # (strings, ints, floats are wrapped separately to avoid _seen issues)
    if isinstance(obj, (str, int, float)):
        return TaintWrapper(obj, taint_origin=taint_origin)
    
    if isinstance(obj, bool):
        # Don't wrap booleans, return as-is
        return obj

    if _seen is None:
        _seen = set()
    obj_id = id(obj)
    if obj_id in _seen:
        return obj
    _seen.add(obj_id)

    if is_tainted(obj):
        return obj
    if hasattr(obj, "__class__") and hasattr(obj.__class__, "__mro__"):
        import enum

        if issubclass(obj.__class__, enum.Enum):
            return obj  # Don't wrap any enum members (including StrEnum)

    if isinstance(obj, (dict, list, tuple)) and not isinstance(obj, (str, bytes, bytearray)):
        # For collections, wrap the entire collection in TaintWrapper
        # The nested items will be wrapped when accessed through __getitem__
        return TaintWrapper(obj, taint_origin=taint_origin)
    if isinstance(obj, io.IOBase):
        # File objects get TaintWrapper with persistence enabled
        return TaintWrapper(obj, taint_origin=taint_origin, enable_persistence=True)

    is_builtin = obj.__class__.__module__ == "builtins"
    is_function = inspect.isfunction(obj)
    if is_builtin or is_function:
        return obj

    # For all other objects, wrap them in TaintWrapper as a fallback
    # This includes:
    # - Objects with __dict__ (custom classes)
    # - Objects with __slots__ (some built-in types)
    # - C extension objects like re.Match that have neither __dict__ nor __slots__
    # TaintWrapper will handle all of these transparently
    return TaintWrapper(obj, taint_origin=taint_origin)
