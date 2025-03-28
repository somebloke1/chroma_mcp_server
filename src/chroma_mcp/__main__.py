#!/usr/bin/env python3
"""
Entry point for the Chroma MCP Server when run as a Python module.
Allows the server to be started with 'python -m src.chroma_mcp'.
"""

from src.chroma_mcp.server import main

if __name__ == "__main__":
    main() 