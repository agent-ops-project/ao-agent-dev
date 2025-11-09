"""
Debug script to see exactly when and where the exec_func error occurs.

Run with: aco-launch example_workflows/debug_decorator_issue.py
"""

import sys
print("=== Script starting ===")
print(f"exec_func in builtins at start: {hasattr(__builtins__, 'exec_func')}")

try:
    print("About to import fastmcp...")
    from fastmcp import FastMCP
    print("✓ FastMCP imported successfully")
    
    print("About to create FastMCP instance...")
    mcp = FastMCP("test-server")
    print("✓ FastMCP instance created")
    
    print("About to define decorated function...")
    print(f"exec_func available now: {hasattr(__builtins__, 'exec_func')}")
    
    @mcp.tool()
    async def test_function():
        """Test function with decorator."""
        print("Inside test function")
        return "test result"
    
    print("✓ Decorated function defined successfully")
    
except Exception as e:
    print(f"✗ Error occurred: {e}")
    print(f"Error type: {type(e).__name__}")
    import traceback
    print("Full traceback:")
    traceback.print_exc()
    
    # Try to get more info about the error
    print(f"\nDebugging info:")
    print(f"exec_func in globals: {'exec_func' in globals()}")
    print(f"exec_func in builtins: {hasattr(__builtins__, 'exec_func')}")
    
    # Check what's in builtins
    builtin_names = [name for name in dir(__builtins__) if 'exec' in name.lower()]
    print(f"Builtins with 'exec': {builtin_names}")

print("=== Script ending ===")