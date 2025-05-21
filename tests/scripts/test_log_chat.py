"""
Unit tests for the log_chat.py script module.
"""

import sys
import pytest
from unittest.mock import patch, MagicMock
import argparse
import subprocess

from chroma_mcp_client.scripts.log_chat import main


class TestLogChatScript:
    """Test cases for the log_chat.py script module."""

    @patch("sys.argv", ["log-chat", "--prompt-summary", "Test prompt", "--response-summary", "Test response"])
    @patch("subprocess.run")
    def test_log_chat_required_args(self, mock_subprocess_run):
        """Test log-chat with only required arguments."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        # Call the main function
        result = main()

        # Check that subprocess.run was called with the correct arguments
        assert result == 0
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert args[0] == "chroma-mcp-client"
        assert args[1] == "log-chat"
        assert "--prompt-summary" in args
        assert "Test prompt" in args
        assert "--response-summary" in args
        assert "Test response" in args

    @patch(
        "sys.argv",
        [
            "log-chat",
            "--prompt-summary",
            "Test prompt",
            "--response-summary",
            "Test response",
            "--raw-prompt",
            "Full test prompt",
            "--raw-response",
            "Full test response",
            "--involved-entities",
            "entity1,entity2",
            "--session-id",
            "test-session",
            "--collection-name",
            "custom_collection",
        ],
    )
    @patch("subprocess.run")
    def test_log_chat_all_args(self, mock_subprocess_run):
        """Test log-chat with all possible arguments."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        # Call the main function
        result = main()

        # Check that subprocess.run was called with the correct arguments
        assert result == 0
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]

        # Check all expected arguments are present
        assert args[0] == "chroma-mcp-client"
        assert args[1] == "log-chat"
        assert "--prompt-summary" in args
        assert "Test prompt" in args
        assert "--response-summary" in args
        assert "Test response" in args
        assert "--raw-prompt" in args
        assert "Full test prompt" in args
        assert "--raw-response" in args
        assert "Full test response" in args
        assert "--involved-entities" in args
        assert "entity1,entity2" in args
        assert "--session-id" in args
        assert "test-session" in args
        assert "--collection-name" in args
        assert "custom_collection" in args

    @patch("chroma_mcp_client.scripts.log_chat.argparse.ArgumentParser.parse_args")
    @patch("subprocess.run")
    def test_log_chat_error_handling(self, mock_subprocess_run, mock_parse_args):
        """Test that log-chat handles errors properly."""
        # Mock the args
        mock_args = argparse.Namespace(
            prompt_summary="Test prompt",
            response_summary="Test response",
            raw_prompt=None,
            raw_response=None,
            involved_entities=None,
            session_id=None,
            collection_name="chat_history_v1",
        )
        mock_parse_args.return_value = mock_args

        # Mock subprocess.run to raise an exception
        mock_subprocess_run.side_effect = Exception("Test error")

        # Call the main function
        result = main()

        # Check the result
        assert result == 1

    @patch("chroma_mcp_client.scripts.log_chat.argparse.ArgumentParser.parse_args")
    @patch("subprocess.run")
    def test_log_chat_command_failure(self, mock_subprocess_run, mock_parse_args):
        """Test that log-chat handles command failures properly."""
        # Mock the args
        mock_args = argparse.Namespace(
            prompt_summary="Test prompt",
            response_summary="Test response",
            raw_prompt=None,
            raw_response=None,
            involved_entities=None,
            session_id=None,
            collection_name="chat_history_v1",
        )
        mock_parse_args.return_value = mock_args

        # Mock subprocess.run to return a non-zero exit code
        mock_subprocess_run.return_value = MagicMock(returncode=1)

        # Call the main function
        result = main()

        # Check the result
        assert result == 1
        mock_subprocess_run.assert_called_once()
