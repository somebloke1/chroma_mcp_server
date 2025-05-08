#!/bin/bash
# Wrapper script to run the promote-learning command via hatch

# Exit on error
set -e

# Determine script location and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "Running promote-learning in $PROJECT_ROOT..."

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