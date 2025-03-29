#!/usr/bin/env python3
"""
Runner script for the Chroma MCP Server using uvx.
This script builds the package locally and uses uvx to run it without publishing to PyPI.

Arguments:
    --keep-index: Keep the temporary index directory (don't ask interactively)
    --help, -h: Show this help message
"""

import os
import sys
import subprocess
import tempfile
import shutil
import argparse
from pathlib import Path
import hashlib


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


def parse_args(args=None):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Build and run the Chroma MCP Server using uvx"
    )
    parser.add_argument(
        "--keep-index", 
        action="store_true",
        help="Keep the temporary index directory (don't ask interactively)"
    )
    parser.add_argument(
        "--server-args",
        nargs="*",
        help="Arguments to pass to the server"
    )
    parser.add_argument(
        "--python",
        help="Path to Python interpreter to use for building the package"
    )
    
    # Parse known args only, pass the rest to the server
    return parser.parse_known_args(args)


def run_command(cmd, cwd=None, env=None, verbose=True):
    """Run a command and return its output."""
    if verbose:
        print_colored(f"Running: {' '.join(cmd)}", Colors.BLUE)
        if cwd:
            print_colored(f"  in directory: {cwd}", Colors.BLUE)
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        cwd=cwd,
        env=env
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
    success, stdout, _ = run_command(["which", "uv"], verbose=False)
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


def build_package(python_executable=None):
    """Build the package using pip wheel directly."""
    print_colored("Building package...", Colors.YELLOW)
    
    # Create dist directory if it doesn't exist
    dist_dir = Path(__file__).parent / "dist"
    if not dist_dir.exists():
        os.makedirs(dist_dir)
    
    # Use specified Python executable or current one
    if not python_executable:
        python_executable = sys.executable
    
    print_colored(f"Using Python: {python_executable}", Colors.BLUE)
    
    # Build the wheel directly using the specified Python interpreter
    success, _, _ = run_command(
        [python_executable, "-m", "pip", "wheel", "--no-deps", "-w", "dist", "."]
    )
    
    if not success:
        print_colored("Failed to build the package.", Colors.RED)
        return False
    
    return True


def find_wheel():
    """Find the built wheel file."""
    dist_dir = Path(__file__).parent / "dist"
    if not dist_dir.exists():
        print_colored("Dist directory not found.", Colors.RED)
        return None
    
    wheels = list(dist_dir.glob("*.whl"))
    if not wheels:
        print_colored("No wheel files found in dist directory.", Colors.RED)
        return None
    
    # Return the newest wheel
    return str(max(wheels, key=lambda p: p.stat().st_mtime))


def create_local_index(wheel_path):
    """Create a local PyPI index with the wheel file."""
    temp_dir = tempfile.mkdtemp(prefix="chroma_mcp_")
    print_colored(f"Created temporary index directory: {temp_dir}", Colors.BLUE)
    
    # Copy the wheel to the temporary directory
    wheel_name = os.path.basename(wheel_path)
    dest_path = os.path.join(temp_dir, wheel_name)
    shutil.copy2(wheel_path, dest_path)
    
    # Get package name from wheel (format: {name}-{version}-{rest}.whl)
    parts = wheel_name.split("-")
    package_name = parts[0]  # This is likely with underscores (chroma_mcp_server)
    hyphen_name = package_name.replace("_", "-")  # Convert to hyphens (chroma-mcp-server)
    version = parts[1]  # Version number
    
    # Check if wheel uses underscores, and create a copy with hyphens if needed
    if "_" in package_name:
        # Create a copy of the wheel with hyphens in the name
        hyphen_wheel_name = wheel_name.replace(package_name, hyphen_name)
        hyphen_dest_path = os.path.join(temp_dir, hyphen_wheel_name)
        shutil.copy2(dest_path, hyphen_dest_path)
        print_colored(f"Created wheel copy: {hyphen_wheel_name}", Colors.BLUE)
    else:
        hyphen_wheel_name = wheel_name  # Already has hyphens
    
    # Create simple index structure
    simple_dir = os.path.join(temp_dir, "simple")
    os.makedirs(simple_dir)
    
    # Create only the hyphenated directory in the index (what uvx expects)
    hyphen_dir = os.path.join(simple_dir, hyphen_name)
    os.makedirs(hyphen_dir)
    
    # Calculate hash with proper sha256= prefix
    with open(hyphen_dest_path, 'rb') as f:
        file_hash = f"sha256={hashlib.sha256(f.read()).hexdigest()}"
    
    # Create a more PEP 503 compliant index.html
    with open(os.path.join(hyphen_dir, "index.html"), "w") as f:
        f.write(f"""<!DOCTYPE html>
<html>
  <head>
    <title>Links for {hyphen_name}</title>
  </head>
  <body>
    <h1>Links for {hyphen_name}</h1>
    <a href="{hyphen_wheel_name}#{file_hash}">{hyphen_name}-{version}</a><br/>
  </body>
</html>
""")
    
    # Also copy the wheel directly to the package directory for direct access
    shutil.copy2(hyphen_dest_path, os.path.join(hyphen_dir, hyphen_wheel_name))
    
    # Create the top-level index.html
    with open(os.path.join(simple_dir, "index.html"), "w") as f:
        f.write(f"""<!DOCTYPE html>
<html>
  <head>
    <title>Simple index</title>
  </head>
  <body>
    <h1>Simple index</h1>
    <a href="{hyphen_name}/">{hyphen_name}</a><br/>
  </body>
</html>
""")
    
    return temp_dir, package_name


