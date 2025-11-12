# Agent Copilot (Agent Ops)

Agent Copilot is a development tool for LLM call visualization and debugging that helps developers understand data flow between LLM calls in their agentic AI applications.

## Project Overview

This project provides a comprehensive development environment for analyzing, debugging, and visualizing AI agent workflows. The tool intercepts and tracks LLM calls, traces data flow between them, and presents this information through interactive user interfaces.

### Key Features

- **LLM Call Tracking**: Monkey-patches popular LLM APIs (OpenAI, Anthropic, VertexAI, etc.) to intercept and log calls
- **Data Flow Analysis**: Tracks "taint" propagation from one LLM call to another through the program execution
- **Interactive Visualization**: VS Code extension and web app for viewing call graphs and data flow
- **Caching & Editing**: Cache LLM responses and allow users to edit inputs/outputs for experimentation
- **Multiple Workflows**: Support for various AI benchmarks and evaluation workflows

## Architecture

The system consists of three main components:

1. **User Program Runner**: `aco-launch` command that feels like running `python` normally but with monitoring
2. **Development Server**: Core analysis engine that processes logs and updates UI via TCP socket (port 5959)
3. **User Interface**: VS Code extension and web app for visualization and interaction

### How It Works

1. **AST Transformation**: File watcher daemon rewrites Python files to propagate "taint" through third-party library calls
2. **Monkey Patching**: LLM API calls are intercepted to log inputs/outputs and wrap results with taint information
3. **Taint Propagation**: Data flow is tracked from LLM outputs through program execution until reaching another LLM
4. **Visualization**: Interactive graph shows LLM calls as nodes and data dependencies as edges

## Installation & Setup

### Python Environment

This is how you would install the code:
```bash
# Activate environment
source ~/miniforge3/bin/activate aco

# Install package
pip install -e .

# Install UI dependencies
cd src/user_interfaces && npm install
npm run build:all
```

### Development Setup
```bash
# Install with dev dependencies
pip install -e ".[dev]"
pre-commit install
cd src/user_interfaces && npm run build:all

# Create symlink for linters
ln -s src aco
```

## Running the System

### Basic Usage
Replace `python` with `aco-launch` to run your scripts with monitoring:
```bash
# Instead of: python script.py
aco-launch script.py

# Instead of: python -m foo.bar
aco-launch -m foo.bar

# With environment variables
ENV_VAR=5 aco-launch script.py --some-flag
```

For Claude code, use this
```bash
~/miniforge3/envs/aco/bin/python -m aco.cli.aco_launch script.py
```


### Server Management
```bash
aco-server start    # Start the development server
aco-server stop     # Stop the server
aco-server restart  # Restart after code changes
aco-server clear    # Clear runs and cached LLM calls
aco-server logs     # View server logs
```

### User Interface
- **VS Code Extension**: Run "Run Extension" from debugger, then open projects in the new window
- **Web App**: `cd src/user_interfaces/web_app && node server.js`, then `npm run dev:webapp`

## Testing

```bash
# Run specific tests
source ~/miniforge3/bin/activate aco && python -m pytest -v tests/

# Run taint tests
source ~/miniforge3/bin/activate aco && python -m pytest -v tests/taint/
```

## Example Workflows

The project includes several example workflows in `example_workflows/`:

### Simple Workflows
- `debug_examples/`: Basic debugging workflows (OpenAI, Anthropic examples)
- `ours_doc_bench/`: Questions over PDFs
- `ours_human_eval/`: Code evaluation benchmark

### Medium Workflows  
- `chess_text2sql/`: Text-to-SQL benchmark (CHESS)
- `bird/`: BIRD Text2SQL benchmark

### Complex Workflows
- `miroflow_deep_research/`: MiroFlow open-source deep research agent
- `ours_swe_bench/`: SWE-bench benchmark for code fixing

## Key Directories

- `src/cli/`: Command-line interface (`aco-launch`, `aco-server`, `aco-config`)
- `src/server/`: Core analysis server, AST transformation, file watching
- `src/runner/`: User program execution, monkey patching, taint wrappers
- `src/user_interfaces/`: VS Code extension and web app
- `tests/`: Unit tests, especially taint propagation tests
- `example_workflows/`: Various AI workflow examples

## Configuration

Use `aco-config` to set the project root for example workflows. Some examples are git submodules requiring separate access permissions.

## Development Notes

- Server runs on TCP port 5959 by default
- File changes trigger automatic AST rewrites and compilation to `.pyc` files
- LLM calls are cached in SQLite database for replay/editing
- Taint wrappers track data provenance through program execution
- Pre-commit hooks maintain code quality