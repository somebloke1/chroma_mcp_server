#!/bin/bash
# Build the package

# Install hatch if not installed
if ! command -v hatch &> /dev/null; then
    echo "Hatch not found. Installing hatch..."
    pip install hatch
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info

# Build the package
echo "Building package with Hatch..."
hatch build

echo "Build complete. Distribution files are in the 'dist' directory."
ls -la dist/ 