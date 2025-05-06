#!/bin/bash
# Run chroma-mcp-server-dev using Hatch

# --- Define Project Root ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# --- Change to Project Root ---
cd "$PROJECT_ROOT"
# Don't print the working directory change as it will break the MCP server integration here
# echo "ℹ️ Changed working directory to project root: $PROJECT_ROOT"

# Install hatch if not installed
if ! command -v hatch &> /dev/null; then
    echo "Hatch not found. Installing hatch..."
    pip install hatch
fi

hatch run chroma-mcp-server-dev "$@"