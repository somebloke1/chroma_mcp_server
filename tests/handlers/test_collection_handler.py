"""Test cases for the CollectionHandler class."""

import pytest
from unittest.mock import patch, MagicMock
import chromadb

from src.chroma_mcp import (
    CollectionHandler,
    ChromaClientConfig
)
from src.chroma_mcp.utils.errors import ValidationError, CollectionNotFoundError

@pytest.fixture
def mock_collection():
    """Create a mock collection."""
    collection = MagicMock()
    collection.name = "test_collection"
    collection.id = "test_id"
    collection.metadata = {"description": "test description"}
    collection.count.return_value = 5
    
    # Setup mock responses
    collection.get.return_value = {
        "ids": ["1", "2"],
        "documents": ["doc1", "doc2"],
        "metadatas": [{"key": "value1"}, {"key": "value2"}],
        "embeddings": [[0.1, 0.2], [0.3, 0.4]]
    }
    
    collection.query.return_value = {
        "ids": [["1", "2"]],
        "documents": [["doc1", "doc2"]],
        "metadatas": [[{"key": "value1"}, {"key": "value2"}]],
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

class TestCollectionHandler:
    """Test cases for CollectionHandler."""

    async def test_create_collection_success(self, mock_chroma_client, mock_collection, mock_config):
        """Test successful collection creation."""
        with patch("src.chroma_mcp.handlers.collection_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = CollectionHandler(config=mock_config)
            await handler.create_collection("test_collection", {"description": "test description"})

    async def test_create_collection_invalid_name(self, mock_chroma_client, mock_config):
        """Test collection creation with invalid name."""
        with patch("src.chroma_mcp.handlers.collection_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = CollectionHandler(config=mock_config)
            with pytest.raises(ValidationError):
                await handler.create_collection("", new_name="invalid name with spaces")

    async def test_list_collections_success(self, mock_chroma_client, mock_collection, mock_config):
        """Test successful collections listing."""
        with patch("src.chroma_mcp.handlers.collection_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = CollectionHandler(config=mock_config)
            await handler.list_collections()

    async def test_list_collections_with_pagination(self, mock_chroma_client, mock_collection, mock_config):
        """Test collections listing with pagination."""
        with patch("src.chroma_mcp.handlers.collection_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = CollectionHandler(config=mock_config)
            await handler.list_collections(offset=1, limit=10)

    async def test_get_collection_success(self, mock_chroma_client, mock_collection, mock_config):
        """Test successful collection retrieval."""
        with patch("src.chroma_mcp.handlers.collection_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = CollectionHandler(config=mock_config)
            await handler.get_collection("test_collection")

    async def test_get_collection_not_found(self, mock_chroma_client, mock_config):
        """Test collection retrieval when collection doesn't exist."""
        mock_chroma_client.get_collection.side_effect = chromadb.errors.InvalidCollectionException("Collection not found")
        with patch("src.chroma_mcp.handlers.collection_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = CollectionHandler(config=mock_config)
            with pytest.raises(CollectionNotFoundError):
                await handler.get_collection("nonexistent")

    async def test_modify_collection_success(self, mock_chroma_client, mock_collection, mock_config):
        """Test successful collection modification."""
        with patch("src.chroma_mcp.handlers.collection_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = CollectionHandler(config=mock_config)
            await handler.modify_collection("test_collection", new_metadata={"description": "updated description"})

    async def test_modify_collection_invalid_name(self, mock_chroma_client, mock_config):
        """Test collection modification with invalid name."""
        with patch("src.chroma_mcp.handlers.collection_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = CollectionHandler(config=mock_config)
            with pytest.raises(ValidationError):
                await handler.modify_collection("", new_name="invalid name with spaces")

    async def test_delete_collection_success(self, mock_chroma_client, mock_collection, mock_config):
        """Test successful collection deletion."""
        with patch("src.chroma_mcp.handlers.collection_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = CollectionHandler(config=mock_config)
            await handler.delete_collection("test_collection")

    async def test_delete_collection_not_found(self, mock_chroma_client, mock_config):
        """Test collection deletion when collection doesn't exist."""
        mock_chroma_client.get_collection.side_effect = chromadb.errors.InvalidCollectionException("Collection not found")
        with patch("src.chroma_mcp.handlers.collection_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = CollectionHandler(config=mock_config)
            with pytest.raises(CollectionNotFoundError):
                await handler.delete_collection("nonexistent")

    async def test_peek_collection_success(self, mock_chroma_client, mock_collection, mock_config):
        """Test successful collection peek."""
        with patch("src.chroma_mcp.handlers.collection_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = CollectionHandler(config=mock_config)
            await handler.peek_collection("test_collection", 5)

    async def test_peek_collection_empty(self, mock_chroma_client, mock_collection, mock_config):
        """Test peeking an empty collection."""
        mock_collection.get.return_value = {"ids": [], "metadatas": [], "documents": [], "embeddings": []}
        mock_collection.count.return_value = 0
        with patch("src.chroma_mcp.handlers.collection_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = CollectionHandler(config=mock_config)
            result = await handler.peek_collection("test_collection", 5)
            assert result["count"] == 0
            assert result["sample"]["ids"] == []
            assert result["sample"]["documents"] == []
            assert result["sample"]["metadatas"] == []
            assert result["sample"]["embeddings"] is None 