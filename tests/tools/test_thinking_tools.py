"""Tests for thinking tools."""

import pytest
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from unittest.mock import patch, AsyncMock, ANY

from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS, ErrorData

# Import McpError here as well
from mcp.shared.exceptions import McpError

from src.chroma_mcp.utils.errors import ValidationError, CollectionNotFoundError, raise_validation_error, handle_chroma_error
from src.chroma_mcp.tools.thinking_tools import (
    ThoughtMetadata, # Import if needed for checks
    THOUGHTS_COLLECTION, # Import constants
    DEFAULT_SIMILARITY_THRESHOLD,
    _sequential_thinking_impl,
    _find_similar_thoughts_impl,
    _get_session_summary_impl,
    _find_similar_sessions_impl
)

@pytest.fixture
def mock_chroma_client_thinking():
    """Fixture to mock the Chroma client and its methods for thinking tests."""
    with patch("src.chroma_mcp.tools.thinking_tools.get_chroma_client") as mock_get_client:
        mock_client_instance = AsyncMock()
        mock_collection_instance = AsyncMock()
        
        # Configure mock collection methods
        mock_collection_instance.add = AsyncMock()
        mock_collection_instance.get = AsyncMock(return_value={"ids": [], "documents": [], "metadatas": []}) # Default empty get
        mock_collection_instance.query = AsyncMock(return_value={"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}) # Default empty query
        
        # Configure mock client methods
        mock_client_instance.get_or_create_collection = AsyncMock(return_value=mock_collection_instance)
        mock_client_instance.get_collection = AsyncMock(return_value=mock_collection_instance)
        
        mock_get_client.return_value = mock_client_instance
        yield mock_client_instance, mock_collection_instance

class TestThinkingTools:
    """Test cases for thinking tools implementation functions."""

    # --- _sequential_thinking_impl Tests ---
    @pytest.mark.asyncio
    async def test_sequential_thinking_success_new_session(self, mock_chroma_client_thinking):
        """Test recording the first thought in a new session."""
        mock_client, mock_collection = mock_chroma_client_thinking
        thought = "Initial idea"
        thought_num = 1
        total_thoughts = 5
        
        result = await _sequential_thinking_impl(
            thought=thought,
            thought_number=thought_num,
            total_thoughts=total_thoughts
        )
        
        mock_client.get_or_create_collection.assert_awaited_once_with(name=THOUGHTS_COLLECTION, embedding_function=ANY)
        mock_collection.add.assert_awaited_once()
        call_args = mock_collection.add.call_args
        assert call_args.kwargs["documents"] == [thought]
        assert len(call_args.kwargs["ids"]) == 1
        thought_id = call_args.kwargs["ids"][0]
        assert thought_id.startswith("thought_")
        assert call_args.kwargs["metadatas"][0]["thought_number"] == thought_num
        assert call_args.kwargs["metadatas"][0]["total_thoughts"] == total_thoughts
        assert "session_id" in call_args.kwargs["metadatas"][0]
        session_id = call_args.kwargs["metadatas"][0]["session_id"]
        
        assert result["success"] is True
        assert result["thought_id"] == thought_id
        assert result["session_id"] == session_id
        assert result["thought_number"] == thought_num
        assert result["total_thoughts"] == total_thoughts
        assert result["previous_thoughts"] == []
        assert result["next_thought_needed"] is False

    @pytest.mark.asyncio
    async def test_sequential_thinking_existing_session_with_prev(self, mock_chroma_client_thinking):
        """Test recording a subsequent thought, fetching previous."""
        mock_client, mock_collection = mock_chroma_client_thinking
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
        
        result = await _sequential_thinking_impl(
            thought=thought,
            thought_number=thought_num,
            total_thoughts=total_thoughts,
            session_id=session_id,
            next_thought_needed=True
        )
        
        mock_collection.get.assert_awaited_once()
        get_call_args = mock_collection.get.call_args
        assert get_call_args.kwargs["where"] == {"session_id": session_id, "thought_number": {"$lt": 2}}
        
        mock_collection.add.assert_awaited_once()
        add_call_args = mock_collection.add.call_args
        assert add_call_args.kwargs["metadatas"][0]["session_id"] == session_id
        
        assert result["success"] is True
        assert result["session_id"] == session_id
        assert result["thought_number"] == thought_num
        assert len(result["previous_thoughts"]) == 1
        assert result["previous_thoughts"][0]["content"] == "First idea"
        assert result["previous_thoughts"][0]["metadata"]["thought_number"] == 1
        assert result["next_thought_needed"] is True

    @pytest.mark.asyncio
    async def test_sequential_thinking_with_branch_and_custom(self, mock_chroma_client_thinking):
        """Test recording a branched thought with custom data."""
        mock_client, mock_collection = mock_chroma_client_thinking
        session_id = "branch_session"
        thought = "Alternative idea"
        custom_data = {"rating": 5, "approved": True}
        
        result = await _sequential_thinking_impl(
            thought=thought,
            thought_number=2,
            total_thoughts=4,
            session_id=session_id,
            branch_from_thought=1,
            branch_id="alt_path",
            custom_data=custom_data
        )
        
        mock_collection.add.assert_awaited_once()
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
        
        assert result["success"] is True
        assert result["thought_id"] == thought_id
        # Mock get returns empty, so previous_thoughts is empty
        assert result["previous_thoughts"] == [] 

    @pytest.mark.asyncio
    async def test_sequential_thinking_validation_error(self, mock_chroma_client_thinking):
        """Test validation errors for sequential thinking."""
        with pytest.raises(McpError) as exc_info_no_thought:
            await _sequential_thinking_impl(thought="", thought_number=1, total_thoughts=1)
        assert "Thought content is required" in str(exc_info_no_thought.value)
        
        with pytest.raises(McpError) as exc_info_bad_num:
            await _sequential_thinking_impl(thought="t", thought_number=0, total_thoughts=1)
        assert "Invalid thought number" in str(exc_info_bad_num.value)
        
        with pytest.raises(McpError) as exc_info_bad_num2:
            await _sequential_thinking_impl(thought="t", thought_number=3, total_thoughts=2)
        assert "Invalid thought number" in str(exc_info_bad_num2.value)

    # --- _find_similar_thoughts_impl Tests ---
    @pytest.mark.asyncio
    async def test_find_similar_thoughts_success(self, mock_chroma_client_thinking):
        """Test finding similar thoughts successfully."""
        mock_client, mock_collection = mock_chroma_client_thinking
        query = "find me similar ideas"
        threshold = 0.7
        
        # Mock query results
        mock_collection.query.return_value = {
            "ids": [["t1", "t2", "t3"]],
            "documents": [["idea A", "idea B", "idea C"]],
            "metadatas": [[{"session_id": "s1"}, {"session_id": "s2", "custom:tag": "X"}, {"session_id": "s1"}]],
            "distances": [[0.1, 0.25, 0.4]] # Similarities: 0.9, 0.75, 0.6
        }
        
        result = await _find_similar_thoughts_impl(query=query, threshold=threshold, n_results=3)
        
        mock_client.get_collection.assert_awaited_once_with(name=THOUGHTS_COLLECTION, embedding_function=ANY)
        mock_collection.query.assert_awaited_once_with(query_texts=[query], n_results=3, where=None, include=ANY)
        
        assert len(result["similar_thoughts"]) == 2 # t3 is below threshold
        assert result["total_found"] == 2
        assert result["threshold"] == threshold
        # Check first result
        assert result["similar_thoughts"][0]["content"] == "idea A"
        assert result["similar_thoughts"][0]["similarity"] == pytest.approx(0.9)
        assert result["similar_thoughts"][0]["metadata"]["session_id"] == "s1"
        # Check second result with reconstructed custom metadata
        assert result["similar_thoughts"][1]["content"] == "idea B"
        assert result["similar_thoughts"][1]["similarity"] == pytest.approx(0.75)
        assert result["similar_thoughts"][1]["metadata"]["session_id"] == "s2"
        assert result["similar_thoughts"][1]["metadata"]["custom_data"] == {"tag": "X"}

    @pytest.mark.asyncio
    async def test_find_similar_thoughts_with_session_filter(self, mock_chroma_client_thinking):
        """Test finding similar thoughts filtered by session ID."""
        mock_client, mock_collection = mock_chroma_client_thinking
        session_id_to_find = "s1"
        
        # Mock query results (same as above)
        mock_collection.query.return_value = {
            "ids": [["t1", "t2", "t3"]],
            "documents": [["idea A", "idea B", "idea C"]],
            "metadatas": [[{"session_id": "s1"}, {"session_id": "s2"}, {"session_id": "s1"}]],
            "distances": [[0.1, 0.25, 0.4]]
        }
        
        result = await _find_similar_thoughts_impl(query="find s1", session_id=session_id_to_find, threshold=0.5)
        
        # Check query was called with the where clause
        mock_collection.query.assert_awaited_once_with(query_texts=[ANY], n_results=ANY, where={"session_id": session_id_to_find}, include=ANY)
        
        # All results are from s1 and above threshold 0.5, but mock query doesn't actually filter internally
        # The test relies on the where clause being passed correctly.
        # The result processing will show all 3 as the mock query doesn't apply the where filter.
        # If we wanted to test the filtering more strictly, the mock would need more complex logic.
        assert len(result["similar_thoughts"]) == 3 # Mock returns all 3, filtering happens in Chroma
        assert result["similar_thoughts"][0]["metadata"]["session_id"] == "s1"
        assert result["similar_thoughts"][2]["metadata"]["session_id"] == "s1"

    @pytest.mark.asyncio
    async def test_find_similar_thoughts_collection_not_found(self, mock_chroma_client_thinking):
        """Test handling when thoughts collection doesn't exist."""
        mock_client, _ = mock_chroma_client_thinking
        mock_client.get_collection.side_effect = Exception("Collection 'thoughts' does not exist.")
        
        result = await _find_similar_thoughts_impl(query="test")
        
        assert result["similar_thoughts"] == []
        assert result["total_found"] == 0
        assert "Collection 'thoughts' not found" in result["message"]

    # --- _get_session_summary_impl Tests ---
    @pytest.mark.asyncio
    async def test_get_session_summary_success(self, mock_chroma_client_thinking):
        """Test getting a session summary successfully."""
        mock_client, mock_collection = mock_chroma_client_thinking
        session_id = "summary_session"
        
        # Mock collection.get to return thoughts for the session
        mock_collection.get.return_value = {
            "ids": [f"t_{session_id}_2", f"t_{session_id}_1"] ,
            "documents": ["Thought two", "Thought one"] ,
            "metadatas": [
                {"session_id": session_id, "thought_number": 2, "timestamp": 67890, "custom:mood": "happy"},
                {"session_id": session_id, "thought_number": 1, "timestamp": 12345}
            ]
        }
        
        result = await _get_session_summary_impl(session_id=session_id)
        
        mock_client.get_collection.assert_awaited_once_with(name=THOUGHTS_COLLECTION, embedding_function=ANY)
        mock_collection.get.assert_awaited_once_with(where={"session_id": session_id}, include=ANY)
        
        assert result["session_id"] == session_id
        assert result["total_thoughts_in_session"] == 2
        assert len(result["session_thoughts"]) == 2
        # Check sorting and content
        assert result["session_thoughts"][0]["content"] == "Thought one"
        assert result["session_thoughts"][0]["metadata"]["thought_number"] == 1
        assert result["session_thoughts"][1]["content"] == "Thought two"
        assert result["session_thoughts"][1]["metadata"]["thought_number"] == 2
        assert result["session_thoughts"][1]["metadata"]["custom_data"] == {"mood": "happy"}

    @pytest.mark.asyncio
    async def test_get_session_summary_collection_not_found(self, mock_chroma_client_thinking):
        """Test getting summary when collection doesn't exist."""
        mock_client, _ = mock_chroma_client_thinking
        mock_client.get_collection.side_effect = Exception("Collection 'thoughts' does not exist.")
        
        result = await _get_session_summary_impl(session_id="any_session")
        
        assert result["session_thoughts"] == []
        assert result["total_thoughts_in_session"] == 0
        assert "Collection 'thoughts' not found" in result["message"]

    # --- _find_similar_sessions_impl Tests ---
    @pytest.mark.asyncio
    async def test_find_similar_sessions_success(self, mock_chroma_client_thinking):
        """Test finding similar sessions successfully."""
        mock_client, mock_collection = mock_chroma_client_thinking
        query = "find related sessions"
        threshold = 0.8
        
        # Mock query results from thoughts collection
        mock_collection.query.return_value = {
            "ids": [["t_s1_1", "t_s2_1", "t_s1_2", "t_s3_1"]],
            "metadatas": [[{"session_id": "s1"}, {"session_id": "s2"}, {"session_id": "s1"}, {"session_id": "s3"}]],
            "distances": [[0.05, 0.15, 0.1, 0.3]] # Similarities: 0.95, 0.85, 0.90, 0.70
        }
        
        # Mock the _get_session_summary_impl dependency
        with patch("src.chroma_mcp.tools.thinking_tools._get_session_summary_impl") as mock_get_summary:
            # Define different return values for each expected session ID
            def summary_side_effect(session_id, **kwargs):
                if session_id == "s1":
                    return {"session_id": "s1", "session_thoughts": ["s1 thought"], "total_thoughts_in_session": 1}
                elif session_id == "s2":
                    return {"session_id": "s2", "session_thoughts": ["s2 thought"], "total_thoughts_in_session": 1}
                else:
                    return {"session_id": session_id, "session_thoughts": [], "total_thoughts_in_session": 0}
            mock_get_summary.side_effect = summary_side_effect
            
            result = await _find_similar_sessions_impl(query=query, threshold=threshold, n_results=2)
        
        mock_client.get_collection.assert_awaited_once_with(name=THOUGHTS_COLLECTION, embedding_function=ANY)
        mock_collection.query.assert_awaited_once()
        # Check get_session_summary was called for the top sessions based on similarity
        # s1 max similarity: 0.95 (from 0.05 distance), s2 max similarity: 0.85
        # s3 similarity 0.7 is below threshold 0.8
        assert mock_get_summary.await_count == 2
        mock_get_summary.assert_any_await("s1")
        mock_get_summary.assert_any_await("s2")
        
        assert len(result["similar_sessions"]) == 2
        assert result["total_found"] == 2
        assert result["similar_sessions"][0]["session_id"] == "s1"
        assert result["similar_sessions"][0]["similarity_score"] == pytest.approx(0.95)
        assert result["similar_sessions"][1]["session_id"] == "s2"
        assert result["similar_sessions"][1]["similarity_score"] == pytest.approx(0.85)

    @pytest.mark.asyncio
    async def test_find_similar_sessions_collection_not_found(self, mock_chroma_client_thinking):
        """Test finding similar sessions when collection missing."""
        mock_client, _ = mock_chroma_client_thinking
        mock_client.get_collection.side_effect = Exception("Collection 'thoughts' does not exist.")
        
        result = await _find_similar_sessions_impl(query="test")
        
        assert result["similar_sessions"] == []
        assert result["total_found"] == 0
        assert "Collection 'thoughts' not found" in result["message"] 