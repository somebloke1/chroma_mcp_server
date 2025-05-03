"""
Tests for the thinking CLI.
"""
import argparse
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call
from mcp import ClientSession, types

# Remove the problematic import within the patch context
# with patch("chroma_mcp_thinking.thinking_cli.ClientSession") as MockClientSession:
from chroma_mcp_thinking.thinking_cli import (
    main,
    cmd_record_async,
    cmd_branch_async,
    cmd_search_async,
    cmd_summary_async,
    # Also import sync wrappers for main routing test
    cmd_record,
    cmd_branch,
    cmd_search,
    cmd_summary,
)


@pytest.fixture
def mock_mcp_client():
    """Create a mock mcp.ClientSession for stdio interaction."""
    client = MagicMock(spec=ClientSession)
    client.initialize = AsyncMock(return_value=None)

    # Mock call_tool to return CallToolResult objects
    async def mock_call_tool(*args, **kwargs):
        name = kwargs.get("name")
        result_text = "{}"
        if name == "chroma_sequential_thinking":
            arguments = kwargs.get("arguments", {})
            thought_num = arguments.get("thought_number", 0)
            session_id_arg = arguments.get("session_id", "mock-session-id")  # Use provided or default
            if thought_num == 1:
                result_text = json.dumps({"session_id": session_id_arg})
            else:
                result_text = json.dumps({})
        elif name == "chroma_find_similar_thoughts":
            result_text = json.dumps(
                {
                    "similar_thoughts": [
                        {
                            "session_id": "mock-session-id",
                            "thought_number": 1,
                            "thought": "Mock similar thought",
                            "score": 0.85,
                        }
                    ]
                }
            )
        elif name == "chroma_get_session_summary":
            result_text = json.dumps(
                {
                    "session_thoughts": [
                        {"thought_number": 1, "session_id": "mock-session-id", "thought": "Mock summary thought"}
                    ]
                }
            )
        # Create a CallToolResult object containing the TextContent
        # Ensure the 'type' field is included for TextContent
        return types.CallToolResult(content=[types.TextContent(type="text", text=result_text)])

    client.call_tool = AsyncMock(side_effect=mock_call_tool)
    return client


# Use pytest.mark.asyncio and patch context managers directly
@pytest.mark.asyncio
@patch("chroma_mcp_thinking.thinking_cli.stdio_client")
@patch("chroma_mcp_thinking.thinking_cli.ClientSession")
async def test_cmd_record_single_thought(MockSessionClass, mock_stdio, mock_mcp_client):
    """Test recording a single thought via stdio (async)."""
    # MockSessionClass is now a MagicMock instance

    # Configure mock for stdio_client context manager
    mock_stdio_cm = AsyncMock()
    mock_stdio_cm.__aenter__.return_value = (MagicMock(), MagicMock())
    mock_stdio.return_value = mock_stdio_cm

    # Configure mock for the object returned by ClientSession()
    mock_session_cm = AsyncMock()  # This is the context manager object
    mock_session_cm.__aenter__.return_value = mock_mcp_client  # Configure its aenter
    MockSessionClass.return_value = mock_session_cm  # Make ClientSession() return it

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
    # Call the ASYNC function directly
    await cmd_record_async(args)

    # Check initialize and call_tool were called on the client
    mock_mcp_client.initialize.assert_awaited_once()
    mock_mcp_client.call_tool.assert_awaited_once()
    call_args = mock_mcp_client.call_tool.await_args
    assert call_args.kwargs["name"] == "chroma_sequential_thinking"
    assert call_args.kwargs["arguments"]["thought"] == "Test thought"
    assert call_args.kwargs["arguments"]["thought_number"] == 1
    assert call_args.kwargs["arguments"]["total_thoughts"] == 1
    assert "next_thought_needed" not in call_args.kwargs["arguments"]


@pytest.mark.asyncio
@patch("chroma_mcp_thinking.thinking_cli.stdio_client")
@patch("chroma_mcp_thinking.thinking_cli.ClientSession")
async def test_cmd_branch(MockSessionClass, mock_stdio, mock_mcp_client):
    """Test creating a thought branch via stdio (async)."""
    # MockSessionClass is now a MagicMock instance

    # Configure mock for stdio_client context manager
    mock_stdio_cm = AsyncMock()
    mock_stdio_cm.__aenter__.return_value = (MagicMock(), MagicMock())
    mock_stdio.return_value = mock_stdio_cm

    # Configure mock for the object returned by ClientSession()
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_mcp_client
    MockSessionClass.return_value = mock_session_cm

    branch_thoughts = ["Branch thought 1", "Branch thought 2"]
    args = argparse.Namespace(
        parent_session_id="parent-session-id",
        parent_thought_number=2,
        thoughts=branch_thoughts,
        file=None,
        branch_id="test-branch",
        verbose=False,
    )
    # Call the ASYNC function directly
    await cmd_branch_async(args)

    mock_mcp_client.initialize.assert_awaited_once()
    assert mock_mcp_client.call_tool.await_count == len(branch_thoughts)

    # Check the first call (should include branch_from_thought)
    first_call_args = mock_mcp_client.call_tool.await_args_list[0].kwargs
    assert first_call_args["name"] == "chroma_sequential_thinking"
    assert first_call_args["arguments"]["thought"] == branch_thoughts[0]
    assert first_call_args["arguments"]["thought_number"] == 1
    assert first_call_args["arguments"]["branch_id"] == "test-branch"
    assert first_call_args["arguments"]["branch_from_thought"] == 2
    assert first_call_args["arguments"]["session_id"] == "parent-session-id"

    # Check the second call
    second_call_args = mock_mcp_client.call_tool.await_args_list[1].kwargs
    assert second_call_args["name"] == "chroma_sequential_thinking"
    assert second_call_args["arguments"]["thought"] == branch_thoughts[1]
    assert second_call_args["arguments"]["thought_number"] == 2
    assert second_call_args["arguments"]["branch_id"] == "test-branch"
    assert second_call_args["arguments"]["branch_from_thought"] == 0
    assert second_call_args["arguments"]["session_id"] == "parent-session-id"


