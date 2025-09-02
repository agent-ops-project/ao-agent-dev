# JSON Module Monkey Patching Plan

## Overview
Add taint tracking and random position preservation for Python's built-in `json` module functions: `dumps`, `loads`, `dump`, and `load`.

## Analysis of Existing Patterns
From examining `builtin_patches.py`, the codebase follows these patterns:
- Use `forbiddenfruit.curse()` for patching methods on built-in types
- Direct function replacement for module-level functions
- Store original methods in `_original_methods` to avoid recursion
- Use `inject_random_marker()` and `remove_random_marker()` for position tracking
- Combine taint origins from all input sources using `get_taint_origins()`
- Return `TaintStr` objects when taint information exists

## JSON Module Function Analysis

### Input/Output Flow:
1. **json.loads(s)**: JSON string → Python object
   - Taint source: JSON string `s`
   - Taint target: String values in resulting Python object

2. **json.dumps(obj)**: Python object → JSON string  
   - Taint source: String values in Python object `obj`
   - Taint target: Resulting JSON string

3. **json.load(fp)**: File object → Python object
   - Taint source: Content read from file object `fp`
   - Taint target: String values in resulting Python object

4. **json.dump(obj, fp)**: Python object → File object
   - Taint source: String values in Python object `obj`
   - Taint target: Content written to file object `fp` (challenging to track)

## Implementation Strategy

### 1. json.loads() Patch
- Parse JSON normally first to get the object structure
- Use `taint_wrap()` to recursively wrap the entire result object with taint from input string
- This will automatically create TaintStr, TaintDict, TaintList objects as needed
- Preserves nested structure while adding taint tracking

### 2. json.dumps() Patch  
- Use `get_taint_origins()` to collect all taint information from input object (handles nested structures)
- Use marker injection on tainted string values before serialization
- Parse result to extract marker positions for the final JSON string
- Return TaintStr with combined taint origins and position tracking

## Key Challenges & Solutions

### Challenge 1: Deep Object Traversal
JSON can contain nested structures (lists, dicts). Need recursive traversal.
**Solution**: Use existing `taint_wrap()` function from `taint_wrappers.py` which already handles recursive wrapping of nested objects with `TaintDict`, `TaintList`, etc.

### Challenge 2: Marker Position Mapping
Markers in JSON string don't directly map to object string positions.
**Solution**: Track markers during parsing, map back to final string positions.

### Challenge 3: Multiple Taint Sources
Objects may contain multiple tainted strings from different sources.
**Solution**: Use existing `get_taint_origins()` function to collect all taint sources from nested objects.

### Challenge 4: File Object Handling
File objects have complex state and may not support position tracking.
**Solution**: Focus on load/loads first, handle dump/dumps file operations simply.

## Implementation Order
1. `json.loads()` - Core string-to-object transformation
2. `json.dumps()` - Core object-to-string transformation

**Note**: Only implementing `loads` and `dumps` for now. File operations (`load`/`dump`) will be deferred.

## Testing Strategy
- Test basic taint propagation (tainted input → tainted output)
- Test random position preservation through JSON transformations
- Test nested object structures (lists, dicts, mixed)
- Test edge cases: empty objects, None values, special characters
- Test round-trip operations (loads→dumps→loads)
- Test combination with existing patches (e.g., tainted strings from re module)

**Note**: File operation tests removed since we're only implementing `loads` and `dumps`.

## Code Structure
```python
def json_patch():
    """Patches related to json module for taint propagation."""
    _store_json_original_methods()
    
    # Replace module-level functions  
    json.loads = _cursed_json_loads
    json.dumps = _cursed_json_dumps

def _cursed_json_loads(s, ...):
    """Tainted version of json.loads()."""
    # Parse JSON normally first
    # Use taint_wrap() to recursively wrap result with taint from input string
    
def _cursed_json_dumps(obj, ...):
    """Tainted version of json.dumps()."""
    # Use marker injection on string values in object
    # Serialize with markers, then extract positions
    # Return TaintStr with combined taint origins

# Note: The taint_wrap() function from taint_wrappers.py will handle:
# - Recursive traversal of nested objects
# - Proper wrapping with TaintDict, TaintList, TaintStr, etc.
# - Taint origin collection and propagation
```

This plan ensures comprehensive taint tracking while following established patterns in the codebase.