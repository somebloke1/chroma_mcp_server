#!/bin/bash
# Script to simplify logging runtime errors for validation evidence

# Exit on error
set -e

# Determine script location and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "Running error logging in $PROJECT_ROOT..."

# Change to project root directory
cd "${PROJECT_ROOT}"
echo "ℹ️ Changed working directory to project root: $PROJECT_ROOT"

# Default values
COLLECTION_NAME="validation_evidence_v1"
VERBOSE=""

# Parse command line arguments
while [ "$#" -gt 0 ]; do
    case "$1" in
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        -t|--error-type)
            ERROR_TYPE="$2"
            shift 2
            ;;
        -m|--message)
            ERROR_MESSAGE="$2"
            shift 2
            ;;
        -s|--stacktrace)
            STACKTRACE="$2"
            shift 2
            ;;
        -f|--files)
            AFFECTED_FILES="$2"
            shift 2
            ;;
        -r|--resolution)
            RESOLUTION="$2"
            shift 2
            ;;
        --verified)
            RESOLUTION_VERIFIED="--resolution-verified"
            shift
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
if [ -z "$ERROR_TYPE" ] || [ -z "$ERROR_MESSAGE" ]; then
    echo "Error: --error-type and --message are required"
    echo "Usage: $0 --error-type TYPE --message MSG [--stacktrace TRACE] [--files FILES] [--resolution RES] [--verified] [--collection NAME] [--verbose]"
    exit 1
fi

# Build and execute command
COMMAND="chroma-mcp-client log-error --error-type \"$ERROR_TYPE\" --error-message \"$ERROR_MESSAGE\""

# Add optional parameters if provided
if [ ! -z "$STACKTRACE" ]; then
    COMMAND="$COMMAND --stacktrace \"$STACKTRACE\""
fi

if [ ! -z "$AFFECTED_FILES" ]; then
    COMMAND="$COMMAND --affected-files \"$AFFECTED_FILES\""
fi

if [ ! -z "$RESOLUTION" ]; then
    COMMAND="$COMMAND --resolution \"$RESOLUTION\""
fi

if [ ! -z "$RESOLUTION_VERIFIED" ]; then
    COMMAND="$COMMAND $RESOLUTION_VERIFIED"
fi

COMMAND="$COMMAND --collection-name \"$COLLECTION_NAME\" $VERBOSE"

echo "Executing: $COMMAND"
eval $COMMAND 