@pytest.mark.asyncio
@patch("chroma_mcp_thinking.thinking_cli.stdio_client")
@patch("chroma_mcp_thinking.thinking_cli.ClientSession")
async def test_cmd_search_thoughts(MockSessionClass, mock_stdio, mock_mcp_client):
    """Test searching for thoughts via stdio (async)."""
    # MockSessionClass is now a MagicMock instance

    # Configure mock for stdio_client context manager
    mock_stdio_cm = AsyncMock()
    mock_stdio_cm.__aenter__.return_value = (MagicMock(), MagicMock())
    mock_stdio.return_value = mock_stdio_cm

    # Configure mock for the object returned by ClientSession()
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_mcp_client
    MockSessionClass.return_value = mock_session_cm

    args = argparse.Namespace(
        query="test query", session_id=None, n_results=5, threshold=-1.0, include_branches=False, verbose=False
    )
    # Call the ASYNC function directly
    await cmd_search_async(args)

    mock_mcp_client.initialize.assert_awaited_once()
    mock_mcp_client.call_tool.assert_awaited_once()

    call_args = mock_mcp_client.call_tool.await_args.kwargs
    assert call_args["name"] == "chroma_find_similar_thoughts"
    assert call_args["arguments"]["query"] == "test query"
    assert call_args["arguments"]["n_results"] == 5
    assert call_args["arguments"]["threshold"] == -1.0
    assert call_args["arguments"]["include_branches"] is False


@pytest.mark.asyncio
@patch("chroma_mcp_thinking.thinking_cli.stdio_client")
@patch("chroma_mcp_thinking.thinking_cli.ClientSession")
async def test_cmd_summary(MockSessionClass, mock_stdio, mock_mcp_client):
    """Test getting a session summary via stdio (async)."""
    # MockSessionClass is now a MagicMock instance

    # Configure mock for stdio_client context manager
    mock_stdio_cm = AsyncMock()
    mock_stdio_cm.__aenter__.return_value = (MagicMock(), MagicMock())
    mock_stdio.return_value = mock_stdio_cm

    # Configure mock for the object returned by ClientSession()
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_mcp_client
    MockSessionClass.return_value = mock_session_cm

    args = argparse.Namespace(session_id="test-session-id", include_branches=True)
    # Call the ASYNC function directly
    await cmd_summary_async(args)

    mock_mcp_client.initialize.assert_awaited_once()
    mock_mcp_client.call_tool.assert_awaited_once()

    call_args = mock_mcp_client.call_tool.await_args.kwargs
    assert call_args["name"] == "chroma_get_session_summary"
    assert call_args["arguments"]["session_id"] == "test-session-id"
    assert call_args["arguments"]["include_branches"] is True


@patch("chroma_mcp_thinking.thinking_cli.cmd_record")
@patch("chroma_mcp_thinking.thinking_cli.cmd_branch")
@patch("chroma_mcp_thinking.thinking_cli.cmd_search")
@patch("chroma_mcp_thinking.thinking_cli.cmd_summary")
@patch("argparse.ArgumentParser.parse_args")
def test_main_routes_to_correct_command(mock_parse_args, mock_summary, mock_search, mock_branch, mock_record):
    """Test that main routes to the correct command function (sync wrappers)."""
    # Test record command
    mock_args_record = argparse.Namespace(
        command="record",
        thought="t",
        file=None,
        thought_number=None,
        total_thoughts=None,
        next_thought_needed=False,
        func=mock_record,  # Add func attribute pointing to the mock
    )
    mock_parse_args.return_value = mock_args_record
    main()
    mock_record.assert_called_once_with(mock_args_record)
    mock_record.reset_mock()

    # Test branch command
    mock_args_branch = argparse.Namespace(
        command="branch",
        parent_session_id="s1",
        parent_thought_number=1,
        thoughts=["t1"],
        file=None,
        thought=None,
        thought_number=None,
        total_thoughts=None,
        next_thought_needed=False,
        func=mock_branch,  # Add func attribute
    )
    mock_parse_args.return_value = mock_args_branch
    main()
    mock_branch.assert_called_once_with(mock_args_branch)
    mock_branch.reset_mock()

    # Test search command
    mock_args_search = argparse.Namespace(
        command="search",
        query="q",
        thought=None,
        file=None,
        thought_number=None,
        total_thoughts=None,
        next_thought_needed=False,
        func=mock_search,  # Add func attribute
    )
    mock_parse_args.return_value = mock_args_search
    main()
    mock_search.assert_called_once_with(mock_args_search)
    mock_search.reset_mock()

    # Test summary command
    mock_args_summary = argparse.Namespace(
        command="summary",
        session_id="s1",
        thought=None,
        file=None,
        thought_number=None,
        total_thoughts=None,
        next_thought_needed=False,
        func=mock_summary,  # Add func attribute
    )
    mock_parse_args.return_value = mock_args_summary
    main()
    mock_summary.assert_called_once_with(mock_args_summary)
