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
VERBOSE_LEVEL=0 # 0: default, 1: -v, 2: -vv, 3: -vvv
HTML=false
CLEAN_ENV=false
TEST_PATHS=()
PYTHON_VERSION=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage|-c)
            COVERAGE=true
            shift
            ;;
        -vvv)
            VERBOSE_LEVEL=3
            shift
            ;;
        -vv)
            # Only set if not already -vvv
            [[ $VERBOSE_LEVEL -lt 3 ]] && VERBOSE_LEVEL=2
            shift
            ;;
        --verbose|-v)
            # Only set if not already -vv or -vvv
            [[ $VERBOSE_LEVEL -lt 2 ]] && VERBOSE_LEVEL=1
            shift
            ;;
        --html)
            HTML=true
            COVERAGE=true # HTML implies coverage
            shift
            ;;
        --clean)
            CLEAN_ENV=true
            shift
            ;;
        --python|--py)
            if [[ -z "$2" || "$2" == -* ]]; then
                echo "Error: --python requires a version argument (e.g., 3.10, 3.11, 3.12)"
                exit 1
            fi
            PYTHON_VERSION="$2"
            shift 2
            ;;
        -*)
            echo "Unknown option: $1"
            echo "Usage: $0 [--coverage|-c] [-v|-vv|-vvv] [--html] [--clean] [--python VERSION] [test_path1 test_path2 ...]"
            echo "  --python, --py VERSION    Run tests only on specified Python version (e.g., 3.10, 3.11, 3.12)"
            exit 1
            ;;
        *)
            # Collect all non-option arguments as test paths
            TEST_PATHS+=("$1")
            shift
            ;;
    esac
done

# Remove environment if clean flag is set
if [ "$CLEAN_ENV" = true ]; then
    echo "Removing existing test environment..."
    hatch env remove test
    echo "Test environment removed."
fi

# Build the base pytest command arguments
# Using the settings we found work reliably (timeout, no xdist)
PYTEST_BASE_ARGS="--timeout=10 -p no:xdist"

# Add verbosity flag if requested
VERBOSITY_FLAG=""
if [ "$VERBOSE_LEVEL" -eq 1 ]; then
    VERBOSITY_FLAG="-v"
elif [ "$VERBOSE_LEVEL" -eq 2 ]; then
    VERBOSITY_FLAG="-vv"
elif [ "$VERBOSE_LEVEL" -eq 3 ]; then
    VERBOSITY_FLAG="-vvv"
fi

PYTEST_ARGS="$PYTEST_BASE_ARGS $VERBOSITY_FLAG"

# Add test paths if specified, otherwise use the default tests/ directory
if [ ${#TEST_PATHS[@]} -gt 0 ]; then
    echo "Running specified test path(s): ${TEST_PATHS[*]}"
    PYTEST_ARGS="$PYTEST_ARGS ${TEST_PATHS[*]}"
else
    echo "Running all tests in tests/ directory"
    PYTEST_ARGS="$PYTEST_ARGS tests/"
fi

# Determine the execution command based on coverage flag and Python version
if [ -n "$PYTHON_VERSION" ]; then
    # Format the Python version into the hatch environment name (e.g., test.py3.10)
    # First, ensure the version doesn't already start with "py"
    if [[ "$PYTHON_VERSION" == py* ]]; then
        PY_ENV="test.$PYTHON_VERSION"
    else
        PY_ENV="test.py$PYTHON_VERSION"
    fi
    echo "Limiting tests to Python version $PYTHON_VERSION (environment: $PY_ENV)"
    
    if [ "$COVERAGE" = true ]; then
        echo "Running tests with Coverage enabled (Verbosity: $VERBOSE_LEVEL)..."
        RUN_CMD="hatch -e $PY_ENV run coverage run -m pytest $PYTEST_ARGS"
    else
        echo "Running tests without Coverage (Verbosity: $VERBOSE_LEVEL)..."
        RUN_CMD="hatch -e $PY_ENV run python -m pytest $PYTEST_ARGS"
    fi
else
    # Run on all Python versions using the default test matrix
    if [ "$COVERAGE" = true ]; then
        echo "Running tests with Coverage enabled (Verbosity: $VERBOSE_LEVEL)..."
        RUN_CMD="hatch run test:coverage run -m pytest $PYTEST_ARGS"
    else
        echo "Running tests without Coverage (Verbosity: $VERBOSE_LEVEL)..."
        RUN_CMD="hatch run test:python -m pytest $PYTEST_ARGS"
    fi
fi

# Execute the tests
echo "Executing: $RUN_CMD"
$RUN_CMD # Execute the constructed command
EXIT_CODE=$?

# Check if pytest run failed (exit code 1 or higher)
# Exit code 0 is success, others indicate issues.
if [ $EXIT_CODE -ne 0 ]; then
    echo "❌ Pytest run exited with non-zero code: $EXIT_CODE"
    # Optionally, be more specific: if [ $EXIT_CODE -eq 1 ]; then echo "Test failures occurred"; fi
    exit $EXIT_CODE
fi

# Handle coverage reporting if coverage was enabled
if [ "$COVERAGE" = true ]; then
    echo "✅ Coverage run finished."
    echo "<<< Coverage run finished >>>"
    # Comment out ALL subsequent coverage commands
    echo "Combining parallel coverage data (if any)..."
    hatch run coverage combine --quiet
    echo "Generating XML coverage report..."
    hatch run coverage xml # Generate XML for Codecov
    echo "Generating XML terminal coverage report..."
    hatch run coverage report -m # Show terminal report
    if [ "$HTML" = true ]; then
        echo "Generating HTML coverage report..."
        hatch run coverage html
    fi
    echo "<<< Coverage combination finished >>>"
fi

echo "✅ Tests complete."
exit 0 