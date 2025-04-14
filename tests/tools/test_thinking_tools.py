"""Tests for thinking tools."""

import pytest
import uuid
import time
import json
from contextlib import contextmanager

from typing import Dict, Any, List, Optional
from datetime import datetime
from unittest.mock import patch, MagicMock, ANY

from mcp import types
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS, INTERNAL_ERROR, ErrorData

from src.chroma_mcp.utils.errors import ValidationError
from src.chroma_mcp.tools.thinking_tools import (
    ThoughtMetadata,  # Import if needed for checks
    THOUGHTS_COLLECTION,  # Import constants
    SESSIONS_COLLECTION,  # FIX: Import this constant
    DEFAULT_SIMILARITY_THRESHOLD,
    _sequential_thinking_impl,
    _find_similar_thoughts_impl,
    _get_session_summary_impl,
    _find_similar_sessions_impl,
    SequentialThinkingInput,
    FindSimilarThoughtsInput,
    GetSessionSummaryInput,
    FindSimilarSessionsInput,
    SequentialThinkingWithCustomDataInput,
    _sequential_thinking_with_custom_data_impl,
)

# --- Helper Functions (Copied from test_collection_tools.py) ---


def assert_successful_json_list_result(
    result: List[types.TextContent], expected_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Asserts the result is a list containing one TextContent with valid JSON."""
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], types.TextContent)
    assert result[0].type == "text"

    try:
        result_data = json.loads(result[0].text)
    except json.JSONDecodeError:
        pytest.fail(f"Failed to parse JSON content: {result[0].text}")

    assert isinstance(result_data, dict)
    if expected_data is not None:
        assert result_data == expected_data
    return result_data


# Context manager to assert McpError is raised
@contextmanager
def assert_raises_mcp_error(expected_message: str):
    """Context manager to check if a specific McpError is raised."""
    try:
        yield
    except McpError as e:
        # Check both e.error_data (if exists) and e.args[0]
        message = ""
        if hasattr(e, "error_data") and hasattr(e.error_data, "message"):
            message = str(e.error_data.message)
        elif e.args and isinstance(e.args[0], ErrorData) and hasattr(e.args[0], "message"):
            message = str(e.args[0].message)
        else:
            message = str(e)  # Fallback to the exception string itself

        assert (
            expected_message in message
        ), f"Expected error message containing '{expected_message}' but got '{message}'"
        return
    except Exception as e:
        pytest.fail(f"Expected McpError but got {type(e).__name__}: {e}")
    pytest.fail("Expected McpError but no exception was raised.")


# --- End Helper Functions ---


@pytest.fixture
def mock_chroma_client_thinking():
    """Provides a mocked Chroma client, thoughts collection, and sessions collection."""
    # Patch get_chroma_client within the thinking_tools module
    with patch("src.chroma_mcp.tools.thinking_tools.get_chroma_client") as mock_get_client:
        mock_client = MagicMock()
        mock_thoughts_collection = MagicMock(name="thoughts_collection")
        mock_sessions_collection = MagicMock(name="sessions_collection")

        # Configure the mock client to return specific collections by name
        def get_collection_side_effect(name, embedding_function=None):
            if name == THOUGHTS_COLLECTION:
                return mock_thoughts_collection
            elif name == SESSIONS_COLLECTION:
                return mock_sessions_collection
            else:
                # Raise error for unexpected collection names
                raise ValueError(f"Mock Client: Collection {name} does not exist.")

        mock_client.get_collection.side_effect = get_collection_side_effect
        mock_client.get_or_create_collection.side_effect = get_collection_side_effect  # Mock this too

        mock_get_client.return_value = mock_client

        # Also patch the embedding function if it's used directly
        with patch("src.chroma_mcp.tools.thinking_tools.get_embedding_function") as mock_get_emb:
            mock_get_emb.return_value = MagicMock(name="mock_embedding_function")
            # Yield all mocks needed by tests
            yield mock_client, mock_thoughts_collection, mock_sessions_collection


class TestThinkingTools:
    """Test cases for thinking tools implementation functions."""

    # --- _sequential_thinking_impl Tests ---
    @pytest.mark.asyncio  # Mark as async
    async def test_sequential_thinking_new_session_success(self, mock_chroma_client_thinking):
        """Test recording the first thought in a new session."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking

        input_data = SequentialThinkingInput(
            thought="Initial thought",
            thought_number=1,
            total_thoughts=3,
        )

        # ACT
        result = await _sequential_thinking_impl(input_data)

        # ASSERT using MODIFIED helper
        result_data = assert_successful_json_list_result(result)

        # Assertions on mocks
        mock_client.get_or_create_collection.assert_called_once_with(THOUGHTS_COLLECTION)
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        assert call_args.kwargs["documents"] == ["Initial thought"]
        assert len(call_args.kwargs["ids"]) == 1
        thought_id = call_args.kwargs["ids"][0]
        assert thought_id.startswith("thought_")
        assert call_args.kwargs["metadatas"][0]["thought_number"] == 1
        assert call_args.kwargs["metadatas"][0]["total_thoughts"] == 3
        assert "session_id" in call_args.kwargs["metadatas"][0]
        session_id = call_args.kwargs["metadatas"][0]["session_id"]

        # Assertions on result data keys and values
        assert result_data.get("thought_id") == thought_id
        assert result_data.get("session_id") == session_id
        assert result_data.get("previous_thoughts_count") == 0  # Check count

    @pytest.mark.asyncio  # Mark as async
    async def test_sequential_thinking_existing_session(self, mock_chroma_client_thinking):
        """Test recording subsequent thoughts in an existing session."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking
        session_id = "existing_session_123"

        input_data = SequentialThinkingInput(
            thought="Second thought",
            thought_number=2,
            total_thoughts=3,
            session_id=session_id,
        )

        # Mock collection.get for previous thoughts check
        mock_collection.get.return_value = {
            "ids": [f"thought_{session_id}_1"],
            "documents": ["First idea"],
            "metadatas": [
                {
                    "session_id": session_id,
                    "thought_number": 1,
                    "total_thoughts": 3,
                    "timestamp": 12345,
                    "branch_id": None,  # Simulate non-branched thought
                }
            ],
        }

        # ACT
        result = await _sequential_thinking_impl(input_data)

        # ASSERT using MODIFIED helper
        result_data = assert_successful_json_list_result(result)

        # Assertions on mocks
        mock_collection.get.assert_called_once()
        get_call_args = mock_collection.get.call_args
        # Updated expected_where to reflect the simplified get call
        expected_where = {"session_id": session_id}  # Fetch all session thoughts, filter in Python
        assert get_call_args.kwargs["where"] == expected_where

        mock_collection.add.assert_called_once()
        add_call_args = mock_collection.add.call_args
        assert add_call_args.kwargs["metadatas"][0]["session_id"] == session_id
        added_thought_id = add_call_args.kwargs["ids"][0]

        # Assertions on result data
        assert result_data.get("session_id") == session_id
        assert result_data.get("thought_id") == added_thought_id
        assert result_data.get("previous_thoughts_count") == 1  # Check count

    @pytest.mark.asyncio  # Mark as async
    async def test_sequential_thinking_new_branch(self, mock_chroma_client_thinking):
        """Test starting a new branch from a specific thought."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking
        session_id = "branch_session_456"
        branch_id = "feature_branch_abc"
        branch_from = 2

        input_data = SequentialThinkingInput(
            thought="First thought on the branch",
            thought_number=3,
            total_thoughts=5,
            session_id=session_id,
            branch_id=branch_id,
            branch_from_thought=branch_from,
        )

        # Mock collection.get for previous thoughts (might return thoughts from main trunk)
        mock_collection.get.return_value = {
            "ids": [f"thought_{session_id}_1", f"thought_{session_id}_2"],
            "documents": ["First idea", "Second idea"],
            "metadatas": [
                {
                    "session_id": session_id,
                    "thought_number": 1,
                    "total_thoughts": 3,
                    "timestamp": 12345,
                    "branch_id": None,
                },
                {
                    "session_id": session_id,
                    "thought_number": 2,
                    "total_thoughts": 3,
                    "timestamp": 12345,
                    "branch_id": branch_id,
                },
            ],
        }

        # ACT
        result = await _sequential_thinking_impl(input_data)

        # ASSERT using MODIFIED helper
        result_data = assert_successful_json_list_result(result)

        # Assertions on mocks
        mock_collection.get.assert_called_once()
        get_call_args = mock_collection.get.call_args
        # Updated expected_where to reflect the simplified get call
        expected_where = {"session_id": session_id}  # Fetch all session thoughts, filter in Python
        assert get_call_args.kwargs["where"] == expected_where

        mock_collection.add.assert_called_once()
        add_call_args = mock_collection.add.call_args
        assert add_call_args.kwargs["metadatas"][0]["session_id"] == session_id
        assert add_call_args.kwargs["metadatas"][0]["branch_id"] == branch_id
        added_thought_id = add_call_args.kwargs["ids"][0]

        # Assertions on result data
        assert result_data.get("session_id") == session_id
        assert result_data.get("thought_id") == added_thought_id
        assert result_data.get("previous_thoughts_count") == 2  # Check count

    @pytest.mark.asyncio  # Mark as async
    async def test_sequential_thinking_invalid_custom_data_json(self, mock_chroma_client_thinking):
        """Test failure when custom_data is invalid JSON."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking

        input_data = SequentialThinkingWithCustomDataInput(
            thought="Thought with bad custom data",
            thought_number=1,
            total_thoughts=1,
            custom_data='{"key": "value", "unterminated}',  # Invalid JSON
        )

        # ASSERT: Expect McpError to be raised now
        with assert_raises_mcp_error("Invalid JSON format for custom_data string"):
            await _sequential_thinking_with_custom_data_impl(input_data)

        # Ensure add was not called
        mock_collection.add.assert_not_called()

    @pytest.mark.asyncio  # Mark as async
    async def test_sequential_thinking_custom_data_not_dict(self, mock_chroma_client_thinking):
        """Test failure when custom_data JSON decodes to non-dictionary."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking

        input_data = SequentialThinkingWithCustomDataInput(
            thought="Thought with non-dict custom data",
            thought_number=1,
            total_thoughts=1,
            custom_data="[1, 2, 3]",  # Valid JSON, but not a dict
        )

        # ASSERT: Expect McpError to be raised now
        with assert_raises_mcp_error("Custom data string must decode to a JSON object (dictionary)."):
            await _sequential_thinking_with_custom_data_impl(input_data)

        # Ensure add was not called
        mock_collection.add.assert_not_called()

    # --- _find_similar_thoughts_impl Tests ---
    @pytest.mark.asyncio  # Mark as async
    async def test_find_similar_thoughts_success(self, mock_chroma_client_thinking):
        """Test finding similar thoughts successfully."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking

        query = "find me similar ideas"
        threshold = DEFAULT_SIMILARITY_THRESHOLD  # Use constant

        # Mock query results
        mock_collection.query.return_value = {
            "ids": [["t1", "t2", "t3"]],
            "documents": [["idea A", "idea B", "idea C"]],
            "metadatas": [[{"session_id": "s1"}, {"session_id": "s2", "custom:tag": "X"}, {"session_id": "s1"}]],
            "distances": [[0.1, 0.25, 0.4]],  # Similarities: 0.9, 0.75, 0.6
        }

        # ACT - Use default n_results from model (which is 5)
        input_model = FindSimilarThoughtsInput(query=query, threshold=threshold)
        result = await _find_similar_thoughts_impl(input_model)

        # ASSERT using MODIFIED helper
        result_data = assert_successful_json_list_result(result)

        # Assertions on mocks
        mock_client.get_collection.assert_called_once_with(THOUGHTS_COLLECTION)
        # Expect n_results=5 (Pydantic default)
        mock_collection.query.assert_called_once_with(
            query_texts=[query], n_results=5, where=None, include=["documents", "metadatas", "distances"]
        )

        # Assertions on result data
        assert len(result_data.get("similar_thoughts", [])) == 2  # t3 is below threshold
        assert result_data.get("total_found") == 2
        assert result_data.get("threshold_used") == threshold
        # Check content of results
        thought1 = result_data["similar_thoughts"][0]
        assert thought1["id"] == "t1"
        assert thought1["similarity"] == 0.9
        assert thought1["metadata"]["session_id"] == "s1"
        # Check reconstructed custom data
        thought2 = result_data["similar_thoughts"][1]
        assert thought2["id"] == "t2"
        assert thought2["metadata"]["session_id"] == "s2"
        assert thought2["metadata"].get("custom_data") == {"tag": "X"}

    @pytest.mark.asyncio  # Mark as async
    async def test_find_similar_thoughts_with_session_filter(self, mock_chroma_client_thinking):
        """Test finding similar thoughts filtered by session ID."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking

        session_id_to_find = "s1"

        # Mock query results (same as above)
        mock_collection.query.return_value = {
            "ids": [["t1", "t2", "t3"]],
            "documents": [["idea A", "idea B", "idea C"]],
            "metadatas": [[{"session_id": "s1"}, {"session_id": "s2"}, {"session_id": "s1"}]],
            "distances": [[0.1, 0.25, 0.4]],
        }

        # ACT
        input_model = FindSimilarThoughtsInput(
            query=session_id_to_find, session_id=session_id_to_find, n_results=3, include_branches=False, threshold=0.5
        )
        result = await _find_similar_thoughts_impl(input_model)

        # ASSERT using MODIFIED helper
        result_data = assert_successful_json_list_result(result)

        # Check query was called with the where clause
        mock_collection.query.assert_called_once_with(
            query_texts=[session_id_to_find], n_results=3, where={"session_id": session_id_to_find}, include=ANY
        )

        # Assertions on result data (mock doesn't filter, so we expect all 3, but check metadata)
        assert len(result_data.get("similar_thoughts", [])) == 3
        assert result_data["similar_thoughts"][0].get("metadata", {}).get("session_id") == "s1"
        # assert result_data["similar_thoughts"][1].get("metadata", {}).get("session_id") == "s2" # Mock doesn't filter
        assert result_data["similar_thoughts"][2].get("metadata", {}).get("session_id") == "s1"

    @pytest.mark.asyncio  # Mark as async
    async def test_find_similar_thoughts_collection_not_found(self, mock_chroma_client_thinking):
        """Test find_similar_thoughts when the collection does not exist."""
        mock_client, _, _ = mock_chroma_client_thinking
        # Mock get_collection to raise the specific ValueError
        mock_client.get_collection.side_effect = ValueError(f"Collection {THOUGHTS_COLLECTION} does not exist.")

        # ACT
        input_model = FindSimilarThoughtsInput(query="any query")
        result = await _find_similar_thoughts_impl(input_model)

        # ASSERT: Should return success list with a message
        result_data = assert_successful_json_list_result(result)
        assert result_data.get("similar_thoughts") == []
        assert result_data.get("total_found") == 0
        mock_client.get_collection.assert_called_once_with(THOUGHTS_COLLECTION)
        # Ensure query was not called if collection not found
        # (Need the mock collection instance for this)
        # Assuming the side effect prevents query from being called implicitly
        # If side_effect doesn't prevent access, mock collection mock would be needed:
        # mock_thoughts_collection.query.assert_not_called()

    # --- _get_session_summary_impl Tests ---
    @pytest.mark.asyncio  # Mark as async
    async def test_get_session_summary_success(self, mock_chroma_client_thinking):
        """Test getting a session summary successfully."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking
        session_id = "summary_session"

        # Mock collection.get results
        mock_collection.get.return_value = {
            "ids": [f"thought_{session_id}_2", f"thought_{session_id}_1"],  # Unordered
            "documents": ["Thought two", "Thought one"],
            "metadatas": [
                {"session_id": session_id, "thought_number": 2, "custom:tag": "final"},
                {"session_id": session_id, "thought_number": 1},
            ],
        }

        # ACT
        input_model = GetSessionSummaryInput(session_id=session_id)
        result = await _get_session_summary_impl(input_model)

        # ASSERT using MODIFIED helper
        result_data = assert_successful_json_list_result(result)

        # Assertions on mocks
        mock_client.get_collection.assert_called_once_with(THOUGHTS_COLLECTION)
        mock_collection.get.assert_called_once_with(
            where={"session_id": session_id}, include=["documents", "metadatas"]
        )

        # Assertions on result data
        assert result_data.get("session_id") == session_id
        assert len(result_data.get("session_thoughts", [])) == 2
        # Check sorting and custom data reconstruction
        assert result_data["session_thoughts"][0]["metadata"]["thought_number"] == 1
        assert result_data["session_thoughts"][1]["metadata"]["thought_number"] == 2
        assert result_data["session_thoughts"][1]["metadata"].get("custom_data") == {"tag": "final"}

    @pytest.mark.asyncio  # Mark as async
    async def test_get_session_summary_no_thoughts(self, mock_chroma_client_thinking):
        """Test getting a summary for a session with no thoughts found."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking
        session_id = "empty_session"
        # Mock collection.get returning empty results
        mock_collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}

        # Expected result structure when no thoughts are found
        expected_result_data = {"session_id": session_id, "session_thoughts": [], "total_thoughts_in_session": 0}

        # ACT
        input_model = GetSessionSummaryInput(session_id=session_id)
        result = await _get_session_summary_impl(input_model)

        # ASSERT using MODIFIED helper - compare with the expected structure
        assert_successful_json_list_result(result, expected_data=expected_result_data)

        # Assertions on mocks
        mock_client.get_collection.assert_called_once_with(THOUGHTS_COLLECTION)
        mock_collection.get.assert_called_once_with(
            where={"session_id": session_id}, include=["documents", "metadatas"]
        )

    @pytest.mark.asyncio  # Mark as async
    async def test_get_session_summary_collection_not_found(self, mock_chroma_client_thinking):
        """Test getting summary when the collection does not exist."""
        mock_client, _, _ = mock_chroma_client_thinking
        session_id = "no_collection_session"
        # Mock get_collection to raise error
        mock_client.get_collection.side_effect = ValueError(f"Collection {THOUGHTS_COLLECTION} does not exist.")

        # ACT
        input_model = GetSessionSummaryInput(session_id=session_id)
        result = await _get_session_summary_impl(input_model)

        # ASSERT: Expect success list with a message
        result_data = assert_successful_json_list_result(result)
        assert f"Collection '{THOUGHTS_COLLECTION}' not found" in result_data.get("message", "")
        assert result_data.get("session_thoughts") == []

    @pytest.mark.asyncio
    async def test_get_session_summary_unexpected_error(self, mock_chroma_client_thinking):
        """Test unexpected error during get session summary."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking
        error_message = "Cannot get thoughts"
        mock_collection.get.side_effect = Exception(error_message)

        # ACT & ASSERT: Expect McpError to be raised
        input_model = GetSessionSummaryInput(session_id="some_session")
        with assert_raises_mcp_error(
            f"Tool Error: An unexpected error occurred while getting session summary for 'some_session'. Details: {error_message}"
        ):
            await _get_session_summary_impl(input_model)

        mock_collection.get.assert_called_once()  # Ensure the failing method was called

    # --- _find_similar_sessions_impl Tests ---
    @pytest.mark.asyncio  # Mark as async
    async def test_find_similar_sessions_success(self, mock_chroma_client_thinking):
        """Test finding similar sessions successfully."""
        mock_client, mock_thoughts_collection, mock_sessions_collection = mock_chroma_client_thinking

        query = "Project planning"
        threshold = 0.6
        n_results = 5  # Test with default n_results

        # --- Setup Mocks ---
        # Mock the .get() call on the THOUGHTS collection to return session IDs
        mock_thoughts_collection.get.return_value = {
            "ids": ["t1", "t2", "t3"],
            "metadatas": [
                {"session_id": "session_abc"},
                {"session_id": "session_xyz"},
                {"session_id": "session_abc"},  # Duplicate ID is fine for get
            ],
            # Other fields like documents are not needed for this specific mock
        }

        # Mock the SESSIONS collection query response
        mock_sessions_collection.query.return_value = {
            "ids": [["session_abc", "session_xyz"]],
            "distances": [[0.3, 0.7]],  # Similarities: 0.7, 0.3 (session_xyz filtered)
            "metadatas": [[{"summary": "Plan A"}, {"summary": "Plan B"}]],
            "documents": [[None], [None]],
        }
        # Mock the SESSIONS collection .get() call used for embedding new sessions
        # Assume session_abc and session_xyz already exist
        mock_sessions_collection.get.return_value = {"ids": ["session_abc", "session_xyz"]}

        # Mock the internal call to _get_session_summary_impl for the final result assembly
        with patch("src.chroma_mcp.tools.thinking_tools._get_session_summary_impl") as mock_get_summary:
            # Configure mock_get_summary to return a successful result for session_abc
            mock_summary_result_list = [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "session_id": "session_abc",
                            "session_thoughts": [{"id": "t1", "content": "plan A step 1"}],
                            "total_thoughts_in_session": 1,
                        }
                    ),
                )
            ]
            mock_get_summary.return_value = mock_summary_result_list

            # --- Act ---
            input_model = FindSimilarSessionsInput(query=query, threshold=threshold)
            result = await _find_similar_sessions_impl(input_model)

            # --- Assert --- using MODIFIED helper
            result_data = assert_successful_json_list_result(result)

            # Assertions on mocks - Expect THOUGHTS first, then SESSIONS
            mock_client.get_collection.assert_any_call(THOUGHTS_COLLECTION)
            # Ensure the specific get call for metadata was made on thoughts collection
            mock_thoughts_collection.get.assert_called_once_with(include=["metadatas"])
            # Ensure get_collection was called for SESSIONS
            mock_client.get_collection.assert_any_call(SESSIONS_COLLECTION)
            # Ensure get was called on sessions collection to check existing IDs
            mock_sessions_collection.get.assert_called_once_with()
            # Ensure session summary was called for the final result
            mock_get_summary.assert_called_once_with(GetSessionSummaryInput(session_id="session_abc"))

            # Assert query on the sessions collection mock
            mock_sessions_collection.query.assert_called_once_with(
                query_texts=[query], n_results=n_results, include=["metadatas", "distances"]
            )

            # Assertions on result data
            assert len(result_data.get("similar_sessions", [])) == 1  # session_xyz filtered
            assert result_data["similar_sessions"][0]["session_id"] == "session_abc"
            assert result_data["similar_sessions"][0]["similarity_score"] == pytest.approx(0.7)
            # Check that the summary data from the mocked _get_session_summary_impl is present
            assert len(result_data["similar_sessions"][0].get("session_thoughts", [])) == 1
            assert result_data["similar_sessions"][0]["session_thoughts"][0]["content"] == "plan A step 1"

    @pytest.mark.asyncio  # Mark as async
    async def test_find_similar_sessions_collection_not_found(self, mock_chroma_client_thinking):
        """Test finding similar sessions when the sessions collection doesn't exist."""
        mock_client, _, mock_sessions_collection = mock_chroma_client_thinking

        # Configure get_collection to raise error specifically for SESSIONS_COLLECTION
        def get_collection_side_effect(name, embedding_function=None):
            if name == THOUGHTS_COLLECTION:
                return MagicMock()  # Return a dummy thoughts collection
            elif name == SESSIONS_COLLECTION:
                raise ValueError(f"Collection {SESSIONS_COLLECTION} does not exist.")  # Simulate Chroma error
            else:
                raise ValueError(f"Unexpected collection {name}")

        mock_client.get_collection.side_effect = get_collection_side_effect

        # ACT
        input_model = FindSimilarSessionsInput(query="any query")
        result = await _find_similar_sessions_impl(input_model)

        # ASSERT: Expect success list with empty results if THOUGHTS collection missing
        result_data = assert_successful_json_list_result(result)
        assert result_data.get("similar_sessions") == []
        assert result_data.get("total_found") == 0

    @pytest.mark.asyncio
    async def test_find_similar_sessions_sessions_collection_not_found(self, mock_chroma_client_thinking):
        """Test finding similar sessions when the required SESSIONS collection doesn't exist."""
        mock_client, mock_thoughts_collection, _ = mock_chroma_client_thinking  # Don't need mock_sessions_collection

        # Mock thoughts collection get to return some session IDs
        mock_thoughts_collection.get.return_value = {"metadatas": [{"session_id": "s1"}]}

        # Configure get_collection to raise error specifically for SESSIONS_COLLECTION
        def get_collection_side_effect(name, embedding_function=None):
            if name == THOUGHTS_COLLECTION:
                return mock_thoughts_collection
            elif name == SESSIONS_COLLECTION:
                raise ValueError(f"Collection {SESSIONS_COLLECTION} does not exist.")
            else:
                raise ValueError(f"Unexpected collection {name}")

        mock_client.get_collection.side_effect = get_collection_side_effect

        # ACT & ASSERT: Expect McpError to be raised
        input_model = FindSimilarSessionsInput(query="any query")
        with assert_raises_mcp_error(f"Tool Error: Collection '{SESSIONS_COLLECTION}' not found"):
            await _find_similar_sessions_impl(input_model)

    # +++ Start New Coverage Tests +++

    @pytest.mark.asyncio
    async def test_sequential_thinking_get_create_collection_error(self, mock_chroma_client_thinking):
        """Test error during get_or_create_collection in sequential thinking."""
        mock_client, _, _ = mock_chroma_client_thinking
        error_message = "DB connection failed"
        mock_client.get_or_create_collection.side_effect = Exception(error_message)

        input_model = SequentialThinkingInput(thought="t", thought_number=1, total_thoughts=1)

        with assert_raises_mcp_error(f"ChromaDB Error accessing collection '{THOUGHTS_COLLECTION}': {error_message}"):
            await _sequential_thinking_impl(input_model)

    @pytest.mark.asyncio
    async def test_sequential_thinking_collection_add_error(self, mock_chroma_client_thinking):
        """Test error during collection.add in sequential thinking."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking
        error_message = "Failed to add document"
        mock_collection.add.side_effect = ValueError(error_message)

        input_model = SequentialThinkingInput(thought="t", thought_number=1, total_thoughts=1)

        with assert_raises_mcp_error(f"ChromaDB Error adding thought: {error_message}"):
            await _sequential_thinking_impl(input_model)

    @pytest.mark.asyncio
    async def test_sequential_thinking_get_prev_thoughts_error(self, mock_chroma_client_thinking):
        """Test non-critical error during collection.get for previous thoughts."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking
        mock_collection.get.side_effect = Exception("Failed to get previous")

        # Call with thought_number > 1 to trigger the .get call
        input_model = SequentialThinkingInput(thought="t2", thought_number=2, total_thoughts=2, session_id="s1")

        # ACT: Should still succeed despite the get error, just log a warning
        result = await _sequential_thinking_impl(input_model)
        result_data = assert_successful_json_list_result(result)

        # ASSERT: Check that the thought was added, but count is 0
        mock_collection.add.assert_called_once()
        mock_collection.get.assert_called_once()  # Ensure get was called
        assert result_data["previous_thoughts_count"] == 0
        assert result_data["session_id"] == "s1"

    @pytest.mark.asyncio
    async def test_find_similar_thoughts_query_error(self, mock_chroma_client_thinking):
        """Test error during collection.query in find similar thoughts."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking
        error_message = "Invalid query syntax"
        mock_collection.query.side_effect = ValueError(error_message)

        input_model = FindSimilarThoughtsInput(query="q")

        with assert_raises_mcp_error(f"ChromaDB Query Error: {error_message}"):
            await _find_similar_thoughts_impl(input_model)

    @pytest.mark.asyncio
    async def test_find_similar_thoughts_generic_error(self, mock_chroma_client_thinking):
        """Test generic error during find similar thoughts."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking
        error_message = "Something unexpected happened"
        mock_collection.query.side_effect = Exception(error_message)

        input_model = FindSimilarThoughtsInput(query="q")

        with assert_raises_mcp_error(
            f"Tool Error: An unexpected error occurred while finding similar thoughts. Details: {error_message}"
        ):
            await _find_similar_thoughts_impl(input_model)

    @pytest.mark.asyncio
    async def test_get_session_summary_get_error(self, mock_chroma_client_thinking):
        """Test error during collection.get in get session summary."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking
        error_message = "Invalid filter for get"
        mock_collection.get.side_effect = ValueError(error_message)

        input_model = GetSessionSummaryInput(session_id="s1")

        with assert_raises_mcp_error(f"ChromaDB Get Error: {error_message}"):
            await _get_session_summary_impl(input_model)

    @pytest.mark.asyncio
    async def test_find_similar_sessions_thoughts_get_error(self, mock_chroma_client_thinking):
        """Test error getting thoughts collection in find similar sessions."""
        mock_client, mock_thoughts_collection, _ = mock_chroma_client_thinking
        error_message = "Cannot access thoughts DB"
        mock_thoughts_collection.get.side_effect = Exception(error_message)

        input_model = FindSimilarSessionsInput(query="q")

        with assert_raises_mcp_error(f"ChromaDB Error accessing thoughts collection: {error_message}"):
            await _find_similar_sessions_impl(input_model)

    @pytest.mark.asyncio
    async def test_find_similar_sessions_sessions_get_error(self, mock_chroma_client_thinking):
        """Test error getting sessions collection in find similar sessions."""
        mock_client, mock_thoughts_collection, mock_sessions_collection = mock_chroma_client_thinking
        error_message = "Cannot access sessions DB"
        # Mock thoughts collection successfully
        mock_thoughts_collection.get.return_value = {"metadatas": [{"session_id": "s1"}]}
        # Mock sessions collection get error
        mock_sessions_collection.get.side_effect = Exception(error_message)

        input_model = FindSimilarSessionsInput(query="q")

        # This error happens during the check for existing sessions
        with assert_raises_mcp_error(f"ChromaDB Error updating sessions: {error_message}"):
            await _find_similar_sessions_impl(input_model)

    @pytest.mark.asyncio
    async def test_find_similar_sessions_embed_error(self, mock_chroma_client_thinking):
        """Test error embedding/adding sessions in find similar sessions."""
        mock_client, mock_thoughts_collection, mock_sessions_collection = mock_chroma_client_thinking
        error_message = "Embedding failed"
        # Mock thoughts collection successfully
        mock_thoughts_collection.get.return_value = {"metadatas": [{"session_id": "s1"}]}
        # Mock sessions collection get returns empty (to trigger add)
        mock_sessions_collection.get.return_value = {"ids": []}
        # Mock sessions collection add error
        mock_sessions_collection.add.side_effect = Exception(error_message)

        # Mock the internal call to _get_session_summary_impl for embedding
        with patch("src.chroma_mcp.tools.thinking_tools._get_session_summary_impl") as mock_get_summary:
            # Return a list containing a TextContent object, not CallToolResult
            mock_summary_result_list = [
                types.TextContent(type="text", text=json.dumps({"session_thoughts": [{"content": "Summary"}]}))
            ]
            mock_get_summary.return_value = mock_summary_result_list

            input_model = FindSimilarSessionsInput(query="q")

            with assert_raises_mcp_error(f"ChromaDB Error updating sessions: {error_message}"):
                await _find_similar_sessions_impl(input_model)

    @pytest.mark.asyncio
    async def test_find_similar_sessions_query_error(self, mock_chroma_client_thinking):
        """Test error during query on sessions collection in find similar sessions."""
        mock_client, mock_thoughts_collection, mock_sessions_collection = mock_chroma_client_thinking
        error_message = "Session query failed"
        # Mock thoughts collection successfully
        mock_thoughts_collection.get.return_value = {"metadatas": [{"session_id": "s1"}]}
        # Mock sessions collection get returns existing
        mock_sessions_collection.get.return_value = {"ids": ["s1"]}
        # Mock sessions collection query error
        mock_sessions_collection.query.side_effect = ValueError(error_message)

        input_model = FindSimilarSessionsInput(query="q")

        with assert_raises_mcp_error(f"ChromaDB Query Error on sessions: {error_message}"):
            await _find_similar_sessions_impl(input_model)

    @pytest.mark.asyncio
    async def test_find_similar_sessions_invalid_threshold(self, mock_chroma_client_thinking):
        """Test finding similar sessions with an invalid threshold value."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking

        input_data_low = FindSimilarSessionsInput(query="test", threshold=-0.1)
        input_data_high = FindSimilarSessionsInput(query="test", threshold=1.1)

        expected_msg = "Threshold must be between 0.0 and 1.0"

        with assert_raises_mcp_error(expected_msg):
            await _find_similar_sessions_impl(input_data_low)

        with assert_raises_mcp_error(expected_msg):
            await _find_similar_sessions_impl(input_data_high)

    # +++ End New Coverage Tests +++
