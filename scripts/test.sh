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
LOG_RESULTS=false  # Added flag for logging results to validation system
BEFORE_XML=""  # Path to before XML for comparison
AUTO_CAPTURE_WORKFLOW=false  # Flag for automatic test workflow capture

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
        --log-results)
            LOG_RESULTS=true
            shift
            ;;
        --auto-capture-workflow)
            AUTO_CAPTURE_WORKFLOW=true
            LOG_RESULTS=true  # Auto-capture implies logging results
            shift
            ;;
        --before-xml)
            if [[ -z "$2" || "$2" == -* ]]; then
                echo "Error: --before-xml requires a path to JUnit XML file"
                exit 1
            fi
            BEFORE_XML="$2"
            shift 2
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
            echo "Usage: $0 [--coverage|-c] [-v|-vv|-vvv] [--html] [--clean] [--python VERSION] [--log-results] [--before-xml FILE] [--auto-capture-workflow] [test_path1 test_path2 ...]"
            echo "  --python, --py VERSION    Run tests only on specified Python version (e.g., 3.10, 3.11, 3.12)"
            echo "  --log-results             Log test results to the validation system"
            echo "  --before-xml FILE         Path to JUnit XML from before changes for comparison"
            echo "  --auto-capture-workflow   Automatically capture and process test workflow (failures & fixes)"
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

# Always generate JUnit XML output
XML_OUTPUT_PATH="test-results.xml"
PYTEST_XML_ARG="--junitxml=${XML_OUTPUT_PATH}"

# Build the base pytest command arguments
# Using the settings we found work reliably (timeout, no xdist)
PYTEST_BASE_ARGS="--timeout=10 -p no:xdist ${PYTEST_XML_ARG}"

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

# Get current git commit hash
CURRENT_COMMIT=$(git rev-parse HEAD || echo "unknown")

# Execute the tests
echo "Executing: $RUN_CMD"
$RUN_CMD # Execute the constructed command
EXIT_CODE=$?

