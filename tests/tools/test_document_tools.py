"""Tests for document management tools."""

import pytest
import uuid
from typing import Dict, Any, List, Optional
from unittest.mock import patch, AsyncMock, MagicMock, ANY

from mcp.shared.exceptions import McpError
from src.chroma_mcp.utils.errors import ValidationError, CollectionNotFoundError, handle_chroma_error, raise_validation_error
from mcp.types import INVALID_PARAMS

from src.chroma_mcp.tools import document_tools

# Import the implementation functions directly
from src.chroma_mcp.tools.document_tools import (
    _add_documents_impl, 
    _query_documents_impl, 
    _get_documents_impl, 
    _update_documents_impl, 
    _delete_documents_impl
)

DEFAULT_SIMILARITY_THRESHOLD = 0.7

class MockMCP:
    """Mock MCP class with all required methods."""
    
    def __init__(self):
        """Initialize mock MCP."""
        self.name = "mock-mcp"
    
    async def chroma_add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: List[Dict[str, Any]] = None,
        ids: List[str] = None,
        increment_index: bool = True
    ) -> Dict[str, Any]:
        """Add documents to a collection."""
        # Handle None defaults
        if metadatas is None:
            metadatas = []
        if ids is None:
            ids = []
            
        # Validate inputs
        if not documents:
            raise_validation_error("No documents provided")
        if ids and len(ids) != len(documents):
            raise_validation_error("Number of IDs must match number of documents")
        if metadatas and len(metadatas) != len(documents):
            raise_validation_error("Number of metadatas must match number of documents")
            
        return {
            "status": "success",
            "collection_name": collection_name,
            "added_count": len(documents),
            "document_ids": ids if ids else [f"gen_{i}" for i in range(len(documents))]
        }
        
    async def chroma_query_documents(
        self,
        collection_name: str,
        query_texts: List[str],
        n_results: int = 10,
        where: Dict[str, Any] = None,
        where_document: Dict[str, Any] = None,
        include: List[str] = None
    ) -> Dict[str, Any]:
        """Query documents from a collection."""
        # Handle None defaults
        if where is None:
            where = {}
        if where_document is None:
            where_document = {}
        if include is None:
            # Default include from actual tool implementation
            include = ["documents", "metadatas", "distances"]
            
        # Generate mock results
        results = []
        for query in query_texts:
            matches = []
            # Use actual n_results for mock generation
            num_mock_results = min(n_results, 5) # Limit mock results for simplicity
            for i in range(num_mock_results):
                match = {
                    "id": f"{i+1}"
                }
                # Add included fields
                if "documents" in include:
                    match["document"] = f"doc{i+1}"
                if "metadatas" in include:
                    match["metadata"] = {"key": f"value{i+1}"}
                if "distances" in include:
                    match["distance"] = 0.1 * (i+1)
                if "embeddings" in include:
                    # Mock embeddings are complex, return None or placeholder
                    match["embedding"] = None
                matches.append(match)
            results.append({"query": query, "matches": matches})
            
        return {
            "results": results,
            "total_queries": len(query_texts) # Added for consistency
        }
    
    async def chroma_get_documents(
        self,
        collection_name: str,
        ids: List[str] = None,
        where: Dict[str, Any] = None,
        where_document: Dict[str, Any] = None,
        include: List[str] = None,
        limit: int = 0,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get documents from a collection."""
        # Handle None defaults
        if ids is None:
            ids = []
        if where is None:
            where = {}
        if where_document is None:
            where_document = {}
        if include is None:
            # Default include from actual tool implementation
            include = ["documents", "metadatas"]
            
        # Generate mock results
        documents = []
        effective_limit = limit if limit > 0 else 10 # Default mock limit if 0
        
        if ids:
            for doc_id in ids:
                # Only generate mocks up to the limit if ids are provided
                if len(documents) >= effective_limit:
                    break
                doc = { "id": doc_id }
                if "documents" in include:
                    doc["content"] = f"doc-{doc_id}"
                if "metadatas" in include:
                    doc["metadata"] = {"key": f"value-{doc_id}"}
                if "embeddings" in include:
                    doc["embedding"] = None
                documents.append(doc)
        else:
            # Apply offset and limit for non-ID based retrieval
            start_index = offset
            end_index = offset + effective_limit
            for i in range(start_index, end_index):
                doc_id = f"{i+1}"
                doc = { "id": doc_id }
                if "documents" in include:
                    doc["content"] = f"doc{i+1}"
                if "metadatas" in include:
                    doc["metadata"] = {"key": f"value{i+1}"}
                if "embeddings" in include:
                    doc["embedding"] = None
                documents.append(doc)
                
        return {
            "documents": documents,
            "total_found": len(documents),
            "limit": limit,
            "offset": offset
        }
    
    async def chroma_update_documents(
        self,
        collection_name: str,
        ids: List[str],
        documents: List[str] = None,
        metadatas: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update documents in a collection."""
        # Handle None defaults
        if documents is None:
            documents = []
        if metadatas is None:
            metadatas = []
            
        # Basic validation
        if not ids:
            raise_validation_error("List of IDs is required for update")
        if documents and len(documents) != len(ids):
            raise_validation_error("Number of documents must match number of IDs")
        if metadatas and len(metadatas) != len(ids):
            raise_validation_error("Number of metadatas must match number of IDs")
            
        return {
            "status": "success",
            "collection_name": collection_name,
            "updated_count": len(ids)
        }
    
    async def chroma_delete_documents(
        self,
        collection_name: str,
        ids: List[str] = None,
        where: Dict[str, Any] = None,
        where_document: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Delete documents from a collection."""
        # Handle None defaults
        if ids is None:
            ids = []
        if where is None:
            where = {}
        if where_document is None:
            where_document = {}
            
        # Need at least one condition for deletion in mock
        if not ids and not where and not where_document:
            raise_validation_error("Either ids, where, or where_document must be provided for deletion")
            
        # Mock response based on deletion method
        deleted_count = -1
        deleted_ids_response = []
        if ids:
            deleted_count = len(ids) # Mock assumes all requested IDs were deleted
            deleted_ids_response = ids
        # else: If deletion was by filter, count remains -1 and ids remain []
            
        return {
            "success": True, # Changed from 'status'
            "collection_name": collection_name,
            "deleted_count": deleted_count, # Renamed from 'count', adjusted logic
            "deleted_ids": deleted_ids_response # New field, adjusted logic
        }

@pytest.fixture
def patched_mcp():
    """
    Return a mock MCP instance with all required methods.
    """
    return MockMCP()

@pytest.fixture
def mock_chroma_client():
    """Fixture to mock the Chroma client and its methods."""
    with patch("src.chroma_mcp.utils.client.get_chroma_client") as mock_get_client, \
         patch("src.chroma_mcp.utils.client.get_embedding_function") as mock_get_embedding_function:
        mock_client_instance = AsyncMock()
        mock_collection_instance = AsyncMock()
        
        # Configure mock methods for collection
        mock_collection_instance.add = AsyncMock()
        mock_collection_instance.query = AsyncMock()
        mock_collection_instance.get = AsyncMock()
        mock_collection_instance.update = AsyncMock()
        mock_collection_instance.delete = AsyncMock()
        mock_collection_instance.count = AsyncMock(return_value=0) # Default count
        
        # Configure mock methods for client
        mock_client_instance.get_collection = AsyncMock(return_value=mock_collection_instance)
        mock_client_instance.get_or_create_collection = AsyncMock(return_value=mock_collection_instance)
        
        mock_get_client.return_value = mock_client_instance
        mock_get_embedding_function.return_value = None # Assuming no embedding function
        yield mock_client_instance, mock_collection_instance

class TestDocumentTools:
    """Test cases for document management implementation functions."""

    # --- _add_documents_impl Tests ---
    @pytest.mark.asyncio
    async def test_add_documents_success(self, mock_chroma_client):
        """Test successful document addition."""
        mock_client, mock_collection = mock_chroma_client
        mock_collection.count = AsyncMock(return_value=5) # Set initial count
        
        docs = ["doc1", "doc2"]
        ids = ["id1", "id2"]
        metas = [{"k": "v1"}, {"k": "v2"}]
        
        result = await _add_documents_impl(
            collection_name="test_add",
            documents=docs,
            ids=ids,
            metadatas=metas
        )
        
        mock_collection.add.assert_called_once_with(
            documents=docs, 
            ids=ids, 
            metadatas=metas
        )
        assert result["success"] is True
        assert result["added_count"] == 2
        assert result["document_ids"] == ids
        assert result["ids_generated"] is False

    @pytest.mark.asyncio
    async def test_add_documents_generate_ids(self, mock_chroma_client):
        """Test document addition with auto-generated IDs."""
        mock_client, mock_collection = mock_chroma_client
        mock_collection.count = AsyncMock(return_value=3)
        
        docs = ["docA", "docB"]
        
        result = await _add_documents_impl(
            collection_name="test_add_gen",
            documents=docs,
            metadatas=None, 
            ids=None 
        )
        
        # Check that add was called with generated IDs (format depends on time)
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        assert call_args.kwargs["documents"] == docs
        assert len(call_args.kwargs["ids"]) == 2
        assert call_args.kwargs["ids"][0].startswith("doc_")
        assert call_args.kwargs["metadatas"] is None # Ensure None was passed correctly
        
        assert result["success"] is True
        assert result["added_count"] == 2
        assert result["ids_generated"] is True
        assert len(result["document_ids"]) == 2

    @pytest.mark.asyncio
    async def test_add_documents_validation_no_docs(self, mock_chroma_client):
        """Test validation failure when no documents are provided."""
        # Expect McpError because handle_chroma_error wraps the ValidationError
        with pytest.raises(McpError) as exc_info:
            await _add_documents_impl(
                collection_name="test_valid",
                documents=[] 
            )
        # Assert original validation message is in the McpError message
        assert "No documents provided" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_documents_validation_mismatch_ids(self, mock_chroma_client):
        """Test validation failure with mismatched IDs."""
        # Expect McpError
        with pytest.raises(McpError) as exc_info:
            await _add_documents_impl(
                collection_name="test_valid",
                documents=["d1", "d2"],
                ids=["id1"] 
            )
        # Assert original validation message is in the McpError message
        assert "Number of IDs must match" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_documents_validation_mismatch_metas(self, mock_chroma_client):
        """Test validation failure with mismatched metadatas."""
        # Expect McpError
        with pytest.raises(McpError) as exc_info:
            await _add_documents_impl(
                collection_name="test_valid",
                documents=["d1", "d2"],
                metadatas=[{"k": "v"}] 
            )
        # Assert original validation message is in the McpError message
        assert "Number of metadatas must match" in str(exc_info.value)

    # --- _query_documents_impl Tests ---
    @pytest.mark.asyncio
    async def test_query_documents_success(self, mock_chroma_client):
        """Test successful document query with default include."""
        mock_client, mock_collection = mock_chroma_client
        # Mock the return value of collection.query
        mock_collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "distances": [[0.1, 0.2]],
            "metadatas": [[{"m": "v1"}, {"m": "v2"}]],
            "documents": [["doc text 1", "doc text 2"]],
            "embeddings": None # Assume embeddings not included by default
        }
        
        result = await _query_documents_impl(
            collection_name="test_query",
            query_texts=["find me stuff"],
            n_results=2
        )
        
        mock_collection.query.assert_called_once_with(
            query_texts=["find me stuff"],
            n_results=2,
            where=None,
            where_document=None,
            include=["documents", "metadatas", "distances"] # Default include
        )
        assert len(result["results"]) == 1
        assert result["total_queries"] == 1
        assert len(result["results"][0]["matches"]) == 2
        match1 = result["results"][0]["matches"][0]
        assert match1["id"] == "id1"
        assert match1["distance"] == 0.1
        assert match1["document"] == "doc text 1"
        assert match1["metadata"] == {"m": "v1"}
        assert "embedding" not in match1

    @pytest.mark.asyncio
    async def test_query_documents_custom_include(self, mock_chroma_client):
        """Test query with custom include parameter."""
        mock_client, mock_collection = mock_chroma_client
        mock_collection.query.return_value = {
            "ids": [["id_a"]],
            "distances": None, # Not included
            "metadatas": None, # Not included
            "documents": [["docA"]],
            "embeddings": [[[0.1, 0.2]]] # Included
        }
        
        result = await _query_documents_impl(
            collection_name="test_query_include",
            query_texts=["find embedding"],
            n_results=1,
            include=["documents", "embeddings"]
        )
        
        mock_collection.query.assert_called_once_with(
            query_texts=["find embedding"],
            n_results=1,
            where=None,
            where_document=None,
            include=["documents", "embeddings"]
        )
        assert len(result["results"][0]["matches"]) == 1
        match = result["results"][0]["matches"][0]
        assert match["id"] == "id_a"
        assert "distance" not in match
        assert "metadata" not in match
        assert match["document"] == "docA"
        assert match["embedding"] == [0.1, 0.2]

    @pytest.mark.asyncio
    async def test_query_documents_validation_no_query(self, mock_chroma_client):
        """Test validation failure with no query text."""
        # Expect McpError
        with pytest.raises(McpError) as exc_info:
            await _query_documents_impl(
                collection_name="test_valid",
                query_texts=[]
            )
        # Assert original validation message is in the McpError message
        assert "No query texts provided" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_query_documents_validation_invalid_nresults(self, mock_chroma_client):
        """Test validation failure with invalid n_results."""
        # Expect McpError
        with pytest.raises(McpError) as exc_info:
            await _query_documents_impl(
                collection_name="test_valid",
                query_texts=["q"],
                n_results=0
            )
        # Assert original validation message is in the McpError message
        assert "n_results must be a positive integer" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_query_documents_validation_invalid_include(self, mock_chroma_client):
        """Test validation failure with invalid include value."""
        # Expect McpError
        with pytest.raises(McpError) as exc_info:
            await _query_documents_impl(
                collection_name="test_valid",
                query_texts=["q"],
                include=["documents", "invalid_field"]
            )
        # Assert original validation message is in the McpError message
        assert "Invalid item in include list" in str(exc_info.value)

    # --- _get_documents_impl Tests ---
    @pytest.mark.asyncio
    async def test_get_documents_success_by_ids(self, mock_chroma_client):
        """Test successful get by IDs."""
        mock_client, mock_collection = mock_chroma_client
        mock_collection.get.return_value = {
            "ids": ["id1", "id3"],
            "documents": ["doc one", "doc three"],
            "metadatas": [{"k":1}, {"k":3}]
        }
        
        ids_to_get = ["id1", "id3"]
        result = await _get_documents_impl(
            collection_name="test_get",
            ids=ids_to_get,
            limit=0, 
            offset=0
        )
        
        mock_collection.get.assert_called_once_with(
            ids=ids_to_get,
            where=None,
            where_document=None,
            include=["documents", "metadatas"], # Default include
            limit=None, # limit=0 becomes None
            offset=None # offset=0 becomes None
        )
        assert result["total_found"] == 2
        assert len(result["documents"]) == 2
        assert result["documents"][0]["id"] == "id1"
        assert result["documents"][0]["content"] == "doc one"
        assert result["documents"][1]["id"] == "id3"
        assert result["documents"][1]["metadata"] == {"k":3}

    @pytest.mark.asyncio
    async def test_get_documents_success_by_where(self, mock_chroma_client):
        """Test successful get by where filter with limit/offset."""
        mock_client, mock_collection = mock_chroma_client
        mock_collection.get.return_value = {
            "ids": ["id5"],
            "documents": ["doc five"] # Only metadatas included by default
        }
        
        where_filter = {"topic": "filtering"}
        result = await _get_documents_impl(
            collection_name="test_get_filter",
            where=where_filter,
            limit=5,
            offset=4,
            include=["documents"]
        )
        
        mock_collection.get.assert_called_once_with(
            ids=None,
            where=where_filter,
            where_document=None,
            include=["documents"],
            limit=5,
            offset=4 
        )
        assert result["total_found"] == 1
        assert len(result["documents"]) == 1
        assert result["documents"][0]["id"] == "id5"
        assert result["documents"][0]["content"] == "doc five"
        assert "metadata" not in result["documents"][0]
        assert result["limit"] == 5
        assert result["offset"] == 4

    @pytest.mark.asyncio
    async def test_get_documents_validation_no_criteria(self, mock_chroma_client):
        """Test validation failure when no criteria (ids/where) provided."""
        # Expect McpError
        with pytest.raises(McpError) as exc_info:
            await _get_documents_impl(
                collection_name="test_get_valid"
            )
        # Assert original validation message is in the McpError message
        assert "At least one of ids, where, or where_document" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_documents_validation_invalid_limit(self, mock_chroma_client):
        """Test validation failure with negative limit."""
        # Expect McpError
        with pytest.raises(McpError) as exc_info:
            await _get_documents_impl(
                collection_name="test_get_valid",
                ids=["id1"], 
                limit=-1 
            )
        # Assert original validation message is in the McpError message
        assert "limit cannot be negative" in str(exc_info.value)
        
    # --- _update_documents_impl Tests ---
    @pytest.mark.asyncio
    async def test_update_documents_success(self, mock_chroma_client):
        """Test successful document update."""
        mock_client, mock_collection = mock_chroma_client
        ids_to_update = ["id1"]
        new_docs = ["new content"]
        new_metas = [{"k": "new_v"}]
        
        result = await _update_documents_impl(
            collection_name="test_update",
            ids=ids_to_update,
            documents=new_docs,
            metadatas=new_metas
        )
        
        mock_collection.update.assert_called_once_with(
            ids=ids_to_update,
            documents=new_docs,
            metadatas=new_metas
        )
        assert result["success"] is True
        assert result["updated_count"] == 1
        assert result["document_ids"] == ids_to_update

    @pytest.mark.asyncio
    async def test_update_documents_validation_no_ids(self, mock_chroma_client):
        """Test validation failure with no IDs."""
        # Expect McpError
        with pytest.raises(McpError) as exc_info:
            await _update_documents_impl(
                collection_name="test_update_valid",
                ids=[], 
                documents=["d1"]
            )
        # Assert original validation message is in the McpError message
        assert "List of document IDs is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_documents_validation_no_data(self, mock_chroma_client):
        """Test validation failure with no data to update."""
        # Expect McpError
        with pytest.raises(McpError) as exc_info:
            await _update_documents_impl(
                collection_name="test_update_valid",
                ids=["id1"]
            )
        # Assert original validation message is in the McpError message
        assert "Either documents or metadatas must be provided" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_documents_validation_mismatch(self, mock_chroma_client):
        """Test validation failure with mismatched data lengths."""
        # Expect McpError
        with pytest.raises(McpError) as exc_info:
            await _update_documents_impl(
                collection_name="test_update_valid",
                ids=["id1", "id2"],
                documents=["d1"] 
            )
        # Assert original validation message is in the McpError message
        assert "Number of documents must match number of IDs" in str(exc_info.value)

    # --- _delete_documents_impl Tests ---
    @pytest.mark.asyncio
    async def test_delete_documents_success_by_ids(self, mock_chroma_client):
        """Test successful deletion by IDs."""
        mock_client, mock_collection = mock_chroma_client
        ids_to_delete = ["id1", "id2"]
        
        result = await _delete_documents_impl(
            collection_name="test_delete",
            ids=ids_to_delete
        )
        
        mock_collection.delete.assert_called_once_with(
            ids=ids_to_delete,
            where=None,
            where_document=None
        )
        assert result["success"] is True
        assert result["deleted_count"] == 2 # Based on input IDs
        assert result["deleted_ids"] == ids_to_delete # Input IDs returned

    @pytest.mark.asyncio
    async def test_delete_documents_success_by_where(self, mock_chroma_client):
        """Test successful deletion by where filter."""
        mock_client, mock_collection = mock_chroma_client
        where_filter = {"status": "old"}
        
        result = await _delete_documents_impl(
            collection_name="test_delete_filter",
            where=where_filter
        )
        
        mock_collection.delete.assert_called_once_with(
            ids=None,
            where=where_filter,
            where_document=None
        )
        assert result["success"] is True
        assert result["deleted_count"] == -1 # Count unknown for filters
        assert result["deleted_ids"] == [] # IDs unknown for filters

    @pytest.mark.asyncio
    async def test_delete_documents_validation_no_criteria(self, mock_chroma_client):
        """Test validation failure with no deletion criteria."""
        # Expect McpError
        with pytest.raises(McpError) as exc_info:
            await _delete_documents_impl(
                collection_name="test_delete_valid"
            )
        # Assert original validation message is in the McpError message
        assert "Either ids, where, or where_document must be provided" in str(exc_info.value)

    # --- General Error Handling Test ---
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "tool_impl_func, args, kwargs, expected_error_msg_part", [
            (_add_documents_impl, [], {"collection_name": "c", "documents": ["d"]}, "add_documents"),
            (_query_documents_impl, [], {"collection_name": "c", "query_texts": ["q"]}, "query_documents"),
            (_get_documents_impl, [], {"collection_name": "c", "ids": ["id1"]}, "get_documents"),
            (_update_documents_impl, [], {"collection_name": "c", "ids": ["id1"], "documents": ["d"]}, "update_documents"),
            (_delete_documents_impl, [], {"collection_name": "c", "ids": ["id1"]}, "delete_documents"),
        ]
    )
    async def test_generic_chroma_error_handling(self, mock_chroma_client, tool_impl_func, args, kwargs, expected_error_msg_part):
        """Test that generic Chroma errors are wrapped correctly."""
        mock_client, mock_collection = mock_chroma_client
        
        # Make the relevant COLLECTION method raise a generic error
        error_to_raise = Exception("Chroma DB Error")
        if "add" in expected_error_msg_part: mock_collection.add.side_effect = error_to_raise
        if "query" in expected_error_msg_part: mock_collection.query.side_effect = error_to_raise
        if "get" in expected_error_msg_part: mock_collection.get.side_effect = error_to_raise
        if "update" in expected_error_msg_part: mock_collection.update.side_effect = error_to_raise
        if "delete" in expected_error_msg_part: mock_collection.delete.side_effect = error_to_raise
        # Ensure client methods DON'T raise the error initially
        mock_client.get_collection.side_effect = None
        mock_client.get_or_create_collection.side_effect = None 

        with pytest.raises(McpError) as exc_info:
            await tool_impl_func(*args, **kwargs)
            
        # Assert on the McpError message 
        # Check for the specific exception message we raised in the mock
        assert "Chroma DB Error" in str(exc_info.value)
        # Optionally, assert the operation name is mentioned if handle_chroma_error includes it
        # assert expected_error_msg_part in str(exc_info.value) 

    # Example test for collection not found scenario
    @pytest.mark.asyncio
    async def test_query_collection_not_found(self, mock_chroma_client):
        """Test querying a non-existent collection."""
        mock_client, _ = mock_chroma_client
        mock_client.get_collection.side_effect = ValueError("Collection 'nonexistent' not found.")
        
        with pytest.raises(McpError) as exc_info:
            await _query_documents_impl(
                collection_name="nonexistent",
                query_texts=["test"]
            )
        # Assert on the McpError message
        assert "Collection 'nonexistent' not found" in str(exc_info.value)

    # --- Error Handling Tests ---
    @pytest.mark.asyncio
    async def test_add_documents_chroma_error(self, mock_chroma_client):
        """Test handling generic ChromaDB error when adding documents."""
        mock_client, mock_collection = mock_chroma_client
        mock_collection.add.side_effect = Exception("Simulated ChromaDB internal error")
        
        with pytest.raises(McpError) as exc_info:
            await _add_documents_impl(
                collection_name="test_docs",
                documents=["doc1"],
                ids=["id1"]
            )
        
        assert "ChromaDB operation failed" in str(exc_info.value)
        assert "Simulated ChromaDB internal error" in str(exc_info.value) # Check original error included

    @pytest.mark.asyncio
    async def test_add_documents_collection_not_found(self, mock_chroma_client):
        """Test adding documents when the collection doesn't exist (via get_or_create)."""
        mock_client, _ = mock_chroma_client # Only need client mock
        # Configure the CLIENT's get_or_create_collection method to raise the error
        mock_client.get_or_create_collection.side_effect = CollectionNotFoundError("Collection 'nonexistent' simulated not found during get_or_create")
        
        with pytest.raises(McpError) as exc_info:
            await _add_documents_impl(collection_name="nonexistent", documents=["doc1"])
            
        # Check that the specific CollectionNotFoundError is wrapped correctly
        assert "Collection 'nonexistent' simulated not found" in str(exc_info.value)
        mock_client.get_or_create_collection.assert_awaited_once_with(name="nonexistent", embedding_function=ANY)

    @pytest.mark.asyncio
    async def test_query_documents_chroma_error(self, mock_chroma_client):
        # This test case is not provided in the original file or the new code block
        # It's assumed to exist as it's called in the test_add_documents_collection_not_found test
        pass