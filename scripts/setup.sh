#!/bin/bash

# Exit on error
set -e

echo "🚀 Setting up Chroma MCP Server development environment..."

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.12"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then 
    echo "❌ Error: Python $required_version or higher is required (you have $python_version)"
    exit 1
fi

# Create and activate virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv .venv

# Determine the correct activate script based on OS
if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
    source .venv/bin/activate
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    source .venv/Scripts/activate
else
    echo "❌ Error: Unsupported operating system"
    exit 1
fi

# Upgrade pip to latest version
echo "🔄 Upgrading pip..."
python -m pip install --upgrade pip

# Install build dependencies
echo "🏗️ Installing build dependencies..."
python -m pip install build wheel setuptools setuptools_scm

# Install the package in editable mode with dev dependencies
echo "📥 Installing package in development mode..."
python -m pip install -e ".[dev]"

# Install all requirements
echo "📚 Installing requirements..."
python -m pip install -r requirements.txt

# Verify installation
echo "✅ Verifying installation..."
python -c "import chromadb; import fastmcp; print('✨ Core dependencies verified')"

echo "
🎉 Setup completed successfully!

To activate the virtual environment:
  source .venv/bin/activate    # On Unix/macOS
  .venv\\Scripts\\activate      # On Windows

To deactivate:
  deactivate

To run tests:
  pytest

To run the server:
  python -m chroma_mcp.server
" 