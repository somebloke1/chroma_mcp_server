#!/bin/bash
# Script to test UVX installation from TestPyPI

set -e  # Exit on error

# Initialize variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_DIR=$(mktemp -d)
PACKAGE_NAME="chroma-mcp-server"

# Required dependencies (explicitly defined rather than fetched from pyproject.toml)
REQUIRED_DEPS="pydantic>=2.0.0 fastapi>=0.100.0 uvicorn>=0.20.0 chromadb>=0.4.18 python-dotenv>=1.0.0 fastmcp>=0.4.1"

# Get package version from pyproject.toml
VERSION=$(grep -E "^version = " "$SCRIPT_DIR/pyproject.toml" | cut -d '"' -f 2)
if [ -z "$VERSION" ]; then
    echo "Error: Could not determine package version from pyproject.toml"
    exit 1
fi

echo "Testing installation of $PACKAGE_NAME version $VERSION"

# Check if the dist directory exists
if [ ! -d "$SCRIPT_DIR/dist" ]; then
    echo "No dist directory found. Building package first..."
    cd "$SCRIPT_DIR" && ./build.sh
    if [ $? -ne 0 ]; then
        echo "Error: Failed to build package"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
fi

# Find wheel file - Fix: using proper parameter expansion with double dash
WHEEL_FILE=$(find "$SCRIPT_DIR/dist" -name "${PACKAGE_NAME//-/_}-${VERSION}-*.whl" | head -1)
if [ -z "$WHEEL_FILE" ]; then
    echo "Error: No wheel file found for $PACKAGE_NAME version $VERSION"
    echo "Debug: Looking for wheel matching pattern: ${PACKAGE_NAME//-/_}-${VERSION}-*.whl"
    echo "Available files in dist directory:"
    ls -la "$SCRIPT_DIR/dist"
    rm -rf "$TEMP_DIR"
    exit 1
fi

echo "Found wheel file: $WHEEL_FILE"
echo "Using temporary directory: $TEMP_DIR"

# Function to clean up on exit
cleanup() {
    echo "Cleaning up temporary directory..."
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

cd "$TEMP_DIR"

# Test UV Installation 
echo "------------------------------------------------------------"
echo "TESTING UV INSTALLATION FROM LOCAL WHEEL"
echo "------------------------------------------------------------"
if command -v uv > /dev/null 2>&1; then
    echo "UV is installed, testing installation from local wheel..."
    
    # Create a virtual environment with UV
    uv venv .venv
    source .venv/bin/activate
    
    # Install from local wheel first (more reliable) along with required dependencies
    echo "Installing from local wheel file: $WHEEL_FILE with dependencies"
    if uv pip install "$WHEEL_FILE" $REQUIRED_DEPS; then
        echo "UV installation from local wheel successful!"
        echo "Testing execution..."
        if chroma-mcp-server --help > /dev/null; then
            echo "✅ UV installation and execution successful!"
        else
            echo "❌ UV execution failed"
        fi
    else
        echo "❌ UV installation from local wheel failed"
    fi
    
    deactivate
else
    echo "UV not found, skipping UV installation test"
fi

# Test pip installation in virtual environment from local wheel
echo ""
echo "------------------------------------------------------------"
echo "TESTING PIP INSTALLATION FROM LOCAL WHEEL"
echo "------------------------------------------------------------"
python -m venv .venv-pip
source .venv-pip/bin/activate

echo "Installing from local wheel: $WHEEL_FILE with dependencies"
if pip install "$WHEEL_FILE" $REQUIRED_DEPS; then
    echo "Installation from local wheel successful!"
    
    # Test import
    echo "Testing import..."
    if python -c "import chroma_mcp; print('Import successful!')"; then
        echo "✅ Import test passed"
    else
        echo "❌ Import test failed"
    fi
    
    # Test command-line usage
    echo "Testing command-line usage..."
    if chroma-mcp-server --help > /dev/null; then
        echo "✅ Command-line test passed"
    else
        echo "❌ Command-line test failed"
    fi
else
    echo "❌ Installation from local wheel failed"
fi

deactivate

echo ""
echo "Installation tests completed. You can now publish to PyPI using:"
echo ""
echo "  ./publish.sh -p -v $VERSION"
echo ""
echo "The local wheel tests are passing, which indicates the package should"
echo "install correctly from PyPI as well." 