def run_with_uvx(index_url, package_name, args=None):
    """Run the Chroma MCP server with uvx using a local index."""
    if args is None:
        args = ["--help"]
    
    # Convert package_name to hyphenated version for uvx
    hyphen_package_name = package_name.replace("_", "-")
    
    print_colored(f"Running {hyphen_package_name} with uvx...", Colors.YELLOW)
    
    # Build the uvx command using the hyphenated package name
    cmd = ["uvx", "--index-url", f"file://{index_url}/simple", hyphen_package_name]
    cmd.extend(args)
    
    # Run the command
    success, stdout, stderr = run_command(cmd)
    
    return success


def main():
    """Main function."""
    # Parse command line arguments
    known_args, unknown_args = parse_args()
    
    print_colored("=" * 65, Colors.BLUE)
    print_colored("            Running Chroma MCP Server with uvx", Colors.BLUE)
    print_colored("=" * 65, Colors.BLUE)
    
    # Ensure uv is installed
    if not ensure_uv_installed():
        return 1
    
    # Build the package with specified Python if provided
    if not build_package(known_args.python):
        return 1
    
    # Find the wheel
    wheel_path = find_wheel()
    if not wheel_path:
        return 1
    print_colored(f"Using wheel: {wheel_path}", Colors.GREEN)
    
    # Create local index
    index_dir, package_name = create_local_index(wheel_path)
    
    # Get the hyphenated version of the package name for display and uvx
    hyphen_package_name = package_name.replace("_", "-")
    
    try:
        # Run with uvx
        # Use unknown_args for the server arguments if specified
        args = unknown_args if unknown_args else (known_args.server_args or ["--help"])
        if run_with_uvx(index_dir, package_name, args):
            print_colored(f"\n✅ Successfully ran {hyphen_package_name} with uvx!", Colors.GREEN)
        else:
            print_colored(f"\n❌ Failed to run {hyphen_package_name} with uvx.", Colors.RED)
            return 1
        
        # Provide mcp.json example
        print_colored(f"""
To use this in your MCP configuration, add the following to .cursor/mcp.json:

{{
  "mcpServers": {{
    "chroma_mcp_server": {{
      "command": "uvx",
      "args": [
        "--index-url", "file://{index_dir}/simple",
        "{hyphen_package_name}",
        "--data-dir", "data",
        "--log-dir", "logs"
      ],
      "env": {{
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8"
      }}
    }}
  }}
}}
""", Colors.YELLOW)
        
    finally:
        # Decide whether to keep the index directory
        keep = known_args.keep_index
        
        # If not specified by argument and running interactively, ask
        if not keep and sys.stdout.isatty():
            keep = input("\nKeep the temporary index directory? (y/n): ").lower() == "y"
            
        if not keep:
            print_colored(f"Cleaning up temporary index directory: {index_dir}", Colors.BLUE)
            shutil.rmtree(index_dir)
        else:
            print_colored(f"Keeping temporary index directory: {index_dir}", Colors.BLUE)
            print_colored("You can use this with uvx like:", Colors.BLUE)
            print_colored(f"uvx --index-url file://{index_dir}/simple {hyphen_package_name}", Colors.BLUE)
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 