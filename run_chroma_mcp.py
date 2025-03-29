#!/usr/bin/env python3
"""
Runner script for the Chroma MCP Server.
This properly sets up the Python path and runs the server module.
Maintained for backward compatibility.
"""

import os
import sys

# Add the current directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Import the CLI entry point and run it
from src.chroma_mcp.cli import main

if __name__ == "__main__":
    sys.exit(main()) 