#!/usr/bin/env python3
"""Simple debug test to check if re patches are working"""

import re
import sys
import os

# Add agent-copilot to path
sys.path.insert(0, "/Users/ferdi/Documents/agent-copilot/src")

from aco.runner.taint_wrappers import TaintStr, get_taint_origins
from aco.runner.monkey_patching.apply_monkey_patches import apply_all_monkey_patches

print("=== Debug RE Test ===")

# Apply patches
print("Applying monkey patches...")
apply_all_monkey_patches()

# Test basic TaintStr creation
print("\n1. Testing TaintStr creation:")
tainted = TaintStr("Hello world test", taint_origin=["debug_test"])
print(f"  Created: {type(tainted)} with content '{tainted}'")
print(f"  Taint origins: {get_taint_origins(tainted)}")

# Test re.search directly
print("\n2. Testing re.search directly:")
pattern = re.compile(r"world")
match = pattern.search(tainted)
print(f"  Match found: {match is not None}")
if match:
    group = match.group()
    print(f"  Group type: {type(group)}")
    print(f"  Group content: '{group}'")
    print(f"  Group taint origins: {get_taint_origins(group)}")

# Test module-level re.search
print("\n3. Testing module-level re.search:")
match2 = re.search(r"world", tainted)
print(f"  Match found: {match2 is not None}")
if match2:
    group2 = match2.group()
    print(f"  Group type: {type(group2)}")
    print(f"  Group content: '{group2}'")
    print(f"  Group taint origins: {get_taint_origins(group2)}")

print("\n=== End Debug ===")
