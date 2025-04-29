"""
Tests for the ThinkingSession class.
"""
import pytest
from mcp import ClientSession
from unittest.mock import MagicMock, patch

# Mock the dependencies
# Assume McpClient needs to be mocked if ThinkingSession instantiates it
# If a client is passed in, we might mock that specific instance instead
# Patching the class globally for simplicity here
# with patch("chroma_mcp_thinking.thinking_session.ChromaMcpClient"):
with patch("chroma_mcp_thinking.thinking_session.ClientSession") as MockMcpClient:
    from chroma_mcp_thinking.thinking_session import ThinkingSession


@pytest.fixture
def mock_client():
    """Create a mock ChromaMcpClient."""
    client = MagicMock()
    client.mcp_chroma_dev_chroma_sequential_thinking.return_value = {"session_id": "test-session-id"}
    client.mcp_chroma_dev_chroma_find_similar_thoughts.return_value = {
        "similar_thoughts": [
            {
                "metadata": {"session_id": "test-session-id", "thought_number": 1},
                "document": "Test thought",
                "distance": 0.5,
            }
        ]
    }
    client.mcp_chroma_dev_chroma_find_similar_sessions.return_value = {
        "similar_sessions": [
            {"metadata": {"session_id": "test-session-id"}, "document": "First thought", "distance": 0.5}
        ]
    }
    client.mcp_chroma_dev_chroma_get_session_summary.return_value = {
        "thoughts": [{"metadata": {"thought_number": 1, "session_id": "test-session-id"}, "document": "Test thought"}]
    }
    return client


def test_thinking_session_init():
    """Test ThinkingSession initialization."""
    # Test with default arguments
    # Patch ClientSession as used within ThinkingSession's __init__
    with patch("chroma_mcp_thinking.thinking_session.ClientSession") as MockClientSession:
        mock_instance = MockClientSession.return_value
        mock_instance.mcp_chroma_dev_chroma_sequential_thinking = MagicMock()
        mock_instance.mcp_chroma_dev_chroma_find_similar_thoughts = MagicMock()
        mock_instance.mcp_chroma_dev_chroma_get_session_summary = MagicMock()
        mock_instance.mcp_chroma_dev_chroma_find_similar_sessions = MagicMock()

        session = ThinkingSession()  # Should now use the mocked ClientSession
        assert isinstance(session.client, MagicMock)  # Check it used the mocked instance
        assert session.session_id is not None
        MockClientSession.assert_called_once()  # Verify ClientSession was instantiated

    # Test with provided session ID
    test_session_id = "test-session-123"
    with patch("chroma_mcp_thinking.thinking_session.ClientSession") as MockClientSession:
        session = ThinkingSession(session_id=test_session_id)
        assert session.session_id == test_session_id
        MockClientSession.assert_called_once()

    # Test with provided client instance
    mock_provided_client = MagicMock(spec=ClientSession)
    session = ThinkingSession(client=mock_provided_client, session_id="provided-client-session")
    assert session.client is mock_provided_client
    assert session.session_id == "provided-client-session"


def test_record_thought(mock_client):
    """Test recording a thought."""
    session = ThinkingSession(client=mock_client, session_id="test-session-id")

    result = session.record_thought(
        thought="Test thought", thought_number=1, total_thoughts=3, next_thought_needed=True
    )

    # Client method should be called with correct arguments
    mock_client.mcp_chroma_dev_chroma_sequential_thinking.assert_called_once()
    call_args = mock_client.mcp_chroma_dev_chroma_sequential_thinking.call_args[1]
    assert call_args["thought"] == "Test thought"
    assert call_args["thought_number"] == 1
    assert call_args["total_thoughts"] == 3
    assert call_args["session_id"] == "test-session-id"
    assert call_args["next_thought_needed"] is True

    # Result should be returned from client method
    assert result == {"session_id": "test-session-id"}


def test_find_similar_thoughts(mock_client):
    """Test finding similar thoughts."""
    session = ThinkingSession(client=mock_client, session_id="test-session-id")

    results = session.find_similar_thoughts(query="test query", n_results=5, threshold=0.7, include_branches=True)

    # Client method should be called with correct arguments
    mock_client.mcp_chroma_dev_chroma_find_similar_thoughts.assert_called_once()
    call_args = mock_client.mcp_chroma_dev_chroma_find_similar_thoughts.call_args[1]
    assert call_args["query"] == "test query"
    assert call_args["session_id"] == "test-session-id"
    assert call_args["n_results"] == 5
    assert call_args["threshold"] == 0.7
    assert call_args["include_branches"] is True

    # Results should be extracted from client response
    assert len(results) == 1
    assert results[0]["document"] == "Test thought"
    assert results[0]["metadata"]["session_id"] == "test-session-id"


def test_get_session_summary(mock_client):
    """Test getting session summary."""
    session = ThinkingSession(client=mock_client, session_id="test-session-id")

    summary = session.get_session_summary(include_branches=True)

    # Client method should be called with correct arguments
    mock_client.mcp_chroma_dev_chroma_get_session_summary.assert_called_once()
    call_args = mock_client.mcp_chroma_dev_chroma_get_session_summary.call_args[1]
    assert call_args["session_id"] == "test-session-id"
    assert call_args["include_branches"] is True

    # Summary should be returned from client method
    assert "thoughts" in summary
    assert len(summary["thoughts"]) == 1
    assert summary["thoughts"][0]["document"] == "Test thought"


def test_find_similar_sessions(mock_client):
    """Test finding similar sessions."""
    results = ThinkingSession.find_similar_sessions(query="test query", client=mock_client, n_results=5, threshold=0.7)

    # Client method should be called with correct arguments
    mock_client.mcp_chroma_dev_chroma_find_similar_sessions.assert_called_once()
    call_args = mock_client.mcp_chroma_dev_chroma_find_similar_sessions.call_args[1]
    assert call_args["query"] == "test query"
    assert call_args["n_results"] == 5
    assert call_args["threshold"] == 0.7

    # Results should be extracted from client response
    assert len(results) == 1
    assert results[0]["document"] == "First thought"
    assert results[0]["metadata"]["session_id"] == "test-session-id"
