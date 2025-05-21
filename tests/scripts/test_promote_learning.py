"""
Unit tests for the promote_learning.py script module.
"""

import sys
import pytest
from unittest.mock import patch, MagicMock
import argparse
import subprocess

from chroma_mcp_client.scripts.promote_learning import main


class TestPromoteLearningScript:
    """Test cases for the promote_learning.py script module."""

    @patch("sys.argv", ["promote-learning", "--id", "test-id"])
    @patch("subprocess.run")
    def test_promote_learning_required_args(self, mock_subprocess_run):
        """Test promote-learning with only required arguments."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        # Call the main function
        result = main()

        # Check that subprocess.run was called with the correct arguments
        assert result == 0
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert args[0] == "chroma-mcp-client"
        assert args[1] == "promote-learning"
        assert "--id" in args
        assert "test-id" in args

    @patch(
        "sys.argv",
        [
            "promote-learning",
            "--id",
            "test-id",
            "--target-collection",
            "custom_derived_learnings",
            "--source-collection",
            "custom_chat_history",
            "--reason",
            "Test promotion reason",
            "--confidence",
            "0.95",
            "--category",
            "test-category",
        ],
    )
    @patch("subprocess.run")
    def test_promote_learning_all_args(self, mock_subprocess_run):
        """Test promote-learning with all possible arguments."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        # Call the main function
        result = main()

        # Check that subprocess.run was called with the correct arguments
        assert result == 0
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]

        # Check all expected arguments are present
        assert args[0] == "chroma-mcp-client"
        assert args[1] == "promote-learning"
        assert "--id" in args
        assert "test-id" in args
        assert "--target-collection" in args
        assert "custom_derived_learnings" in args
        assert "--source-collection" in args
        assert "custom_chat_history" in args
        assert "--reason" in args
        assert "Test promotion reason" in args
        assert "--confidence" in args
        assert "0.95" in args
        assert "--category" in args
        assert "test-category" in args

    @patch("chroma_mcp_client.scripts.promote_learning.argparse.ArgumentParser.parse_args")
    @patch("subprocess.run")
    def test_promote_learning_error_handling(self, mock_subprocess_run, mock_parse_args):
        """Test that promote-learning handles errors properly."""
        # Mock the args
        mock_args = argparse.Namespace(
            id="test-id",
            target_collection="derived_learnings_v1",
            source_collection="chat_history_v1",
            reason=None,
            confidence=0.85,
            category=None,
        )
        mock_parse_args.return_value = mock_args

        # Mock subprocess.run to raise an exception
        mock_subprocess_run.side_effect = Exception("Test error")

        # Call the main function
        result = main()

        # Check the result
        assert result == 1

    @patch("chroma_mcp_client.scripts.promote_learning.argparse.ArgumentParser.parse_args")
    @patch("subprocess.run")
    def test_promote_learning_command_failure(self, mock_subprocess_run, mock_parse_args):
        """Test that promote-learning handles command failures properly."""
        # Mock the args
        mock_args = argparse.Namespace(
            id="test-id",
            target_collection="derived_learnings_v1",
            source_collection="chat_history_v1",
            reason=None,
            confidence=0.85,
            category=None,
        )
        mock_parse_args.return_value = mock_args

        # Mock subprocess.run to return a non-zero exit code
        mock_subprocess_run.return_value = MagicMock(returncode=1)

        # Call the main function
        result = main()

        # Check the result
        assert result == 1
        mock_subprocess_run.assert_called_once()
