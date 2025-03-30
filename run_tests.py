#!/usr/bin/env python3
"""Run tests for the Chroma MCP Server with configurable options for test types and coverage reporting."""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List


def ensure_hatch_env() -> None:
    """Ensure Hatch environment exists and is activated.
    
    Checks if running in a Hatch environment and if not, runs the script through Hatch.
    """
    # Check if hatch is installed
    try:
        subprocess.run(["hatch", "--version"], check=True, capture_output=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Hatch not found. Installing Hatch...")
        subprocess.run([sys.executable, "-m", "pip", "install", "hatch"], check=True)
    
    # Check if we're already in a Hatch environment
    in_hatch_env = os.environ.get("VIRTUAL_ENV") and "hatch" in os.environ.get("VIRTUAL_ENV", "").lower()
    
    if not in_hatch_env:
        print("Not running in Hatch environment. Restarting with Hatch...")
        
        # Prepare the command to run the script with Hatch
        cmd_args = [sys.executable] + sys.argv
        result = subprocess.run(["hatch", "run", "--"] + cmd_args, check=False)
        sys.exit(result.returncode)
    
    # Ensure test dependencies are installed
    try:
        import pytest
        import pytest_cov
    except ImportError:
        print("Installing test dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest", "pytest-asyncio", "pytest-cov"], check=True)


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
    
    parser.add_argument(
        "--xml",
        action="store_true",
        help="Generate XML coverage report for CI/CD"
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
    if args.coverage or args.html or args.xml:
        pytest_args.extend(["--cov=chroma_mcp", "--cov-report=term-missing"])
        
        if args.html:
            pytest_args.append("--cov-report=html")
            
        if args.xml:
            pytest_args.append("--cov-report=xml")
    
    return pytest_args


def main() -> int:
    """Run the test suite with specified options.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Add the project root to Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    # Ensure Hatch environment
    ensure_hatch_env()
    
    try:
        import pytest
    except ImportError:
        print("Error: pytest not found. Please run: pip install pytest pytest-asyncio pytest-cov")
        return 1
    
    # Parse arguments and run tests
    args = parse_arguments()
    pytest_args = build_pytest_args(args)
    
    print(f"Running tests with args: {pytest_args}")
    return pytest.main(pytest_args)


if __name__ == "__main__":
    sys.exit(main()) 