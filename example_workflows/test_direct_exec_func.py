"""
Direct test to see if exec_func is available when running without aco-launch.

This script will definitely fail if exec_func is not available.

Run with: python example_workflows/test_direct_exec_func.py
"""

print("=== Testing exec_func availability ===")

# Check builtins
import builtins
print(f"exec_func in builtins: {hasattr(builtins, 'exec_func')}")

# Check globals
print(f"exec_func in globals: {'exec_func' in globals()}")

# Try to use exec_func directly - this will fail if not available
try:
    # Simulate what the rewritten decorator does
    def dummy_function():
        return "dummy"
    
    # This is exactly what @mcp.tool() becomes after AST rewriting
    result = exec_func(dummy_function, (), {})
    print(f"✓ exec_func worked: {result}")
    
except NameError as e:
    print(f"✗ NameError (exec_func not defined): {e}")
    exit(1)  # Exit with error code
    
except Exception as e:
    print(f"✗ Other error: {e}")
    exit(1)

print("✓ All tests passed")