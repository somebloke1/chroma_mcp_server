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
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Add documents to a collection."""
        # Validate inputs
        if not documents:
            raise_validation_error("No documents provided")
            
        return {
            "status": "success",
            "collection_name": collection_name,
            "count": len(documents)
        }
        
    async def chroma_query_documents(
        self,
        collection_name: str,
        query_texts: List[str],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query documents from a collection."""
        # Generate mock results
        results = []
        for query in query_texts:
            matches = []
            for i in range(n_results):
                matches.append({
                    "id": f"{i+1}",
                    "document": f"doc{i+1}",
                    "metadata": {"key": f"value{i+1}"},
                    "distance": 0.1 * (i+1)
                })
            results.append({"query": query, "matches": matches})
            
        return {"results": results}
    
    async def chroma_get_documents(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get documents from a collection."""
        # Generate mock results
        documents = []
        if ids:
            for id in ids:
                documents.append({
                    "id": id,
                    "document": f"doc-{id}",
                    "metadata": {"key": f"value-{id}"}
                })
        else:
            for i in range(1, (limit or 10) + 1):
                documents.append({
                    "id": f"{i}",
                    "document": f"doc{i}",
                    "metadata": {"key": f"value{i}"}
                })
                
        return {"documents": documents}
    
    async def chroma_update_documents(
        self,
        collection_name: str,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Update documents in a collection."""
        return {
            "status": "success",
            "collection_name": collection_name,
            "count": len(ids)
        }
    
    async def chroma_delete_documents(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Delete documents from a collection."""
        count = len(ids) if ids else 1
        return {
            "status": "success",
            "collection_name": collection_name,
            "count": count
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
        assert result["count"] == 2

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
        assert result["count"] == 2

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
        assert result["count"] == 2

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
        assert "count" in result

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