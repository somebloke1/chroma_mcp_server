#!/bin/bash
# Simplified development setup

# Install hatch if not installed
if ! command -v hatch &> /dev/null; then
    echo "Hatch not found. Installing hatch..."
    pip install hatch
fi

# Create and enter hatch shell
echo "Starting development environment..."
hatch shell 