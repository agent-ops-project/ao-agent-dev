from aco.runner.taint_wrappers import TaintWrapper, get_taint_origins, untaint_if_needed, taint_wrap
from inspect import getsourcefile, iscoroutinefunction
from aco.common.utils import get_aco_py_files


def _unified_taint_string_operation(operation_func, *inputs):
    """
    Unified helper for all taint-aware string operations.

    Args:
        operation_func: Function that performs the string operation
        *inputs: All inputs that may contain taint

    Returns:
        Result with taint information preserved
    """
    # Collect taint origins from all inputs
    all_origins = set()
    for inp in inputs:
        if isinstance(inp, (tuple, list)):
            # Handle tuple/list inputs (like values in % formatting)
            for item in inp:
                all_origins.update(get_taint_origins(item))
        elif isinstance(inp, dict):
            # Handle dict inputs (like kwargs in .format())
            for value in inp.values():
                all_origins.update(get_taint_origins(value))
        else:
            # Handle single values
            all_origins.update(get_taint_origins(inp))

    # Call the operation function with untainted inputs
    result = operation_func(*[untaint_if_needed(inp) for inp in inputs])

    # Return tainted result if any origins exist
    if all_origins:
        return TaintWrapper(result, list(all_origins))
    return result


def taint_fstring_join(*args):
    """Taint-aware replacement for f-string concatenation."""

    def join_operation(*unwrapped_args):
        return "".join(str(arg) for arg in unwrapped_args)

    return _unified_taint_string_operation(join_operation, *args)


def taint_format_string(format_string, *args, **kwargs):
    """Taint-aware replacement for .format() string method calls."""

    def format_operation(unwrapped_format_string, *unwrapped_args, **unwrapped_kwargs):
        return unwrapped_format_string.format(*unwrapped_args, **unwrapped_kwargs)

    return _unified_taint_string_operation(format_operation, format_string, args, kwargs)


def taint_percent_format(format_string, values):
    """Taint-aware replacement for % string formatting operations."""

    def percent_operation(unwrapped_format_string, unwrapped_values):
        return unwrapped_format_string % unwrapped_values

    return _unified_taint_string_operation(percent_operation, format_string, values)


def taint_open(*args, **kwargs):
    """Taint-aware replacement for open() with database persistence."""
    # Extract filename for default taint origin
    if args and len(args) >= 1:
        filename = args[0]
    else:
        filename = kwargs.get("file") or kwargs.get("filename")

    # Call the original open
    file_obj = open(*args, **kwargs)

    # Create default taint origin from filename
    default_taint = f"file:{filename}" if filename else "file:unknown"

    # Return TaintWrapper with persistence enabled
    return TaintWrapper(file_obj, taint_origin=[default_taint], enable_persistence=True)


def _is_user_function(func):
    """
    Check if function is user code or third-party code.

    Handles decorated functions by unwrapping via __wrapped__ attribute.
    """
    # Get user files from the pre-computed singleton
    from aco.common.utils import MODULES_TO_FILES

    user_py_files = list(MODULES_TO_FILES.values()) + get_aco_py_files()

    if not user_py_files:
        # No user files found, must be third-party
        return False

    # Strategy 1: Direct source file check (handles undecorated functions)
    try:
        source_file = getsourcefile(func)
    except TypeError:
        # Built-in function or function without source file
        return False

    if source_file and source_file in user_py_files:
        return True

    # Strategy 2: Check __wrapped__ attribute (functools.wraps pattern)
    # This handles most well-behaved decorators including @retry, @lru_cache, etc.
    current_func = func
    max_unwrap_depth = 10  # Prevent infinite loops
    depth = 0

    while hasattr(current_func, "__wrapped__") and depth < max_unwrap_depth:
        current_func = current_func.__wrapped__
        depth += 1

        try:
            source_file = getsourcefile(current_func)
            if source_file and source_file in user_py_files:
                return True
        except TypeError:
            return False

    return False


def _is_type_annotation_access(obj, key):
    """
    Detect if this is a type annotation rather than runtime access.

    Args:
        obj: The object being subscripted
        key: The key/index being accessed (unused)

    Returns:
        True if this looks like a type annotation (e.g., Dict[str, int])
    """
    # Check 1: Is the object a type/class rather than an instance?
    if isinstance(obj, type):
        return True

    # Check 2: Is it from typing module?
    if hasattr(obj, "__module__") and obj.__module__ == "typing":
        return True

    # Check 3: Is it a generic alias (Python 3.9+)?
    if hasattr(obj, "__origin__"):  # GenericAlias objects like list[int]
        return True

    # Check 4: Does it support generic subscripting (__class_getitem__)?
    if hasattr(obj, "__class_getitem__"):
        # Make sure it's not a regular dict/list/set with custom __class_getitem__
        obj_type_name = type(obj).__name__
        if obj_type_name in {"dict", "list", "tuple", "set"}:
            # This is a runtime collection instance, not a type
            return False
        # Likely a generic type that supports subscripting
        return True

    # Check 5: Common type constructs by name
    if hasattr(obj, "__name__"):
        type_names = {"Dict", "List", "Tuple", "Set", "Optional", "Union", "Any", "Callable"}
        if obj.__name__ in type_names:
            return True

    return False


