#!/bin/bash
# Wrapper script for running the interactive chat review and promotion workflow.
# Usage: ./scripts/review_and_promote.sh [--days-limit N] [--fetch-limit M] ...
# Arguments are passed directly to the chroma-client review-and-promote command.

set -e # Exit immediately if a command exits with a non-zero status.

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Navigate to the project root directory (assuming the script is in ./scripts/)
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# Execute the command via hatch, passing all arguments
# Use the module execution path for reliability within hatch run
echo "Running interactive promoter via: hatch run python -m chroma_mcp_client.cli review-and-promote $@"
hatch run python -m chroma_mcp_client.cli review-and-promote "$@"

echo "Interactive promotion script finished." 