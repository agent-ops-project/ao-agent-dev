"""
Global test configuration - blocks all external HTTP calls and sets dummy API keys.
"""

import os
import re
import pytest
import responses
from aco.common.utils import scan_user_py_files_and_modules
from aco.runner.ast_rewriter import cache_rewritten_modules, install_rewrite_hook
from aco.runner.monkey_patching.apply_monkey_patches import apply_all_monkey_patches

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
    """Configure pytest to set up AST rewriting and monkey patches."""
    # Get the project root directory (parent of tests directory)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)

    # Register taint functions in builtins FIRST
    # This must happen before caching modules, since rewritten code will call these functions
    import builtins
    from aco.runner.fstring_rewriter import (
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

    # Cache all user modules (rewrite + compile, but don't execute)
    cache_rewritten_modules(module_to_file)

    # Install import hook to serve cached rewritten code
    # Module-level code only runs when modules are actually imported
    install_rewrite_hook()

    # Apply the monkey patches for LLM APIs
    apply_all_monkey_patches()


@pytest.fixture(autouse=True)
def cleanup_taint_registry():
    """Clean up global taint registry between tests to prevent state leakage."""
    from aco.runner.taint_wrappers import obj_id_to_taint_origin

    # Clean up before test
    obj_id_to_taint_origin.clear()

    yield

    # Clean up after test
    obj_id_to_taint_origin.clear()


@pytest.fixture
def http_calls(block_external_http):
    """Access HTTP call information in tests."""
    return block_external_http
