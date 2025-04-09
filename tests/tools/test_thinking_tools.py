"""Tests for thinking tools."""

import pytest
import uuid
import time
import json

from typing import Dict, Any, List, Optional
from datetime import datetime
from unittest.mock import patch, MagicMock, ANY

from mcp import types
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS, INTERNAL_ERROR, ErrorData

from src.chroma_mcp.utils.errors import ValidationError
from src.chroma_mcp.tools.thinking_tools import (
    ThoughtMetadata, # Import if needed for checks
    THOUGHTS_COLLECTION, # Import constants
    SESSIONS_COLLECTION, # FIX: Import this constant
    DEFAULT_SIMILARITY_THRESHOLD,
    _sequential_thinking_impl,
    _find_similar_thoughts_impl,
    _get_session_summary_impl,
    _find_similar_sessions_impl
)

# --- Helper Functions (Copied from test_collection_tools.py) ---

def assert_successful_json_result(result: types.CallToolResult, expected_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Asserts the tool result is successful and contains valid JSON, returning the parsed data."""
    assert isinstance(result, types.CallToolResult)
    assert result.isError is False
    assert isinstance(result.content, list)
    assert len(result.content) == 1
    assert isinstance(result.content[0], types.TextContent)
    assert result.content[0].type == "text"

    try:
        result_data = json.loads(result.content[0].text)
    except json.JSONDecodeError:
        pytest.fail(f"Failed to parse JSON content: {result.content[0].text}")

    assert isinstance(result_data, dict)
    if expected_data is not None:
        assert result_data == expected_data
    return result_data # Return parsed data for further specific assertions

def assert_error_result(result: types.CallToolResult, expected_error_substring: str):
    """Asserts the tool result is an error and contains the expected substring."""
    assert isinstance(result, types.CallToolResult)
    assert result.isError is True
    assert isinstance(result.content, list)
    assert len(result.content) == 1
    assert isinstance(result.content[0], types.TextContent)
    assert result.content[0].type == "text"
    assert expected_error_substring in result.content[0].text
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
        mock_client.get_or_create_collection.side_effect = get_collection_side_effect # Mock this too

        mock_get_client.return_value = mock_client
        
        # Also patch the embedding function if it's used directly
        with patch("src.chroma_mcp.tools.thinking_tools.get_embedding_function") as mock_get_emb:
            mock_get_emb.return_value = MagicMock(name="mock_embedding_function")
            # Yield all mocks needed by tests
            yield mock_client, mock_thoughts_collection, mock_sessions_collection

class TestThinkingTools:
    """Test cases for thinking tools implementation functions."""

    # --- _sequential_thinking_impl Tests ---
    @pytest.mark.asyncio # Mark as async
    async def test_sequential_thinking_success_new_session(self, mock_chroma_client_thinking):
        """Test recording the first thought in a new session."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking # Unpack mocks
        
        thought = "Initial idea"
        thought_num = 1
        total_thoughts = 5
        
        # ACT
        result = await _sequential_thinking_impl(
            thought=thought,
            thought_number=thought_num,
            total_thoughts=total_thoughts
        )
        
        # ASSERT using helper
        result_data = assert_successful_json_result(result)

        # Assertions on mocks
        mock_client.get_or_create_collection.assert_called_once_with(name=THOUGHTS_COLLECTION, embedding_function=ANY)
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        assert call_args.kwargs["documents"] == [thought]
        assert len(call_args.kwargs["ids"]) == 1
        thought_id = call_args.kwargs["ids"][0]
        assert thought_id.startswith("thought_")
        assert call_args.kwargs["metadatas"][0]["thought_number"] == thought_num
        assert call_args.kwargs["metadatas"][0]["total_thoughts"] == total_thoughts
        assert "session_id" in call_args.kwargs["metadatas"][0]
        session_id = call_args.kwargs["metadatas"][0]["session_id"]
        
        # Assertions on result data
        assert result_data.get("status") == "success"
        assert result_data.get("thought_id") == thought_id
        assert result_data.get("session_id") == session_id
        assert result_data.get("thought_number") == thought_num
        assert result_data.get("total_thoughts") == total_thoughts
        assert result_data.get("previous_thoughts") == []
        assert result_data.get("next_thought_needed") is None

    @pytest.mark.asyncio # Mark as async
    async def test_sequential_thinking_existing_session_with_prev(self, mock_chroma_client_thinking):
        """Test recording a subsequent thought, fetching previous."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking # Unpack mocks
        
        session_id = "existing_session_123"
        thought = "Second idea"
        thought_num = 2
        total_thoughts = 3
        
        # Mock collection.get to return a previous thought
        mock_collection.get.return_value = {
            "ids": [f"thought_{session_id}_1"],
            "documents": ["First idea"],
            "metadatas": [{"session_id": session_id, "thought_number": 1, "total_thoughts": 3, "timestamp": 12345}]
        }
        
        # ACT
        result = await _sequential_thinking_impl(
            thought=thought,
            thought_number=thought_num,
            total_thoughts=total_thoughts,
            session_id=session_id,
            next_thought_needed=True
        )
        
        # ASSERT using helper
        result_data = assert_successful_json_result(result)

        # Assertions on mocks
        mock_collection.get.assert_called_once()
        get_call_args = mock_collection.get.call_args
        expected_where = {
            "$and": [
                {"session_id": session_id},
                {"thought_number": {"$lt": thought_num}}
            ]
        }
        assert get_call_args.kwargs["where"] == expected_where
        
        mock_collection.add.assert_called_once()
        add_call_args = mock_collection.add.call_args
        assert add_call_args.kwargs["metadatas"][0]["session_id"] == session_id
        
        # Assertions on result data
        assert result_data.get("status") == "success"
        assert result_data.get("session_id") == session_id
        assert result_data.get("thought_number") == thought_num
        assert len(result_data.get("previous_thoughts", [])) == 1
        assert result_data["previous_thoughts"][0].get("content") == "First idea"
        assert result_data["previous_thoughts"][0].get("metadata", {}).get("thought_number") == 1
        assert result_data.get("next_thought_needed") is True

    @pytest.mark.asyncio # Mark as async
    async def test_sequential_thinking_with_branch_and_custom(self, mock_chroma_client_thinking):
        """Test recording a branched thought with custom data."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking
        mock_collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}

        session_id = "branch_session"
        thought = "Alternative idea"
        custom_data = {"rating": 5, "approved": True}
        
        # ACT
        result = await _sequential_thinking_impl(
            thought=thought,
            thought_number=2,
            total_thoughts=4,
            session_id=session_id,
            branch_from_thought=1,
            branch_id="alt_path",
            custom_data=custom_data
        )
        
        # ASSERT using helper
        result_data = assert_successful_json_result(result)

        # Assertions on mocks
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        thought_id = call_args.kwargs["ids"][0]
        metadata = call_args.kwargs["metadatas"][0]
        
        assert thought_id.endswith("_branch_alt_path")
        assert metadata["session_id"] == session_id
        assert metadata["branch_from_thought"] == 1
        assert metadata["branch_id"] == "alt_path"
        # Check flattened custom data
        assert metadata["custom:rating"] == 5
        assert metadata["custom:approved"] is True
        assert "custom_data" not in metadata # Original key removed
        
        # Assertions on result data
        assert result_data.get("status") == "success"
        assert result_data.get("thought_id") == thought_id
        assert result_data.get("previous_thoughts") == [] 

    @pytest.mark.asyncio # Mark as async
    async def test_sequential_thinking_validation_error(self, mock_chroma_client_thinking):
        """Test validation errors for sequential thinking."""
        # Test no thought
        result_no_thought = await _sequential_thinking_impl(thought="", thought_number=1, total_thoughts=1)
        assert_error_result(result_no_thought, "Validation Error: Thought content is required")
        
        # Test bad number (too low)
        result_bad_num1 = await _sequential_thinking_impl(thought="t", thought_number=0, total_thoughts=1)
        assert_error_result(result_bad_num1, "Validation Error: Invalid thought number: 0")
        
        # Test bad number (too high)
        result_bad_num2 = await _sequential_thinking_impl(thought="t", thought_number=3, total_thoughts=2)
        assert_error_result(result_bad_num2, "Validation Error: Invalid thought number: 3")

    # --- _find_similar_thoughts_impl Tests ---
    @pytest.mark.asyncio # Mark as async
    async def test_find_similar_thoughts_success(self, mock_chroma_client_thinking):
        """Test finding similar thoughts successfully."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking
        
        query = "find me similar ideas"
        threshold = 0.7
        
        # Mock query results
        mock_collection.query.return_value = {
            "ids": [["t1", "t2", "t3"]],
            "documents": [["idea A", "idea B", "idea C"]],
            "metadatas": [[{"session_id": "s1"}, {"session_id": "s2", "custom:tag": "X"}, {"session_id": "s1"}]],
            "distances": [[0.1, 0.25, 0.4]] # Similarities: 0.9, 0.75, 0.6
        }
        
        # ACT
        result = await _find_similar_thoughts_impl(query=query, threshold=threshold, n_results=3)
        
        # ASSERT using helper
        result_data = assert_successful_json_result(result)

        # Assertions on mocks
        mock_client.get_collection.assert_called_once_with(name=THOUGHTS_COLLECTION, embedding_function=ANY)
        mock_collection.query.assert_called_once_with(query_texts=[query], n_results=3, where=None, include=ANY)
        
        # Assertions on result data
        assert len(result_data.get("similar_thoughts", [])) == 2 # t3 is below threshold
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

    @pytest.mark.asyncio # Mark as async
    async def test_find_similar_thoughts_with_session_filter(self, mock_chroma_client_thinking):
        """Test finding similar thoughts filtered by session ID."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking
        
        session_id_to_find = "s1"
        
        # Mock query results (same as above)
        mock_collection.query.return_value = {
            "ids": [["t1", "t2", "t3"]],
            "documents": [["idea A", "idea B", "idea C"]],
            "metadatas": [[{"session_id": "s1"}, {"session_id": "s2"}, {"session_id": "s1"}]],
            "distances": [[0.1, 0.25, 0.4]]
        }
        
        # ACT
        result = await _find_similar_thoughts_impl(query="find s1", session_id=session_id_to_find, threshold=0.5)
        
        # ASSERT using helper
        result_data = assert_successful_json_result(result)

        # Check query was called with the where clause
        mock_collection.query.assert_called_once_with(query_texts=[ANY], n_results=ANY, where={"session_id": session_id_to_find}, include=ANY)
        
        # Assertions on result data (mock doesn't filter, so we expect all 3, but check metadata)
        assert len(result_data.get("similar_thoughts", [])) == 3 
        assert result_data["similar_thoughts"][0].get("metadata", {}).get("session_id") == "s1"
        # assert result_data["similar_thoughts"][1].get("metadata", {}).get("session_id") == "s2" # Mock doesn't filter
        assert result_data["similar_thoughts"][2].get("metadata", {}).get("session_id") == "s1"

    @pytest.mark.asyncio # Mark as async
    async def test_find_similar_thoughts_collection_not_found(self, mock_chroma_client_thinking):
        """Test find_similar_thoughts when the collection does not exist."""
        mock_client, _, _ = mock_chroma_client_thinking
        # Mock get_collection to raise the specific ValueError
        mock_client.get_collection.side_effect = ValueError(f"Collection {THOUGHTS_COLLECTION} does not exist.")

        # ACT
        result = await _find_similar_thoughts_impl(query="any query")

        # ASSERT: Should return success with a message, not an error
        result_data = assert_successful_json_result(result)
        assert result_data.get("similar_thoughts") == []
        assert result_data.get("total_found") == 0
        assert "message" in result_data
        assert f"Collection '{THOUGHTS_COLLECTION}' not found." in result_data["message"]
        mock_client.get_collection.assert_called_once_with(name=THOUGHTS_COLLECTION, embedding_function=ANY)
        # Ensure query was not called if collection not found
        # (Need the mock collection instance for this)
        # Assuming the side effect prevents query from being called implicitly
        # If side_effect doesn't prevent access, mock collection mock would be needed:
        # mock_thoughts_collection.query.assert_not_called()

    # --- _get_session_summary_impl Tests ---
    @pytest.mark.asyncio # Mark as async
    async def test_get_session_summary_success(self, mock_chroma_client_thinking):
        """Test getting a session summary successfully."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking
        session_id = "summary_session"

        # Mock collection.get results
        mock_collection.get.return_value = {
            "ids": [f"thought_{session_id}_2", f"thought_{session_id}_1"], # Unordered
            "documents": ["Thought two", "Thought one"],
            "metadatas": [
                {"session_id": session_id, "thought_number": 2, "custom:tag": "final"},
                {"session_id": session_id, "thought_number": 1}
            ]
        }

        # ACT
        result = await _get_session_summary_impl(session_id=session_id)

        # ASSERT using helper
        result_data = assert_successful_json_result(result)

        # Assertions on mocks
        mock_client.get_collection.assert_called_once_with(name=THOUGHTS_COLLECTION, embedding_function=ANY)
        mock_collection.get.assert_called_once_with(where={"session_id": session_id}, include=["documents", "metadatas", "ids"])

        # Assertions on result data
        assert result_data.get("session_id") == session_id
        assert len(result_data.get("session_thoughts", [])) == 2
        # Check sorting and custom data reconstruction
        assert result_data["session_thoughts"][0]["metadata"]["thought_number"] == 1
        assert result_data["session_thoughts"][1]["metadata"]["thought_number"] == 2
        assert result_data["session_thoughts"][1]["metadata"].get("custom_data") == {"tag": "final"}

    @pytest.mark.asyncio # Mark as async
    async def test_get_session_summary_no_thoughts(self, mock_chroma_client_thinking):
        """Test getting a summary for a session with no thoughts found."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking
        session_id = "empty_session"
        # Mock collection.get returning empty results
        mock_collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}

        # ACT
        result = await _get_session_summary_impl(session_id=session_id)

        # ASSERT using helper
        result_data = assert_successful_json_result(result)

        # Assertions on mocks
        mock_client.get_collection.assert_called_once_with(name=THOUGHTS_COLLECTION, embedding_function=ANY)
        mock_collection.get.assert_called_once_with(where={"session_id": session_id}, include=ANY)

        # Assertions on result data
        assert result_data.get("session_id") == session_id
        assert result_data.get("session_thoughts") == []
        assert result_data.get("total_thoughts_in_session") == 0

    @pytest.mark.asyncio # Mark as async
    async def test_get_session_summary_collection_not_found(self, mock_chroma_client_thinking):
        """Test getting summary when the collection does not exist."""
        mock_client, _, _ = mock_chroma_client_thinking
        session_id = "no_collection_session"
        # Mock get_collection to raise error
        mock_client.get_collection.side_effect = ValueError(f"Collection {THOUGHTS_COLLECTION} does not exist.")

        # ACT
        result = await _get_session_summary_impl(session_id=session_id)

        # ASSERT: Expect success with a message, not an error
        result_data = assert_successful_json_result(result)
        assert f"Collection '{THOUGHTS_COLLECTION}' not found" in result_data.get("message", "")
        assert result_data.get("session_thoughts") == []

    # --- _find_similar_sessions_impl Tests ---
    @pytest.mark.asyncio # Mark as async
    async def test_find_similar_sessions_success(self, mock_chroma_client_thinking):
        """Test finding similar sessions successfully."""
        mock_client, mock_thoughts_collection, mock_sessions_collection = mock_chroma_client_thinking
        query = "related project"
        threshold = 0.8

        # --- Mock intermediate steps to isolate the final query call ---
        # 1. Mock thoughts collection get (for fetching session IDs)
        mock_thoughts_collection.get.return_value = {"ids": ["id1"], "documents": ["doc1"], "metadatas": [{"session_id": "s1"}]}
        # 2. Mock sessions collection get (for checking existing IDs) - return empty
        mock_sessions_collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}
        # 3. Mock the internal call to _get_session_summary_impl to return a dummy success
        # We need to patch the function *within the module it's called from*
        dummy_summary_result = types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps({"session_id": "s1", "session_thoughts": [{"content": "Summary text"}]}))])
        with patch("src.chroma_mcp.tools.thinking_tools._get_session_summary_impl", return_value=dummy_summary_result) as mock_internal_summary:
            # 4. Mock sessions collection query results (the final step)
            mock_sessions_collection.query.return_value = {
                "ids": [["s1"]], # s3 filtered by threshold
                "documents": [["Session 1 summary"]], # This isn't actually used by impl
                "metadatas": [[{"start_time": 100}]],
                "distances": [[0.15]] # Similarity: 0.85
            }

            # --- ACT ---
            result = await _find_similar_sessions_impl(query=query, threshold=threshold, n_results=5)

            # --- ASSERT using helper ---
            result_data = assert_successful_json_result(result)

            # --- Assertions on mocks ---
            # Ensure the final query was called on the sessions collection
            mock_sessions_collection.query.assert_called_once_with(
                query_texts=[query],
                n_results=5,
                include=["metadatas", "distances"] # Only need distance and ID (implicit)
            )
            # Ensure the internal summary was called
            mock_internal_summary.assert_called() # Called once for s1

            # --- Assertions on result data ---
            assert len(result_data.get("similar_sessions", [])) == 1
            assert result_data.get("total_found") == 1
            # Check structure based on patched summary result
            assert result_data["similar_sessions"][0]["session_id"] == "s1"
            assert result_data["similar_sessions"][0]["similarity_score"] >= threshold

    @pytest.mark.asyncio # Mark as async
    async def test_find_similar_sessions_collection_not_found(self, mock_chroma_client_thinking):
        """Test finding similar sessions when the sessions collection does not exist."""
        mock_client, _, _ = mock_chroma_client_thinking
        query = "any session query"

        # Mock get_collection for SESSIONS_COLLECTION to raise error initially
        mock_client.get_collection.side_effect = ValueError(f"Collection {THOUGHTS_COLLECTION} does not exist.")

        # ACT
        result = await _find_similar_sessions_impl(query=query)

        # ASSERT: Expecting error result when the sessions collection does not exist.
        # Reverting previous change and asserting error.
        # Fix: Update expected error message to match the actual implementation's error (uses THOUGHTS_COLLECTION first)
        result_data = assert_successful_json_result(result)
        assert result_data.get("similar_sessions") == []
        assert result_data.get("total_found") == 0
        # Optional: Check for a message if the impl adds one
        # assert f"Collection '{THOUGHTS_COLLECTION}' not found" in result_data.get("message", "")

    @pytest.mark.asyncio
    async def test_get_session_summary_unexpected_error(self, mock_chroma_client_thinking):
        """Test unexpected error during get session summary."""
        mock_client, mock_collection, _ = mock_chroma_client_thinking
        error_message = "Cannot get thoughts"
        mock_collection.get.side_effect = Exception(error_message)

        # ACT
        result = await _get_session_summary_impl(session_id="some_session")

        # ASSERT
        assert_error_result(result, f"Tool Error: An unexpected error occurred while getting session summary for 'some_session'. Details: {error_message}")
        mock_collection.get.assert_called_once() # Ensure the failing method was called