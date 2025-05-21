"""
Unit tests for the log_test.py script module.
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock
import argparse

from chroma_mcp_client.scripts.log_test import main


class TestLogTestScript:
    """Test cases for the log_test.py script module."""

    @patch("sys.argv", ["log-test", "--test-name", "test_example", "--status", "pass"])
    @patch("subprocess.run")
    def test_log_test_required_args(self, mock_subprocess_run):
        """Test log-test with only required arguments."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        # Call the main function
        result = main()

        # Check that subprocess.run was called with the correct arguments
        assert result == 0
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert args[0] == "chroma-mcp-client"
        assert args[1] == "log-test"
        assert "--test-name" in args
        assert "test_example" in args
        assert "--status" in args
        assert "pass" in args
        assert "--workspace-dir" in args  # This has a default value

    @patch(
        "sys.argv",
        [
            "log-test",
            "--test-name",
            "test_example",
            "--status",
            "fail",
            "--file-path",
            "/path/to/test_file.py",
            "--duration",
            "1.23",
            "--message",
            "Test message",
            "--workspace-dir",
            "/custom/workspace",
            "--workflow-id",
            "test-workflow",
            "--collection-name",
            "custom_collection",
        ],
    )
    @patch("subprocess.run")
    def test_log_test_all_args(self, mock_subprocess_run):
        """Test log-test with all possible arguments."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        # Call the main function
        result = main()

        # Check that subprocess.run was called with the correct arguments
        assert result == 0
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]

        # Check all expected arguments are present
        assert args[0] == "chroma-mcp-client"
        assert args[1] == "log-test"
        assert "--test-name" in args
        assert "test_example" in args
        assert "--status" in args
        assert "fail" in args
        assert "--file-path" in args
        assert "/path/to/test_file.py" in args
        assert "--duration" in args
        assert "1.23" in args
        assert "--message" in args
        assert "Test message" in args
        assert "--workspace-dir" in args
        assert "/custom/workspace" in args
        assert "--workflow-id" in args
        assert "test-workflow" in args
        assert "--collection-name" in args
        assert "custom_collection" in args

    @patch("chroma_mcp_client.scripts.log_test.argparse.ArgumentParser.parse_args")
    @patch("subprocess.run")
    @patch("os.getcwd")
    def test_log_test_default_values(self, mock_getcwd, mock_subprocess_run, mock_parse_args):
        """Test that log-test uses correct default values."""
        # Mock the current working directory
        mock_getcwd.return_value = "/default/workspace"

        # Mock the args with required values and default values
        mock_args = argparse.Namespace(
            test_name="test_example",
            status="pass",
            file_path=None,
            duration=None,
            message=None,
            workspace_dir="/default/workspace",  # From os.getcwd()
            workflow_id=None,
            collection_name="test_results_v1",  # Default value
        )
        mock_parse_args.return_value = mock_args

        # Mock subprocess.run to return success
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        # Call the main function
        result = main()

        # Check the result
        assert result == 0
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]

        # Check that default values are passed correctly
        assert "--workspace-dir" in args
        assert "/default/workspace" in args
        assert "--collection-name" in args
        assert "test_results_v1" in args

    @patch("chroma_mcp_client.scripts.log_test.argparse.ArgumentParser.parse_args")
    @patch("subprocess.run")
    def test_log_test_exception_handling(self, mock_subprocess_run, mock_parse_args):
        """Test that log-test handles exceptions properly."""
        # Mock the args
        mock_args = argparse.Namespace(
            test_name="test_example",
            status="pass",
            file_path=None,
            duration=None,
            message=None,
            workspace_dir="/default/workspace",
            workflow_id=None,
            collection_name="test_results_v1",
        )
        mock_parse_args.return_value = mock_args

        # Mock subprocess.run to throw an exception
        mock_subprocess_run.side_effect = Exception("Test error")

        # Call the main function
        result = main()

        # Check the result
        assert result == 1
        mock_subprocess_run.assert_called_once()
