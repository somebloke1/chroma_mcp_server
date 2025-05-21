"""
Unit tests for the log_error.py script module.
"""

import sys
import pytest
from unittest.mock import patch, MagicMock
import argparse

from chroma_mcp_client.scripts.log_error import main


class TestLogErrorScript:
    """Test cases for the log_error.py script module."""

    @patch("sys.argv", ["log-error", "--error-message", "Test error", "--error-type", "TestError"])
    @patch("subprocess.run")
    def test_log_error_required_args(self, mock_subprocess_run):
        """Test log-error with only required arguments."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        # Call the main function
        result = main()

        # Check that subprocess.run was called with the correct arguments
        assert result == 0
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert args[0] == "chroma-mcp-client"
        assert args[1] == "log-error"
        assert "--error-message" in args
        assert "Test error" in args
        assert "--error-type" in args
        assert "TestError" in args

    @patch(
        "sys.argv",
        [
            "log-error",
            "--error-message",
            "Test error",
            "--error-type",
            "TestError",
            "--file-path",
            "/path/to/file.py",
            "--line-number",
            "42",
            "--stack-trace",
            "Traceback...",
            "--context",
            "Additional context",
            "--workflow-id",
            "test-workflow",
            "--collection-name",
            "custom_collection",
        ],
    )
    @patch("subprocess.run")
    def test_log_error_all_args(self, mock_subprocess_run):
        """Test log-error with all possible arguments."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        # Call the main function
        result = main()

        # Check that subprocess.run was called with the correct arguments
        assert result == 0
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]

        # Check all expected arguments are present
        assert args[0] == "chroma-mcp-client"
        assert args[1] == "log-error"
        assert "--error-message" in args
        assert "Test error" in args
        assert "--error-type" in args
        assert "TestError" in args
        assert "--file-path" in args
        assert "/path/to/file.py" in args
        assert "--line-number" in args
        assert "42" in args
        assert "--stack-trace" in args
        assert "Traceback..." in args
        assert "--context" in args
        assert "Additional context" in args
        assert "--workflow-id" in args
        assert "test-workflow" in args
        assert "--collection-name" in args
        assert "custom_collection" in args

    @patch("chroma_mcp_client.scripts.log_error.argparse.ArgumentParser.parse_args")
    @patch("subprocess.run")
    def test_log_error_default_values(self, mock_subprocess_run, mock_parse_args):
        """Test that log-error uses correct default values."""
        # Mock the args with required values and default collection
        mock_args = argparse.Namespace(
            error_message="Test error",
            error_type="TestError",
            file_path=None,
            line_number=None,
            stack_trace=None,
            context=None,
            workflow_id=None,
            collection_name="error_logs_v1",  # Default value
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
        assert "--collection-name" in args
        assert "error_logs_v1" in args

    @patch("chroma_mcp_client.scripts.log_error.argparse.ArgumentParser.parse_args")
    @patch("subprocess.run")
    def test_log_error_exception_handling(self, mock_subprocess_run, mock_parse_args):
        """Test that log-error handles exceptions properly."""
        # Mock the args
        mock_args = argparse.Namespace(
            error_message="Test error",
            error_type="TestError",
            file_path=None,
            line_number=None,
            stack_trace=None,
            context=None,
            workflow_id=None,
            collection_name="error_logs_v1",
        )
        mock_parse_args.return_value = mock_args

        # Mock subprocess.run to throw an exception
        mock_subprocess_run.side_effect = Exception("Test error")

        # Call the main function
        result = main()

        # Check the result
        assert result == 1
        mock_subprocess_run.assert_called_once()
