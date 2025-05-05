#!/bin/bash
# Wrapper script to run the chat history analysis via hatch

# Exit on error
set -e

# Determine script location and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "Running chat history analysis in $PROJECT_ROOT..."

# Change to project root directory
cd "${PROJECT_ROOT}"

# Execute the chroma-client analyze-chat-history subcommand using hatch
# Pass all arguments received by this script to the subcommand
hatch run chroma-client analyze-chat-history "$@"

exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "Error: Chat history analysis failed with exit code $exit_code"
    exit $exit_code
else
    echo "Chat history analysis finished."
fi

exit 0 