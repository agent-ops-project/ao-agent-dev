#!/bin/bash
set -e

echo "🚀 Setting up Pyre-Analyst..."

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "📋 Python version: $python_version"

if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
    echo "❌ Python 3.8+ required"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
python3 -m pip install --upgrade pip

# Install required packages
echo "📚 Installing dependencies..."
python3 -m pip install pyre-check==0.9.23 libcst click==8.1.7

# Verify Pyre installation
echo "✅ Verifying Pyre installation..."
if pyre --version > /dev/null 2>&1; then
    echo "✅ Pyre installed successfully"
    pyre --version
else
    echo "❌ Pyre installation failed"
    exit 1
fi

# Create directories
echo "📁 Creating directory structure..."
mkdir -p results
mkdir -p temp

echo ""
echo "🎉 Setup complete!"
echo ""
echo "⚠️  Before running analysis, activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "🚀 Quick test:"
echo "   python3 scripts/run_analysis.py --test"
echo ""
echo "🔍 Analyze your code:"
echo "   python3 scripts/run_analysis.py /path/to/your/code"
echo "" 