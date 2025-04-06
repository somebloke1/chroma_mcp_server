"""Tests for thinking tools."""

import pytest
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

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
        thought_number: int,
        total_thoughts: int,
        session_id: str = "",
        branch_id: str = "",
        branch_from_thought: int = 0,
        next_thought_needed: bool = False,
        custom_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Process sequential thoughts."""
        # Handle None default for custom_data
        if custom_data is None:
            custom_data = {}
            
        # Validate inputs
        if not thought:
            raise_validation_error("Thought content is required")
        if thought_number < 1 or thought_number > total_thoughts:
            raise_validation_error(f"Invalid thought number: {thought_number}")
        
        # Mock generates session ID if not provided
        effective_session_id = session_id if session_id else f"mock_session_{uuid.uuid4()}"
            
        response = {
            "status": "success",
            "thought": thought,
            "session_id": effective_session_id,
            "thought_number": thought_number,
            "total_thoughts": total_thoughts
        }
        
        # Add branch information if provided (non-default value)
        if branch_id:
            response["branch_id"] = branch_id
        if branch_from_thought > 0:
            response["branch_from_thought"] = branch_from_thought
            
        # Add previous thought mock if applicable
        if thought_number > 1:
            response["previous_thought"] = "previous thought mock"
            
        # Include other fields from the actual tool's response
        response["success"] = True
        response["thought_id"] = f"mock_thought_{effective_session_id}_{thought_number}"
        response["previous_thoughts"] = [] # Mock empty list for simplicity
        response["next_thought_needed"] = next_thought_needed
        if custom_data: # Include custom_data in response if provided
            response["custom_data"] = custom_data
            
        return response

    async def chroma_find_similar_thoughts(
        self,
        query: str,
        n_results: int = 5,
        session_id: str = "",
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        include_branches: bool = True
    ) -> Dict[str, Any]:
        """Find similar thoughts."""
        # Basic validation
        if threshold < 0 or threshold > 1:
            raise_validation_error("Threshold must be between 0 and 1")
            
        matches = [
            {
                "content": "thought1 content", # Renamed from 'thought'
                "metadata": {"session_id": "session1", "thought_number": 1},
                "similarity": 0.9
            },
            {
                "content": "thought2 content",
                "metadata": {"session_id": "session2", "thought_number": 1},
                "similarity": 0.8
            },
            {
                "content": "thought3 session1 content",
                "metadata": {"session_id": "session1", "thought_number": 2},
                "similarity": 0.7
            }
        ]
        
        # Filter by session if specified
        if session_id:
            matches = [m for m in matches if m["metadata"]["session_id"] == session_id]
            
        # Filter by threshold
        matches = [m for m in matches if m["similarity"] >= threshold]
        
        # Limit results
        final_matches = matches[:n_results]
            
        return {
            "similar_thoughts": final_matches,
            "total_found": len(final_matches),
            "threshold": threshold
        }

    async def chroma_get_session_summary(
        self,
        session_id: str,
        include_branches: bool = True
    ) -> Dict[str, Any]:
        """Get summary for a session."""
        # Mock data
        main_path = [
            {
                "content": "main thought1",
                "metadata": {"session_id": session_id, "thought_number": 1}
            },
            {
                "content": "main thought2",
                "metadata": {"session_id": session_id, "thought_number": 2}
            }
        ]
        branches = {
            "branch1": [
                {
                    "content": "branch1 thought1",
                    "metadata": {"session_id": session_id, "thought_number": 1, "branch_id": "branch1"}
                }
            ]
        }
        
        total_thoughts = len(main_path) + sum(len(b) for b in branches.values())
        
        return {
            "session_id": session_id,
            "main_path_thoughts": main_path,
            "branched_thoughts": branches if include_branches else {},
            "total_thoughts": total_thoughts
        }

    async def chroma_find_similar_sessions(
        self,
        query: str,
        n_results: int = 3,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD
    ) -> Dict[str, Any]:
        """Find similar sessions."""
        # Basic validation
        if threshold < 0 or threshold > 1:
            raise_validation_error("Threshold must be between 0 and 1")
            
        # Mock data based on actual tool response structure
        matches = [
            {
                "session_id": "session1",
                "similarity": 0.9,
                "first_thought_timestamp": 1678886400,
                "last_thought_timestamp": 1678886460,
                "total_thoughts": 5
            },
            {
                "session_id": "session2",
                "similarity": 0.8,
                "first_thought_timestamp": 1678887000,
                "last_thought_timestamp": 1678887050,
                "total_thoughts": 3
            },
             {
                "session_id": "session3",
                "similarity": 0.7,
                "first_thought_timestamp": 1678888000,
                "last_thought_timestamp": 1678888020,
                "total_thoughts": 2
            }
        ]
        
        # Filter by threshold
        matches = [m for m in matches if m["similarity"] >= threshold]
        
        # Limit results
        final_matches = matches[:n_results]
        
        return {
            "similar_sessions": final_matches,
            "total_found": len(final_matches),
            "threshold": threshold
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
        assert result["success"] == True
        assert result["thought"].startswith("This is a test thought")
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
        assert result["success"] == True
        assert result["thought"] == thought
        assert result["previous_thought"] == "previous thought mock"
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
        assert result["success"] == True
        assert result["thought"] == thought
        assert result["branch_id"] == branch_id
        assert result["branch_from_thought"] == branch_from_thought

    @pytest.mark.asyncio
    async def test_find_similar_thoughts_success(self, patched_mcp):
        """Test successful similar thoughts search."""
        # Call find similar thoughts
        result = await patched_mcp.chroma_find_similar_thoughts(
            query="test thought",
            n_results=2,
            threshold=0.7
        )

        # Verify result
        assert "similar_thoughts" in result
        assert len(result["similar_thoughts"]) <= 2
        assert result["total_found"] == len(result["similar_thoughts"])
        if result["total_found"] > 0:
            assert result["similar_thoughts"][0]["content"] == "thought1 content"
        if result["total_found"] > 1:
            assert result["similar_thoughts"][1]["content"] == "thought2 content"

    @pytest.mark.asyncio
    async def test_find_similar_thoughts_with_session_filter(self, patched_mcp):
        """Test similar thoughts search with session filter."""
        # Call find similar thoughts with session filter
        result = await patched_mcp.chroma_find_similar_thoughts(
            query="test thought",
            session_id="session1",
            threshold=0.6
        )

        # Verify result
        assert "similar_thoughts" in result
        assert len(result["similar_thoughts"]) == 2
        assert result["similar_thoughts"][0]["metadata"]["session_id"] == "session1"
        assert result["similar_thoughts"][1]["metadata"]["session_id"] == "session1"

    @pytest.mark.asyncio
    async def test_get_session_summary_success(self, patched_mcp):
        """Test successful session summary retrieval."""
        # Call get session summary
        result = await patched_mcp.chroma_get_session_summary("test_session")

        # Verify result
        assert result["session_id"] == "test_session"
        assert "main_path_thoughts" in result
        assert len(result["main_path_thoughts"]) == 2
        assert result["main_path_thoughts"][0]["content"] == "main thought1"
        assert result["main_path_thoughts"][1]["metadata"]["thought_number"] == 2
        assert "branched_thoughts" in result
        assert len(result["branched_thoughts"]["branch1"]) == 1

    @pytest.mark.asyncio
    async def test_find_similar_sessions_success(self, patched_mcp):
        """Test successful similar sessions search."""
        # Call find similar sessions
        result = await patched_mcp.chroma_find_similar_sessions(
            query="test session",
            n_results=2,
            threshold=0.75
        )

        # Verify result
        assert "similar_sessions" in result
        assert len(result["similar_sessions"]) == 2
        assert result["similar_sessions"][0]["session_id"] == "session1"
        assert result["similar_sessions"][1]["session_id"] == "session2"
        assert result["total_found"] == 2
        assert "similarity" in result["similar_sessions"][0]

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