"""
Shared test launcher framework for running tests via develop command.
This ensures tests use .pyc files with AST rewrites.
"""

import json
import socket
import subprocess
import time
import pytest
import os
import sys
from pathlib import Path


class DevelopTestLauncher:
    """
    Reusable launcher for running test modules via develop command.

    Usage:
        launcher = DevelopTestLauncher("test_module_name")
        results = launcher.run_all_tests_batch()
        # or
        result = launcher.run_single_test("test_function_name")
    """

    def __init__(self, test_module_name, project_root=None):
        """
        Initialize the test launcher.

        Args:
            test_module_name: Name of the test module (e.g., "test_re_patches")
            project_root: Path to project root (defaults to tests directory)
        """
        self.test_module_name = test_module_name
        self.project_root = project_root or Path(__file__).parent
        # For test_re_patches -> user_programs.re_patches_test
        if test_module_name.startswith("test_"):
            wrapper_name = test_module_name.replace("test_", "") + "_test"
        else:
            wrapper_name = f"{test_module_name}_test"
        self.wrapper_module = f"user_programs.{wrapper_name}"

        # Cache for batch results
        self._batch_results = None

        # For now, we'll skip the test function discovery and only use batch execution
        # This simplifies the implementation and avoids complex import issues
        self.test_module = None

    def get_test_functions(self):
        """Get all test function names from the test module."""
        test_functions = []

        # Get standalone test functions
        for name in dir(self.test_module):
            if name.startswith("test_") and callable(getattr(self.test_module, name)):
                test_functions.append(name)

        # Get test methods from test classes
        for name in dir(self.test_module):
            obj = getattr(self.test_module, name)
            if isinstance(obj, type) and (name.startswith("Test") or name.startswith("test_")):
                # This is a test class
                for method_name in dir(obj):
                    if method_name.startswith("test_") and callable(getattr(obj, method_name)):
                        # Format as class::method for easy identification
                        test_functions.append(f"{name}::{method_name}")

        return sorted(test_functions)

    def run_via_develop(self, specific_test=None):
        """Run tests via develop command and parse JSON results."""

        # Build command
        cmd = ["develop", "--project-root", str(self.project_root), "-m", self.wrapper_module]

        # Add specific test name if provided
        if specific_test:
            cmd.append(specific_test)

        print(f"Running command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, cwd=str(self.project_root)
            )

            # Parse JSON results from output
            output_lines = result.stdout.split("\n")

            # Find JSON results section
            json_start = False
            json_lines = []

            for line in output_lines:
                if "JSON_RESULTS_START" in line:
                    json_start = True
                    continue
                elif "JSON_RESULTS_END" in line:
                    break
                elif json_start:
                    json_lines.append(line)

            if json_lines:
                json_text = "\n".join(json_lines)
                test_results = json.loads(json_text)
                return test_results
            else:
                print("WARNING: No JSON results found in output")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                return None

        except subprocess.TimeoutExpired:
            print("ERROR: Test execution timed out")
            return None
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse JSON results: {e}")
            return None
        except Exception as e:
            print(f"ERROR: Failed to run tests: {e}")
            return None

    def start_server_if_needed(self):
        """Start the daemon server if not already running."""
        from aco.cli.aco_server import launch_daemon_server

        print("Starting daemon server...")
        launch_daemon_server()
        time.sleep(2)

        # Check server is ready
        try:
            socket.create_connection(("127.0.0.1", 5959), timeout=2).close()
            print("Server is ready")
            return True
        except:
            print("WARNING: Server may not be ready")
            return False

    def run_all_tests(self):
        """Run all tests in a single develop process and cache results."""
        if self._batch_results is not None:
            return self._batch_results

        print(f"Running all tests for {self.test_module_name} via develop...")

        self.start_server_if_needed()

        # Run all tests in single batch (no specific test argument)
        results = self.run_via_develop()
        self._batch_results = results or {}

        print(f"Batch execution completed with {len(self._batch_results)} test results")
        return self._batch_results


def create_pytest_functions(test_module_name, launcher=None):
    """
    Create pytest functions for a test module.

    Returns a dict of functions that can be added to a test file:
    - pytest_generate_tests: Hook for dynamic test generation
    - test_individual: Individual tests via single batch execution
    - test_all: All tests in single batch
    """

    if launcher is None:
        launcher = DevelopTestLauncher(test_module_name)

    def pytest_generate_tests(metafunc):
        """Dynamically generate test cases for each test function."""
        if metafunc.function.__name__ == "test_individual":
            # Get test function names by running the batch and extracting keys
            all_results = launcher.run_all_tests()
            test_functions = list(all_results.keys()) if all_results else []
            metafunc.parametrize("test_name", test_functions, ids=test_functions)

    def test_individual(test_name):
        """Test individual function via single batch develop command."""
        # Get all results from single batch execution (cached after first call)
        all_results = launcher.run_all_tests()

        # Check if the specific test is in results
        if test_name not in all_results:
            pytest.fail(f"Test {test_name} not found in batch results: {list(all_results.keys())}")

        result = all_results[test_name]
        _assert_test_result(test_name, result)

    def test_all():
        """Test all functions in single batch."""
        print(f"\n" + "=" * 60)
        print(f"Testing all {test_module_name} functions via single batch develop command")
        print("=" * 60)

        results = launcher.run_all_tests()
        _report_batch_results(results)

    return {
        "pytest_generate_tests": pytest_generate_tests,
        "test_individual": test_individual,
        "test_all": test_all,
    }


def _assert_test_result(test_name, result):
    """Assert that a test result indicates success."""
    status = result.get("status", "unknown")
    message = result.get("message", "No message")

    # Fail if the test didn't pass
    if status == "failed":
        pytest.fail(f"Test {test_name} failed: {message}")
    elif status == "error":
        error_msg = f"Test {test_name} had error: {message}"
        pytest.fail(error_msg)
    elif status != "passed":
        pytest.fail(f"Test {test_name} had unexpected status: {status}")


def _report_batch_results(results):
    """Report results from a batch test execution."""
    # Analyze results
    failed_tests = []
    error_tests = []
    passed_tests = []

    for test_name, result in results.items():
        status = result.get("status", "unknown")

        if status == "passed":
            passed_tests.append(test_name)
        elif status == "failed":
            failed_tests.append((test_name, result.get("message", "No message")))
        elif status == "error":
            error_tests.append((test_name, result.get("message", "No message")))

    # Report results
    print("\n" + "=" * 60)
    print("BATCH TEST RESULTS SUMMARY:")
    print(f"  Total tests: {len(results)}")
    print(f"  Passed: {len(passed_tests)}")
    print(f"  Failed: {len(failed_tests)}")
    print(f"  Errors: {len(error_tests)}")
    print("=" * 60)

    if failed_tests:
        print("\nFailed tests:")
        for test_name, message in failed_tests:
            print(f"  ✗ {test_name}: {message}")

    if error_tests:
        print("\nError tests:")
        for test_name, message in error_tests:
            print(f"  ✗ {test_name}: {message}")

    # Fail if any tests failed
    if failed_tests or error_tests:
        pytest.fail(f"{len(failed_tests)} tests failed, {len(error_tests)} tests had errors")

    print(f"\n✅ All {len(passed_tests)} tests passed!")