def exec_func(func, args, kwargs):
    """
    Execute function with taint tracking.

    User code: called directly
    Third-party code: arguments untainted, results tainted via TAINT_ESCROW
    """
    if iscoroutinefunction(func):

        async def wrapper():
            # User code: call directly
            if _is_user_function(func):
                try:
                    return await func(*args, **kwargs)
                except:
                    # Fall back to third-party handling
                    pass

            # Third-party code: collect taint from arguments
            all_origins = set()
            all_origins.update(get_taint_origins(args))
            all_origins.update(get_taint_origins(kwargs))

            # Include taint from bound methods
            bound_self = None
            root_wrapper = None
            if hasattr(func, "__self__"):
                bound_self = func.__self__
            elif hasattr(func, "func") and hasattr(func.func, "__self__"):
                bound_self = func.func.__self__

            if bound_self is not None:
                all_origins.update(get_taint_origins(bound_self))
                # Check if bound_self has root wrapper reference
                if hasattr(bound_self, "_root_wrapper"):
                    root_wrapper = object.__getattribute__(bound_self, "_root_wrapper")

            # Special handling for file operations with persistence
            if bound_self and getattr(bound_self, "_enable_persistence", False):
                return _handle_persistent_file_operation(bound_self, func, args, kwargs)

            # Update root wrapper with collected taint if available
            if root_wrapper is not None and all_origins:
                try:
                    current_taint = object.__getattribute__(root_wrapper, "_taint_origin")
                    updated_taint = list(set(current_taint) | all_origins)
                    object.__setattr__(root_wrapper, "_taint_origin", updated_taint)
                except AttributeError:
                    pass

            # Set taint in TAINT_ESCROW
            import builtins

            builtins.TAINT_ESCROW.set(list(all_origins))

            # Untaint arguments for the function call
            untainted_args = untaint_if_needed(args)
            untainted_kwargs = untaint_if_needed(kwargs)

            # Handle type annotations specially
            if (
                hasattr(func, "__name__")
                and func.__name__ == "getitem"
                and len(untainted_args) >= 2
            ):
                obj, key = untainted_args[0], untainted_args[1]
                if _is_type_annotation_access(obj, key):
                    return func(*untainted_args, **untainted_kwargs)

            # Call with untainted arguments
            func_to_call = func
            if bound_self is not None and hasattr(func, "__func__"):
                untainted_bound_self = untaint_if_needed(bound_self)
                func_to_call = func.__func__.__get__(
                    untainted_bound_self, type(untainted_bound_self)
                )

            result = await func_to_call(*untainted_args, **untainted_kwargs)

            # Wrap result with final taint from TAINT_ESCROW
            final_taint = list(builtins.TAINT_ESCROW.get())
            if final_taint:
                return taint_wrap(result, taint_origin=final_taint, root_wrapper=root_wrapper)
            return result

        return wrapper()

    # Sync version
    # User code: call directly
    if _is_user_function(func):
        try:
            return func(*args, **kwargs)
        except:
            print("~~ caused exception, retry")
            pass

    # Third-party code: collect taint from arguments
    all_origins = set()
    all_origins.update(get_taint_origins(args))
    all_origins.update(get_taint_origins(kwargs))

    # Include taint from bound methods
    bound_self = None
    root_wrapper = None
    if hasattr(func, "__self__"):
        bound_self = func.__self__
    elif hasattr(func, "func") and hasattr(func.func, "__self__"):
        bound_self = func.func.__self__

    if bound_self is not None:
        all_origins.update(get_taint_origins(bound_self))
        # Check if bound_self has root wrapper reference
        if hasattr(bound_self, "_root_wrapper"):
            root_wrapper = object.__getattribute__(bound_self, "_root_wrapper")

    # File operations with persistence
    if bound_self and getattr(bound_self, "_enable_persistence", False):
        return _handle_persistent_file_operation(bound_self, func, args, kwargs)

    # Update root wrapper with collected taint if available
    if root_wrapper is not None and all_origins:
        try:
            current_taint = object.__getattribute__(root_wrapper, "_taint_origin")
            updated_taint = list(set(current_taint) | all_origins)
            object.__setattr__(root_wrapper, "_taint_origin", updated_taint)
        except AttributeError:
            pass

    # Set taint in TAINT_ESCROW
    import builtins

    builtins.TAINT_ESCROW.set(list(all_origins))

    # Untaint arguments
    untainted_args = untaint_if_needed(args)
    untainted_kwargs = untaint_if_needed(kwargs)

    # Handle type annotations specially
    if hasattr(func, "__name__") and func.__name__ == "getitem" and len(untainted_args) >= 2:
        obj, key = untainted_args[0], untainted_args[1]
        if _is_type_annotation_access(obj, key):
            return func(*untainted_args, **untainted_kwargs)

    # Call with untainted arguments
    func_to_call = func
    if bound_self is not None and hasattr(func, "__func__"):
        untainted_bound_self = untaint_if_needed(bound_self)
        func_to_call = func.__func__.__get__(untainted_bound_self, type(untainted_bound_self))

    result = func_to_call(*untainted_args, **untainted_kwargs)

    # Wrap result with final taint from TAINT_ESCROW
    final_taint = list(builtins.TAINT_ESCROW.get())
    if final_taint:
        return taint_wrap(result, taint_origin=final_taint, root_wrapper=root_wrapper)
    return result


