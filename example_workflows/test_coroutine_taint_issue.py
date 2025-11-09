import asyncio
import functools

from aco.runner.taint_wrappers import TaintStr

def with_timeout(timeout_s: float = 5.0):
    """Simplified version of the problematic decorator."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # This is where the problem occurs:
            # asyncio.wait_for is third-party and gets wrapped by exec_func
            # but it receives a coroutine object, not raw tainted data
            return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_s)
        return wrapper
    return decorator

# Simulate user code that should preserve taint
@with_timeout(2.0)
async def user_function_that_returns_tainted_data(user_input):
    result = "processed"
    return result

async def demonstrate_issue():
    """Demonstrate the taint loss issue."""
    
    print("=== Coroutine Taint Issue Demonstration ===\n")
    
    # Create tainted input
    tainted_input = TaintStr("sensitive_data", ["user_input"])
    print(f"1. Original tainted input: {tainted_input}")
    print(f"   Taint origins: {getattr(tainted_input, '_taint_origin', 'None')}\n")
    
    # Call the decorated function
    print("2. Calling @with_timeout decorated function...")
    print("   This creates: asyncio.wait_for(user_function(...), timeout)")
    print("   Problem: asyncio.wait_for gets wrapped by exec_func")
    print("   But it receives a coroutine object, not the raw tainted data\n")
    
    try:
        result = await user_function_that_returns_tainted_data(tainted_input)
        print(f"3. Result: {result}")
        print(f"   Taint origins: {getattr(result, '_taint_origin', 'None')}")
        
        if hasattr(result, '_taint_origin'):
            print("   ✓ Taint preserved (this is what should happen)")
        else:
            print("   ✗ Taint lost (this is the current problem)")
            
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    asyncio.run(demonstrate_issue())
    
    print("""
=== The Problem Explained ===

1. User writes: @with_timeout(2.0) async def user_func(tainted_data): ...

2. Decorator creates: 
   async def wrapper(*args, **kwargs):
       return await asyncio.wait_for(user_func(*args, **kwargs), timeout_s)

3. When called, this becomes:
   asyncio.wait_for(coroutine_object, 2.0)

4. Our AST transformer sees 'asyncio.wait_for' as third-party and wraps it with exec_func

5. exec_func receives:
   - func = asyncio.wait_for  
   - args = (coroutine_object, 2.0)
   - The coroutine_object contains taint, but exec_func doesn't know how to extract it

6. Result: exec_func calls asyncio.wait_for with untainted arguments, 
   losing the taint that was inside the coroutine.

=== Solution Needed ===

We need exec_func to understand that coroutine objects can carry taint
and preserve that taint through coroutine transformation functions like asyncio.wait_for.
""")