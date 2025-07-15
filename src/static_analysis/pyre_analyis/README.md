# Pyre-Analyst: LLM Data Flow Detection

Fast static analysis tool that detects data flows between LLM API calls using Pyre/Pysa without modifying user codebases.

## Features

- 🚀 **Fast Analysis**: Leverages Pyre's daemon and incremental analysis capabilities
- ⚡ **Incremental Mode**: Only re-analyzes changed files for maximum performance  
- 🔒 **Non-Invasive**: No modifications to user repositories required
- 🤖 **LLM-Focused**: Detects flows between OpenAI, Anthropic, and other LLM APIs
- 🔄 **AST Transformation**: Handles complex patterns automatically
- 📊 **JSON Output**: Machine-readable results with line/column precision
- 🔧 **Daemon Mode**: Background server for fast repeated analysis
- 📁 **Smart Caching**: Persistent analysis cache for improved performance

## Quick Start

Follow these steps to get started:

1.  **Run the setup script** (first time only):
    ```bash
    ./setup.sh
    ```

2.  **Activate the virtual environment**:
    Before running an analysis, always activate the virtual environment:
    ```bash
    source venv/bin/activate
    ```
    You should see `(venv)` appear in your shell prompt.

3.  **Analyze a Python codebase**:
    ```bash
    python3 scripts/run_analysis.py /path/to/user/codebase
    ```

4.  **Test with an example file**:
    ```bash
    python3 scripts/run_analysis.py --test
    ```

5.  **Use incremental mode for faster repeated analysis**:
    ```bash
    # First run - sets up cache
    python3 scripts/run_analysis.py --incremental /path/to/user/codebase
    
    # Subsequent runs - only analyzes changed files
    python3 scripts/run_analysis.py --incremental /path/to/user/codebase --changed file1.py file2.py
    ```

6.  **Manage Pyre daemon for background processing**:
    ```bash
    python3 scripts/run_analysis.py --start-daemon    # Start daemon
    python3 scripts/run_analysis.py --daemon-status   # Check status  
    python3 scripts/run_analysis.py --stop-daemon     # Stop daemon
    ```

## How It Works

1. **AST Transformation**: Simplifies complex LLM patterns into basic function calls
2. **Isolated Analysis**: Runs Pyre in a temporary environment 
3. **Taint Analysis**: Treats all LLM calls as both sources and sinks
4. **Result Mapping**: Maps findings back to original code locations

## Example Output

```json
[
  {
    "line": 15,
    "column": 26,
    "path": "user_code.py",
    "code": 5001,
    "name": "LLM data flow",
    "description": "Data from OpenAI call flows to Anthropic call",
    "source": "openai.chat.completions.create",
    "sink": "anthropic.messages.create"
  }
]
```

## Supported Patterns

- ✅ Direct LLM API calls (OpenAI, Anthropic)
- ✅ Variable assignments and flows
- ✅ Dictionary operations (automatic)
- ✅ Function calls (pass-through taint)
- ✅ Member variable patterns (transformed)
- ✅ Complex nested patterns

## Requirements

- Python 3.8+
- Pyre-check
- LibCST (for AST transformation)

## Configuration

Edit `config.json` to customize:
- LLM API patterns to detect
- Analysis timeout settings
- Output format preferences 