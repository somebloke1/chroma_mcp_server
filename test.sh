#!/bin/bash
# Run tests with coverage using the Python-based test runner with Hatch

# Install hatch if not installed
if ! command -v hatch &> /dev/null; then
    echo "Hatch not found. Installing hatch..."
    pip install hatch
fi

# Run tests using the Python test runner through Hatch
echo "Running tests with coverage using run_tests.py through Hatch..."
hatch run python run_tests.py --coverage --verbose

echo "Tests complete." 