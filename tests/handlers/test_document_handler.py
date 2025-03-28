"""Test cases for the DocumentHandler class."""

import pytest
from unittest.mock import patch, MagicMock

from src.chroma_mcp import (
    DocumentHandler,
    ChromaClientConfig,
    ValidationError,
    CollectionNotFoundError,
)

from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS
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
        "documents": ["doc1", "doc2"],
        "metadatas": [{"key": "value1"}, {"key": "value2"}],
        "embeddings": [[0.1, 0.2], [0.3, 0.4]]
    }
    
    collection.query.return_value = {
        "ids": [["1", "2"]],
        "documents": [["doc1", "doc2"]],
        "metadatas": [[{"key": "value1"}, {"key": "value2"}]],
        "distances": [[0.1, 0.2]],
        "embeddings": [[[0.1, 0.2], [0.3, 0.4]]]
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
def sample_documents():
    """Create sample documents for testing."""
    return {
        "documents": ["doc1", "doc2"],
        "embeddings": [[0.1, 0.2], [0.3, 0.4]],
        "ids": ["1", "2"],
        "metadatas": [{"key": "value1"}, {"key": "value2"}]
    }

class TestDocumentHandler:
    """Test suite for DocumentHandler class."""

    async def test_add_documents_success(self, mock_chroma_client, mock_collection, sample_documents, mock_config):
        """Test successful document addition."""
        with patch("src.chroma_mcp.handlers.document_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = DocumentHandler(config=mock_config)
            result = await handler.add_documents(
                collection_name="test_collection",
                documents=sample_documents["documents"],
                metadatas=sample_documents["metadatas"],
                ids=sample_documents["ids"],
                embeddings=sample_documents["embeddings"]
            )

            assert result["success"] is True
            assert result["count"] == 2
            assert result["collection_name"] == "test_collection"
            mock_collection.add.assert_called_once()

    async def test_add_documents_validation_error(self, mock_chroma_client, mock_config):
        """Test document addition with validation error."""
        with patch("src.chroma_mcp.handlers.document_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = DocumentHandler(config=mock_config)
            
            with pytest.raises(ValidationError) as exc_info:
                await handler.add_documents(
                    collection_name="test_collection",
                    documents=["doc1"],
                    metadatas=[{"key": "value1"}, {"key": "value2"}]  # Mismatched length
                )

            assert "Number of metadatas must match number of documents" in str(exc_info.value)

    async def test_query_documents_success(self, mock_chroma_client, mock_collection, mock_config):
        """Test successful document query."""
        with patch("src.chroma_mcp.handlers.document_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = DocumentHandler(config=mock_config)
            result = await handler.query_documents(
                collection_name="test_collection",
                query_texts=["test query"],
                n_results=2
            )

            assert len(result["ids"][0]) == 2
            assert len(result["documents"][0]) == 2
            assert len(result["metadatas"][0]) == 2
            assert len(result["distances"][0]) == 2
            mock_collection.query.assert_called_once()

    async def test_query_documents_invalid_input(self, mock_chroma_client, mock_config):
        """Test document query with invalid input."""
        with patch("src.chroma_mcp.handlers.document_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = DocumentHandler(config=mock_config)
            
            with pytest.raises(ValidationError) as exc_info:
                await handler.query_documents(
                    collection_name="test_collection",
                    query_texts=None,
                    query_embeddings=None
                )

            assert "Either query_texts or query_embeddings must be provided" in str(exc_info.value)

    async def test_get_documents_success(self, mock_chroma_client, mock_collection, mock_config):
        """Test successful document retrieval."""
        with patch("src.chroma_mcp.handlers.document_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = DocumentHandler(config=mock_config)
            result = await handler.get_documents(
                collection_name="test_collection",
                ids=["1", "2"]
            )

            assert len(result["ids"]) == 2
            assert len(result["documents"]) == 2
            assert len(result["metadatas"]) == 2
            mock_collection.get.assert_called_once()

    async def test_get_documents_with_filters(self, mock_chroma_client, mock_collection, mock_config):
        """Test document retrieval with filters."""
        with patch("src.chroma_mcp.handlers.document_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = DocumentHandler(config=mock_config)
            result = await handler.get_documents(
                collection_name="test_collection",
                where={"key": "value"},
                limit=2,
                offset=0
            )

            assert len(result["ids"]) == 2
            mock_collection.get.assert_called_once()

    async def test_update_documents_success(self, mock_chroma_client, mock_collection, sample_documents, mock_config):
        """Test successful document update."""
        with patch("src.chroma_mcp.handlers.document_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = DocumentHandler(config=mock_config)
            result = await handler.update_documents(
                collection_name="test_collection",
                ids=sample_documents["ids"],
                documents=sample_documents["documents"],
                metadatas=sample_documents["metadatas"]
            )

            assert result["success"] is True
            assert result["count"] == 2
            mock_collection.update.assert_called_once()

    async def test_update_documents_validation_error(self, mock_chroma_client, mock_config):
        """Test document update with validation error."""
        with patch("src.chroma_mcp.handlers.document_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = DocumentHandler(config=mock_config)
            
            with pytest.raises(ValidationError) as exc_info:
                await handler.update_documents(
                    collection_name="test_collection",
                    ids=["1", "2"],
                    documents=["doc1"]  # Mismatched length
                )

            assert "Number of documents must match number of ids" in str(exc_info.value)

    async def test_delete_documents_success(self, mock_chroma_client, mock_collection, mock_config):
        """Test successful document deletion."""
        with patch("src.chroma_mcp.handlers.document_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = DocumentHandler(config=mock_config)
            result = await handler.delete_documents(
                collection_name="test_collection",
                ids=["1", "2"]
            )

            assert result["success"] is True
            assert len(result["deleted_documents"]["ids"]) == 2
            mock_collection.delete.assert_called_once()

    async def test_delete_documents_with_where(self, mock_chroma_client, mock_collection, mock_config):
        """Test document deletion with where clause."""
        with patch("src.chroma_mcp.handlers.document_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = DocumentHandler(config=mock_config)
            result = await handler.delete_documents(
                collection_name="test_collection",
                where={"key": "value"}
            )

            assert result["success"] is True
            mock_collection.delete.assert_called_once()

    async def test_delete_documents_validation_error(self, mock_chroma_client, mock_config):
        """Test document deletion with validation error."""
        with patch("src.chroma_mcp.handlers.document_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = DocumentHandler(config=mock_config)
            
            with pytest.raises(ValidationError) as exc_info:
                await handler.delete_documents(
                    collection_name="test_collection"
                )

            assert "At least one of ids, where, or where_document must be provided" in str(exc_info.value)

    async def test_collection_not_found(self, mock_chroma_client, mock_config):
        """Test operations when collection is not found."""
        mock_chroma_client.get_collection.side_effect = CollectionNotFoundError("Collection not found")
        with patch("src.chroma_mcp.handlers.document_handler.get_chroma_client", return_value=mock_chroma_client):
            handler = DocumentHandler(config=mock_config)
            with pytest.raises(CollectionNotFoundError):
                await handler.get_documents("test_collection", {"ids": ["1"]}) 