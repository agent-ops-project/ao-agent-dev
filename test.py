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
