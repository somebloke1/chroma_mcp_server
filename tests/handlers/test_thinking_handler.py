"""Test cases for the ThinkingHandler class."""

import pytest
from unittest.mock import patch, MagicMock
import uuid
import time
import chromadb

from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS
from src.chroma_mcp import (
    ThinkingHandler,
    ThoughtMetadata,
    ChromaClientConfig,
    ValidationError,
    CollectionNotFoundError,
)
from src.chroma_mcp.utils.client import get_chroma_client

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_collection():
    """Create a mock collection."""
    collection = MagicMock()
    collection.name = "test_collection"
    collection.id = "test_id"
    collection.metadata = {"description": "test description"}
    
    # Setup mock responses
    collection.get.return_value = {
        "ids": ["1", "2"],
        "documents": ["thought1", "thought2"],
        "metadatas": [
            {
                "thought_number": 1,
                "total_thoughts": 3,
                "session_id": "test_session",
                "timestamp": int(time.time()),
                "branch_id": None,
                "next_thought_needed": False,
                "custom_data": None
            },
            {
                "thought_number": 2,
                "total_thoughts": 3,
                "session_id": "test_session",
                "timestamp": int(time.time()),
                "branch_id": None,
                "next_thought_needed": False,
                "custom_data": None
            }
        ],
        "embeddings": [[0.1, 0.2], [0.3, 0.4]]
    }
    
    collection.query.return_value = {
        "ids": [["1", "2"]],
        "documents": [["thought1", "thought2"]],
        "metadatas": [[
            {
                "thought_number": 1,
                "total_thoughts": 3,
                "session_id": "test_session",
                "timestamp": int(time.time()),
                "branch_id": None,
                "next_thought_needed": False,
                "custom_data": None
            },
            {
                "thought_number": 2,
                "total_thoughts": 3,
                "session_id": "test_session",
                "timestamp": int(time.time()),
                "branch_id": None,
                "next_thought_needed": False,
                "custom_data": None
            }
        ]],
        "distances": [[0.1, 0.2]]
    }
    
    return collection

@pytest.fixture
def mock_config():
    """Create a mock ChromaDB client config."""
    return ChromaClientConfig(client_type="ephemeral")

@pytest.fixture
def mock_chroma_client(mock_collection):
    """Create a mock ChromaDB client."""
    client = MagicMock()
    client.get_collection.return_value = mock_collection
    client.create_collection.return_value = mock_collection
    return client

@pytest.fixture
def sample_thought():
    """Create a sample thought for testing."""
    return {
        "thought": "Test thought",
        "session_id": "test_session",
        "branch_id": None,
        "next_thought_needed": True,
        "thought_number": 1,
        "total_thoughts": 3,
        "metadata": {
            "thought_number": 1,
            "total_thoughts": 3
        }
    }

@pytest.fixture
def sample_session():
    """Create a sample session for testing."""
    return {
        "session_id": "test_session",
        "thoughts": [
            {
                "thought": "Initial thought",
                "metadata": {
                    "thought_number": 1,
                    "total_thoughts": 3
                }
            }
        ],
        "metadata": {
            "start_time": 1234567890,
            "status": "in_progress",
            "total_thoughts": 3
        }
    }

@pytest.fixture
def sample_thoughts():
    """Create sample thoughts for testing."""
    return {
        "thoughts": ["thought1", "thought2"],
        "embeddings": [[0.1, 0.2], [0.3, 0.4]],
        "ids": ["1", "2"],
        "metadatas": [{"key": "value1"}, {"key": "value2"}]
    }

