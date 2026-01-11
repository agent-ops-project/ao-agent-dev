# Taint Tracking

AO tracks data flow ("taint") between LLM calls using an ID-based dictionary, AST rewriting, and a file watcher process.

## Overview

The taint tracking system answers: "Which LLM calls influenced this value?"

When an LLM produces output, that output is "tainted" with the LLM call's ID. As the data flows through the program, the taint information propagates. When tainted data reaches another LLM call, we know there's a data dependency.

## Core Architecture

### TAINT_DICT

`TAINT_DICT` is a global thread-safe dictionary that maps object IDs to their taint origins:

```python
{id(obj): (obj, [origin_ids])}
```

Where:
- `id(obj)` is the object's memory address (stable while we hold a reference)
- `obj` is the actual object (kept alive to prevent id reuse)
- `[origin_ids]` is the list of taint origin identifiers

Key properties:
1. **Direct storage:** All objects (including built-ins like int, str, list) are stored directly
2. **Uniform handling:** All objects are treated the same way regardless of type
3. **Prevents id reuse:** Storing the object reference prevents garbage collection

### Taint Propagation Example

Consider the following program:

```python
a = llm_call("hello")
b = llm_call("bye")
c = a + b
c += "hello"
d = llm_call(c)
```

Its functions and operations (e.g., `+`) will be wrapped such that taint is propagated: `a`, `b`, `c` and `d` will all have an entry in `TAINT_DICT`. `a`'s entry will record that `a` was produced by the first LLM call, `b` by the second, `c`'s entry will be a list with both origins, etc.

### TAINT_STACK

`TAINT_STACK` passes taint through third-party code boundaries. It's used for communication between `exec_func` and monkey-patched code.

We don't rewrite "third-party functions" (e.g., `llm_call()`) for performance reasons. Instead:

1. `exec_func` collects taint from all arguments → pushes onto `TAINT_STACK`
2. Calls the (un-rewritten) third-party function
3. If the function is monkey-patched (e.g., LLM call), the patch calls `read()` to get input origins, then `update()` to set its own node ID
4. After the function returns, `exec_func` pops the stack and applies taint to the outputs

#### Why a Stack? LangChain Example

Consider a LangChain agent with a user-defined tool:

```python
@tool
def get_weather(city: str) -> str:
    data = requests.get(f"https://weather.api/{city}").json()  # third-party call
    return f"Weather in {city}: {data['temp']}"

agent = create_react_agent(llm, [get_weather])
agent.invoke("What's the weather in SF?")
```

The execution flow:
```
1. exec_func(agent.invoke) → push []
   Stack: [()]

2. LangChain calls LLM #1 (decides to use tool)
   → httpx patch: read()=[], update([n1])
   Stack: [([n1],)]

3. LangChain calls user's get_weather (AST-rewritten, called directly)
   Inside get_weather, requests.get triggers:
   → exec_func(requests.get) → push []
   Stack: [([n1],), ()]
   → exec_func pops
   Stack: [([n1],)]  ← n1 preserved!

4. LangChain calls LLM #2 (formats final answer)
   → httpx patch: read()=[n1] ✓ (edge n1→n2 created!)
   → update([n2])
   Stack: [([n2],)]

5. exec_func(agent.invoke) pops
   Stack: []
```

**What the stack solves:** Nested `exec_func` calls (step 3) don't overwrite the outer taint context. Each level has its own stack entry.

**What the stack doesn't solve:** ContextVar isolation. LangChain uses `copy_context().run()` to execute each step, which discards ContextVar changes when it returns. We solve this with task-keyed storage (keyed by `asyncio.current_task()` or thread ID) instead of ContextVar.

**Current limitations (TODOs):**

1. **User tool taint not propagated to TAINT_STACK:** If the user's tool returns a tainted variable (e.g., from a nested LLM call), that taint is stored in `TAINT_DICT` but not reflected in `TAINT_STACK`. From the third-party framework's perspective, user tool calls are "taint in = taint out" - the output carries the same taint as the inputs, not the tool's internal taint.

2. **User tools not logged as graph nodes:** When LangChain calls a user-defined tool, we don't create a node in the dataflow graph for it, even though it's semantically a tool call. Only LLM calls currently appear as nodes.

## AST Rewriting

The AST transformer rewrites user code to track taint through all operations:

