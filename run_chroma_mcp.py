#!/usr/bin/env python3
"""
Runner script for the Chroma MCP Server.
This properly sets up the Python path and runs the server module.
"""

import os
import sys
import subprocess

def main():
    """Run the Chroma MCP server."""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create the command
    cmd = [
        sys.executable,
        "-m",
        "src.chroma_mcp.server"
    ]
    
    # Set the environment
    env = os.environ.copy()
    env["PYTHONPATH"] = script_dir
    
    # Don't print anything to stdout as it breaks the JSON protocol
    # Run the server silently
    try:
        process = subprocess.Popen(
            cmd,
            env=env,
            cwd=script_dir
        )
        process.wait()
    except KeyboardInterrupt:
        print("Server stopped by user", file=sys.stderr)  # Print to stderr instead
    except Exception as e:
        print(f"Error running server: {e}", file=sys.stderr)  # Print to stderr instead
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 