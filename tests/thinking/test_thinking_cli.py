"""
Tests for the thinking CLI.
"""
import argparse
import json
import pytest
from unittest.mock import patch, MagicMock

# Mock ChromaMcpClient since we don't need the actual implementation for tests
with patch("chroma_mcp_thinking.thinking_cli.ChromaMcpClient"):
    from chroma_mcp_thinking.thinking_cli import main, cmd_record, cmd_branch, cmd_search, cmd_summary


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


@patch("chroma_mcp_thinking.thinking_cli.setup_client")
def test_cmd_record_single_thought(mock_setup_client, mock_client):
    """Test recording a single thought."""
    mock_setup_client.return_value = mock_client

    # Create args
    args = argparse.Namespace(
        thought="Test thought",
        file=None,
        session_id=None,
        metadata=None,
        thought_number=1,
        total_thoughts=1,
        next_thought_needed=False,
        verbose=False,
    )

    # Call function
    cmd_record(args)

    # Check that the client was called correctly
    mock_client.mcp_chroma_dev_chroma_sequential_thinking.assert_called_once()
    call_args = mock_client.mcp_chroma_dev_chroma_sequential_thinking.call_args[1]
    assert call_args["thought"] == "Test thought"
    assert call_args["thought_number"] == 1
    assert call_args["total_thoughts"] == 1
    assert call_args["next_thought_needed"] is False


@patch("chroma_mcp_thinking.thinking_cli.setup_client")
def test_cmd_branch(mock_setup_client, mock_client):
    """Test creating a thought branch."""
    mock_setup_client.return_value = mock_client

    # Create args
    args = argparse.Namespace(
        parent_session_id="parent-session-id",
        parent_thought_number=2,
        thoughts=["Branch thought 1", "Branch thought 2"],
        file=None,
        branch_id="test-branch",
        verbose=False,
    )

    # Call function
    cmd_branch(args)

    # Check that the client was called correctly for each thought
    assert mock_client.mcp_chroma_dev_chroma_sequential_thinking.call_count == 2

    # Check the first call (should include branch_from_thought)
    first_call = mock_client.mcp_chroma_dev_chroma_sequential_thinking.call_args_list[0][1]
    assert first_call["thought"] == "Branch thought 1"
    assert first_call["thought_number"] == 1
    assert first_call["branch_id"] == "test-branch"
    assert first_call["branch_from_thought"] == 2
    assert first_call["session_id"] == "parent-session-id"

    # Check the second call
    second_call = mock_client.mcp_chroma_dev_chroma_sequential_thinking.call_args_list[1][1]
    assert second_call["thought"] == "Branch thought 2"
    assert second_call["thought_number"] == 2
    assert second_call["branch_id"] == "test-branch"
    assert second_call["branch_from_thought"] == 0  # Only the first thought links to parent
    assert second_call["session_id"] == "parent-session-id"


@patch("chroma_mcp_thinking.thinking_cli.setup_client")
def test_cmd_search_thoughts(mock_setup_client, mock_client):
    """Test searching for thoughts."""
    mock_setup_client.return_value = mock_client

    # Create args
    args = argparse.Namespace(
        query="test query",
        sessions=False,
        session_id=None,
        limit=5,
        threshold=-1,
        exclude_branches=False,
        verbose=False,
    )

    # Call function
    cmd_search(args)

    # Check that the client was called correctly
    mock_client.mcp_chroma_dev_chroma_find_similar_thoughts.assert_called_once()
    call_args = mock_client.mcp_chroma_dev_chroma_find_similar_thoughts.call_args[1]
    assert call_args["query"] == "test query"
    assert call_args["n_results"] == 5
    assert call_args["threshold"] == -1
    assert call_args["include_branches"] is True


@patch("chroma_mcp_thinking.thinking_cli.setup_client")
def test_cmd_search_sessions(mock_setup_client, mock_client):
    """Test searching for sessions."""
    mock_setup_client.return_value = mock_client

    # Create args
    args = argparse.Namespace(
        query="test query", sessions=True, session_id=None, limit=5, threshold=-1, exclude_branches=False, verbose=False
    )

    # Call function
    cmd_search(args)

    # Check that the client was called correctly
    mock_client.mcp_chroma_dev_chroma_find_similar_sessions.assert_called_once()
    call_args = mock_client.mcp_chroma_dev_chroma_find_similar_sessions.call_args[1]
    assert call_args["query"] == "test query"
    assert call_args["n_results"] == 5
    assert call_args["threshold"] == -1


@patch("chroma_mcp_thinking.thinking_cli.setup_client")
def test_cmd_summary(mock_setup_client, mock_client):
    """Test getting a session summary."""
    mock_setup_client.return_value = mock_client

    # Create args
    args = argparse.Namespace(session_id="test-session-id", exclude_branches=False)

    # Call function
    cmd_summary(args)

    # Check that the client was called correctly
    mock_client.mcp_chroma_dev_chroma_get_session_summary.assert_called_once()
    call_args = mock_client.mcp_chroma_dev_chroma_get_session_summary.call_args[1]
    assert call_args["session_id"] == "test-session-id"
    assert call_args["include_branches"] is True


@patch("chroma_mcp_thinking.thinking_cli.cmd_record")
@patch("chroma_mcp_thinking.thinking_cli.cmd_branch")
@patch("chroma_mcp_thinking.thinking_cli.cmd_search")
@patch("chroma_mcp_thinking.thinking_cli.cmd_summary")
@patch("argparse.ArgumentParser.parse_args")
def test_main_routes_to_correct_command(mock_parse_args, mock_summary, mock_search, mock_branch, mock_record):
    """Test that main routes to the correct command function."""
    # Test record command
    mock_parse_args.return_value = argparse.Namespace(command="record")
    main()
    mock_record.assert_called_once()

    # Reset mocks
    mock_record.reset_mock()

    # Test branch command
    mock_parse_args.return_value = argparse.Namespace(command="branch")
    main()
    mock_branch.assert_called_once()

    # Reset mocks
    mock_branch.reset_mock()

    # Test search command
    mock_parse_args.return_value = argparse.Namespace(command="search")
    main()
    mock_search.assert_called_once()

    # Reset mocks
    mock_search.reset_mock()

    # Test summary command
    mock_parse_args.return_value = argparse.Namespace(command="summary")
    main()
    mock_summary.assert_called_once()
