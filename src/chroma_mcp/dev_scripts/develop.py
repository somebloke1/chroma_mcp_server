#!/usr/bin/env python3
"""
Python implementation of the develop.sh script.
This module provides functionality for setting up a development environment.
"""

import os
import subprocess
import sys
from pathlib import Path
from chroma_mcp.dev_scripts.project_root import get_project_root


def run_command(cmd: list[str], cwd: Path = None) -> int:
    """Run a shell command and return its exit code."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def main() -> int:
    """Main entry point for the develop script."""
    # Get project root
    project_root = get_project_root()

    print(f"ℹ️ Setting up development environment in: {project_root}")

    # Ensure Hatch is installed
    try:
        subprocess.run(["hatch", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Hatch not found. Installing hatch...")
        if run_command([sys.executable, "-m", "pip", "install", "hatch"]) != 0:
            print("Failed to install Hatch. Aborting.")
            return 1

    # Enter Hatch shell for development
    print("Entering Hatch shell for development...")
    os.chdir(project_root)
    # We're using subprocess.call directly to allow the shell to be interactive
    return subprocess.call(["hatch", "shell"], cwd=project_root)


if __name__ == "__main__":
    sys.exit(main())