# Check if JUnit XML was generated
if [ -f "${XML_OUTPUT_PATH}" ]; then
    echo "📊 Test results XML generated: ${XML_OUTPUT_PATH}"
    
    # Determine if tests failed
    TESTS_FAILED=false
    if [ $EXIT_CODE -ne 0 ]; then
        TESTS_FAILED=true
    fi
    
    # Handle automatic workflow capture
    if [ "$AUTO_CAPTURE_WORKFLOW" = true ]; then
        echo "🔄 Automatic test workflow capture enabled"
        
        # Save the run time for this test execution
        TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
        
        if [ "$TESTS_FAILED" = true ]; then
            # Save failing test results for future comparison
            FAILURE_XML="failed_tests_${TIMESTAMP}.xml"
            cp "${XML_OUTPUT_PATH}" "${FAILURE_XML}"
            echo "❌ Tests failed - saved results to ${FAILURE_XML} for future comparison"
            
            # Store the failure in validation system
            echo "📋 Registering test failure in workflow system..."
            python -m chroma_mcp_client.cli log-test-results "${XML_OUTPUT_PATH}"
            
            # Save commit hash for the failure
            echo "${CURRENT_COMMIT}" > "${FAILURE_XML}.commit"
            
            # Create a workflow state file
            echo "{\"status\": \"failed\", \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\", \"xml_path\": \"${FAILURE_XML}\", \"commit\": \"${CURRENT_COMMIT}\"}" > "test_workflow_${TIMESTAMP}.json"
            echo "🔍 Created workflow state file: test_workflow_${TIMESTAMP}.json"
        else
            # Tests passed - look for previous failures to compare with
            echo "✅ Tests passed - checking for previous failures to detect transitions"
            
            # Find the most recent workflow state file
            LATEST_WORKFLOW=$(ls -t test_workflow_*.json 2>/dev/null | head -n 1)
            
            if [ -n "$LATEST_WORKFLOW" ]; then
                echo "🔍 Found previous workflow state: ${LATEST_WORKFLOW}"
                
                # Extract the failure XML path from the workflow state
                FAILURE_XML=$(grep -o '"xml_path": "[^"]*"' "${LATEST_WORKFLOW}" | cut -d'"' -f4)
                FAILURE_COMMIT=$(grep -o '"commit": "[^"]*"' "${LATEST_WORKFLOW}" | cut -d'"' -f4)
                
                if [ -f "${FAILURE_XML}" ]; then
                    echo "🧪 Comparing with previous failure: ${FAILURE_XML}"
                    
                    # Run test transition detection with the found failure XML
                    echo "📊 Analyzing test transitions..."
                    python -m chroma_mcp_client.cli log-test-results "${XML_OUTPUT_PATH}" --before-xml "${FAILURE_XML}" --commit-before "${FAILURE_COMMIT}" --commit-after "${CURRENT_COMMIT}"
                    
                    # Mark workflow as complete
                    echo "{\"status\": \"transitioned\", \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\", \"before_xml\": \"${FAILURE_XML}\", \"after_xml\": \"${XML_OUTPUT_PATH}\", \"before_commit\": \"${FAILURE_COMMIT}\", \"after_commit\": \"${CURRENT_COMMIT}\"}" > "test_workflow_complete_${TIMESTAMP}.json"
                    echo "✅ Created completed workflow record: test_workflow_complete_${TIMESTAMP}.json"
                else
                    echo "⚠️ Previous failure XML not found: ${FAILURE_XML}"
                fi
            else
                echo "ℹ️ No previous test failures found to compare with"
            fi
        fi
    # Standard log results mode    
    elif [ "$LOG_RESULTS" = true ]; then
        echo "🔍 Logging test results to validation system..."
        
        # Base log command
        LOG_CMD="python -m chroma_mcp_client.cli log-test-results ${XML_OUTPUT_PATH}"
        
        # Add before XML if specified
        if [ -n "$BEFORE_XML" ]; then
            LOG_CMD="${LOG_CMD} --before-xml ${BEFORE_XML}"
            
            # Get git hash for the before file if possible
            # This is a simplistic approach - in a real system, you'd store this with the before file
            BEFORE_COMMIT="unknown"
            if [ -f "${BEFORE_XML}.commit" ]; then
                BEFORE_COMMIT=$(cat "${BEFORE_XML}.commit")
            fi
            
            LOG_CMD="${LOG_CMD} --commit-before ${BEFORE_COMMIT} --commit-after ${CURRENT_COMMIT}"
        fi
        
        # Execute log command
        echo "Executing: $LOG_CMD"
        $LOG_CMD
        
        # Save current commit hash for future comparisons
        echo "${CURRENT_COMMIT}" > "${XML_OUTPUT_PATH}.commit"
        echo "📝 Saved commit hash for future comparisons"
    fi
else
    echo "⚠️ No JUnit XML output found at ${XML_OUTPUT_PATH}"
fi

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
    
    # Log code quality metrics if requested
    if [ "$LOG_RESULTS" = true ]; then
        echo "🔍 Logging code quality metrics from coverage..."
        
        # Create temporary coverage output file
        COV_OUTPUT_FILE="coverage_output.txt"
        hatch run coverage report -m > "$COV_OUTPUT_FILE"
        
        # Log quality metrics
        echo "Executing: python -m chroma_mcp_client.cli log-quality-check --tool coverage --after-output ${COV_OUTPUT_FILE} --metric-type coverage"
        python -m chroma_mcp_client.cli log-quality-check --tool coverage --after-output "${COV_OUTPUT_FILE}" --metric-type coverage
        
        # Clean up temporary file
        rm -f "$COV_OUTPUT_FILE"
    fi
    
    if [ "$HTML" = true ]; then
        echo "Generating HTML coverage report..."
        hatch run coverage html
    fi
    echo "<<< Coverage combination finished >>>"
fi

echo "✅ Tests complete."
exit 0