| Original Code | Transformed Code |
|---------------|------------------|
| `x = value` | `x = taint_assign(value)` |
| `obj.attr` | `get_attr(obj, 'attr')` |
| `obj[key]` | `get_item(obj, key)` |
| `obj.attr = value` | `set_attr(obj, 'attr', value)` |
| `obj[key] = value` | `exec_setitem(obj, key, value)` |
| `func(args)` | `exec_func(func, (args,), {})` |
| `obj.method(args)` | `exec_func(obj, (args,), {}, method_name='method')` |
| `a + b` | `exec_func(operator.add, (a, b), {})` |
| `f"hello {x}"` | `taint_fstring_join("hello ", x)` |

### What exec_func Does

For **user code** (AST-rewritten): Calls directly. The AST rewrites handle taint propagation.

For **third-party code**:
1. Collect taint from parent object (for methods) and all arguments
2. Push taint onto `TAINT_STACK`
3. Call the function
4. Pop stack and apply taint to result

## String De-interning

Python has a performance optimization that makes `id("hello") == id("hello")` for short strings. This is a problem since two `"hello"` strings may have been produced by different LLM calls (or one may have been produced by no LLM call at all).

We enforce that Python gives a unique id to each string by encoding and decoding it:

```python
def _de_intern_string(s):
    """Create a copy of string s with a unique id (not interned)."""
    return s.encode("utf-8").decode("utf-8")
```

## File Watcher

The file watcher is a daemon process that pre-compiles AST-rewritten Python files.

### How It Works

1. Server spawns the file watcher on startup
2. File watcher monitors all `.py` files in the user's project
3. When a file changes:
   - Read the source file
   - Apply AST transformations
   - Compile to `.pyc` in `~/.cache/ao/pyc`

### Why Pre-compile?

Pre-compilation eliminates runtime overhead:

- AST transformation happens before execution
- Python loads pre-compiled `.pyc` files natively
- No startup delay for the user

### AST Rewrite Hook

The import hook (`ast_rewrite_hook.py`) is needed because:

1. **Custom cache location:** The `.pyc` files are stored in `~/.cache/ao/pyc/` with hashed filenames, not the standard `__pycache__` directory. Python's default import machinery won't find them there.
2. **Fallback compilation:** If the `.pyc` is missing or stale, the hook compiles on-demand via `rewrite_source_to_code()`.
3. **User code tracking:** It populates `_module_to_user_file` as modules are imported, which the taint system uses to distinguish user code from third-party code.
4. **FileWatcher notification:** When a file is compiled on-demand (cache miss), it notifies the FileWatcher to start monitoring that file.

The flow is: `ASTImportFinder.find_spec()` → checks if module should be rewritten → `ASTImportLoader.source_to_code()` → tries cached `.pyc` first → falls back to `rewrite_source_to_code()` if cache miss.

## User Code vs Third-Party Code

We only rewrite "user code". We blacklist certain modules (e.g., ones defined in `site-packages`) because rewritten code incurs larger import times. This is a pure performance optimization as third-party library imports (`import os`, `import openai`, etc) often import many files.

For "third-party functions", we just assume the taint of its inputs is also the taint of its outputs. See `ast_transformer.py` and `ast_helpers.py` for more details (there are some edge cases).

## Caching and Reruns

When an LLM call is intercepted (e.g., in `httpx_patch.py`), the following happens:

1. **Cache lookup**: `DB.get_in_out()` hashes the input and looks it up by `(session_id, input_hash)`. The `database_manager.py` handles all cache operations.

2. **Cache hit**: If a matching entry exists:
   - If `input_overwrite` is set (user edited input in UI), use the modified input instead
   - If `output` is cached (from previous run or user-edited), return it directly without calling the LLM

3. **Cache miss**: If no entry exists or output is `None`:
   - Call the actual LLM with the (possibly overwritten) input
   - Store the result via `DB.cache_output()` for future runs

4. **Graph update**: `send_graph_node_and_edges()` notifies the server to update the UI with the node and its edges (from taint tracking).

**Reruns work deterministically** because:
- The same `session_id` (inherited from parent) means cache lookups find previous entries
- Cached outputs are returned without re-calling the LLM
- Users can modify inputs/outputs via the UI, and these overwrites are respected on rerun
- Randomness is patched (random, numpy, torch) to produce the same sequence given the same seed

This enables interactive debugging: run once, inspect the graph, edit an LLM's input or output, and rerun to see how changes propagate through the dataflow.

## Why Both AST Rewriting and Monkey Patching?

| Mechanism | Use Case | Reason |
|-----------|----------|--------|
| **Monkey Patching** | LLM API calls | Custom handling for each API (parse inputs/outputs) |
| **AST Rewriting** | All other library calls | Generic taint propagation without per-library code |

## Next Steps

- [API patching](api-patching.md) - How LLM APIs are intercepted
- [Testing](testing.md) - Running the test suite
