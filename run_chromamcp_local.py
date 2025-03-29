#!/usr/bin/env python3
"""
Local development runner for Chroma MCP Server.
Creates a dedicated virtual environment and installs the package locally.
"""

import os
import sys
import shutil
import subprocess
import argparse
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

def ensure_venv(venv_path):
    """Ensure a virtual environment exists at the given path."""
    if os.path.exists(venv_path):
        print_colored(f"Using existing virtual environment at {venv_path}", Colors.GREEN)
        return True
    
    print_colored(f"Creating virtual environment at {venv_path}", Colors.YELLOW)
    success, _, _ = run_command([sys.executable, "-m", "venv", venv_path])
    if not success:
        print_colored("Failed to create virtual environment.", Colors.RED)
        return False
    
    return True

def install_package(venv_path, package_path):
    """Install the package into the virtual environment."""
    print_colored(f"Installing package from {package_path}", Colors.YELLOW)
    
    # Determine the pip executable path based on OS
    if sys.platform == "win32":
        pip_executable = os.path.join(venv_path, "Scripts", "pip")
    else:
        pip_executable = os.path.join(venv_path, "bin", "pip")
    
    if not os.path.exists(pip_executable):
        print_colored(f"ERROR: Could not find pip at {pip_executable}", Colors.RED)
        return False
    
    # Upgrade pip first
    print_colored("Upgrading pip...", Colors.YELLOW)
    success, _, _ = run_command([pip_executable, "install", "--upgrade", "pip"])
    if not success:
        print_colored("Failed to upgrade pip, but continuing...", Colors.RED)
    
    # Install package with dev extras (instead of manual dependencies and --no-deps)
    print_colored("Installing package with dev extras...", Colors.YELLOW)
    success, _, _ = run_command([pip_executable, "install", "-e", f"{package_path}[dev]"])
    if not success:
        print_colored("Failed to install package with dev extras.", Colors.RED)
        
        # Fallback: try to install the base package and core dependencies separately
        print_colored("Falling back to base installation...", Colors.YELLOW)
        core_deps = [
            "python-dotenv>=1.1.0",
            "pydantic>=2.10.6",
            "fastapi>=0.115.11",
            "fastmcp>=0.4.1",
            "uvicorn>=0.34.0",
            "chromadb>=0.6.3"  # Explicitly include chromadb
        ]
        
        # First install core dependencies
        success, _, _ = run_command([pip_executable, "install"] + core_deps)
        if not success:
            print_colored("Failed to install core dependencies.", Colors.RED)
            return False
            
        # Then install the package without dependencies
        success, _, _ = run_command([pip_executable, "install", "-e", package_path, "--no-deps"])
        if not success:
            print_colored("Failed to install package.", Colors.RED)
            return False
    
    return True

def run_server(venv_path, args):
    """Run the server from the virtual environment."""
    print_colored("Running Chroma MCP Server...", Colors.YELLOW)
    
    # Determine the python executable path based on OS
    if sys.platform == "win32":
        python_executable = os.path.join(venv_path, "Scripts", "python")
    else:
        python_executable = os.path.join(venv_path, "bin", "python")
    
    if not os.path.exists(python_executable):
        print_colored(f"ERROR: Could not find Python at {python_executable}", Colors.RED)
        return False
    
    # Create command to run server
    cmd = [python_executable, "-m", "chroma_mcp.server"]
    if args:
        cmd.extend(args)
    
    # Run the server (this will block until the server exits)
    run_command(cmd)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run the Chroma MCP Server using a dedicated virtual environment."
    )
    parser.add_argument(
        "--venv",
        help="Path to virtual environment (default: .venv_chromamcp)",
        default=".venv_chromamcp"
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
    print_colored("       Running Chroma MCP Server in local environment", Colors.BLUE)
    print_colored("=" * 65, Colors.BLUE)
    
    # Get absolute paths
    package_path = os.path.abspath(os.path.dirname(__file__))
    venv_path = os.path.abspath(args.venv)
    
    # Ensure virtual environment exists
    if not ensure_venv(venv_path):
        return 1
    
    # Install package
    if not install_package(venv_path, package_path):
        return 1
    
    # Run server
    run_server(venv_path, args.server_args)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 