# CodeQL LLM Taint Analysis Tool

A specialized static analysis tool that uses **CodeQL** to detect data flows between LLM API calls (OpenAI and Anthropic) in Python codebases.

## 🎯 Purpose

This tool performs **true taint analysis** (not pattern matching) to identify cases where:
- Data from one LLM API call flows into another LLM API call
- Sensitive information might be leaked between different LLM services
- Connected vs independent LLM calls can be distinguished

## ✨ Key Features

- **True Data Flow Analysis**: Uses CodeQL's powerful taint tracking
- **No User Code Modification**: Analyzes codebases without touching user files
- **LLM-Specific**: Focused on OpenAI and Anthropic API calls  
- **Path Visualization**: Shows complete data flow paths
- **SARIF Output**: Industry-standard results format

## 🚀 Quick Start

### 1. Setup
```bash
# Make setup script executable
chmod +x setup.sh

# Run setup (downloads CodeQL CLI and standard library)
./setup.sh
```

### 2. Test Installation
```bash
# Run test analysis on example file
./scripts/run_analysis.py --test
```

### 3. Analyze User Code
```bash
# Analyze a directory
./scripts/run_analysis.py /path/to/user/code
```

## 📁 Directory Structure

```
codeql-analyst/
├── setup.sh              # Installation script
├── config.json           # Configuration
├── README.md             # This file
├── scripts/
│   └── run_analysis.py    # Main analysis script
├── queries/
│   └── llm-taint.ql      # CodeQL query for LLM taint analysis
├── databases/            # CodeQL databases (auto-created)
├── results/              # Analysis results (auto-created)
├── codeql-cli/          # CodeQL CLI binaries (auto-downloaded)
└── codeql-repo/         # CodeQL standard library (auto-downloaded)
```

## 🔍 How It Works

1. **Database Creation**: CodeQL creates a semantic database from Python source code
2. **Taint Analysis**: Custom query tracks data flows from LLM API responses to LLM API inputs
3. **Path Discovery**: Identifies complete flow paths through the codebase
4. **Result Reporting**: Outputs findings with detailed flow information

## 📊 Example Output

```
🔍 Found 1 LLM taint flow(s):
============================================================

--- Finding #1 ---
Rule: python/llm-taint-flow
Message: Data flows from LLM API call here to another LLM API call, potentially exposing sensitive information.
Location: example.py:23

🔄 Taint Flow Path:
  1. example.py:7 - OpenAI API response
  2. example.py:15 - Data assigned to variable
  3. example.py:23 - Variable used in Anthropic API call
```

## 🎯 Client Requirements Met

- ✅ **True taint analysis** (not pattern matching like Semgrep)
- ✅ **No user codebase modification** (analysis runs externally)
- ✅ **Detects connected vs independent flows**
- ✅ **Works with OpenAI and Anthropic APIs**
- ✅ **Shows complete data flow paths**

## 🔧 Configuration

Edit `config.json` to customize:
- Supported LLM APIs and methods
- Output formats
- Query parameters

## 🐛 Troubleshooting

### CodeQL not found
```bash
# Re-run setup
./setup.sh

# Or specify custom path
./scripts/run_analysis.py /path/to/code --codeql-path /custom/codeql/path
```

### No results found
- Ensure the target code actually has LLM API calls
- Check that OpenAI/Anthropic modules are imported
- Verify data flows exist between different LLM calls

### Database creation fails
- Ensure target directory contains Python files
- Check file permissions
- Verify sufficient disk space

## 📝 Notes

- **Language Support**: Currently Python only
- **API Support**: OpenAI and Anthropic (easily extensible)
- **Performance**: Scales well with codebase size
- **Accuracy**: True semantic analysis, minimal false positives

## 🆚 vs Other Tools

| Tool | Analysis Type | Accuracy | Setup Complexity |
|------|---------------|----------|------------------|
| **CodeQL** | True taint analysis | High | Medium |
| Semgrep | Pattern matching | Low | Low |
| Pyre | Taint analysis | High | High (requires repo modification) |

This tool provides the accuracy of Pyre without requiring modifications to the user's codebase. 