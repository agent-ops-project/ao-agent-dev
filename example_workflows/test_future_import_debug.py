#!/usr/bin/env python3
"""
Test script to debug __future__ import handling in AST rewriting.
"""

import ast
import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from aco.server.ast_transformer import TaintPropagationTransformer


def test_future_import_handling():
    """Test that __future__ imports are handled correctly in AST rewriting."""
    
    print("=" * 60)
    print("Testing __future__ import handling in AST rewriting")
    print("=" * 60)
    
    # Test code with __future__ import and third-party call
    test_code = '''from __future__ import annotations

import json

def test_function():
    data = {"test": "data"}
    result = json.dumps(data)  # Third-party call -> should be rewritten
    return result
'''
    
    print("Original code:")
    print(test_code)
    
    # Parse the original AST
    tree = ast.parse(test_code, filename="test_future.py")
    
    print("\nOriginal AST structure:")
    for i, node in enumerate(tree.body):
        print(f"  {i}: {type(node).__name__}", end="")
        if isinstance(node, ast.ImportFrom):
            print(f" from {node.module}")
        elif isinstance(node, ast.Import):
            print(f" {[alias.name for alias in node.names]}")
        else:
            print()
    
    # Apply transformer
    print(f"\nApplying AST transformation...")
    module_to_file = {}  # Empty so everything is third-party
    transformer = TaintPropagationTransformer(
        module_to_file=module_to_file, 
        current_file="test_future.py"
    )
    
    # Transform the tree
    new_tree = transformer.visit(tree)
    
    # Inject imports
    new_tree = transformer._inject_taint_imports(new_tree)
    
    print(f"\nTransformed AST structure:")
    for i, node in enumerate(new_tree.body):
        print(f"  {i}: {type(node).__name__}", end="")
        if isinstance(node, ast.ImportFrom):
            print(f" from {node.module}")
        elif isinstance(node, ast.Import):
            print(f" {[alias.name for alias in node.names]}")
        elif isinstance(node, ast.Try):
            print(" (try block for safe import)")
        else:
            print()
    
    # Try to convert back to source and compile
    try:
        import astor
        rewritten_source = astor.to_source(new_tree)
        
        print("\nRewritten source code:")
        print("=" * 40)
        print(rewritten_source)
        print("=" * 40)
        
        # Test compilation
        try:
            compiled = compile(new_tree, "test_future.py", "exec")
            print("✓ SUCCESS: Rewritten code compiles correctly!")
        except SyntaxError as e:
            print(f"✗ SYNTAX ERROR: {e}")
            print(f"Error at line {e.lineno}: {e.text}")
            
    except ImportError:
        print("astor not available - testing compilation directly")
        
        # Test compilation without source conversion
        try:
            compiled = compile(new_tree, "test_future.py", "exec")
            print("✓ SUCCESS: Rewritten AST compiles correctly!")
        except SyntaxError as e:
            print(f"✗ SYNTAX ERROR: {e}")


def test_real_problematic_file():
    """Test the actual problematic file that's failing."""
    
    print("\n" + "=" * 60)
    print("Testing real problematic file")
    print("=" * 60)
    
    problematic_file = "/Users/jub/agent-copilot/example_workflows/miroflow_deep_research/MiroFlow/libs/miroflow-contrib/tests/tracing/test_tracing.py"
    
    try:
        with open(problematic_file, 'r') as f:
            source_code = f.read()
        
        print(f"Reading file: {problematic_file}")
        
        # Parse the original AST
        tree = ast.parse(source_code, filename=problematic_file)
        
        print(f"\nFirst 10 nodes of original AST:")
        for i, node in enumerate(tree.body[:10]):
            print(f"  {i}: {type(node).__name__}", end="")
            if isinstance(node, ast.ImportFrom):
                print(f" from {node.module}")
            elif isinstance(node, ast.Import):
                print(f" {[alias.name for alias in node.names]}")
            else:
                print()
        
        # Apply transformer
        module_to_file = {}  # Empty so everything is third-party
        transformer = TaintPropagationTransformer(
            module_to_file=module_to_file, 
            current_file=problematic_file
        )
        
        # Transform the tree
        new_tree = transformer.visit(tree)
        
        # Inject imports
        new_tree = transformer._inject_taint_imports(new_tree)
        
        print(f"\nFirst 10 nodes after transformation:")
        for i, node in enumerate(new_tree.body[:10]):
            print(f"  {i}: {type(node).__name__}", end="")
            if isinstance(node, ast.ImportFrom):
                print(f" from {node.module}")
            elif isinstance(node, ast.Import):
                print(f" {[alias.name for alias in node.names]}")
            elif isinstance(node, ast.Try):
                print(" (try block for safe import)")
            else:
                print()
        
        # Test compilation
        try:
            compiled = compile(new_tree, problematic_file, "exec")
            print("✓ SUCCESS: Real file compiles correctly after transformation!")
        except SyntaxError as e:
            print(f"✗ SYNTAX ERROR in real file: {e}")
            print(f"Error at line {e.lineno}")
            
    except Exception as e:
        print(f"Error processing real file: {e}")


if __name__ == "__main__":
    test_future_import_handling()
    test_real_problematic_file()