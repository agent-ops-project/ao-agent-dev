"""
AST rewriting for taint tracking through string formatting and third-party library calls.

This module provides AST transformation capabilities to rewrite:
1. Python f-strings, .format() calls, and % formatting
2. Third-party library function calls (re.search, json.dumps, etc.)

Key Components:
- FStringTransformer: AST node transformer for string formatting
- ThirdPartyCallTransformer: AST node transformer for third-party library calls
- taint_fstring_join: Taint-aware replacement for f-string concatenation
- taint_format_string: Taint-aware replacement for .format() calls
- taint_percent_format: Taint-aware replacement for % formatting
- exec_func: Generic taint-aware function executor for third-party calls

The rewriter preserves taint information and tracking through both string and
function operations, ensuring sensitive data remains tainted throughout execution.
"""

import ast
from aco.common.logger import logger
from aco.runner.taint_wrappers import TaintStr, get_taint_origins, untaint_if_needed


def taint_fstring_join(*args):
    """
    Taint-aware replacement for f-string concatenation.

    This function is used as a runtime replacement for f-string expressions.
    It joins the provided arguments into a single string while preserving
    taint information and tracking positional data from tainted sources.

    The function:
    1. Collects taint origins from all arguments
    2. Unwraps all arguments to get raw values
    3. Joins all arguments into a single string
    4. Returns a TaintStr with collected taint origins if any taint exists

    Args:
        *args: Variable number of arguments to join (values from f-string expressions)

    Returns:
        str or TaintStr: The joined string with taint information preserved

    Example:
        # Original: f"Hello {name}, you have {count} items"
        # Becomes: taint_fstring_join("Hello ", name, ", you have ", count, " items")
    """
    # First collect all taint origins before unwrapping
    all_origins = set()
    for a in args:
        all_origins.update(get_taint_origins(a))

    # Unwrap all arguments and convert to strings
    unwrapped_args = [str(untaint_if_needed(a)) for a in args]
    result = "".join(unwrapped_args)

    if all_origins:
        return TaintStr(result, list(all_origins))
    return result


def taint_format_string(format_string, *args, **kwargs):
    """
    Taint-aware replacement for .format() string method calls.

    This function replaces calls to str.format() to preserve taint information
    through string formatting operations. It handles both positional and
    keyword arguments while tracking which parts of the result contain
    tainted data.

    The function:
    1. Collects taint origins from format string and all arguments
    2. Unwraps all arguments to get raw values
    3. Performs the string formatting operation
    4. Returns a TaintStr if any taint exists

    Args:
        format_string (str): The format string template
        *args: Positional arguments for formatting
        **kwargs: Keyword arguments for formatting

    Returns:
        str or TaintStr: The formatted string with taint information preserved

    Example:
        # Original: "Hello {}, you have {} items".format(name, count)
        # Becomes: taint_format_string("Hello {}, you have {} items", name, count)
    """
    # Collect taint origins before unwrapping
    all_origins = set(get_taint_origins(format_string))
    for a in args:
        all_origins.update(get_taint_origins(a))
    for v in kwargs.values():
        all_origins.update(get_taint_origins(v))

    # Unwrap all arguments before formatting
    unwrapped_format_string = untaint_if_needed(format_string)
    unwrapped_args = [untaint_if_needed(a) for a in args]
    unwrapped_kwargs = {k: untaint_if_needed(v) for k, v in kwargs.items()}

    result = unwrapped_format_string.format(*unwrapped_args, **unwrapped_kwargs)

    if all_origins:
        return TaintStr(result, list(all_origins))
    return result


