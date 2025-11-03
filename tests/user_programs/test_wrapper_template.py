#!/usr/bin/env python3
"""
Generic test wrapper template for running tests via develop command.
This ensures tests use .pyc files with AST rewrites.
"""

import sys
import json
import traceback
from pathlib import Path


def create_test_wrapper(test_module_name):
    """Create a test wrapper for any test module."""

    # Add tests directory to path so we can import the test module
    tests_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(tests_dir))

    # Import the test module
    # First try to import from the user_programs directory with _original suffix
    original_module_name = f"{test_module_name}_original"
    try:
        test_module = __import__(original_module_name)
    except ImportError:
        # Fall back to importing from tests directory
        try:
            test_module = __import__(f"tests.{test_module_name}", fromlist=[test_module_name])
        except ImportError:
            test_module = __import__(test_module_name)

    def run_tests(specific_test=None):
        """Run all tests from the test module and return results."""
        results = {}

        # Get all test functions and methods from the module
        test_functions = []

        # Get standalone test functions
        for name in dir(test_module):
            if name.startswith("test_") and callable(getattr(test_module, name)):
                test_functions.append(name)

        # Get test methods from test classes
        for name in dir(test_module):
            obj = getattr(test_module, name)
            if isinstance(obj, type) and (name.startswith("Test") or name.startswith("test_")):
                # This is a test class
                for method_name in dir(obj):
                    if method_name.startswith("test_") and callable(getattr(obj, method_name)):
                        # Format as class::method for easy identification
                        test_functions.append(f"{name}::{method_name}")

        # If specific test is requested, only run that one
        if specific_test:
            if specific_test in test_functions:
                test_functions = [specific_test]
                print(f"Running specific test: {specific_test}")
            else:
                print(f"ERROR: Test '{specific_test}' not found")
                return {"error": f"Test '{specific_test}' not found"}
        else:
            print(f"Found {len(test_functions)} test functions")

        print("=" * 50)

        for test_name in test_functions:
            try:
                print(f"\nRunning {test_name}...")

                if "::" in test_name:
                    # This is a class method
                    class_name, method_name = test_name.split("::")
                    test_class = getattr(test_module, class_name)
                    test_instance = test_class()
                    test_func = getattr(test_instance, method_name)
                else:
                    # This is a standalone function
                    test_func = getattr(test_module, test_name)

                # Run the test
                test_func()
                results[test_name] = {"status": "passed", "message": f"{test_name} passed"}
                print(f"✓ {test_name} passed")

            except AssertionError as e:
                tb = traceback.format_exc()
                error_msg = str(e) if str(e) else "Assertion failed"
                results[test_name] = {
                    "status": "failed",
                    "message": f"{error_msg}\n\nTraceback:\n{tb}",
                    "type": "assertion",
                    "traceback": tb,
                }
                print(f"✗ {test_name} failed: {error_msg}")

            except Exception as e:
                tb = traceback.format_exc()
                results[test_name] = {
                    "status": "error",
                    "message": f"{str(e)}\n\nTraceback:\n{tb}",
                    "type": type(e).__name__,
                    "traceback": tb,
                }
                print(f"✗ {test_name} error: {e}")

        return results

    def main():
        """Main entry point."""
        # Check if specific test was requested via command line
        specific_test = None
        if len(sys.argv) > 1:
            specific_test = sys.argv[1]

        print("=" * 50)
        if specific_test:
            print(f"Running specific test: {specific_test}")
        else:
            print(f"Running {test_module_name} tests via develop")
        print("=" * 50)

        try:
            results = run_tests(specific_test)

            # Count results
            passed = sum(1 for r in results.values() if r.get("status") == "passed")
            failed = sum(1 for r in results.values() if r.get("status") == "failed")
            errors = sum(1 for r in results.values() if r.get("status") == "error")

            # Print summary
            print("\n" + "=" * 50)
            print("TEST SUMMARY:")
            print(f"  Passed: {passed}")
            print(f"  Failed: {failed}")
            print(f"  Errors: {errors}")
            print(f"  Total:  {len(results)}")
            print("=" * 50)

            # Output JSON results for the test harness
            print("\nJSON_RESULTS_START")
            print(json.dumps(results, indent=2))
            print("JSON_RESULTS_END")

            # Exit code
            sys.exit(0 if (failed == 0 and errors == 0) else 1)

        except Exception as e:
            print(f"\nFATAL ERROR: {e}")
            traceback.print_exc()
            sys.exit(2)

    return run_tests, main


# This can be used as a template for creating specific wrappers
if __name__ == "__main__":
    print("This is a template file. Use it to create specific test wrappers.")
