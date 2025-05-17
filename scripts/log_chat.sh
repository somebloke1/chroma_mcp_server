#!/bin/bash
# Wrapper script to run the chat logging functionality via hatch
# Usage: ./scripts/log_chat.sh [--prompt-summary "..."] [--response-summary "..."] [other options]

# Exit on error
set -e

# Determine script location and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "Running chat logging in $PROJECT_ROOT..."

# Change to project root directory
cd "${PROJECT_ROOT}"

# Execute the chroma-mcp-client log-chat subcommand using hatch
# Pass all arguments received by this script to the subcommand
TOKENIZERS_PARALLELISM=false hatch run chroma-mcp-client log-chat "$@"

exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "Error: Chat logging failed with exit code $exit_code"
    exit $exit_code
else
    echo "Chat logging completed successfully."
fi

exit 0 