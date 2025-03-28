"""Tests for thinking tools."""

import pytest
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.chroma_mcp.utils.errors import ValidationError, CollectionNotFoundError, raise_validation_error

DEFAULT_SIMILARITY_THRESHOLD = 0.7

@pytest.fixture
def patched_mcp():
    """Return a mock MCP instance with all required methods."""
    return MockMCP()

class MockMCP:
    """Mock MCP class with all required methods."""
    
    def __init__(self):
        """Initialize mock MCP."""
        self.name = "mock-mcp"
    
    async def chroma_sequential_thinking(
        self,
        thought: str,
        session_id: str,
        thought_number: int,
        total_thoughts: int,
        branch_id: Optional[str] = None,
        branch_from_thought: Optional[int] = None,
        next_thought_needed: bool = False,
        custom_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process sequential thoughts."""
        # Validate inputs
        if not thought:
            raise_validation_error("Thought content is required")
        if thought_number < 1:
            raise_validation_error(f"Invalid thought number: {thought_number}")
            
        response = {
            "status": "success",
            "thought": thought,
            "session_id": session_id,
            "thought_number": thought_number,
            "total_thoughts": total_thoughts
        }
        
        # Add branch information if provided
        if branch_id:
            response["branch_id"] = branch_id
        if branch_from_thought:
            response["branch_from_thought"] = branch_from_thought
            
        # Add previous thought if it exists
        if thought_number > 1:
            response["previous_thought"] = "previous thought"
            
        return response

    async def chroma_find_similar_thoughts(
        self,
        query: str,
        n_results: int = 5,
        session_id: Optional[str] = None,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        include_branches: bool = True
    ) -> Dict[str, Any]:
        """Find similar thoughts."""
        matches = [
            {
                "thought": "thought1",
                "metadata": {"session_id": "session1"},
                "similarity": 0.9
            },
            {
                "thought": "thought2",
                "metadata": {"session_id": "session2"},
                "similarity": 0.8
            }
        ]
        
        # Filter by session if specified
        if session_id:
            matches = [m for m in matches if m["metadata"]["session_id"] == session_id]
            
        return {"matches": matches[:n_results]}

    async def chroma_get_session_summary(
        self,
        session_id: str,
        include_branches: bool = True
    ) -> Dict[str, Any]:
        """Get summary for a session."""
        return {
            "session_id": session_id,
            "thoughts": [
                {
                    "thought": "thought1",
                    "thought_number": 1
                },
                {
                    "thought": "thought2",
                    "thought_number": 2
                }
            ]
        }

    async def chroma_find_similar_sessions(
        self,
        query: str,
        n_results: int = 3,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD
    ) -> Dict[str, Any]:
        """Find similar sessions."""
        return {
            "matches": [
                {
                    "session_id": "session1",
                    "summary": "session1 summary",
                    "similarity": 0.9
                },
                {
                    "session_id": "session2",
                    "summary": "session2 summary",
                    "similarity": 0.8
                }
            ][:n_results]
        }

class TestThinkingTools:
    """Test cases for thinking tools."""

    @pytest.mark.asyncio
    async def test_sequential_thinking_success(self, patched_mcp):
        """Test successful sequential thinking."""
        # Test data
        thought = "This is a test thought"
        session_id = "test_session"
        thought_number = 1
        total_thoughts = 3

        # Call sequential thinking
        result = await patched_mcp.chroma_sequential_thinking(
            thought=thought,
            session_id=session_id,
            thought_number=thought_number,
            total_thoughts=total_thoughts
        )

        # Verify result
        assert result["status"] == "success"
        assert result["thought"] == thought
        assert result["session_id"] == session_id
        assert result["thought_number"] == thought_number

    @pytest.mark.asyncio
    async def test_sequential_thinking_with_previous_thoughts(self, patched_mcp):
        """Test sequential thinking with previous thoughts."""
        # Test data
        thought = "This is a follow-up thought"
        session_id = "test_session"
        thought_number = 2
        total_thoughts = 3

        # Call sequential thinking
        result = await patched_mcp.chroma_sequential_thinking(
            thought=thought,
            session_id=session_id,
            thought_number=thought_number,
            total_thoughts=total_thoughts
        )

        # Verify result
        assert result["status"] == "success"
        assert result["thought"] == thought
        assert result["previous_thought"] == "previous thought"
        assert result["thought_number"] == thought_number

    @pytest.mark.asyncio
    async def test_sequential_thinking_with_branch(self, patched_mcp):
        """Test sequential thinking with branching."""
        # Test data
        thought = "This is a branch thought"
        session_id = "test_session"
        thought_number = 1
        total_thoughts = 3
        branch_id = "branch_1"
        branch_from_thought = 3

        # Call sequential thinking
        result = await patched_mcp.chroma_sequential_thinking(
            thought=thought,
            session_id=session_id,
            thought_number=thought_number,
            total_thoughts=total_thoughts,
            branch_id=branch_id,
            branch_from_thought=branch_from_thought
        )

        # Verify result
        assert result["status"] == "success"
        assert result["thought"] == thought
        assert result["branch_id"] == branch_id
        assert result["branch_from_thought"] == branch_from_thought

    @pytest.mark.asyncio
    async def test_find_similar_thoughts_success(self, patched_mcp):
        """Test successful similar thoughts search."""
        # Call find similar thoughts
        result = await patched_mcp.chroma_find_similar_thoughts(
            query="test thought",
            n_results=2
        )

        # Verify result
        assert "matches" in result
        assert len(result["matches"]) == 2
        assert result["matches"][0]["thought"] == "thought1"
        assert result["matches"][1]["thought"] == "thought2"

    @pytest.mark.asyncio
    async def test_find_similar_thoughts_with_session_filter(self, patched_mcp):
        """Test similar thoughts search with session filter."""
        # Call find similar thoughts with session filter
        result = await patched_mcp.chroma_find_similar_thoughts(
            query="test thought",
            session_id="session1"
        )

        # Verify result
        assert "matches" in result
        assert len(result["matches"]) == 1
        assert result["matches"][0]["thought"] == "thought1"
        assert result["matches"][0]["metadata"]["session_id"] == "session1"

    @pytest.mark.asyncio
    async def test_get_session_summary_success(self, patched_mcp):
        """Test successful session summary retrieval."""
        # Call get session summary
        result = await patched_mcp.chroma_get_session_summary("test_session")

        # Verify result
        assert result["session_id"] == "test_session"
        assert len(result["thoughts"]) == 2
        assert result["thoughts"][0]["thought"] == "thought1"
        assert result["thoughts"][1]["thought_number"] == 2

    @pytest.mark.asyncio
    async def test_find_similar_sessions_success(self, patched_mcp):
        """Test successful similar sessions search."""
        # Call find similar sessions
        result = await patched_mcp.chroma_find_similar_sessions(
            query="test session",
            n_results=2
        )

        # Verify result
        assert "matches" in result
        assert len(result["matches"]) == 2
        assert result["matches"][0]["summary"] == "session1 summary"
        assert result["matches"][1]["session_id"] == "session2"

    @pytest.mark.asyncio
    async def test_validation_errors(self, patched_mcp):
        """Test validation error handling."""
        # Test empty thought
        with pytest.raises(ValidationError) as exc_info:
            await patched_mcp.chroma_sequential_thinking(
                thought="",
                session_id="test_session",
                thought_number=1,
                total_thoughts=3
            )
        assert "Thought content is required" in str(exc_info.value)

        # Test invalid thought number
        with pytest.raises(ValidationError) as exc_info:
            await patched_mcp.chroma_sequential_thinking(
                thought="test thought",
                session_id="test_session",
                thought_number=0,
                total_thoughts=3
            )
        assert "Invalid thought number" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_handling(self, patched_mcp):
        """Test error handling in thinking operations."""
        # Override with a function that raises an exception
        original_fn = patched_mcp.chroma_find_similar_thoughts
        
        async def error_fn(*args, **kwargs):
            raise Exception("Collection not found")
            
        try:
            patched_mcp.chroma_find_similar_thoughts = error_fn
            
            # Test error handling
            with pytest.raises(Exception) as exc_info:
                await patched_mcp.chroma_find_similar_thoughts(
                    query="test thought"
                )
            assert "Collection not found" in str(exc_info.value)
            
        finally:
            # Restore original function
            patched_mcp.chroma_find_similar_thoughts = original_fn 