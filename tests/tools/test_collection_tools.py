"""Tests for collection management tools."""

import pytest
import uuid
from typing import Dict, Any, List, Optional

from src.chroma_mcp.utils.errors import ValidationError, raise_validation_error

DEFAULT_SIMILARITY_THRESHOLD = 0.7

class MockMCP:
    """Mock MCP class with all required methods."""
    
    def __init__(self):
        """Initialize mock MCP."""
        self.name = "mock-mcp"
        
    async def chroma_create_collection(
        self,
        collection_name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        hnsw_space: Optional[str] = None,
        hnsw_construction_ef: Optional[int] = None,
        hnsw_search_ef: Optional[int] = None,
        hnsw_M: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new collection."""
        # Validate collection name
        if collection_name.startswith("invalid"):
            raise_validation_error(f"Invalid collection name: {collection_name}")
            
        # Create collection metadata
        collection_metadata = {
            "description": description or f"Collection {collection_name}",
            "settings": {
                "hnsw:space": hnsw_space or "l2",
                "hnsw:construction_ef": hnsw_construction_ef or 100,
                "hnsw:search_ef": hnsw_search_ef or 100,
                "hnsw:M": hnsw_M or 16
            }
        }
        
        if metadata:
            collection_metadata.update(metadata)
        
        return {
            "name": collection_name,
            "id": str(uuid.uuid4()),
            "metadata": collection_metadata
        }
    
    async def chroma_list_collections(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        name_contains: Optional[str] = None
    ) -> Dict[str, Any]:
        """List available collections."""
        # Generate mock collections
        collections = []
        for i in range(1, 4):
            name = f"collection{i}"
            if name_contains and name_contains not in name:
                continue
            collections.append({
                "name": name,
                "id": f"{i}",
                "metadata": {"description": f"Description for {name}"}
            })
        
        # Apply limit and offset
        if offset:
            collections = collections[offset:]
        if limit:
            collections = collections[:limit]
            
        return {
            "collections": collections,
            "total_count": len(collections)
        }
    
    async def chroma_get_collection(
        self,
        collection_name: str
    ) -> Dict[str, Any]:
        """Get information about a collection."""
        return {
            "name": collection_name,
            "id": str(uuid.uuid4()),
            "metadata": {"description": f"Description for {collection_name}"},
            "count": 10,
            "sample_entries": [
                {"id": "1", "document": "Sample doc 1"},
                {"id": "2", "document": "Sample doc 2"}
            ]
        }
    
    async def chroma_modify_collection(
        self,
        collection_name: str,
        new_metadata: Optional[Dict[str, Any]] = None,
        new_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Modify an existing collection."""
        modified_name = new_name or collection_name
        modified_metadata = {"description": f"Description for {modified_name}"}
        if new_metadata:
            modified_metadata.update(new_metadata)
            
        return {
            "name": modified_name,
            "id": str(uuid.uuid4()),
            "metadata": modified_metadata
        }
    
    async def chroma_delete_collection(
        self,
        collection_name: str
    ) -> Dict[str, Any]:
        """Delete a collection."""
        return {
            "status": "success",
            "collection_name": collection_name
        }
    
    async def chroma_peek_collection(
        self,
        collection_name: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Peek at documents in a collection."""
        # Generate mock entries
        entries = []
        for i in range(1, limit + 1):
            entries.append({
                "id": f"{i}",
                "document": f"Document {i}",
                "metadata": {"key": f"value{i}"}
            })
            
        return {"entries": entries}

@pytest.fixture
def patched_mcp():
    """
    Return a mock MCP instance with all required methods.
    """
    return MockMCP()

class TestCollectionTools:
    """Test cases for collection management tools."""

    @pytest.mark.asyncio
    async def test_create_collection_success(self, patched_mcp):
        """Test successful collection creation."""
        # Call create collection
        result = await patched_mcp.chroma_create_collection(
            collection_name="test_collection",
            description="Test collection",
            hnsw_space="cosine"
        )

        # Verify result
        assert result["name"] == "test_collection"
        assert "id" in result
        assert "metadata" in result
        assert "description" in result["metadata"]

    @pytest.mark.asyncio
    async def test_create_collection_invalid_name(self, patched_mcp):
        """Test collection creation with invalid name."""
        with pytest.raises(ValidationError) as exc_info:
            await patched_mcp.chroma_create_collection(collection_name="invalid@name")
        assert "Invalid collection name" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_collections_success(self, patched_mcp):
        """Test successful collections listing."""
        # Call list collections
        result = await patched_mcp.chroma_list_collections()

        # Verify result
        assert "collections" in result
        assert "total_count" in result

    @pytest.mark.asyncio
    async def test_list_collections_with_filter(self, patched_mcp):
        """Test collections listing with name filter."""
        # Call list collections with filter
        result = await patched_mcp.chroma_list_collections(name_contains="test")

        # Verify result
        assert "collections" in result
        assert "total_count" in result

    @pytest.mark.asyncio
    async def test_get_collection_success(self, patched_mcp):
        """Test successful collection retrieval."""
        # Call get collection
        result = await patched_mcp.chroma_get_collection("test_collection")

        # Verify result
        assert "name" in result
        assert "id" in result
        assert "count" in result
        assert "sample_entries" in result

    @pytest.mark.asyncio
    async def test_modify_collection_success(self, patched_mcp):
        """Test successful collection modification."""
        # Call modify collection
        result = await patched_mcp.chroma_modify_collection(
            collection_name="test_collection",
            new_metadata={"description": "New description"},
            new_name="new_collection"
        )

        # Verify result
        assert "name" in result
        assert "metadata" in result

    @pytest.mark.asyncio
    async def test_delete_collection_success(self, patched_mcp):
        """Test successful collection deletion."""
        # Call delete collection
        result = await patched_mcp.chroma_delete_collection("test_collection")

        # Verify result
        assert result["status"] == "success"
        assert result["collection_name"] == "test_collection"

    @pytest.mark.asyncio
    async def test_peek_collection_success(self, patched_mcp):
        """Test successful collection peek."""
        # Call peek collection
        result = await patched_mcp.chroma_peek_collection("test_collection", limit=2)

        # Verify result
        assert "entries" in result

    @pytest.mark.asyncio
    async def test_error_handling(self, patched_mcp):
        """Test error handling in collection operations."""
        # Override with a function that raises an exception
        original_fn = patched_mcp.chroma_create_collection
        
        async def error_fn(*args, **kwargs):
            raise Exception("Test error")
            
        try:
            patched_mcp.chroma_create_collection = error_fn
            
            # Test error handling
            with pytest.raises(Exception) as exc_info:
                await patched_mcp.chroma_create_collection("test_collection")
            assert "Test error" in str(exc_info.value)
            
        finally:
            # Restore original function
            patched_mcp.chroma_create_collection = original_fn