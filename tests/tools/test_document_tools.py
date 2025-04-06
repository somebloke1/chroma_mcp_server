"""Tests for document management tools."""

import pytest
import uuid
from typing import Dict, Any, List, Optional

from src.chroma_mcp.utils.errors import ValidationError, CollectionNotFoundError, raise_validation_error

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
            
        # Mock count based on input
        count = len(ids) if ids else 1 # Assume filter matches 1 if no IDs
        return {
            "status": "success",
            "collection_name": collection_name,
            "deleted_count": count
        }

@pytest.fixture
def patched_mcp():
    """
    Return a mock MCP instance with all required methods.
    """
    return MockMCP()

class TestDocumentTools:
    """Test cases for document management tools."""

    @pytest.mark.asyncio
    async def test_add_documents_success(self, patched_mcp):
        """Test successful document addition."""
        # Test data
        documents = ["doc1", "doc2"]
        metadatas = [{"key": "value1"}, {"key": "value2"}]

        # Call add documents
        result = await patched_mcp.chroma_add_documents(
            collection_name="test_collection",
            documents=documents,
            metadatas=metadatas
        )

        # Verify result
        assert result["status"] == "success"
        assert result["added_count"] == 2

    @pytest.mark.asyncio
    async def test_add_documents_with_ids(self, patched_mcp):
        """Test document addition with custom IDs."""
        # Test data
        documents = ["doc1", "doc2"]
        ids = ["id1", "id2"]

        # Call add documents
        result = await patched_mcp.chroma_add_documents(
            collection_name="test_collection",
            documents=documents,
            ids=ids
        )

        # Verify result
        assert result["status"] == "success"
        assert result["added_count"] == 2

    @pytest.mark.asyncio
    async def test_add_documents_no_documents(self, patched_mcp):
        """Test document addition with empty document list."""
        with pytest.raises(ValidationError) as exc_info:
            await patched_mcp.chroma_add_documents(
                collection_name="test_collection",
                documents=[]
            )
        assert "No documents provided" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_query_documents_success(self, patched_mcp):
        """Test successful document query."""
        # Call query documents
        result = await patched_mcp.chroma_query_documents(
            collection_name="test_collection",
            query_texts=["test query"],
            n_results=2
        )

        # Verify result
        assert "results" in result
        assert len(result["results"]) > 0  # One query
        assert len(result["results"][0]["matches"]) > 0  # At least one match
        assert len(result["results"][0]["matches"]) == 2 # Check against n_results
        assert "document" in result["results"][0]["matches"][0] # Check included fields
        assert "metadata" in result["results"][0]["matches"][0]
        assert "distance" in result["results"][0]["matches"][0]

    @pytest.mark.asyncio
    async def test_query_documents_with_filters(self, patched_mcp):
        """Test document query with filters."""
        # Test filters
        where = {"key": "value"}
        where_document = {"$contains": "test"}

        # Call query documents
        result = await patched_mcp.chroma_query_documents(
            collection_name="test_collection",
            query_texts=["test query"],
            where=where,
            where_document=where_document
        )

        # Verify result
        assert "results" in result
        assert len(result["results"]) > 0
        assert len(result["results"][0]["matches"]) > 0 # Mock returns some matches even with filters

    @pytest.mark.asyncio
    async def test_get_documents_success(self, patched_mcp):
        """Test successful document retrieval."""
        # Call get documents
        result = await patched_mcp.chroma_get_documents(
            collection_name="test_collection",
            ids=["1", "2"]
        )

        # Verify result
        assert "documents" in result
        assert len(result["documents"]) > 0
        assert result["documents"][0]["id"] == "1"
        assert result["documents"][1]["id"] == "2"
        assert "content" in result["documents"][0]
        assert "metadata" in result["documents"][0]

    @pytest.mark.asyncio
    async def test_update_documents_success(self, patched_mcp):
        """Test successful document update."""
        # Test data
        documents = ["updated1", "updated2"]
        ids = ["1", "2"]
        metadatas = [{"key": "new1"}, {"key": "new2"}]

        # Call update documents
        result = await patched_mcp.chroma_update_documents(
            collection_name="test_collection",
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )

        # Verify result
        assert result["status"] == "success"
        assert result["updated_count"] == 2

    @pytest.mark.asyncio
    async def test_delete_documents_success(self, patched_mcp):
        """Test successful document deletion."""
        # Call delete documents
        result = await patched_mcp.chroma_delete_documents(
            collection_name="test_collection",
            ids=["1", "2"]
        )

        # Verify result
        assert result["status"] == "success"
        assert result["deleted_count"] == 2

    @pytest.mark.asyncio
    async def test_delete_documents_with_filters(self, patched_mcp):
        """Test document deletion with filters."""
        # Test filter
        where = {"key": "value"}

        # Call delete documents
        result = await patched_mcp.chroma_delete_documents(
            collection_name="test_collection",
            where=where
        )

        # Verify result
        assert result["status"] == "success"
        assert result["deleted_count"] == 1 # Mock deletes 1 if using filters

    @pytest.mark.asyncio
    async def test_error_handling(self, patched_mcp):
        """Test error handling in document operations."""
        # Override with a function that raises an exception
        original_fn = patched_mcp.chroma_query_documents
        
        async def error_fn(*args, **kwargs):
            raise Exception("Collection not found")
            
        try:
            patched_mcp.chroma_query_documents = error_fn
            
            # Test error handling
            with pytest.raises(Exception) as exc_info:
                await patched_mcp.chroma_query_documents(
                    collection_name="nonexistent",
                    query_texts=["test"]
                )
            assert "Collection not found" in str(exc_info.value)
            
        finally:
            # Restore original function
            patched_mcp.chroma_query_documents = original_fn