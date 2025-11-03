#!/usr/bin/env python3
"""
Wrapper to run test_re_patches.py tests in a develop process.
This ensures tests use .pyc files with AST rewrites.
"""

import sys
from pathlib import Path

# Add the user_programs directory to path to import the template
sys.path.insert(0, str(Path(__file__).parent))

from test_wrapper_template import create_test_wrapper

# Create wrapper for test_re_patches
run_tests, main = create_test_wrapper("test_re_patches")

if __name__ == "__main__":
    main()