def taint_percent_format(format_string, values):
    """
    Taint-aware replacement for % string formatting operations.

    This function replaces Python's % formatting operator to preserve taint
    information through printf-style string formatting. It handles both
    single values and tuples/lists of values while tracking tainted content.

    The function:
    1. Collects taint origins from format string and values
    2. Unwraps all arguments to get raw values
    3. Performs the % formatting operation
    4. Returns a TaintStr if any taint exists

    Args:
        format_string (str): The format string with % placeholders
        values: The values to format (single value, tuple, or list)

    Returns:
        str or TaintStr: The formatted string with taint information preserved

    Example:
        # Original: "Hello %s, you have %d items" % (name, count)
        # Becomes: taint_percent_format("Hello %s, you have %d items", (name, count))
    """
    # Collect taint origins before unwrapping
    all_origins = set(get_taint_origins(format_string))
    if isinstance(values, (tuple, list)):
        for v in values:
            all_origins.update(get_taint_origins(v))
    else:
        all_origins.update(get_taint_origins(values))

    # Unwrap arguments before formatting
    unwrapped_format_string = untaint_if_needed(format_string)
    unwrapped_values = untaint_if_needed(values)

    result = unwrapped_format_string % unwrapped_values

    if all_origins:
        return TaintStr(result, list(all_origins))
    return result


class FStringTransformer(ast.NodeTransformer):
    """
    AST transformer that rewrites string formatting operations for taint tracking.

    This class extends ast.NodeTransformer to rewrite three types of string
    formatting operations in Python source code:

    1. F-strings (f"...{expr}...") -> taint_fstring_join calls
    2. .format() calls ("...{}...".format(args)) -> taint_format_string calls
    3. % formatting ("...%s..." % values) -> taint_percent_format calls

    The transformer preserves the original AST structure while replacing
    formatting operations with calls to taint-aware equivalents that track
    the flow of sensitive data through string operations.

    Usage:
        transformer = FStringTransformer()
        tree = ast.parse(source_code)
        new_tree = transformer.visit(tree)
        compiled_code = compile(new_tree, filename, 'exec')
    """

    def visit_JoinedStr(self, node):
        """
        Transform f-string literals into taint_fstring_join calls.

        Converts f-string expressions like f"Hello {name}!" into equivalent
        function calls that preserve taint information.

        Args:
            node (ast.JoinedStr): The f-string AST node to transform

        Returns:
            ast.Call: A call to taint_fstring_join with the f-string components as arguments
        """
        # Replace f-string with a call to taint_fstring_join
        new_node = ast.Call(
            func=ast.Name(id="taint_fstring_join", ctx=ast.Load()),
            args=[value for value in node.values],
            keywords=[],
        )
        return ast.copy_location(new_node, node)

    def visit_Call(self, node):
        """
        Transform .format() method calls into taint_format_string calls.

        Detects any .format() method calls and converts them to equivalent
        taint_format_string calls that preserve taint information.

        Args:
            node (ast.Call): The method call AST node to potentially transform

        Returns:
            ast.Call or ast.Call: Either a transformed taint_format_string call
                                 or the original node (via generic_visit)
        """
        # Check if this is a .format() call on any expression
        if isinstance(node.func, ast.Attribute) and node.func.attr == "format":
            # Extract the format expression and arguments
            format_args = node.args
            format_kwargs = node.keywords

            # Create a call to taint_format_string
            new_node = ast.Call(
                func=ast.Name(id="taint_format_string", ctx=ast.Load()),
                args=[node.func.value] + format_args,
                keywords=format_kwargs,
            )
            return ast.copy_location(new_node, node)

        return self.generic_visit(node)

    def visit_BinOp(self, node):
        """
        Transform % formatting operations into taint_percent_format calls.

        Detects binary modulo operations where the left operand is a string
        literal and converts them to equivalent taint_percent_format calls
        that preserve taint information through printf-style formatting.

        Args:
            node (ast.BinOp): The binary operation AST node to potentially transform

        Returns:
            ast.Call or ast.BinOp: Either a transformed taint_percent_format call
                                  or the original node (via generic_visit)
        """
        # Add support for string % formatting
        if isinstance(node.op, ast.Mod) and (
            isinstance(node.left, ast.Constant) and isinstance(node.left.value, str)
        ):
            # Replace with taint_percent_format(format_string, right)
            new_node = ast.Call(
                func=ast.Name(id="taint_percent_format", ctx=ast.Load()),
                args=[node.left, node.right],
                keywords=[],
            )
            return ast.copy_location(new_node, node)
        return self.generic_visit(node)


