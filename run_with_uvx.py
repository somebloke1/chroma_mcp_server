#!/usr/bin/env python3
"""
UVX runner for Chroma MCP Server.
This script uses UVX to run the server after setting up a proper environment.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
import tempfile
import shutil

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

def run_command(cmd, cwd=None, env=None, shell=False, verbose=True):
    """Run a command and return its output."""
    if verbose:
        print_colored(f"Running: {' '.join(cmd) if not shell else cmd}", Colors.BLUE)
        if cwd:
            print_colored(f"  in directory: {cwd}", Colors.BLUE)
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        cwd=cwd,
        env=env,
        shell=shell
    )
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        print_colored(f"Command failed with return code {process.returncode}", Colors.RED)
        if stdout:
            print(stdout)
        if stderr:
            print_colored(stderr, Colors.RED)
        return False, stdout, stderr
    
    if verbose and stdout:
        print(stdout)
    
    return True, stdout, stderr

def ensure_uv_installed():
    """Ensure uv is installed."""
    # Check if uv is installed
    success, _, _ = run_command(["which", "uv"], verbose=False)
    if success:
        print_colored("uv is already installed.", Colors.GREEN)
        return True
    
    # Install uv
    print_colored("Installing uv...", Colors.YELLOW)
    success, _, _ = run_command([sys.executable, "-m", "pip", "install", "uv"])
    if not success:
        print_colored("Failed to install uv. Please install it manually:", Colors.RED)
        print_colored("pip install uv", Colors.RED)
        return False
    
    return True

def setup_venv_and_run_uvx(args):
    """Set up a virtual environment and run uvx."""
    venv_path = os.path.abspath(".venv_uvx")
    
    # Create a virtual environment if it doesn't exist
    if not os.path.exists(venv_path):
        print_colored(f"Creating virtual environment at {venv_path}...", Colors.YELLOW)
        success, _, _ = run_command([sys.executable, "-m", "venv", venv_path])
        if not success:
            print_colored("Failed to create virtual environment.", Colors.RED)
            return False
    else:
        print_colored(f"Using existing virtual environment at {venv_path}", Colors.GREEN)
    
    # Determine executable paths based on OS
    if sys.platform == "win32":
        python_executable = os.path.join(venv_path, "Scripts", "python")
        pip_executable = os.path.join(venv_path, "Scripts", "pip")
    else:
        python_executable = os.path.join(venv_path, "bin", "python")
        pip_executable = os.path.join(venv_path, "bin", "pip")
    
    # Install uv in the virtual environment
    print_colored("Installing uv in virtual environment...", Colors.YELLOW)
    success, _, _ = run_command([pip_executable, "install", "--upgrade", "pip", "uv", "uvx"])
    if not success:
        print_colored("Failed to install uv/uvx in virtual environment.", Colors.RED)
        return False
    
    # Determine the uvx executable path
    if sys.platform == "win32":
        uvx_executable = os.path.join(venv_path, "Scripts", "uvx")
    else:
        uvx_executable = os.path.join(venv_path, "bin", "uvx")
    
    # Run uvx with the specified arguments
    uvx_args = [uvx_executable]
    
    if args.python:
        uvx_args.extend(["-p", args.python])
    
    uvx_args.append("chroma-mcp-server")
    if args.server_args:
        uvx_args.extend(args.server_args)
    
    print_colored("Running uvx...", Colors.YELLOW)
    success, _, _ = run_command(uvx_args)
    if not success:
        print_colored("Failed to run uvx.", Colors.RED)
        return False
    
    return True

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run the Chroma MCP Server using uvx"
    )
    parser.add_argument(
        "--python",
        help="Path to Python interpreter to use for running the server"
    )
    parser.add_argument(
        "server_args",
        nargs="*",
        help="Arguments to pass to the server"
    )
    
    return parser.parse_args()

def main():
    """Main function."""
    args = parse_args()
    
    print_colored("=" * 65, Colors.BLUE)
    print_colored("            Running Chroma MCP Server with uvx", Colors.BLUE)
    print_colored("=" * 65, Colors.BLUE)
    
    # Ensure uv is installed
    if not ensure_uv_installed():
        return 1
    
    # Set up virtual environment and run uvx
    if not setup_venv_and_run_uvx(args):
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 