#!/usr/bin/env python3
"""
Python implementation of the publish.sh script.
This module provides functionality for publishing the chroma-mcp-server package to PyPI.
"""

import argparse
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


def check_dist_files(project_root: Path) -> bool:
    """Check if distribution files exist."""
    dist_dir = project_root / "dist"
    if not dist_dir.exists() or not list(dist_dir.glob("*.whl")) or not list(dist_dir.glob("*.tar.gz")):
        return False
    return True


def main() -> int:
    """Main entry point for the publish script."""
    parser = argparse.ArgumentParser(description="Publish the chroma-mcp-server package to PyPI")

    # Add arguments
    parser.add_argument(
        "--repo", default="pypi", choices=["pypi", "testpypi"], help="Repository to publish to (pypi or testpypi)"
    )
    parser.add_argument("--skip-build", action="store_true", help="Skip building the package before publishing")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests before publishing")

    args = parser.parse_args()

    # Get project root
    project_root = get_project_root()
    print(f"ℹ️ Publishing package from: {project_root}")

    # Ensure build dependencies are installed
    print("Ensuring build dependencies are installed...")
    if run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "build", "twine"]) != 0:
        print("Failed to install build dependencies. Aborting.")
        return 1

    # Ensure Hatch is installed
    try:
        subprocess.run(["hatch", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Hatch not found. Installing hatch...")
        if run_command([sys.executable, "-m", "pip", "install", "hatch"]) != 0:
            print("Failed to install Hatch. Aborting.")
            return 1

    # Run tests if not skipped
    if not args.skip_tests:
        print("Running tests before publishing...")
        if run_command(["hatch", "run", "test"], cwd=project_root) != 0:
            print("Tests failed. Aborting publication.")
            return 1

    # Build the package if not skipped
    if not args.skip_build:
        print("Building distribution packages...")
        # Clean previous builds
        dist_dir = project_root / "dist"
        if dist_dir.exists():
            import shutil

            shutil.rmtree(dist_dir)

        if run_command(["hatch", "build"], cwd=project_root) != 0:
            print("Failed to build the package. Aborting.")
            return 1

    # Check if distribution files exist
    if not check_dist_files(project_root):
        print("Distribution files not found. Run 'hatch build' first.")
        return 1

    # Determine repository URL
    repo_url = "https://test.pypi.org/legacy/" if args.repo == "testpypi" else "https://upload.pypi.org/legacy/"

    # Upload to PyPI
    print(f"Uploading package to {args.repo}...")
    if run_command(["twine", "upload", "--repository-url", repo_url, "dist/*"], cwd=project_root) != 0:
        print(f"Failed to upload package to {args.repo}.")
        return 1

    print(f"Package successfully published to {args.repo}!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
