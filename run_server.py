#!/usr/bin/env python3
"""
Direct runner script for the Chroma MCP Server.
This script adds the src directory to the Python path and runs the server directly.
"""

import os
import sys
import argparse
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Now we can import from the package
from chroma_mcp.server import main

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run the Chroma MCP Server directly"
    )
    parser.add_argument(
        "--log-dir",
        help="Directory for log files (default: current directory)",
        default="logs"
    )
    parser.add_argument(
        "--data-dir",
        help="Directory for data files (default: ./data)",
        default="data"
    )
    parser.add_argument(
        "--dotenv-path",
        help="Path to .env file (optional)",
    )
    parser.add_argument(
        "--host",
        help="Host to bind to (default: 0.0.0.0)",
        default="0.0.0.0"
    )
    parser.add_argument(
        "--port",
        help="Port to bind to (default: 8000)",
        type=int,
        default=8000
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    # Set environment variables for the server
    if args.log_dir:
        os.environ["CHROMA_MCP_LOG_DIR"] = args.log_dir
    if args.data_dir:
        os.environ["CHROMA_MCP_DATA_DIR"] = args.data_dir
    if args.dotenv_path:
        os.environ["CHROMA_MCP_DOTENV_PATH"] = args.dotenv_path
    if args.host:
        os.environ["CHROMA_MCP_HOST"] = args.host
    if args.port:
        os.environ["CHROMA_MCP_PORT"] = str(args.port)
    
    # Run the server
    main() 