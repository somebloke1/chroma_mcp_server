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
    hatch run test:cov # Step 1: Run tests to generate data
    echo "Combining parallel coverage data..."
    coverage combine # Step 2: Combine data files directly
    echo "Generating HTML coverage report..."
    hatch run cov-report:html # Step 3: Generate report from combined data
elif [ "$COVERAGE" = true ]; then
    echo "Running tests across matrix for coverage..."
    hatch run test:cov # Step 1: Run tests to generate data
    echo "Combining parallel coverage data..."
    coverage combine # Step 2: Combine data files directly
    echo "Generating terminal coverage report..."
    hatch run cov-report:term # Step 3: Generate report from combined data
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