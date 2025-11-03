#!/usr/bin/env python3

"""
Test all re module functions for taint propagation using develop launcher.
"""

import pytest
from shared_test_launcher import DevelopTestLauncher, create_pytest_functions

# Create launcher instance
launcher = DevelopTestLauncher("test_re_patches")

# Create pytest functions using the shared framework
pytest_functions = create_pytest_functions("test_re_patches", launcher)

# Extract the functions for pytest to find
pytest_generate_tests = pytest_functions["pytest_generate_tests"]
test_individual = pytest_functions["test_individual"]
test_all = pytest_functions["test_all"]
