"""
Unit tests for the review_promote.py script module.
"""

import sys
import pytest
from unittest.mock import patch, MagicMock
import argparse

from chroma_mcp_client.scripts.review_promote import main


class TestReviewPromoteScript:
    """Test cases for the review_promote.py script module."""

    @patch("sys.argv", ["review-promote", "--query", "test query"])
    @patch("subprocess.run")
    def test_review_promote_with_query(self, mock_subprocess_run):
        """Test review-promote with query argument."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        # Call the main function
        result = main()

        # Check that subprocess.run was called with the correct arguments
        assert result == 0
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert args[0] == "chroma-mcp-client"
        assert args[1] == "review-promote"
        assert "--query" in args
        assert "test query" in args

    @patch(
        "sys.argv",
        [
            "review-promote",
            "--query",
            "test query",
            "--threshold",
            "0.8",
            "--n-results",
            "10",
            "--source-collection",
            "custom_source",
            "--target-collection",
            "custom_target",
            "--interactive",
        ],
    )
    @patch("subprocess.run")
    def test_review_promote_all_args(self, mock_subprocess_run):
        """Test review-promote with all possible arguments."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        # Call the main function
        result = main()

        # Check that subprocess.run was called with the correct arguments
        assert result == 0
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]

        # Check all expected arguments are present
        assert args[0] == "chroma-mcp-client"
        assert args[1] == "review-promote"
        assert "--query" in args
        assert "test query" in args
        assert "--threshold" in args
        assert "0.8" in args
        assert "--n-results" in args
        assert "10" in args
        assert "--source-collection" in args
        assert "custom_source" in args
        assert "--target-collection" in args
        assert "custom_target" in args
        assert "--interactive" in args

    @patch("chroma_mcp_client.scripts.review_promote.argparse.ArgumentParser.parse_args")
    @patch("subprocess.run")
    def test_review_promote_default_values(self, mock_subprocess_run, mock_parse_args):
        """Test that review-promote uses correct default values."""
        # Mock the args with default values
        mock_args = argparse.Namespace(
            query="test query",
            threshold=0.7,
            n_results=5,
            source_collection="chat_history_v1",
            target_collection="derived_learnings_v1",
            interactive=True,
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
        assert "--threshold" in args
        assert "0.7" in args
        assert "--n-results" in args
        assert "5" in args
        assert "--source-collection" in args
        assert "chat_history_v1" in args
        assert "--target-collection" in args
        assert "derived_learnings_v1" in args
        assert "--interactive" in args

    @patch("chroma_mcp_client.scripts.review_promote.argparse.ArgumentParser.parse_args")
    @patch("subprocess.run")
    def test_review_promote_error_handling(self, mock_subprocess_run, mock_parse_args):
        """Test that review-promote handles errors properly."""
        # Mock the args
        mock_args = argparse.Namespace(
            query="test query",
            threshold=0.7,
            n_results=5,
            source_collection="chat_history_v1",
            target_collection="derived_learnings_v1",
            interactive=True,
        )
        mock_parse_args.return_value = mock_args

        # Mock subprocess.run to throw an exception
        mock_subprocess_run.side_effect = Exception("Test error")

        # Call the main function
        result = main()

        # Check the result
        assert result == 1
        mock_subprocess_run.assert_called_once()