def _handle_persistent_file_operation(bound_self, func, args, kwargs):
    """Handle file operations with database persistence."""
    # Extract method name from function or partial object
    if hasattr(func, "func") and hasattr(func, "args") and hasattr(func, "keywords"):
        method_name = func.args[0] if func.args else "unknown"
    else:
        method_name = getattr(func, "__name__", "unknown")

    if method_name == "write":
        return _handle_file_write(bound_self, func, args, kwargs)
    elif method_name in ["read", "readline"]:
        return _handle_file_read(bound_self, func, args, kwargs, method_name)
    elif method_name == "writelines":
        return _handle_file_writelines(bound_self, func, args, kwargs)
    else:
        # Other file methods: call normally and propagate taint
        untainted_args = untaint_if_needed(args)
        untainted_kwargs = untaint_if_needed(kwargs)
        result = func(*untainted_args, **untainted_kwargs)

        import builtins

        final_taint = list(builtins.TAINT_ESCROW.get())
        if final_taint:
            return taint_wrap(result, taint_origin=final_taint)
        return result


def _handle_file_write(bound_self, func, args, kwargs):
    """Handle file write operations with database storage."""
    from aco.server.database_manager import DB

    session_id = object.__getattribute__(bound_self, "_session_id")
    line_no = object.__getattribute__(bound_self, "_line_no")
    file_obj = object.__getattribute__(bound_self, "obj")

    data = args[0] if args else None
    if data is None:
        return func(*args, **kwargs)

    untainted_data = untaint_if_needed(data)
    untainted_args = (untainted_data,) + args[1:] if len(args) > 1 else (untainted_data,)
    untainted_kwargs = untaint_if_needed(kwargs)

    # Store taint info in database
    if session_id and hasattr(file_obj, "name"):
        taint_nodes = get_taint_origins(data)
        if taint_nodes:
            try:
                DB.store_taint_info(session_id, file_obj.name, line_no, taint_nodes)
            except Exception as e:
                import sys

                print(f"Warning: Could not store taint info: {e}", file=sys.stderr)

        newline_count = untainted_data.count("\n") if isinstance(untainted_data, str) else 0
        object.__setattr__(bound_self, "_line_no", line_no + max(1, newline_count))

    return func(*untainted_args, **untainted_kwargs)


def _handle_file_read(bound_self, func, args, kwargs, method_name=None):
    """Handle file read operations with database retrieval."""
    from aco.server.database_manager import DB

    line_no = object.__getattribute__(bound_self, "_line_no")
    file_obj = object.__getattribute__(bound_self, "obj")
    taint_origin = object.__getattribute__(bound_self, "_taint_origin")

    untainted_args = untaint_if_needed(args)
    untainted_kwargs = untaint_if_needed(kwargs)
    data = func(*untainted_args, **untainted_kwargs)

    if isinstance(data, bytes):
        return data

    # Combine file's default taint with stored taint from previous sessions
    combined_taint = list(taint_origin)

    if hasattr(file_obj, "name") and data:
        try:
            prev_session_id, stored_taint_nodes = DB.get_taint_info(file_obj.name, line_no)
            if prev_session_id and stored_taint_nodes:
                combined_taint.extend(stored_taint_nodes)
                combined_taint = list(set(combined_taint))
        except Exception as e:
            import sys

            print(f"Warning: Could not retrieve taint info: {e}", file=sys.stderr)

    if method_name == "readline":
        object.__setattr__(bound_self, "_line_no", line_no + 1)

    if combined_taint:
        return taint_wrap(data, taint_origin=combined_taint)
    return data


def _handle_file_writelines(bound_self, func, args, kwargs):
    """Handle file writelines operations with database storage."""
    from aco.server.database_manager import DB

    session_id = object.__getattribute__(bound_self, "_session_id")
    line_no = object.__getattribute__(bound_self, "_line_no")
    file_obj = object.__getattribute__(bound_self, "obj")

    lines = args[0] if args else None
    if lines is None:
        return func(*args, **kwargs)

    untainted_lines = []
    current_line = line_no

    for line in lines:
        if session_id and hasattr(file_obj, "name"):
            taint_nodes = get_taint_origins(line)
            if taint_nodes:
                try:
                    DB.store_taint_info(session_id, file_obj.name, current_line, taint_nodes)
                except Exception as e:
                    import sys

                    print(f"Warning: Could not store taint info: {e}", file=sys.stderr)

        current_line += 1
        untainted_lines.append(untaint_if_needed(line))

    object.__setattr__(bound_self, "_line_no", current_line)

    untainted_args = (untainted_lines,) + args[1:] if len(args) > 1 else (untainted_lines,)
    untainted_kwargs = untaint_if_needed(kwargs)

    return func(*untainted_args, **untainted_kwargs)
