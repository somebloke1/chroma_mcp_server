#!/bin/bash
# Wrapper script to run the promote-learning command via hatch

# Exit on error
set -e

# Determine script location and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "Running promote-learning in $PROJECT_ROOT..."

# Documentation on available parameters
# --description: Natural language description of the learning (required)
# --pattern: Core pattern identified (required)
# --code-ref: Code reference illustrating the learning (required)
# --tags: Comma-separated tags for categorization (required)
# --confidence: Confidence score between 0.0 and 1.0 (required)
# --source-chat-id: ID of the source entry in the chat history collection
# --collection-name: Target collection for the new learning (default: derived_learnings_v1)
# --chat-collection-name: Source chat history collection (default: chat_history_v1)
# --include-chat-context: Include rich context from the source chat entry (default: true)
# --no-include-chat-context: Don't include rich context from the source chat entry

# Change to project root directory
cd "${PROJECT_ROOT}"

# Execute the chroma-client promote-learning subcommand using hatch
# Pass all arguments received by this script to the subcommand
# Use python -m syntax for robustness with hatch if needed
hatch run chroma-client promote-learning "$@"
# Alternatively: hatch run python -m chroma_mcp_client.cli promote-learning "$@"

exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "Error: promote-learning failed with exit code $exit_code"
    exit $exit_code
else
    echo "promote-learning finished successfully."
fi

exit 0 