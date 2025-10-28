"""
AST rewriting for taint propagation through user code.

This module handles pre-rewriting all user modules at startup to:
1. Transform f-strings into taint-aware function calls
2. Transform library function calls into exec_func wrappers

All rewritten modules are stored in sys.modules so they're loaded
from memory instead of from disk.

The implementation is structured to support future optimizations like
caching compiled code to disk, without requiring refactoring.
"""

import ast
import sys
from types import ModuleType
from aco.common.logger import logger
from aco.runner.fstring_rewriter import FStringTransformer


def rewrite_source_to_code(source: str, filename: str):
    """
    Transform and compile Python source code with AST rewrites.

    This is a pure function that applies AST transformations and compiles
    the result to a code object. Same input always produces same output,
    making it suitable for caching.

    Args:
        source: Python source code as a string
        filename: Path to the source file (used in error messages and code object)

    Returns:
        A compiled code object ready for execution

    Raises:
        SyntaxError: If the source code is invalid
        Exception: If AST transformation fails
    """
    # Parse source into AST
    tree = ast.parse(source, filename=filename)

    # Apply AST transformations
    tree = FStringTransformer().visit(tree)

    # Fix missing location information
    ast.fix_missing_locations(tree)

    # Compile to code object
    code_object = compile(tree, filename, "exec")

    return code_object


def load_module(module_name: str, file_path: str, code_object):
    """
    Load a rewritten module into sys.modules.

    Creates a module object, executes the pre-compiled code in its namespace,
    and registers it in sys.modules. After this, the module is available for
    import by user code.

    Args:
        module_name: The name of the module (e.g., "mypackage.mymodule")
        file_path: The path to the original source file (for reference)
        code_object: Pre-compiled code object (from rewrite_source_to_code)
    """
    # Create an empty module object
    module = ModuleType(module_name)
    module.__file__ = file_path

    # Register in sys.modules first (in case of circular imports)
    sys.modules[module_name] = module

    # Execute the rewritten code in the module's namespace
    exec(code_object, module.__dict__)

    logger.debug(f"Loaded module: {module_name}")


def rewrite_all_user_modules(module_to_file: dict):
    """
    Pre-rewrite and load all user modules at startup.

    This function:
    1. Reads source code for all user modules
    2. Applies AST transformations (via rewrite_source_to_code)
    3. Loads the modules into sys.modules (via load_module)

    When user code later does `import mymodule`, Python finds it in sys.modules
    with the rewritten code already executed, so no import overhead occurs.

    Args:
        module_to_file: Dict mapping module names to their source file paths
                       (e.g., {"mypackage.mymodule": "/path/to/mymodule.py"})

    Raises:
        Exception: If reading, rewriting, or loading any module fails
    """
    for module_name, file_path in module_to_file.items():
        try:
            # Read source code from file
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()

            # Rewrite and compile
            code_object = rewrite_source_to_code(source, file_path)

            # Load into sys.modules
            load_module(module_name, file_path, code_object)

            logger.debug(f"Rewritten and loaded: {module_name}")
        except Exception as e:
            logger.error(f"Failed to rewrite {module_name} at {file_path}: {e}")
            raise
