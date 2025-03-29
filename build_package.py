#!/usr/bin/env python3
"""
Build script for the Chroma MCP Server package.
This script builds the package without requiring external build tools.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


# ANSI color codes
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    YELLOW = '\033[0;33m'
    NC = '\033[0m'  # No Color


def colorize(text, color):
    """Add color to text if running in a terminal."""
    if sys.stdout.isatty():
        return f"{color}{text}{Colors.NC}"
    return text


def print_colored(text, color):
    """Print colored text."""
    print(colorize(text, color))


def run_command(cmd, verbose=True):
    """Run a command and return its output."""
    if verbose:
        print_colored(f"Running: {' '.join(cmd)}", Colors.BLUE)
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        print_colored(f"Command failed with return code {process.returncode}", Colors.RED)
        if stdout:
            print(stdout)
        if stderr:
            print_colored(stderr, Colors.RED)
        return False
    
    if verbose and stdout:
        print(stdout)
    
    return True


def ensure_package(package_name):
    """Ensure a package is installed."""
    try:
        __import__(package_name)
        return True
    except ImportError:
        print_colored(f"Installing {package_name}...", Colors.YELLOW)
        return run_command([sys.executable, "-m", "pip", "install", package_name])


def clean_directory():
    """Clean up build artifacts."""
    print_colored("Cleaning up previous builds...", Colors.YELLOW)
    dirs_to_remove = ["dist", "build"]
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
    
    # Remove *.egg-info directories
    for item in os.listdir("."):
        if item.endswith(".egg-info") and os.path.isdir(item):
            shutil.rmtree(item)


def build_package():
    """Build the package using setuptools."""
    print_colored("Building the package...", Colors.YELLOW)
    
    # Ensure required packages
    if not ensure_package("setuptools"):
        return False
    if not ensure_package("wheel"):
        return False
    
    # Build the package using setup.py directly
    print_colored("Building wheel using setup.py...", Colors.YELLOW)
    success = run_command([sys.executable, "setup.py", "bdist_wheel"])
    
    if not success:
        return False
    
    print_colored("Package built successfully!", Colors.GREEN)
    return True


def main():
    """Main function."""
    print_colored("=" * 65, Colors.BLUE)
    print_colored("            Building Chroma MCP Server Package", Colors.BLUE)
    print_colored("=" * 65, Colors.BLUE)
    
    # Get current directory
    current_dir = Path.cwd()
    print_colored(f"Working directory: {current_dir}", Colors.BLUE)
    
    # Clean up
    clean_directory()
    
    # Build the package
    if not build_package():
        print_colored("Build failed!", Colors.RED)
        return 1
    
    # List the built packages
    print_colored("\nBuilt packages:", Colors.GREEN)
    if os.path.exists("dist"):
        for item in os.listdir("dist"):
            print(f"  - dist/{item}")
    
    print_colored("""
You can now:
1. Install the package locally: pip install dist/*.whl
2. Test with uvx locally: pip install uv && uvx chroma-mcp-server
3. Publish to PyPI: python -m twine upload dist/*
""", Colors.YELLOW)
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 