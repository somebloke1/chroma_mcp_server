#!/bin/bash
# Script to simplify validating evidence for promotion

# Exit on error
set -e

# Determine script location and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "Running evidence validation for promotion in $PROJECT_ROOT..."

# Change to project root directory
cd "${PROJECT_ROOT}"
echo "ℹ️ Changed working directory to project root: $PROJECT_ROOT"

# Default values
THRESHOLD="0.7"
VERBOSE=""

# Parse command line arguments
while [ "$#" -gt 0 ]; do
    case "$1" in
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        -f|--file)
            EVIDENCE_FILE="$2"
            shift 2
            ;;
        -t|--test-ids)
            TEST_TRANSITIONS="$2"
            shift 2
            ;;
        -r|--runtime-ids)
            RUNTIME_ERRORS="$2"
            shift 2
            ;;
        -q|--quality-ids)
            CODE_QUALITY="$2"
            shift 2
            ;;
        --threshold)
            THRESHOLD="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1"
            exit 1
            ;;
    esac
done

# Check that at least one evidence source is provided
if [ -z "$EVIDENCE_FILE" ] && [ -z "$TEST_TRANSITIONS" ] && [ -z "$RUNTIME_ERRORS" ] && [ -z "$CODE_QUALITY" ]; then
    echo "Error: At least one evidence source is required"
    echo "Usage: $0 [--file FILE] [--test-ids IDS] [--runtime-ids IDS] [--quality-ids IDS] [--threshold NUM] [--output FILE] [--verbose]"
    exit 1
fi

# Check that evidence file exists if provided
if [ ! -z "$EVIDENCE_FILE" ] && [ ! -f "$EVIDENCE_FILE" ]; then
    echo "Error: Evidence file not found: $EVIDENCE_FILE"
    exit 1
fi

# Build and execute command
COMMAND="chroma-mcp-client validate-evidence --threshold $THRESHOLD"

# Add evidence sources
if [ ! -z "$EVIDENCE_FILE" ]; then
    COMMAND="$COMMAND --evidence-file \"$EVIDENCE_FILE\""
fi

if [ ! -z "$TEST_TRANSITIONS" ]; then
    COMMAND="$COMMAND --test-transitions \"$TEST_TRANSITIONS\""
fi

if [ ! -z "$RUNTIME_ERRORS" ]; then
    COMMAND="$COMMAND --runtime-errors \"$RUNTIME_ERRORS\""
fi

if [ ! -z "$CODE_QUALITY" ]; then
    COMMAND="$COMMAND --code-quality \"$CODE_QUALITY\""
fi

if [ ! -z "$OUTPUT_FILE" ]; then
    COMMAND="$COMMAND --output-file \"$OUTPUT_FILE\""
fi

COMMAND="$COMMAND $VERBOSE"

echo "Executing: $COMMAND"
eval $COMMAND 