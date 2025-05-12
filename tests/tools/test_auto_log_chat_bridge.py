"""
Unit tests for auto_log_chat_bridge module.
"""

import json
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from mcp.types import TextContent

from src.chroma_mcp.tools.auto_log_chat_bridge import LogChatInput, _log_chat_impl, _do_log_chat, mcp_log_chat


class TestAutoLogChatBridge(unittest.TestCase):
    """Test the auto_log_chat_bridge module."""

    def setUp(self):
        """Set up test data."""
        self.input_model = LogChatInput(
            prompt_summary="Test prompt summary",
            response_summary="Test response summary",
            raw_prompt="This is a test prompt",
            raw_response="This is a test response",
            tool_usage=[{"name": "tool1", "args": {"arg1": "value1"}}],
            file_changes=[{"file": "test.py", "before": "def foo(): pass", "after": "def foo(): return True"}],
            involved_entities="test.py,foo",
            session_id="test-session-id",
            collection_name="chat_history_v1",
        )

    @patch("chroma_mcp_client.connection.get_client_and_ef")
    @patch("chroma_mcp_client.auto_log_chat_impl.log_chat_to_chroma")
    def test_do_log_chat_success(self, mock_log_chat, mock_get_client):
        """Test successful execution of _do_log_chat."""
        # Setup mocks
        mock_client = MagicMock()
        mock_ef = MagicMock()
        mock_get_client.return_value = (mock_client, mock_ef)
        mock_log_chat.return_value = "test-chat-id"

        # Call function
        result = _do_log_chat(self.input_model)

        # Verify results
        mock_get_client.assert_called_once()
        mock_log_chat.assert_called_once_with(
            chroma_client=mock_client,
            prompt_summary=self.input_model.prompt_summary,
            response_summary=self.input_model.response_summary,
            raw_prompt=self.input_model.raw_prompt,
            raw_response=self.input_model.raw_response,
            tool_usage=self.input_model.tool_usage,
            file_changes=self.input_model.file_changes,
            involved_entities=self.input_model.involved_entities,
            session_id=self.input_model.session_id,
        )
        assert result == "test-chat-id"

    @patch("chroma_mcp_client.connection.get_client_and_ef")
    @patch("chroma_mcp_client.auto_log_chat_impl.log_chat_to_chroma")
    def test_do_log_chat_with_empty_session_id(self, mock_log_chat, mock_get_client):
        """Test _do_log_chat with empty session_id."""
        # Setup mocks
        mock_client = MagicMock()
        mock_ef = MagicMock()
        mock_get_client.return_value = (mock_client, mock_ef)
        mock_log_chat.return_value = "test-chat-id"

        # Create input model with empty session_id
        input_model = LogChatInput(
            prompt_summary="Test prompt summary",
            response_summary="Test response summary",
            raw_prompt="This is a test prompt",
            raw_response="This is a test response",
            session_id="",  # Empty string
        )

        # Call function
        result = _do_log_chat(input_model)

        # Verify results
        mock_log_chat.assert_called_once_with(
            chroma_client=mock_client,
            prompt_summary=input_model.prompt_summary,
            response_summary=input_model.response_summary,
            raw_prompt=input_model.raw_prompt,
            raw_response=input_model.raw_response,
            tool_usage=[],  # Default value
            file_changes=[],  # Default value
            involved_entities="",  # Default value
            session_id=None,  # Should be converted to None
        )
        assert result == "test-chat-id"

    @patch("chroma_mcp_client.connection.get_client_and_ef", side_effect=ImportError("Test import error"))
    def test_do_log_chat_import_error(self, mock_get_client):
        """Test _do_log_chat handling of import errors."""
        # Call function and verify it raises the expected exception
        with self.assertRaises(ImportError):
            _do_log_chat(self.input_model)

    @patch("src.chroma_mcp.tools.auto_log_chat_bridge._do_log_chat")
    def test_mcp_log_chat_success(self, mock_do_log_chat):
        """Test successful execution of mcp_log_chat."""
        # Setup mock
        mock_do_log_chat.return_value = "test-chat-id"

        # Call function
        result = mcp_log_chat(self.input_model)

        # Verify results
        mock_do_log_chat.assert_called_once_with(self.input_model)
        assert result == "test-chat-id"

    @patch("src.chroma_mcp.tools.auto_log_chat_bridge._do_log_chat")
    def test_mcp_log_chat_error(self, mock_do_log_chat):
        """Test error handling in mcp_log_chat."""
        # Setup mock to raise exception
        mock_do_log_chat.side_effect = Exception("Test error")

        # Call function and verify it raises the expected exception
        with self.assertRaises(Exception):
            mcp_log_chat(self.input_model)


# Separate pytest-style async tests for the async functions
@pytest.fixture
def input_model():
    """Fixture for input model."""
    return LogChatInput(
        prompt_summary="Test prompt summary",
        response_summary="Test response summary",
        raw_prompt="This is a test prompt",
        raw_response="This is a test response",
        tool_usage=[{"name": "tool1", "args": {"arg1": "value1"}}],
        file_changes=[{"file": "test.py", "before": "def foo(): pass", "after": "def foo(): return True"}],
        involved_entities="test.py,foo",
        session_id="test-session-id",
        collection_name="chat_history_v1",
    )


@pytest.mark.asyncio
@patch("src.chroma_mcp.tools.auto_log_chat_bridge._do_log_chat")
async def test_log_chat_impl_success(mock_do_log_chat, input_model):
    """Test successful execution of _log_chat_impl."""
    # Setup mock
    mock_do_log_chat.return_value = "test-chat-id"

    # Call function
    result = await _log_chat_impl(input_model)

    # Verify results
    mock_do_log_chat.assert_called_once_with(input_model)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"

    # Parse the JSON response
    response_data = json.loads(result[0].text)
    assert response_data["success"] is True
    assert response_data["chat_id"] == "test-chat-id"


@pytest.mark.asyncio
@patch("src.chroma_mcp.tools.auto_log_chat_bridge._do_log_chat")
async def test_log_chat_impl_error(mock_do_log_chat, input_model):
    """Test error handling in _log_chat_impl."""
    # Setup mock to raise exception
    mock_do_log_chat.side_effect = Exception("Test error")

    # Call function
    result = await _log_chat_impl(input_model)

    # Verify results
    mock_do_log_chat.assert_called_once_with(input_model)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"

    # Parse the JSON response
    response_data = json.loads(result[0].text)
    assert response_data["success"] is False
    assert "Test error" in response_data["error"]


if __name__ == "__main__":
    unittest.main()
