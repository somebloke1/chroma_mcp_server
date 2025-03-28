#!/bin/bash
# Shell script to test the Chroma MCP server

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================================================${NC}"
echo -e "${BLUE}             Testing Chroma MCP Server Connection               ${NC}"
echo -e "${BLUE}=================================================================${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Activate virtual environment if it exists
if [ -d "$ROOT_DIR/.venv" ]; then
    echo "Activating virtual environment..."
    source "$ROOT_DIR/.venv/bin/activate"
fi

# Run the verify_chroma_mcp.py script
python "$SCRIPT_DIR/verify_chroma_mcp.py"

# Check the exit code
if [ $? -eq 0 ]; then
    echo -e "${GREEN}=================================================================${NC}"
    echo -e "${GREEN}                 Chroma MCP Test Successful!                     ${NC}"
    echo -e "${GREEN}=================================================================${NC}"
    echo -e "${GREEN}The Chroma MCP server is running correctly and responding to     ${NC}"
    echo -e "${GREEN}requests. You can now use the Chroma MCP tools within Cursor.    ${NC}"
    echo -e "${GREEN}=================================================================${NC}"
    exit 0
else
    echo -e "${RED}=================================================================${NC}"
    echo -e "${RED}                    Chroma MCP Test Failed!                      ${NC}"
    echo -e "${RED}=================================================================${NC}"
    echo -e "${RED}The Chroma MCP server failed to respond correctly.               ${NC}"
    echo -e "${RED}Check the logs at $ROOT_DIR/logs/chroma_mcp_server.log           ${NC}"
    echo -e "${RED}and ensure the server is properly configured.                    ${NC}"
    echo -e "${RED}=================================================================${NC}"
    exit 1
fi 