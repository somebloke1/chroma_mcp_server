#!/bin/bash
# Script to simplify logging test results for validation evidence

# Exit on error
set -e

# Determine script location and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "Running test results logging in $PROJECT_ROOT..."

# Change to project root directory
cd "${PROJECT_ROOT}"
echo "ℹ️ Changed working directory to project root: $PROJECT_ROOT"

# Default values
COLLECTION_NAME="test_results_v1"
VERBOSE=""

# Parse command line arguments
while [ "$#" -gt 0 ]; do
    case "$1" in
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        -x|--xml)
            XML_PATH="$2"
            shift 2
            ;;
        -b|--before-xml)
            BEFORE_XML="$2"
            shift 2
            ;;
        --commit-before)
            COMMIT_BEFORE="$2"
            shift 2
            ;;
        --commit-after)
            COMMIT_AFTER="$2"
            shift 2
            ;;
        -c|--collection)
            COLLECTION_NAME="$2"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1"
            exit 1
            ;;
    esac
done

# Check required parameters
if [ -z "$XML_PATH" ]; then
    echo "Error: --xml path is required"
    echo "Usage: $0 --xml XML_PATH [--before-xml XML_PATH] [--commit-before HASH] [--commit-after HASH] [--collection NAME] [--verbose]"
    exit 1
fi

# Check that XML file exists
if [ ! -f "$XML_PATH" ]; then
    echo "Error: XML file not found: $XML_PATH"
    exit 1
fi

# Build and execute command
COMMAND="chroma-mcp-client log-test-results \"$XML_PATH\""

# Add optional parameters if provided
if [ ! -z "$BEFORE_XML" ]; then
    if [ ! -f "$BEFORE_XML" ]; then
        echo "Warning: Before XML file not found: $BEFORE_XML"
    fi
    COMMAND="$COMMAND --before-xml \"$BEFORE_XML\""
fi

if [ ! -z "$COMMIT_BEFORE" ]; then
    COMMAND="$COMMAND --commit-before \"$COMMIT_BEFORE\""
fi

if [ ! -z "$COMMIT_AFTER" ]; then
    COMMAND="$COMMAND --commit-after \"$COMMIT_AFTER\""
fi

COMMAND="$COMMAND --collection-name \"$COLLECTION_NAME\" $VERBOSE"

echo "Executing: $COMMAND"
eval $COMMAND 