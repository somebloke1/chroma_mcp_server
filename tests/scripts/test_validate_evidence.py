"""
Unit tests for the validate_evidence.py script module.
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock
import argparse

from chroma_mcp_client.scripts.validate_evidence import main


class TestValidateEvidenceScript:
    """Test cases for the validate_evidence.py script module."""

    @patch("sys.argv", ["validate-evidence"])
    @patch("subprocess.run")
    def test_validate_evidence_no_args(self, mock_subprocess_run):
        """Test validate-evidence with no arguments (all defaults)."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        result = main()
        assert result == 0
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert args[0] == "chroma-mcp-client"
        assert args[1] == "validate-evidence"
        # Check default flags with values
        assert "--workspace-dir" in args
        assert "--source-collection" in args
        assert "--output-format" in args

    @patch(
        "sys.argv",
        [
            "validate-evidence",
            "--workflow-id",
            "wf123",
            "--test-name",
            "test1",
            "--status",
            "pass",
            "--workspace-dir",
            "/custom/workspace",
            "--source-collection",
            "custom_src",
            "--interactive",
            "--promote",
            "--output-format",
            "json",
        ],
    )
    @patch("subprocess.run")
    def test_validate_evidence_all_args(self, mock_subprocess_run):
        """Test validate-evidence with all possible arguments."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        result = main()
        assert result == 0
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert args[0] == "chroma-mcp-client"
        assert args[1] == "validate-evidence"
        assert "--workflow-id" in args and "wf123" in args
        assert "--test-name" in args and "test1" in args
        assert "--status" in args and "pass" in args
        assert "--workspace-dir" in args and "/custom/workspace" in args
        assert "--source-collection" in args and "custom_src" in args
        assert "--interactive" in args
        assert "--promote" in args
        assert "--output-format" in args and "json" in args

    @patch("chroma_mcp_client.scripts.validate_evidence.argparse.ArgumentParser.parse_args")
    @patch("subprocess.run")
    @patch("os.getcwd")
    def test_validate_evidence_default_values(self, mock_getcwd, mock_subprocess_run, mock_parse_args):
        """Test default values for validate-evidence."""
        mock_getcwd.return_value = "/default/workspace"
        mock_args = argparse.Namespace(
            workflow_id=None,
            test_name=None,
            status=None,
            workspace_dir="/default/workspace",
            source_collection="test_results_v1",
            interactive=False,
            promote=False,
            output_format="text",
        )
        mock_parse_args.return_value = mock_args
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        result = main()
        assert result == 0
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert "--workspace-dir" in args and "/default/workspace" in args
        assert "--source-collection" in args and "test_results_v1" in args
        assert "--output-format" in args and "text" in args

    @patch("chroma_mcp_client.scripts.validate_evidence.argparse.ArgumentParser.parse_args")
    @patch("subprocess.run")
    def test_validate_evidence_exception(self, mock_subprocess_run, mock_parse_args):
        """Test that validate-evidence handles exceptions properly."""
        mock_args = argparse.Namespace(
            workflow_id=None,
            test_name=None,
            status=None,
            workspace_dir="/default/workspace",
            source_collection="test_results_v1",
            interactive=False,
            promote=False,
            output_format="text",
        )
        mock_parse_args.return_value = mock_args
        mock_subprocess_run.side_effect = Exception("error")

        result = main()
        assert result == 1
        mock_subprocess_run.assert_called_once()
