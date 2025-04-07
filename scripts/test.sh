#!/bin/bash
# Run tests with coverage using Hatch

# --- Define Project Root ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# --- Change to Project Root ---
cd "$PROJECT_ROOT"
echo "ℹ️ Changed working directory to project root: $PROJECT_ROOT"

# Install hatch if not installed
if ! command -v hatch &> /dev/null; then
    echo "Hatch not found. Installing hatch..."
    pip install hatch
fi

# Parse command line arguments
COVERAGE=false
VERBOSE=false
HTML=false
CLEAN_ENV=false

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
        --clean)
            CLEAN_ENV=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--coverage|-c] [--verbose|-v] [--html] [--clean]"
            exit 1
            ;;
    esac
done

# Remove environment if clean flag is set
if [ "$CLEAN_ENV" = true ]; then
    echo "Removing existing test environment..."
    hatch env remove test
    echo "Test environment removed."
fi

# Run tests based on options
echo "Running tests with Hatch..."

# Ensure coverage tool is available for combine step later
# We might need this if combine is run directly in the script context
# Consider adding coverage to global path or project dev dependencies
# pip install coverage # Uncomment if needed, though hatch should manage envs

if [ "$HTML" = true ]; then
    echo "Running tests across matrix for HTML coverage..."
    # Run tests, generate parallel data (no report flag needed in pytest call)
    hatch run test:html # Alias 'html' in hatch config runs pytest
    echo "Combining parallel coverage data..."
    # Use hatch run to ensure coverage is available in the correct env
    hatch run coverage combine
    echo "Generating HTML coverage report..."
    hatch run coverage html # Use hatch run to ensure coverage is available
elif [ "$COVERAGE" = true ]; then
    echo "Running tests across matrix for coverage..."
    # Run tests, generate parallel data
    hatch run test:cov # Alias 'cov' in hatch config runs pytest
    echo "Combining parallel coverage data..."
    hatch run coverage combine
    echo "Generating XML and terminal coverage report..."
    hatch run coverage xml # Generate XML for Codecov
    hatch run coverage report -m # Show terminal report
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