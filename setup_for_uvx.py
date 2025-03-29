#!/usr/bin/env python3
"""
Setup script to make the chroma-mcp-server package findable by uvx.
This installs the package in development mode and registers it with uvx.
"""

import os
import sys
import subprocess
import argparse

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Set up the chroma-mcp-server package for use with uvx"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean existing installations before setup"
    )
    
    return parser.parse_args()

def run_command(cmd, check=True):
    """Run a command and return its output."""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed with return code {e.returncode}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(f"Error: {e.stderr}")
        if check:
            sys.exit(1)
        return e

def main():
    """Main function."""
    args = parse_args()
    
    print("=" * 65)
    print("       Setting up chroma-mcp-server for use with uvx")
    print("=" * 65)
    
    # Get the project root directory
    project_dir = os.path.abspath(os.path.dirname(__file__))
    os.chdir(project_dir)
    
    # Clean existing installation if requested
    if args.clean:
        print("Cleaning existing installations...")
        try:
            run_command([sys.executable, "-m", "pip", "uninstall", "-y", "chroma-mcp-server"], check=False)
        except Exception as e:
            print(f"Warning during uninstall: {e}")
    
    # Install the package in development mode with dev extras
    print("Installing the package in development mode...")
    run_command([sys.executable, "-m", "pip", "install", "-e", ".[dev]"])
    
    # Verify uvx finds the package
    print("\nVerifying chroma-mcp-server can be found by uvx...")
    result = run_command(["uvx", "list"], check=False)
    
    if "chroma-mcp-server" in result.stdout:
        print("\n✅ chroma-mcp-server is now registered with uvx!")
        print("\nYou can now run the server with:")
        print("  uvx chroma-mcp-server [arguments]")
    else:
        print("\n❌ chroma-mcp-server was not found by uvx.")
        print("Make sure the package is properly installed and has the correct entry points.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 