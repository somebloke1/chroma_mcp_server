#!/usr/bin/env python3
"""
Python implementation of the release.sh script.
This module provides functionality for preparing a release of the chroma-mcp-server package.
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from chroma_mcp.dev_scripts.project_root import get_project_root


def run_command(cmd: list[str], cwd: Path = None) -> int:
    """Run a shell command and return its exit code."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def get_current_version(project_root: Path) -> str:
    """Get the current version from pyproject.toml."""
    pyproject_path = project_root / "pyproject.toml"
    with open(pyproject_path, "r") as f:
        content = f.read()

    version_match = re.search(r'version\s*=\s*"([^"]+)"', content)
    if not version_match:
        raise ValueError("Could not find version in pyproject.toml")

    return version_match.group(1)


def update_version(project_root: Path, new_version: str) -> bool:
    """Update the version in pyproject.toml."""
    pyproject_path = project_root / "pyproject.toml"
    with open(pyproject_path, "r") as f:
        content = f.read()

    updated_content = re.sub(r'version\s*=\s*"([^"]+)"', f'version = "{new_version}"', content, count=1)

    with open(pyproject_path, "w") as f:
        f.write(updated_content)

    return True


def update_changelog(project_root: Path, version: str) -> bool:
    """Update the CHANGELOG.md with a new version entry."""
    changelog_path = project_root / "CHANGELOG.md"

    if not changelog_path.exists():
        print("CHANGELOG.md not found. Creating new changelog file.")
        with open(changelog_path, "w") as f:
            f.write("# Changelog\n\n")

    with open(changelog_path, "r") as f:
        content = f.read()

    today = datetime.now().strftime("%Y-%m-%d")
    new_version_entry = f"## [{version}] - {today}\n\n"
    new_version_entry += "**Added:**\n- \n\n"
    new_version_entry += "**Fixed:**\n- \n\n"
    new_version_entry += "**Changed:**\n- \n\n"

    # Check if the version already exists in the changelog
    if f"## [{version}]" in content:
        print(f"Version {version} already exists in CHANGELOG.md. Skipping update.")
        return False

    # Insert the new version entry before the first existing version entry, or after header if none exist
    match = re.search(r"^## \[", content, flags=re.MULTILINE)
    if match:
        # Insert before the first existing version block
        updated_content = content[: match.start()] + new_version_entry + content[match.start() :]
    else:
        # No existing version entries; insert after primary header section
        updated_content = content.replace("# Changelog\n\n", f"# Changelog\n\n{new_version_entry}")

    with open(changelog_path, "w") as f:
        f.write(updated_content)

    return True


def main() -> int:
    """Main entry point for the release script."""
    parser = argparse.ArgumentParser(description="Prepare a release of the chroma-mcp-server package")

    # Add arguments
    parser.add_argument("--version", help="New version number (e.g., 0.2.19)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")

    args = parser.parse_args()

    # Get project root
    project_root = get_project_root()
    print(f"ℹ️ Preparing release in: {project_root}")

    # Get current version
    current_version = get_current_version(project_root)
    print(f"Current version: {current_version}")

    # Determine new version if not provided
    new_version = args.version
    if not new_version:
        # Split the version into components
        version_parts = current_version.split(".")
        if len(version_parts) != 3:
            print("Invalid version format. Expected x.y.z")
            return 1

        # Increment the patch version
        version_parts[2] = str(int(version_parts[2]) + 1)
        new_version = ".".join(version_parts)

    print(f"New version: {new_version}")

    if args.dry_run:
        print("Dry run mode. No changes will be made.")
        return 0

    # Update version in pyproject.toml
    print(f"Updating version in pyproject.toml to {new_version}...")
    if not update_version(project_root, new_version):
        print("Failed to update version in pyproject.toml")
        return 1

    # Update CHANGELOG.md
    print(f"Updating CHANGELOG.md with new version {new_version}...")
    # If the entry already exists, skip without error
    if update_changelog(project_root, new_version):
        print("CHANGELOG.md updated successfully.")
    else:
        print(f"CHANGELOG.md already contains version {new_version}, skipping update.")

    print(
        f"""
Release preparation for v{new_version} completed. Next steps:
1. Update the CHANGELOG.md with your changes
2. Build the package with: hatch build
3. Test the package with: ./scripts/test.sh
4. Commit and tag the release
5. Publish the package with: ./scripts/publish.sh
    """
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
