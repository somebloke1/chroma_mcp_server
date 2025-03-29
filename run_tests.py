#!/usr/bin/env python3
"""Run tests for the Chroma MCP Server with configurable options for test types and coverage reporting."""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List


def ensure_venv() -> None:
    """Ensure virtual environment exists and is activated.
    
    Creates the virtual environment if it doesn't exist and activates it using the appropriate
    activation script for the current platform.
    """
    venv_path = Path(".venv")
    
    # Create venv if it doesn't exist
    if not venv_path.exists():
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
    
    # Get the activation script path based on platform
    if sys.platform == "win32":
        venv_path = os.path.realpath(os.path.join(venv_path, "Scripts"))
        activate_script = os.path.join(venv_path, "activate.bat")
        activate_cmd = str(activate_script)
        venv_python = os.path.join(venv_path, "python.exe")
    else:
        venv_path = os.path.realpath(os.path.join(venv_path, "bin"))
        activate_script = os.path.join(venv_path, "activate")
        activate_cmd = f"source {activate_script}"
        venv_python = os.path.join(venv_path, "python")
    
    if not os.path.exists(activate_script):
        print("Virtual environment is incomplete. Please run: python -m venv .venv")
        sys.exit(1)
    
    # Check if we're already in the virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print(f"Activating virtual environment using {activate_cmd} ...")
        
        # Prepare the command to run the script with activated venv
        if sys.platform == "win32":
            cmd = f'cmd /c "{activate_cmd} && {venv_python} {__file__} {" ".join(sys.argv[1:])}"'
        else:
            cmd = f'bash -c "{activate_cmd} && {venv_python} {__file__} {" ".join(sys.argv[1:])}"'
        
        # Execute the command in a new shell
        sys.exit(os.system(cmd))
    
    try:
        import pytest
    except ImportError:
        print("Installing test dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", ".[dev]"], check=True)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments for test configuration.

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(description="Run tests for the Chroma MCP Server")
    
    parser.add_argument(
        "-t", 
        "--test-type",
        choices=["unit", "integration", "all"],
        default="all",
        help="Type of tests to run (default: all)"
    )
    
    parser.add_argument(
        "-c", 
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML coverage report"
    )
    
    parser.add_argument(
        "-v", 
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser.parse_args()


def get_test_path(test_type: str) -> str:
    """Get the test directory path based on test type.

    Args:
        test_type (str): Type of tests to run (unit, integration, or all)

    Returns:
        str: Path to the test directory
    """
    if test_type == "unit":
        return "tests/unit/"
    elif test_type == "integration":
        return "tests/integration/"
    return "tests/"


def build_pytest_args(args: argparse.Namespace) -> List[str]:
    """Build pytest arguments based on command line options.

    Args:
        args (argparse.Namespace): Parsed command line arguments

    Returns:
        List[str]: List of pytest arguments
    """
    pytest_args = []
    
    # Add test path
    test_path = get_test_path(args.test_type)
    pytest_args.append(test_path)
    
    # Add verbosity
    if args.verbose:
        pytest_args.append("-v")
    
    # Add coverage options
    if args.coverage or args.html:
        pytest_args.extend(["--cov=src.chroma_mcp", "--cov-report=term-missing"])
        
        if args.html:
            pytest_args.append("--cov-report=html")
    
    return pytest_args


def main() -> int:
    """Run the test suite with specified options.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Add the project root to Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    # Ensure virtual environment
    ensure_venv()
    
    try:
        import pytest
    except ImportError:
        print("Error: pytest not found. Please run: pip install -e '.[dev]'")
        return 1
    
    # Parse arguments and run tests
    args = parse_arguments()
    pytest_args = build_pytest_args(args)
    
    return pytest.main(pytest_args)


if __name__ == "__main__":
    sys.exit(main()) 