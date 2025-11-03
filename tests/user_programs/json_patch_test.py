#!/usr/bin/env python3
"""
Wrapper to run test_json_patch.py tests in a develop process.
This ensures tests use .pyc files with AST rewrites.
"""

import sys
from pathlib import Path

# Add the user_programs directory to path to import the template
sys.path.insert(0, str(Path(__file__).parent))

from test_wrapper_template import create_test_wrapper

# Create wrapper for test_json_patch
run_tests, main = create_test_wrapper("test_json_patch")

if __name__ == "__main__":
    main()
