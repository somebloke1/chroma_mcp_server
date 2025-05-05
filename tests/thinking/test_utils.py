"""
Tests for the thinking utility functions.
"""

import pytest
from unittest.mock import MagicMock, patch

# Mock ChromaMcpClient since we don't need the actual implementation for tests
with patch("chroma_mcp_thinking.utils.ChromaMcpClient"):
    with patch("chroma_mcp_thinking.thinking_session.ClientSession") as MockMcpClient:
        from chroma_mcp_thinking.utils import record_thought_chain, find_thoughts_across_sessions, create_thought_branch


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
    client.mcp_chroma_dev_chroma_get_session_summary.return_value = {
        "thoughts": [{"metadata": {"thought_number": 1, "session_id": "test-session-id"}, "document": "Test thought"}]
    }
    return client


@patch("chroma_mcp_thinking.utils.ThinkingSession")
def test_record_thought_chain(mock_thinking_session_class, mock_client):
    """Test recording a thought chain."""
    # Setup mock session
    mock_session = MagicMock()
    mock_session.session_id = "test-session-id"
    mock_session.get_session_summary.return_value = {"thoughts": [{"document": "Test thought"}]}
    mock_thinking_session_class.return_value = mock_session

    # Call the function
    thoughts = ["Thought 1", "Thought 2", "Thought 3"]
    metadata = {"domain": "testing", "tags": ["test", "example"]}
    result = record_thought_chain(
        thoughts=thoughts, session_id="test-session-id", metadata=metadata, client=mock_client
    )

    # Verify ThinkingSession was created correctly
    mock_thinking_session_class.assert_called_once_with(client=mock_client, session_id="test-session-id")

    # Verify record_thought was called for each thought
    assert mock_session.record_thought.call_count == 3

    # Check first thought call
    first_call = mock_session.record_thought.call_args_list[0][1]
    assert first_call["thought"] == "Thought 1"
    assert first_call["thought_number"] == 1
    assert first_call["total_thoughts"] == 3
    assert first_call["next_thought_needed"] is True

    # Check last thought call
    last_call = mock_session.record_thought.call_args_list[2][1]
    assert last_call["thought"] == "Thought 3"
    assert last_call["thought_number"] == 3
    assert last_call["total_thoughts"] == 3
    assert last_call["next_thought_needed"] is False

    # Verify result contains expected keys
    assert "session_id" in result
    assert "total_thoughts" in result
    assert "metadata" in result
    assert "summary" in result
    assert result["session_id"] == "test-session-id"
    assert result["total_thoughts"] == 3
    assert result["metadata"] == metadata


def test_find_thoughts_across_sessions(mock_client):
    """Test finding thoughts across sessions."""
    results = find_thoughts_across_sessions(
        query="test query",
        n_results=5,
        threshold=0.7,
        include_branches=False,
        session_id="specific-session-id",
        client=mock_client,
    )

    # Verify client method was called correctly
    mock_client.mcp_chroma_dev_chroma_find_similar_thoughts.assert_called_once()
    call_args = mock_client.mcp_chroma_dev_chroma_find_similar_thoughts.call_args[1]
    assert call_args["query"] == "test query"
    assert call_args["n_results"] == 5
    assert call_args["threshold"] == 0.7
    assert call_args["include_branches"] is False
    assert call_args["session_id"] == "specific-session-id"

    # Verify results
    assert len(results) == 1
    assert results[0]["document"] == "Test thought"
    assert results[0]["metadata"]["session_id"] == "test-session-id"


@patch("chroma_mcp_thinking.utils.ThinkingSession")
def test_create_thought_branch(mock_thinking_session_class, mock_client):
    """Test creating a thought branch."""
    # Setup mock session
    mock_session = MagicMock()
    mock_session.session_id = "parent-session-id"
    mock_session.get_session_summary.return_value = {"thoughts": [{"document": "Branch thought"}]}
    mock_thinking_session_class.return_value = mock_session

    # Call the function
    branch_thoughts = ["Branch thought 1", "Branch thought 2"]
    branch_id = "test-branch"
    result = create_thought_branch(
        parent_session_id="parent-session-id",
        parent_thought_number=2,
        branch_thoughts=branch_thoughts,
        branch_id=branch_id,
        client=mock_client,
    )

    # Verify ThinkingSession was created correctly
    mock_thinking_session_class.assert_called_once_with(client=mock_client, session_id="parent-session-id")

    # Verify record_thought was called for each thought
    assert mock_session.record_thought.call_count == 2

    # Check first thought call (should include branch_from_thought)
    first_call = mock_session.record_thought.call_args_list[0][1]
    assert first_call["thought"] == "Branch thought 1"
    assert first_call["thought_number"] == 1
    assert first_call["total_thoughts"] == 2
    assert first_call["branch_id"] == "test-branch"
    assert first_call["branch_from_thought"] == 2
    assert first_call["next_thought_needed"] is True

    # Check second thought call
    second_call = mock_session.record_thought.call_args_list[1][1]
    assert second_call["thought"] == "Branch thought 2"
    assert second_call["thought_number"] == 2
    assert second_call["total_thoughts"] == 2
    assert second_call["branch_id"] == "test-branch"
    assert second_call["branch_from_thought"] == 0  # Only the first thought links to parent
    assert second_call["next_thought_needed"] is False

    # Verify result contains expected keys
    assert "session_id" in result
    assert "branch_id" in result
    assert "parent_thought" in result
    assert "total_branch_thoughts" in result
    assert "summary" in result
    assert result["session_id"] == "parent-session-id"
    assert result["branch_id"] == "test-branch"
    assert result["parent_thought"] == 2
    assert result["total_branch_thoughts"] == 2


def test_create_thought_branch_invalid_parent():
    """Test creating a thought branch with invalid parent thought number."""
    with pytest.raises(ValueError):
        create_thought_branch(
            parent_session_id="parent-session-id",
            parent_thought_number=0,  # Invalid, must be at least 1
            branch_thoughts=["Branch thought"],
        )
