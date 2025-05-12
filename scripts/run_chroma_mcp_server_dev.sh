#!/bin/bash
# Add known location of user-installed bins to PATH
export PATH="/usr/local/bin:$PATH" # Adjust path as needed
set -euo pipefail
# Run chroma-mcp-server-dev using Hatch

# --- Define Project Root ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# --- Change to Project Root ---
cd "$PROJECT_ROOT"
# Don't print the working directory change as it will break the MCP server integration here
echo "{\"info\": \"Changed working directory to project root: $PROJECT_ROOT\"}" >> logs/run_chroma_mcp_server_dev.log

# Install hatch if not installed
if ! command -v hatch &> /dev/null; then
    echo "{\"warning\": \"Hatch not found. Installing now...\"}"
    pip install --user hatch
fi

# Ensure logs directory exists
mkdir -p "$PROJECT_ROOT/logs"

# --- Set Environment Variables ---
export PYTHONUNBUFFERED=1
export CHROMA_LOG_DIR="$PROJECT_ROOT/logs"
export MCP_SERVER_LOG_LEVEL="${MCP_SERVER_LOG_LEVEL:-INFO}"

# --- Run the Server ---
echo "{\"info\": \"Starting chroma-mcp-server-dev with PYTHONUNBUFFERED=1 and MCP_SERVER_LOG_LEVEL=$MCP_SERVER_LOG_LEVEL\"}" >> logs/run_chroma_mcp_server_dev.log
exec hatch run chroma-mcp-server-dev