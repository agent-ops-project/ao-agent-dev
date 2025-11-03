"""
Global test configuration - blocks all external HTTP calls and sets dummy API keys.
"""

import os
import re
import pytest
import responses
from aco.common.utils import scan_user_py_files_and_modules
from aco.server.file_watcher import FileWatcher
from aco.runner.monkey_patching.apply_monkey_patches import apply_all_monkey_patches

# IMPORTANT: Set up AST rewriting BEFORE any test modules are imported
# This must happen at import time, not in pytest hooks

# Get the project root directory (parent of tests directory)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

# Register taint functions in builtins so rewritten .pyc files can call them
import builtins
from aco.server.ast_transformer import (
    taint_fstring_join,
    taint_format_string,
    taint_percent_format,
    exec_func,
)

builtins.taint_fstring_join = taint_fstring_join
builtins.taint_format_string = taint_format_string
builtins.taint_percent_format = taint_percent_format
builtins.exec_func = exec_func

# Scan for all Python files in the project
_, _, module_to_file = scan_user_py_files_and_modules(project_root)

# Pre-compile all user modules with AST rewrites to .pyc files
# This ensures test files have the necessary taint transformations
watcher = FileWatcher(module_to_file)
for module_name, file_path in module_to_file.items():
    watcher._compile_file(file_path, module_name)

# CRITICAL: Clear any already-imported modules from sys.modules so Python
# will load the newly compiled .pyc files with AST transformations
# But don't clear conftest itself or pytest infrastructure
import sys

for module_name in list(sys.modules.keys()):
    if (
        module_name in module_to_file
        and not module_name.endswith("conftest")
        and not module_name.startswith("pytest")
        and not module_name.startswith("_pytest")
    ):
        print(f"Clearing cached module: {module_name}")
        del sys.modules[module_name]

# Apply the monkey patches for LLM APIs
apply_all_monkey_patches()

# Set dummy API keys globally
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-dummy-key")
os.environ.setdefault("GOOGLE_API_KEY", "test-dummy-google-key")


@pytest.fixture(autouse=True)
def block_external_http():
    """Block all external HTTP calls, allow localhost only."""
    if not responses:
        yield
        return

    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        # Allow local connections for our develop server
        rsps.add_passthru("http://localhost")
        rsps.add_passthru("http://127.0.0.1")

        # Block everything else - but don't assert that this mock is called
        # since cached responses might not make HTTP calls
        rsps.add(
            responses.POST,
            re.compile(r"https?://(?!localhost|127\.0\.0\.1).*"),
            json={"blocked": True},
            status=200,
        )

        yield rsps


def pytest_configure(config):
    """Configure pytest - AST rewriting and patches are now set up at import time."""
    pass  # All setup is now done at import time above


@pytest.fixture(autouse=True)
def cleanup_taint_registry():
    """Clean up global taint registry between tests to prevent state leakage.

    Note: With the TaintObject wrapper approach, taint is stored in individual
    wrapper instances rather than a global dictionary, so no global cleanup is needed.
    This fixture is kept for compatibility but does nothing.
    """
    yield


@pytest.fixture
def http_calls(block_external_http):
    """Access HTTP call information in tests."""
    return block_external_http
