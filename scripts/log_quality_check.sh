#!/bin/bash
# Script to simplify logging code quality metrics for validation evidence

# Exit on error
set -e

# Determine script location and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "Running quality check logging in $PROJECT_ROOT..."

# Change to project root directory
cd "${PROJECT_ROOT}"
echo "ℹ️ Changed working directory to project root: $PROJECT_ROOT"

# Default values
COLLECTION_NAME="validation_evidence_v1"
VERBOSE=""
TOOL="pylint"
METRIC_TYPE="error_count"

# Parse command line arguments
while [ "$#" -gt 0 ]; do
    case "$1" in
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        -t|--tool)
            TOOL="$2"
            shift 2
            ;;
        -b|--before)
            BEFORE_OUTPUT="$2"
            shift 2
            ;;
        -a|--after)
            AFTER_OUTPUT="$2"
            shift 2
            ;;
        -m|--metric)
            METRIC_TYPE="$2"
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
if [ -z "$AFTER_OUTPUT" ]; then
    echo "Error: --after output file is required"
    echo "Usage: $0 --after FILE [--before FILE] [--tool TOOL] [--metric TYPE] [--collection NAME] [--verbose]"
    exit 1
fi

# Check that after file exists
if [ ! -f "$AFTER_OUTPUT" ]; then
    echo "Error: After output file not found: $AFTER_OUTPUT"
    exit 1
fi

# Build and execute command
COMMAND="chroma-mcp-client log-quality-check --tool \"$TOOL\" --after-output \"$AFTER_OUTPUT\""

# Add optional parameters if provided
if [ ! -z "$BEFORE_OUTPUT" ]; then
    if [ ! -f "$BEFORE_OUTPUT" ]; then
        echo "Warning: Before output file not found: $BEFORE_OUTPUT"
    fi
    COMMAND="$COMMAND --before-output \"$BEFORE_OUTPUT\""
fi

COMMAND="$COMMAND --metric-type \"$METRIC_TYPE\" --collection-name \"$COLLECTION_NAME\" $VERBOSE"

echo "Executing: $COMMAND"
eval $COMMAND 