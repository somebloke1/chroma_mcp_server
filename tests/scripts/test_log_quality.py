"""
Unit tests for the log_quality.py script module.
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock
import argparse

from chroma_mcp_client.scripts.log_quality import main


class TestLogQualityScript:
    """Test cases for the log_quality.py script module."""

    @patch("sys.argv", ["log-quality", "--tool-name", "pylint", "--status", "pass"])
    @patch("subprocess.run")
    def test_log_quality_required_args(self, mock_subprocess_run):
        """Test log-quality with only required arguments."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        result = main()
        assert result == 0
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert args[0] == "chroma-mcp-client"
        assert args[1] == "log-quality"
        assert "--tool-name" in args
        assert "pylint" in args
        assert "--status" in args
        assert "pass" in args
        assert "--workspace-dir" in args

    @patch(
        "sys.argv",
        [
            "log-quality",
            "--tool-name",
            "black",
            "--status",
            "warn",
            "--file-path",
            "/path/to/file.py",
            "--message",
            "All good",
            "--score",
            "9.5",
            "--workspace-dir",
            "/custom/workspace",
            "--workflow-id",
            "wf-123",
            "--collection-name",
            "custom_collection",
        ],
    )
    @patch("subprocess.run")
    def test_log_quality_all_args(self, mock_subprocess_run):
        """Test log-quality with all possible arguments."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        result = main()
        assert result == 0
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert args[0] == "chroma-mcp-client"
        assert args[1] == "log-quality"
        assert "--tool-name" in args and "black" in args
        assert "--status" in args and "warn" in args
        assert "--file-path" in args and "/path/to/file.py" in args
        assert "--message" in args and "All good" in args
        assert "--score" in args and "9.5" in args
        assert "--workspace-dir" in args and "/custom/workspace" in args
        assert "--workflow-id" in args and "wf-123" in args
        assert "--collection-name" in args and "custom_collection" in args

    @patch("chroma_mcp_client.scripts.log_quality.argparse.ArgumentParser.parse_args")
    @patch("subprocess.run")
    @patch("os.getcwd")
    def test_log_quality_default_values(self, mock_getcwd, mock_subprocess_run, mock_parse_args):
        """Test log-quality default values are used correctly."""
        mock_getcwd.return_value = "/default/workspace"
        mock_args = argparse.Namespace(
            tool_name="pylint",
            status="pass",
            file_path=None,
            message=None,
            score=None,
            workspace_dir="/default/workspace",
            workflow_id=None,
            collection_name="quality_checks_v1",
        )
        mock_parse_args.return_value = mock_args
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        result = main()
        assert result == 0
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert "--workspace-dir" in args and "/default/workspace" in args
        assert "--collection-name" in args and "quality_checks_v1" in args

    @patch("chroma_mcp_client.scripts.log_quality.argparse.ArgumentParser.parse_args")
    @patch("subprocess.run")
    def test_log_quality_exception(self, mock_subprocess_run, mock_parse_args):
        """Test that log-quality handles exceptions properly."""
        mock_args = argparse.Namespace(
            tool_name="pylint",
            status="pass",
            file_path=None,
            message=None,
            score=None,
            workspace_dir="/default/workspace",
            workflow_id=None,
            collection_name="quality_checks_v1",
        )
        mock_parse_args.return_value = mock_args
        mock_subprocess_run.side_effect = Exception("error")

        result = main()
        assert result == 1
        mock_subprocess_run.assert_called_once()
