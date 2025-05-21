"""
Unit tests for the analyze_chat.py script module.
"""

import sys
import pytest
from unittest.mock import patch, MagicMock
import argparse
import subprocess

from chroma_mcp_client.scripts.analyze_chat import main


class TestAnalyzeChatScript:
    """Test cases for the analyze_chat.py script module."""

    @patch("sys.argv", ["analyze-chat", "--collection-name", "chat_history_v1"])
    @patch("subprocess.run")
    def test_analyze_chat_required_args(self, mock_subprocess_run):
        """Test analyze-chat with only required arguments."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        # Call the main function
        result = main()

        # Check that subprocess.run was called with the correct arguments
        assert result == 0
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert args[0] == "chroma-mcp-client"
        assert args[1] == "analyze-chat"
        assert "--collection-name" in args
        assert "chat_history_v1" in args

    @patch(
        "sys.argv",
        [
            "analyze-chat",
            "--collection-name",
            "chat_history_v1",
            "--query",
            "test query",
            "--n-results",
            "5",
            "--session-id",
            "test-session",
            "--output-format",
            "json",
            "--verbose",
        ],
    )
    @patch("subprocess.run")
    def test_analyze_chat_all_args(self, mock_subprocess_run):
        """Test analyze-chat with all possible arguments."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        # Call the main function
        result = main()

        # Check that subprocess.run was called with the correct arguments
        assert result == 0
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]

        # Check all expected arguments are present
        assert args[0] == "chroma-mcp-client"
        assert args[1] == "analyze-chat"
        assert "--collection-name" in args
        assert "chat_history_v1" in args
        assert "--query" in args
        assert "test query" in args
        assert "--n-results" in args
        assert "5" in args
        assert "--session-id" in args
        assert "test-session" in args
        assert "--output-format" in args
        assert "json" in args
        assert "--verbose" in args

    @patch("chroma_mcp_client.scripts.analyze_chat.argparse.ArgumentParser.parse_args")
    @patch("subprocess.run")
    def test_analyze_chat_error_handling(self, mock_subprocess_run, mock_parse_args):
        """Test that analyze-chat handles errors properly."""
        # Mock the args
        mock_args = argparse.Namespace(
            collection_name="chat_history_v1",
            query=None,
            n_results=10,
            session_id=None,
            output_format="text",
            verbose=False,
        )
        mock_parse_args.return_value = mock_args

        # Mock subprocess.run to raise an exception
        mock_subprocess_run.side_effect = Exception("Test error")

        # Call the main function
        result = main()

        # Check the result
        assert result == 1

    @patch("chroma_mcp_client.scripts.analyze_chat.argparse.ArgumentParser.parse_args")
    @patch("subprocess.run")
    def test_analyze_chat_command_failure(self, mock_subprocess_run, mock_parse_args):
        """Test that analyze-chat handles command failures properly."""
        # Mock the args
        mock_args = argparse.Namespace(
            collection_name="chat_history_v1",
            query=None,
            n_results=10,
            session_id=None,
            output_format="text",
            verbose=False,
        )
        mock_parse_args.return_value = mock_args

        # Mock subprocess.run to return a non-zero exit code
        mock_subprocess_run.return_value = MagicMock(returncode=1)

        # Call the main function
        result = main()

        # Check the result
        assert result == 1
        mock_subprocess_run.assert_called_once()
