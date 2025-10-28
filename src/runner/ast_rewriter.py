"""
AST rewriting for taint propagation through user code.

This module handles pre-rewriting all user modules at startup to:
1. Transform f-strings into taint-aware function calls
2. Transform library function calls into exec_func wrappers

All rewritten modules are stored in sys.modules so they're loaded
from memory instead of from disk.
"""

import ast
import sys
from types import ModuleType
from importlib.util import spec_from_loader
from importlib.abc import Loader
from aco.common.logger import logger
from aco.runner.fstring_rewriter import FStringTransformer


class InMemoryModuleLoader(Loader):
    """
    Loader that executes pre-compiled and pre-rewritten code.

    This loader takes a pre-compiled code object and executes it
    in the module's namespace when the module is imported.
    """

    def __init__(self, code_object, file_path):
        """
        Initialize the loader with a pre-compiled code object.

        Args:
            code_object: The compiled code object to execute
            file_path: The path to the original source file (for reference)
        """
        self.code_object = code_object
        self.file_path = file_path

    def exec_module(self, module):
        """
        Execute the pre-compiled code in the module's namespace.

        Args:
            module: The module object to populate with the code's definitions
        """
        exec(self.code_object, module.__dict__)

    def create_module(self, spec):
        """
        Return None to use default module creation semantics.

        This allows Python's import system to create the module object,
        and we just populate it with code execution.

        Args:
            spec: The module specification (unused)

        Returns:
            None to use default module creation
        """
        return None


def rewrite_all_user_modules(module_to_file: dict):
    """
    Rewrite all user modules at startup and store them in sys.modules.

    This function:
    1. Scans all user modules
    2. Parses their source code into AST
    3. Applies AST transformations (f-string rewrites, function call wrapping, etc.)
    4. Compiles the rewritten AST to bytecode
    5. Stores the compiled modules in sys.modules

    When user code imports these modules, Python loads them from sys.modules
    instead of reading from disk, ensuring all code uses the rewritten version.

    Args:
        module_to_file: Dict mapping module names to their source file paths

    Raises:
        Exception: If AST rewriting or compilation fails for any module
    """
    rewritten_modules = {}

    # Phase 1: Rewrite and compile all modules
    for module_name, file_path in module_to_file.items():
        try:
            # Read source code from file
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()

            # Parse and rewrite AST
            tree = ast.parse(source, filename=file_path)
            tree = FStringTransformer().visit(tree)
            ast.fix_missing_locations(tree)

            # Compile to code object
            code_object = compile(tree, file_path, "exec")
            rewritten_modules[module_name] = (code_object, file_path)

            logger.debug(f"Rewritten module: {module_name}")
        except Exception as e:
            logger.error(f"Failed to rewrite {module_name} at {file_path}: {e}")
            raise

    # Phase 2: Register all rewritten modules in sys.modules
    for module_name, (code_object, file_path) in rewritten_modules.items():
        # Create a loader for this module
        loader = InMemoryModuleLoader(code_object, file_path)

        # Create a module spec
        spec = spec_from_loader(module_name, loader)

        # Create the module object
        module = ModuleType(module_name)
        module.__spec__ = spec
        module.__loader__ = loader
        module.__file__ = file_path

        # Register in sys.modules
        sys.modules[module_name] = module

        logger.debug(f"Registered in sys.modules: {module_name}")
