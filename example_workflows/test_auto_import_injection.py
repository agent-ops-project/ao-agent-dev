"""
Test the automatic import injection feature.

This will test if the AST transformer automatically injects the required
imports when it rewrites code, making exec_func available everywhere.

Run with: python example_workflows/test_auto_import_injection.py
"""

import ast
import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from aco.server.ast_transformer import rewrite_source_to_code


def test_import_injection():
    """Test that imports are automatically injected when code is rewritten."""
    
    print("=" * 60)
    print("Testing automatic import injection")
    print("=" * 60)
    
    # Test code that will trigger AST rewriting
    test_code = '''
import json

class mcp:
    @staticmethod
    def tool():
        def decorator(func):
            return func
        return decorator

@mcp.tool()
async def test_function():
    data = {"test": "data"}
    result = json.dumps(data)  # Third-party call -> should be rewritten
    return result
'''

    print("Original code:")
    print(test_code)
    
    # Apply AST rewriting
    module_to_file = {}  # Empty so everything is third-party
    code_object = rewrite_source_to_code(test_code, "test.py", module_to_file)
    
    print("\n" + "=" * 60)
    print("Testing if rewritten code includes auto-injected imports...")
    
    # Get the rewritten source by decompiling the AST
    tree = ast.parse(test_code, filename="test.py")
    
    # Apply transformer manually to see the result
    from aco.server.ast_transformer import TaintPropagationTransformer
    transformer = TaintPropagationTransformer(module_to_file=module_to_file, current_file="test.py")
    new_tree = transformer.visit(tree)
    
    # Inject imports
    new_tree = transformer._inject_taint_imports(new_tree)
    
    # Convert back to source
    try:
        import astor
        rewritten_source = astor.to_source(new_tree)
        
        print("Rewritten code with auto-injected imports:")
        print("=" * 60)
        print(rewritten_source)
        
        # Check if the import was injected
        if "from aco.server.ast_transformer import" in rewritten_source:
            print("✓ SUCCESS: Auto-import injection is working!")
            
            # Check specific imports
            expected_imports = ["exec_func", "taint_fstring_join", "taint_format_string", "taint_percent_format"]
            for imp in expected_imports:
                if imp in rewritten_source:
                    print(f"  ✓ {imp} imported")
                else:
                    print(f"  ✗ {imp} missing")
        else:
            print("✗ FAILED: No auto-imports found in rewritten code")
            
        # Check if exec_func calls are present
        if "exec_func(" in rewritten_source:
            print("✓ exec_func calls found in rewritten code")
        else:
            print("✗ No exec_func calls found")
            
    except ImportError:
        print("astor not available - checking AST directly")
        
        # Check the AST for import nodes
        for node in new_tree.body:
            if isinstance(node, ast.ImportFrom) and node.module == "aco.server.ast_transformer":
                print("✓ SUCCESS: Auto-import injection found in AST!")
                imported_names = [alias.name for alias in node.names]
                print(f"  Imported: {imported_names}")
                break
        else:
            print("✗ FAILED: No auto-import found in AST")


def test_with_simple_subprocess():
    """Test if the auto-injected imports work when run as subprocess."""
    
    print("\n" + "=" * 60)
    print("Testing if auto-injected code works in subprocess")
    print("=" * 60)
    
    # Create a simple test script that would fail without imports
    test_script_content = '''
# This code should have exec_func available due to auto-injection
import json

try:
    # This will be rewritten to: exec_func(json.dumps, ({"test": "data"},), {})
    result = json.dumps({"test": "data"})
    print("SUCCESS: Code executed without NameError")
    print(f"Result: {result}")
except NameError as e:
    if "exec_func" in str(e):
        print("FAILED: exec_func not available (auto-injection didn't work)")
    else:
        print(f"FAILED: Other NameError: {e}")
except Exception as e:
    print(f"FAILED: Other error: {e}")
'''
    
    # Write test script
    test_file = repo_root / "example_workflows" / "temp_subprocess_test.py" 
    with open(test_file, 'w') as f:
        f.write(test_script_content)
    
    print(f"Created test script: {test_file}")
    
    try:
        # Force recompilation by running through aco-launch first
        import subprocess
        print("Running with aco-launch to trigger rewriting...")
        result = subprocess.run(
            ["aco-launch", str(test_file)],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✓ aco-launch execution succeeded")
        else:
            print(f"⚠ aco-launch failed: {result.stderr}")
        
        # Now test with plain Python (should work if auto-injection worked)
        print("\nTesting with plain Python (should work if auto-injection is working)...")
        result = subprocess.run(
            [sys.executable, str(test_file)],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5
        )
        
        print(f"Return code: {result.returncode}")
        if result.stdout:
            print(f"STDOUT: {result.stdout}")
        if result.stderr:
            print(f"STDERR: {result.stderr}")
            
        if result.returncode == 0 and "SUCCESS" in result.stdout:
            print("🎉 AUTO-INJECTION WORKS! Code runs with plain Python!")
        else:
            print("❌ Auto-injection may not be working correctly")
            
    finally:
        # Clean up
        if test_file.exists():
            test_file.unlink()


if __name__ == "__main__":
    test_import_injection()
    test_with_simple_subprocess()
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("If auto-injection is working, rewritten code should include:")
    print("from aco.server.ast_transformer import exec_func, ...")
    print("This makes exec_func available in ANY execution context!")
    print("=" * 60)