class ThirdPartyCallTransformer(ast.NodeTransformer):
    """
    AST transformer that wraps third-party library function calls with taint propagation.

    This transformer detects calls to third-party modules (e.g., re.search, json.dumps,
    requests.get) and wraps them with exec_func to automatically propagate taint through
    the function call.

    The transformer:
    1. Identifies calls to module-level functions (e.g., module.function())
    2. Only wraps calls to functions defined OUTSIDE project_root (third-party code)
    3. Skips calls to user-defined functions (inside project_root)
    4. Preserves the original AST structure for everything else

    Usage:
        transformer = ThirdPartyCallTransformer(module_to_file=user_modules, current_file="/path/to/file.py")
        tree = ast.parse(source_code)
        new_tree = transformer.visit(tree)
    """

    def __init__(self, module_to_file=None, current_file=None):
        """
        Initialize the transformer.

        Args:
            module_to_file: Dict mapping user module names to their file paths.
                           Used to identify which modules are user-defined.
            current_file: The path to the current file being transformed.
        """
        self.module_to_file = module_to_file or {}
        self.current_file = current_file
        # Extract the root directory from current_file if available
        if current_file:
            import os

            # Find the common prefix between current_file and all module files
            # to determine project_root
            self.project_root = self._extract_project_root(current_file)
        else:
            self.project_root = None

    def _extract_project_root(self, current_file):
        """Extract project root by finding common prefix of module paths."""
        if not self.module_to_file:
            return None

        import os

        current_file = os.path.abspath(current_file)

        # Find common prefix of all module files with current file
        common_parts = None
        for file_path in self.module_to_file.values():
            file_path = os.path.abspath(file_path)
            if common_parts is None:
                common_parts = file_path.split(os.sep)
            else:
                path_parts = file_path.split(os.sep)
                # Keep only common prefix
                common_parts = [
                    p
                    for i, p in enumerate(common_parts)
                    if i < len(path_parts) and path_parts[i] == p
                ]

        if common_parts:
            return os.sep.join(common_parts) or os.sep
        return None

    def _is_user_module(self, module_name):
        """Check if a module name refers to user code (inside project_root)."""
        if not self.module_to_file:
            return False

        # Direct lookup: is this module name in our user modules?
        return module_name in self.module_to_file

    def visit_Call(self, node):
        """
        Transform third-party function calls into exec_func wrapped calls.

        Detects patterns like:
        - re.search(pattern, string)
        - json.dumps(obj)
        - requests.get(url)

        And transforms them to:
        - exec_func(re.search, (pattern, string), {})
        - exec_func(json.dumps, (obj,), {})
        - exec_func(requests.get, (url,), {})

        Args:
            node (ast.Call): The function call AST node to potentially transform

        Returns:
            ast.Call: Either a transformed exec_func call or the original node
        """
        # First, recursively visit child nodes
        node = self.generic_visit(node)

        # Check if this is a third-party library call (module.function())
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            module_name = node.func.value.id
            func_name = node.func.attr

            # Skip dunder methods - never wrap these
            dunder_methods = {
                "__init__",
                "__new__",
                "__del__",
                "__repr__",
                "__str__",
                "__bytes__",
                "__format__",
                "__lt__",
                "__le__",
                "__eq__",
                "__ne__",
                "__gt__",
                "__ge__",
                "__hash__",
                "__bool__",
                "__getitem__",
                "__setitem__",
                "__delitem__",
                "__len__",
                "__iter__",
                "__reversed__",
                "__contains__",
                "__enter__",
                "__exit__",
                "__call__",
                "__getattr__",
                "__setattr__",
            }
            if func_name in dunder_methods:
                return node

            # Only wrap calls to third-party modules, not user-defined modules
            # If module_name is in our user modules dict, skip it (it's user code)
            if self._is_user_module(module_name):
                return node

            # Transform: node(...args, ...kwargs)
            # Into: exec_func(node.func, (args,), {kwargs})

            # Create the function name node with location info
            func_node = ast.Name(id="exec_func", ctx=ast.Load())
            ast.copy_location(func_node, node)

            # Create tuple for positional args with location info
            args_tuple = ast.Tuple(elts=node.args, ctx=ast.Load())
            ast.copy_location(args_tuple, node)

            # Create dict for keyword args with location info
            # For each keyword, create a Constant node for the key name
            # keys should be AST nodes (Constant nodes for string keys), not raw strings
            kwargs_dict = ast.Dict(
                keys=[ast.Constant(value=kw.arg) if kw.arg else None for kw in node.keywords],
                values=[kw.value for kw in node.keywords],
            )
            ast.copy_location(kwargs_dict, node)

            # Also fix missing locations on the key constants
            for key in kwargs_dict.keys:
                if key is not None:
                    ast.copy_location(key, node)

            new_node = ast.Call(
                func=func_node,
                args=[
                    node.func,  # The function to call
                    args_tuple,  # Positional args
                    kwargs_dict,  # Keyword args
                ],
                keywords=[],
            )
            ast.copy_location(new_node, node)

            # Recursively ensure all nested nodes have location information
            # This is critical because elements in args/kwargs may be newly created nodes
            ast.fix_missing_locations(new_node)

            return new_node

        return node


