#!/bin/bash
# scripts/thinking.sh - Internal wrapper for thinking CLI
# This script is for internal use within the repository

# Exit on error
set -e

# Determine script location and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Find Python executable (use environment variable if set, or default to 'python')
if [ -z "${PYTHON_EXECUTABLE}" ]; then
    # Check if we're in a virtual environment
    if [ -n "${VIRTUAL_ENV}" ]; then
        PYTHON_EXECUTABLE="${VIRTUAL_ENV}/bin/python"
    else
        PYTHON_EXECUTABLE="python"
    fi
fi

# Check if Python executable exists
if ! command -v "${PYTHON_EXECUTABLE}" &> /dev/null; then
    echo "Error: Python executable not found: ${PYTHON_EXECUTABLE}" >&2
    exit 1
fi

# Execute the Python CLI module with all arguments passed to this script
cd "${PROJECT_ROOT}"
"${PYTHON_EXECUTABLE}" -m chroma_mcp_thinking.thinking_cli "$@" 