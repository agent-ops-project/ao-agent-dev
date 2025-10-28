"""
AST rewriting for taint propagation through user code.

This module implements lazy execution with caching:
1. Pre-rewrite all user modules at startup (transform AST, compile to bytecode)
2. Cache the rewritten code (keyed by module name)
3. Install an import hook that serves cached code when modules are imported
4. Module-level code only executes when the module is actually imported

This approach:
- Avoids re-AST-transforming on re-runs (performance benefit)
- Module-level code runs only when imported (correct Python semantics)
- Works with test programs that have module-level code
- Uses Python's standard import machinery correctly
"""

import ast
import sys
from importlib.abc import MetaPathFinder, Loader
from importlib.util import spec_from_loader
from types import ModuleType
from aco.common.logger import logger
from aco.runner.fstring_rewriter import FStringTransformer


# Global cache for rewritten code objects
_rewritten_code_cache = {}
_module_to_file_cache = {}


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


class CachedRewriteLoader(Loader):
    """
    Loader that executes pre-rewritten and pre-compiled code.

    This loader is called by Python's import system when a module is imported.
    It executes the cached, rewritten code in the module's namespace.
    Module-level code only runs at this point, not at startup.
    """

    def __init__(self, code_object, file_path):
        """
        Initialize the loader with a pre-compiled code object.

        Args:
            code_object: The compiled code object (from rewrite_source_to_code)
            file_path: The path to the original source file (for reference)
        """
        self.code_object = code_object
        self.file_path = file_path

    def create_module(self, spec):
        """
        Create a module object with proper attributes.

        Sets up the module with __file__, __loader__, and __spec__.
        Python's import system will then call exec_module on this module.

        Args:
            spec: The module specification

        Returns:
            The module object
        """
        module = ModuleType(spec.name)
        module.__file__ = self.file_path
        module.__loader__ = self
        module.__spec__ = spec
        return module

    def exec_module(self, module):
        """
        Execute the pre-compiled code in the module's namespace.

        This is called by Python's import system when the module is imported.
        Module-level code only runs here, not during cache population.

        Args:
            module: The module object to populate with the code's definitions
        """
        exec(self.code_object, module.__dict__)


class CachedRewriteFinder(MetaPathFinder):
    """
    Import hook that serves pre-rewritten and pre-compiled code.

    This finder intercepts imports and checks if we have a cached,
    rewritten version of the module. If so, it returns a spec with our
    custom loader that serves the cached code.
    """

    def find_spec(self, fullname, path, target=None):
        """
        Find and return a module spec for cached rewritten code.

        Args:
            fullname: The fully qualified module name (e.g., "mypackage.mymodule")
            path: The search path for the module (unused)
            target: The module object (unused)

        Returns:
            ModuleSpec with CachedRewriteLoader if module is cached,
            None otherwise (let other finders handle it)
        """
        # Check if we have a rewritten version cached
        if fullname not in _rewritten_code_cache:
            return None  # Let other finders handle this module

        # Found in cache! Return a spec with our loader
        code_object = _rewritten_code_cache[fullname]
        file_path = _module_to_file_cache.get(fullname, "<cached>")

        loader = CachedRewriteLoader(code_object, file_path)
        return spec_from_loader(fullname, loader)


def cache_rewritten_modules(module_to_file: dict):
    """
    Pre-rewrite and cache all user modules without executing them.

    This function reads all user modules, applies AST transformations,
    compiles them to code objects, and caches them. No module-level code
    is executed at this point.

    When the modules are later imported, Python's import system will call
    our import hook (CachedRewriteFinder), which serves the cached code via
    CachedRewriteLoader.exec_module(), at which point module-level code
    actually runs.

    Args:
        module_to_file: Dict mapping module names to their source file paths
                       (e.g., {"mypackage.mymodule": "/path/to/mymodule.py"})

    Raises:
        Exception: If reading or rewriting any module fails
    """
    global _rewritten_code_cache, _module_to_file_cache

    for module_name, file_path in module_to_file.items():
        try:
            # Read source code from file
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()

            # Rewrite and compile (but don't execute!)
            code_object = rewrite_source_to_code(source, file_path)

            # Cache the compiled code
            _rewritten_code_cache[module_name] = code_object
            _module_to_file_cache[module_name] = file_path

            logger.debug(f"Cached rewritten module: {module_name}")
        except Exception as e:
            logger.error(f"Failed to rewrite {module_name} at {file_path}: {e}")
            raise


def install_rewrite_hook():
    """
    Install the import hook that serves cached rewritten code.

    This inserts CachedRewriteFinder into sys.meta_path, allowing it to
    intercept imports and serve pre-rewritten code for modules that were
    cached by cache_rewritten_modules().

    Should be called after cache_rewritten_modules() and after registering
    taint functions in builtins (since rewritten code will call those functions).
    """
    if not any(isinstance(finder, CachedRewriteFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, CachedRewriteFinder())
        logger.debug("Installed CachedRewriteFinder import hook")
