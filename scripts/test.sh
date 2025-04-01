#!/bin/bash
# Run tests with coverage using Hatch

# Install hatch if not installed
if ! command -v hatch &> /dev/null; then
    echo "Hatch not found. Installing hatch..."
    pip install hatch
fi

# Parse command line arguments
COVERAGE=false
VERBOSE=false
HTML=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage|-c)
            COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --html)
            HTML=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--coverage|-c] [--verbose|-v] [--html]"
            exit 1
            ;;
    esac
done

# Run tests based on options
echo "Running tests with Hatch..."

if [ "$HTML" = true ]; then
    echo "Generating HTML coverage report..."
    hatch run test:html
elif [ "$COVERAGE" = true ]; then
    echo "Running tests with coverage..."
    hatch run test:cov
else
    if [ "$VERBOSE" = true ]; then
        echo "Running tests in verbose mode..."
        hatch run test:run -v
    else
        echo "Running tests..."
        hatch run test:run
    fi
fi

echo "Tests complete." 