class TestThinkingHandler:
    """Test cases for ThinkingHandler."""

    async def test_init_creates_collections(self, mock_chroma_client):
        """Test that initialization creates required collections."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            mock_chroma_client.get_collection.side_effect = ValueError("Collection not found")
            handler = ThinkingHandler()

            assert mock_chroma_client.create_collection.call_count == 2

    async def test_record_thought_success(self, mock_chroma_client, mock_collection, sample_thought):
        """Test successful thought recording."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = ThinkingHandler()
            result = await handler.record_thought(
                thought=sample_thought["thought"],
                thought_number=sample_thought["thought_number"],
                total_thoughts=sample_thought["total_thoughts"],
                session_id=sample_thought["session_id"]
            )

            assert result["success"] is True
            assert result["thought_number"] == 1
            assert result["total_thoughts"] == 3
            mock_collection.add.assert_called()

    async def test_record_thought_with_branch(self, mock_chroma_client, mock_collection, sample_thought):
        """Test recording a thought with branching."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = ThinkingHandler()
            result = await handler.record_thought(
                thought=sample_thought["thought"],
                thought_number=2,
                total_thoughts=3,
                session_id=sample_thought["session_id"],
                branch_from_thought=1,
                branch_id="alternative_1"
            )

            assert result["success"] is True
            assert result["thought_id"] == f"{sample_thought['session_id']}_2_alternative_1"
            assert result["branch_id"] == "alternative_1"
            mock_collection.add.assert_called()

    async def test_record_thought_validation_error(self, mock_chroma_client):
        """Test thought recording with validation error."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = ThinkingHandler()
            
            with pytest.raises(McpError) as exc_info:
                await handler.record_thought(
                    thought="Test thought",
                    thought_number=0,  # Invalid: thought_number must be positive
                    total_thoughts=3,
                    session_id="test_session"
                )

            assert str(exc_info.value) == "Invalid parameters: Invalid thought number"

    async def test_find_similar_thoughts_success(self, mock_chroma_client, mock_collection):
        """Test successful similar thoughts search."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = ThinkingHandler()
            result = await handler.find_similar_thoughts(
                query="test query",
                n_results=2,
                threshold=0.7
            )

            assert len(result["results"]) > 0
            assert "similarity" in result["results"][0]
            mock_collection.query.assert_called_once()

    async def test_find_similar_thoughts_with_session(self, mock_chroma_client, mock_collection):
        """Test finding similar thoughts within a session."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = ThinkingHandler()
            result = await handler.find_similar_thoughts(
                query="test query",
                session_id="test_session"
            )

            assert len(result["results"]) > 0
            mock_collection.query.assert_called_once()

    async def test_get_session_summary_success(self, mock_chroma_client, mock_collection, sample_session):
        """Test successful session summary retrieval."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = ThinkingHandler()
            result = await handler.get_session_summary(
                session_id=sample_session["session_id"]
            )

            assert result["session_id"] == sample_session["session_id"]
            assert "main_path" in result
            assert "branches" in result
            assert len(result["main_path"]) == 2
            assert result["main_path"][0]["metadata"]["thought_number"] == 1
            assert result["main_path"][1]["metadata"]["thought_number"] == 2
            mock_collection.get.assert_called()

    async def test_get_session_summary_not_found(self, mock_chroma_client, mock_collection):
        """Test session summary retrieval when session doesn't exist."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = ThinkingHandler()
            mock_collection.get.return_value = {"ids": [], "metadatas": []}
            
            with pytest.raises(McpError) as exc_info:
                await handler.get_session_summary("nonexistent")
            
            assert "Invalid parameters: Session not found" in str(exc_info.value)

    async def test_find_similar_sessions_success(self, mock_chroma_client, mock_collection):
        """Test successful similar sessions search."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = ThinkingHandler()
            result = await handler.find_similar_sessions(
                query="test query",
                n_results=2,
                threshold=0.7
            )

            assert len(result["results"]) > 0
            assert "similarity" in result["results"][0]
            assert "thoughts" in result["results"][0]
            mock_collection.query.assert_called()

    async def test_find_similar_sessions_no_results(self, mock_chroma_client, mock_collection):
        """Test similar sessions search with no results above threshold."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = ThinkingHandler()
            mock_collection.query.return_value = {
                "ids": [[]],
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[0.9, 0.95]]  # All similarities below threshold
            }

            result = await handler.find_similar_sessions(
                query="test query",
                threshold=0.8
            )

            assert len(result["results"]) == 0
            mock_collection.query.assert_called_once()

    async def test_thought_metadata_creation(self):
        """Test ThoughtMetadata creation and validation."""
        metadata = ThoughtMetadata(
            session_id="test_session",
            thought_number=1,
            total_thoughts=3,
            timestamp=int(time.time()),
            branch_from_thought=None,
            branch_id=None,
            next_thought_needed=True,
            custom_data={"key": "value"}
        )

        assert metadata.session_id == "test_session"
        assert metadata.thought_number == 1
        assert metadata.total_thoughts == 3
        assert metadata.next_thought_needed is True
        assert metadata.custom_data == {"key": "value"}

    async def test_collection_creation_error(self, mock_chroma_client):
        """Test handling of collection creation errors."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            mock_chroma_client.get_collection.side_effect = ValueError("Collection not found")
            mock_chroma_client.create_collection.side_effect = Exception("Creation failed")

            with pytest.raises(McpError) as exc_info:
                handler = ThinkingHandler()

            assert str(exc_info.value).startswith("Failed to ensure collections")

    async def test_add_thoughts_success(self, mock_chroma_client, mock_collection, sample_thoughts, mock_config):
        """Test successful thought addition."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = ThinkingHandler(config=mock_config)
            await handler.add_thoughts("test_collection", sample_thoughts)

    async def test_add_thoughts_validation_error(self, mock_chroma_client, mock_config):
        """Test thought addition with validation error."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = ThinkingHandler(config=mock_config)
            with pytest.raises(ValidationError):
                await handler.add_thoughts("test_collection", {})

    async def test_query_thoughts_success(self, mock_chroma_client, mock_collection, mock_config):
        """Test successful thought query."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = ThinkingHandler(config=mock_config)
            await handler.query_thoughts("test_collection", {"query_texts": ["test query"]})

    async def test_query_thoughts_invalid_input(self, mock_chroma_client, mock_config):
        """Test thought query with invalid input."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = ThinkingHandler(config=mock_config)
            with pytest.raises(ValidationError):
                await handler.query_thoughts("test_collection", {})

    async def test_get_thoughts_success(self, mock_chroma_client, mock_collection, mock_config):
        """Test successful thought retrieval."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = ThinkingHandler(config=mock_config)
            await handler.get_thoughts("test_collection", {"ids": ["1", "2"]})

    async def test_get_thoughts_with_filters(self, mock_chroma_client, mock_collection, mock_config):
        """Test thought retrieval with filters."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = ThinkingHandler(config=mock_config)
            await handler.get_thoughts("test_collection", {"where": {"key": "value"}})

    async def test_update_thoughts_success(self, mock_chroma_client, mock_collection, sample_thoughts, mock_config):
        """Test successful thought update."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = ThinkingHandler(config=mock_config)
            await handler.update_thoughts("test_collection", sample_thoughts)

    async def test_update_thoughts_validation_error(self, mock_chroma_client, mock_config):
        """Test thought update with validation error."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = ThinkingHandler(config=mock_config)
            with pytest.raises(ValidationError):
                await handler.update_thoughts("test_collection", {})

    async def test_delete_thoughts_success(self, mock_chroma_client, mock_collection, mock_config):
        """Test successful thought deletion."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = ThinkingHandler(config=mock_config)
            await handler.delete_thoughts("test_collection", {"ids": ["1", "2"]})

    async def test_delete_thoughts_with_where(self, mock_chroma_client, mock_collection, mock_config):
        """Test thought deletion with where clause."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = ThinkingHandler(config=mock_config)
            await handler.delete_thoughts("test_collection", {"where": {"key": "value"}})

    async def test_delete_thoughts_validation_error(self, mock_chroma_client, mock_config):
        """Test thought deletion with validation error."""
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = ThinkingHandler(config=mock_config)
            with pytest.raises(ValidationError):
                await handler.delete_thoughts("test_collection", {})

    async def test_collection_not_found(self, mock_chroma_client, mock_config):
        """Test operations when collection is not found."""
        mock_chroma_client.get_collection.side_effect = ValueError("Collection not found")
        mock_chroma_client.create_collection.side_effect = Exception("Creation failed")
        
        with patch("src.chroma_mcp.handlers.thinking_handler.get_chroma_client", return_value=mock_chroma_client):
            with pytest.raises(McpError) as exc_info:
                handler = ThinkingHandler(config=mock_config)
                await handler.get_thoughts("test_collection", {"ids": ["1"]})
            
            assert "Failed to ensure collections" in str(exc_info.value)
            assert mock_chroma_client.create_collection.call_count == 1 