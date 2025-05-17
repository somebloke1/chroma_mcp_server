#!/bin/bash
# Wrapper script to run the chat history analysis via hatch

# Exit on error
set -e

# Determine script location and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "Running chat history analysis in $PROJECT_ROOT..."

# Documentation on available parameters
# --collection-name: Specify the ChromaDB collection name (default: chat_history_v1)
# --repo-path: Path to Git repository (default: current directory)
# --status-filter: Filter by metadata status value (default: captured)
# --new-status: Set status after analysis (default: analyzed)
# --days-limit: How many days back to look for entries (default: 7)
# --prioritize-by-confidence: Sort entries by confidence score (default: false)
# -v/--verbose: Increase logging verbosity

# Change to project root directory
cd "${PROJECT_ROOT}"

# Execute the chroma-mcp-client analyze-chat-history subcommand using hatch
# Pass all arguments received by this script to the subcommand
TOKENIZERS_PARALLELISM=false hatch run chroma-mcp-client analyze-chat-history "$@"

exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "Error: Chat history analysis failed with exit code $exit_code"
    exit $exit_code
else
    echo "Chat history analysis finished."
fi

exit 0 