def exec_func(func, args, kwargs):
    """
    Execute an arbitrary function with taint propagation.

    This function is called by rewritten user code to propagate taint through
    arbitrary function calls. It extracts taint from all arguments, calls the
    original function with untainted arguments, and applies taint to the result.

    Args:
        func: The function object to call (e.g., re.match, json.dumps)
        args: Tuple of positional arguments
        kwargs: Dict of keyword arguments

    Returns:
        The function result, wrapped with taint if any input was tainted

    Example:
        # Rewritten from: result = json.dumps({"key": tainted_value})
        # To: result = exec_func(json.dumps, ({"key": tainted_value},), {})
    """
    from aco.runner.taint_wrappers import (
        get_taint_origins,
        taint_wrap,
        untaint_if_needed,
    )

    # Collect taint from all arguments before unwrapping
    all_origins = set()
    all_origins.update(get_taint_origins(args))
    all_origins.update(get_taint_origins(kwargs))

    # If func is a bound method (or partial with a bound method), extract taint from self (__self__)
    # This handles cases like: match.expand(template) where match has taint
    # For partial objects, we need to check func.func.__self__
    bound_self = None
    if hasattr(func, "__self__"):
        bound_self = func.__self__
    elif hasattr(func, "func") and hasattr(func.func, "__self__"):
        # Handle functools.partial objects
        bound_self = func.func.__self__

    if bound_self is not None:
        all_origins.update(get_taint_origins(bound_self))

    # Untaint arguments for the function call
    untainted_args = untaint_if_needed(args)
    untainted_kwargs = untaint_if_needed(kwargs)

    # Call the original function with untainted arguments
    result = func(*untainted_args, **untainted_kwargs)

    # If func is a bound method on a TaintObject, update its taint with any new taint from inputs
    # This ensures the object accumulates taint as it's used with tainted data
    if bound_self is not None and hasattr(bound_self, "_taint_origin"):
        # Get the current taint from inputs (excluding self's original taint)
        input_taint = set()
        input_taint.update(get_taint_origins(args))
        input_taint.update(get_taint_origins(kwargs))
        if input_taint:
            # Update the bound object's taint with new taint from inputs
            try:
                current_origins = object.__getattribute__(bound_self, "_taint_origin")
                new_origins = set(current_origins) | input_taint
                object.__setattr__(bound_self, "_taint_origin", list(new_origins))
            except (AttributeError, TypeError):
                # If we can't update, just continue - the taint will still be in all_origins for the result
                pass

    # Wrap result with taint if there is any taint
    if all_origins:
        return taint_wrap(result, taint_origin=all_origins)

    # If no taint, return result unwrapped
    return result
