#!/bin/bash

echo "🚀 Setting up CodeQL LLM Taint Analysis Tool"

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment detected: $VIRTUAL_ENV"
else
    echo "⚠️  Warning: No virtual environment detected. Consider using a venv."
fi

# Create directories
echo "📁 Creating directory structure..."
mkdir -p queries
mkdir -p databases
mkdir -p results
mkdir -p scripts

# Download and install CodeQL CLI
echo "📦 Downloading CodeQL CLI..."
CODEQL_VERSION="2.22.0"
PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')

if [[ "$PLATFORM" == "darwin" ]]; then
    PLATFORM="osx64"
elif [[ "$PLATFORM" == "linux" ]]; then
    PLATFORM="linux64"
else
    echo "❌ Unsupported platform: $PLATFORM"
    exit 1
fi

CODEQL_URL="https://github.com/github/codeql-cli-binaries/releases/download/v${CODEQL_VERSION}/codeql-${PLATFORM}.zip"

if [ ! -d "codeql-cli" ]; then
    echo "Downloading from: $CODEQL_URL"
    curl -L -o codeql-cli.zip "$CODEQL_URL"
    unzip codeql-cli.zip
    # Rename the extracted folder to match expected name
    if [ -d "codeql" ] && [ ! -d "codeql-cli" ]; then
        mv codeql codeql-cli
    fi
    rm codeql-cli.zip
    echo "✅ CodeQL CLI downloaded"
else
    echo "✅ CodeQL CLI already exists"
fi

# Download CodeQL standard library
if [ ! -d "codeql-repo" ]; then
    echo "📚 Downloading CodeQL standard library..."
    git clone --depth 1 https://github.com/github/codeql.git codeql-repo
    echo "✅ CodeQL standard library downloaded"
else
    echo "✅ CodeQL standard library already exists"
fi

# Create qlpack.yml for queries
echo "🔧 Creating query pack configuration..."
cat > queries/qlpack.yml << 'EOF'
name: llm-taint-queries
version: 0.0.1
dependencies:
  codeql/python-all: "*"
EOF
echo "✅ Query pack configuration created"

# Make scripts executable
chmod +x scripts/*.py 2>/dev/null || true
chmod +x codeql-cli/codeql 2>/dev/null || true

# Add CodeQL to PATH for this session
export PATH="$PWD/codeql-cli:$PATH"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Test the installation:"
echo "   ./scripts/run_analysis.py --test"
echo ""
echo "2. Run on target codebase:"
echo "   ./scripts/run_analysis.py /path/to/user/code"
echo ""
echo "3. View results:"
echo "   cat results/latest-results.sarif"
echo ""
echo "✅ CodeQL LLM Taint Analysis Tool is ready!" 