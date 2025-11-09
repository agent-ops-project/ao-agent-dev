#!/usr/bin/env python3
"""Test script to verify the AST transformation fix."""

import sys

sys.path.append("/Users/jub/agent-copilot")

from aco.server.ast_transformer import rewrite_source_to_code

# Test source that should trigger the third-party function transformation
test_source = """
import re
result = re.search("pattern", "text")
"""


def test_ast_transformation():
    """Test that AST transformation works without the Constant list error."""
    try:
        # This should work without throwing TypeError: got an invalid type in Constant: list
        module_to_file = {"mymodule": "/path/to/mymodule.py"}
        code_object = rewrite_source_to_code(test_source, "test_file.py", module_to_file)
        print("✓ AST transformation completed successfully")
        print(f"✓ Code object created: {type(code_object)}")
        return True
    except Exception as e:
        print(f"✗ AST transformation failed: {e}")
        return False


if __name__ == "__main__":
    success = test_ast_transformation()
    sys.exit(0 if success else 1)
