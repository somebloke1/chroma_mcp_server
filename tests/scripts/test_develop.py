"""
Unit tests for the develop.py script module.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock, call, ANY
from pathlib import Path
import subprocess
import shutil

from chroma_mcp.dev_scripts.develop import run_command, main, get_project_root


class TestDevelopScript:
    """Test cases for the develop.py script module."""

    @patch("subprocess.run")
    def test_run_command(self, mock_subprocess_run):
        """Test the run_command helper function."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        # Call the function
        result = run_command(["echo", "test"])

        # Check the result
        assert result == 0
        mock_subprocess_run.assert_called_once_with(["echo", "test"], cwd=None)

    @patch("subprocess.run")
    @patch("subprocess.call")
    @patch("os.chdir")
    @patch("chroma_mcp.dev_scripts.develop.run_command")
    @patch("chroma_mcp.dev_scripts.develop.get_project_root")
    def test_develop_success(
        self, mock_get_project_root, mock_run_command, mock_chdir, mock_subprocess_call, mock_subprocess_run
    ):
        """Test successful develop execution."""
        # Set up mocks
        mock_project_root = MagicMock(spec=Path)
        mock_get_project_root.return_value = mock_project_root

        # Mock subprocess.run for hatch check
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        # Mock subprocess.call for hatch shell
        mock_subprocess_call.return_value = 0

        # Mock run_command to succeed for all commands
        mock_run_command.return_value = 0

        # Call the main function
        result = main()

        # Check the result
        assert result == 0

        # Verify that chdir was called with the project root
        mock_chdir.assert_called_once_with(mock_project_root)

        # Verify that hatch shell was called
        mock_subprocess_call.assert_called_once_with(["hatch", "shell"], cwd=mock_project_root)

    @patch("subprocess.run")
    @patch("subprocess.call")
    @patch("os.chdir")
    @patch("chroma_mcp.dev_scripts.develop.run_command")
    @patch("chroma_mcp.dev_scripts.develop.get_project_root")
    @patch("sys.executable", "/path/to/python")
    def test_develop_hatch_not_installed(
        self, mock_get_project_root, mock_run_command, mock_chdir, mock_subprocess_call, mock_subprocess_run
    ):
        """Test develop when hatch is not installed."""
        # Set up mocks
        mock_project_root = MagicMock(spec=Path)
        mock_get_project_root.return_value = mock_project_root

        # Mock subprocess.run to raise FileNotFoundError for hatch check
        mock_subprocess_run.side_effect = FileNotFoundError("No such file or directory: 'hatch'")

        # Mock run_command to succeed for pip install but fail for hatch shell
        def run_command_side_effect(cmd, cwd=None):
            if cmd[0] == "/path/to/python" and "-m" in cmd and "pip" in cmd and "install" in cmd:
                return 0  # Success for pip install
            else:
                return 1  # Failure for other commands

        mock_run_command.side_effect = run_command_side_effect

        # Mock subprocess.call to return 1 (failure)
        mock_subprocess_call.return_value = 1

        # Call the main function
        result = main()

        # Check the result - should match the return value from subprocess.call
        assert result == 1

        # Verify that pip install hatch was attempted
        assert any(
            "pip" in str(call_args) and "install" in str(call_args) and "hatch" in str(call_args)
            for call_args in mock_run_command.call_args_list
        )

        # Verify that chdir was called
        mock_chdir.assert_called_once_with(mock_project_root)

    @patch("subprocess.run")
    @patch("subprocess.call")
    @patch("os.chdir")
    @patch("chroma_mcp.dev_scripts.develop.run_command")
    @patch("chroma_mcp.dev_scripts.develop.get_project_root")
    def test_develop_command_failure(
        self, mock_get_project_root, mock_run_command, mock_chdir, mock_subprocess_call, mock_subprocess_run
    ):
        """Test develop when a command fails."""
        # Set up mocks
        mock_project_root = MagicMock(spec=Path)
        mock_get_project_root.return_value = mock_project_root

        # Mock subprocess.run for hatch check
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        # Mock subprocess.call to simulate failure of hatch shell
        mock_subprocess_call.return_value = 1

        # Call the main function
        result = main()

        # Check the result - should be the same as subprocess.call return value
        assert result == 1

        # Verify that chdir was called
        mock_chdir.assert_called_once_with(mock_project_root)
