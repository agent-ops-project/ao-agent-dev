#!/usr/bin/env python3
"""
Comprehensive test script to verify AST transformation behavior.
This script:
1. Creates test code with various call patterns
2. Shows the AST transformation
3. Executes the transformed code to see actual runtime behavior
"""

import ast
import tempfile
import os
import subprocess
import sys

from aco.server.ast_transformer import TaintPropagationTransformer, rewrite_source_to_code


def create_comprehensive_test_code():
    """Create test code that demonstrates various call patterns"""

    return '''
import json
import re
from json import loads

class TestClass:
    def __init__(self):
        self.name = "TestClass instance"
        
    def _handle_llm_call_with_logging(self, prompt):
        """User method that should NOT be wrapped with exec_func"""
        print(f"✅ Called self._handle_llm_call_with_logging with: {prompt}")
        return f"response to: {prompt}"
        
    def test_method_calls(self):
        print("\\n=== Testing Method Calls ===")
        
        # 1. self method call - should NOT be wrapped
        print("\\n1. Testing self method call:")
        result1 = self._handle_llm_call_with_logging("test prompt")
        print(f"   Result: {result1}")
        
        # 2. Third-party function call - should be wrapped
        print("\\n2. Testing json.dumps (third-party):")
        result2 = json.dumps({"test": "data", "number": 42})
        print(f"   Result: {result2}")
        
        # 3. Third-party function from import - should be wrapped  
        print("\\n3. Testing loads (imported function):")
        result3 = loads('{"imported": "test"}')
        print(f"   Result: {result3}")
        
        # 4. Third-party call that returns object, then method on that object
        print("\\n4. Testing re.search and then method on result:")
        match_obj = re.search(r"(test)", "this is a test string")
        if match_obj:
            # This should be wrapped - method on third-party object
            result4 = match_obj.group(1)
            print(f"   Match found: {result4}")
            
            # Test another method on the match object
            span_result = match_obj.span()
            print(f"   Span: {span_result}")
        else:
            print("   No match found")
            
        # 5. User object method call - should NOT be wrapped
        print("\\n5. Testing user object method call:")
        user_obj = UserClass()
        result5 = user_obj.user_method("user data")
        print(f"   Result: {result5}")
        
        # 6. Test assignment then method call
        print("\\n6. Testing variable assignment then method call:")
        my_dict = {"key": "value"}
        # This should NOT be wrapped - dict is built-in but variable is user-controlled
        result6 = my_dict.get("key", "default")
        print(f"   Result: {result6}")
        
        return "All tests completed"

class UserClass:
    def __init__(self):
        self.data = "UserClass data"
        
    def user_method(self, input_data):
        print(f"✅ Called UserClass.user_method with: {input_data}")
        return f"processed: {input_data}"

def main():
    print("=== Starting comprehensive test ===")
    
    # Create and run test
    test_obj = TestClass()
    result = test_obj.test_method_calls()
    print(f"\\nFinal result: {result}")

if __name__ == "__main__":
    main()
'''


def run_transformation_test():
    """Run the comprehensive AST transformation test"""

    print("=== Comprehensive AST Transformation Test ===\\n")

    # Get the test code
    test_code = create_comprehensive_test_code()

    # Show original code
    print("=== ORIGINAL CODE ===")
    print(test_code)
    print("\\n" + "=" * 60 + "\\n")

    # Create module mapping (simulate user code context)
    module_to_file = {"test_module": "/tmp/test_module.py"}
    current_file = "/tmp/test_module.py"

    # Apply AST transformation
    print("=== APPLYING AST TRANSFORMATION ===")
    transformer = TaintPropagationTransformer(
        module_to_file=module_to_file, current_file=current_file
    )

    tree = ast.parse(test_code, filename=current_file)
    transformed_tree = transformer.visit(tree)
    transformed_tree = transformer._inject_taint_imports(transformed_tree)
    ast.fix_missing_locations(transformed_tree)

    # Show transformed code using astor
    import astor

    transformed_code = astor.to_source(transformed_tree)
    print("=== TRANSFORMED CODE ===")
    print(transformed_code)
    print("\\n" + "=" * 60 + "\\n")

    # Analyze what got wrapped
    print("=== TRANSFORMATION ANALYSIS ===")
    analyze_transformations(transformed_tree)
    print("\\n" + "=" * 60 + "\\n")

    # Execute the transformed code
    print("=== EXECUTING TRANSFORMED CODE ===")
    if transformed_code:
        execute_transformed_code(transformed_code)
    else:
        print("Cannot execute - astor not available")


def analyze_transformations(tree):
    """Analyze which calls were transformed"""

    wrapped_calls = []
    unwrapped_calls = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "exec_func":
                # This is a wrapped call
                if len(node.args) >= 1:
                    original_func = node.args[0]
                    if isinstance(original_func, ast.Attribute):
                        if isinstance(original_func.value, ast.Name):
                            module_name = original_func.value.id
                            func_name = original_func.attr
                            wrapped_calls.append(f"{module_name}.{func_name}")

            elif isinstance(node.func, ast.Attribute):
                # This is a regular call that wasn't wrapped
                if isinstance(node.func.value, ast.Name):
                    module_name = node.func.value.id
                    func_name = node.func.attr
                    unwrapped_calls.append(f"{module_name}.{func_name}")

    print("WRAPPED with exec_func (considered third-party):")
    for call in sorted(set(wrapped_calls)):
        print(f"  ❌ {call}")

    print("\\nNOT WRAPPED (considered user code):")
    for call in sorted(set(unwrapped_calls)):
        print(f"  ✅ {call}")


def execute_transformed_code(transformed_code):
    """Execute the transformed code and show output"""

    # Create a temporary file with the transformed code
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(transformed_code)
        temp_file = f.name

    try:
        # Execute the transformed code
        print("Running transformed code...\\n")
        result = subprocess.run(
            [sys.executable, temp_file], capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            print("STDOUT:")
            print(result.stdout)
        else:
            print("EXECUTION FAILED:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            print("Return code:", result.returncode)

    except subprocess.TimeoutExpired:
        print("Execution timed out")
    except Exception as e:
        print(f"Execution error: {e}")
    finally:
        # Clean up
        try:
            os.unlink(temp_file)
        except:
            pass


if __name__ == "__main__":
    run_transformation_test()
