"""Tests for collection management tools."""

import pytest
import uuid
import re # Import re for validation
from typing import Dict, Any, List, Optional
from unittest.mock import patch, AsyncMock
# Import ANY for mock assertions
from unittest.mock import ANY

from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS, ErrorData

# Import specific errors if needed, or rely on ValidationError/Exception
from src.chroma_mcp.utils.errors import ValidationError, raise_validation_error, handle_chroma_error
from src.chroma_mcp.tools.collection_tools import (
    _reconstruct_metadata, # Keep helper if used
    _create_collection_impl,
    _list_collections_impl,
    _get_collection_impl,
    _set_collection_description_impl,
    _set_collection_settings_impl,
    _update_collection_metadata_impl,
    _rename_collection_impl,
    _delete_collection_impl,
    _peek_collection_impl
)
# Correct import for get_collection_settings
from src.chroma_mcp.utils.config import get_collection_settings

DEFAULT_SIMILARITY_THRESHOLD = 0.7

class MockMCP:
    """Mock MCP class for testing collection tools."""
    
    def __init__(self):
        """Initialize mock MCP with storage for collections."""
        self.collections: Dict[str, Dict[str, Any]] = {}
        
    async def chroma_create_collection(
        self,
        collection_name: str,
    ) -> Dict[str, Any]:
        """Mock create a new collection."""
        # Basic validation (simplified but including character check)
        if not collection_name or len(collection_name) > 64 or not re.match(r'^[a-zA-Z0-9_-]+$', collection_name):
            raise ValidationError(f"Invalid collection name: {collection_name}")
        if collection_name in self.collections:
            raise Exception(f"Collection {collection_name} already exists") # Simulate Chroma error
            
        # Default settings (flattened and prefixed)
        default_settings = {
            "chroma:setting:hnsw_space": "cosine",
            "chroma:setting:hnsw_construction_ef": 100,
            "chroma:setting:hnsw_search_ef": 10,
            "chroma:setting:hnsw_M": 16,
            "chroma:setting:hnsw_num_threads": 4
        }
        collection_id = str(uuid.uuid4())
        self.collections[collection_name] = {
            "id": collection_id,
            "metadata": default_settings
        }
        
        return {
            "name": collection_name,
            "id": collection_id,
            "metadata": _reconstruct_metadata(default_settings)
        }
    
    async def chroma_list_collections(
        self,
        # Use non-Optional types with defaults
        limit: int = 0,
        offset: int = 0,
        name_contains: str = ""
    ) -> Dict[str, Any]:
        """Mock list available collections."""
        # Basic validation
        if limit < 0:
            raise ValidationError("limit cannot be negative")
        if offset < 0:
            raise ValidationError("offset cannot be negative")
            
        filtered_collections = []
        collection_names = list(self.collections.keys())
        
        # Filter by name if specified
        if name_contains:
            filtered_names = [name for name in collection_names if name_contains.lower() in name.lower()]
        else:
            filtered_names = collection_names
            
        total_count = len(filtered_names)
        
        # Apply pagination (limit=0 means no limit for mock)
        start = offset
        end = (start + limit) if limit > 0 else None
        paginated_names = filtered_names[start:end]
            
        # Return structure matching actual tool (just names)
        return {
            "collection_names": paginated_names,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }
    
    async def chroma_get_collection(
        self,
        collection_name: str
    ) -> Dict[str, Any]:
        """Mock get information about a collection."""
        if collection_name not in self.collections:
            raise Exception(f"Collection {collection_name} not found") # Simulate Chroma error
            
        data = self.collections[collection_name]
        return {
            "name": collection_name,
            "id": data["id"],
            "metadata": _reconstruct_metadata(data["metadata"]), # Reconstruct for output
            "count": 5, # Mock count
            "sample_entries": { # Mock peek result structure
                "ids": ["s1", "s2"],
                "documents": ["Sample 1", "Sample 2"] 
            }
        }
        
    async def _get_collection_internal(self, collection_name: str):
        """Helper to get internal collection data or raise error."""
        if collection_name not in self.collections:
            raise Exception(f"Collection '{collection_name}' not found")
        return self.collections[collection_name]

    async def chroma_set_collection_description(
        self,
        collection_name: str,
        description: str
    ) -> Dict[str, Any]:
        """Mock set collection description."""
        collection_data = await self._get_collection_internal(collection_name)
        collection_data["metadata"]["description"] = description
        return await self.chroma_get_collection(collection_name)
        
    async def chroma_set_collection_settings(
        self,
        collection_name: str, 
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock set collection settings."""
        if not isinstance(settings, dict):
            raise ValidationError("Settings must be a dictionary.")
        collection_data = await self._get_collection_internal(collection_name)
        # Remove old settings
        collection_data["metadata"] = {k: v for k, v in collection_data["metadata"].items() if not k.startswith("chroma:setting:")}
        # Add new flattened settings (FIXED: remove extra colon)
        new_settings = {f"chroma:setting:{k.replace(':', '_')}": v for k, v in settings.items()}
        collection_data["metadata"].update(new_settings)
        return await self.chroma_get_collection(collection_name)

    async def chroma_update_collection_metadata(
        self,
        collection_name: str,
        metadata_update: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock update collection metadata."""
        if not isinstance(metadata_update, dict):
            raise ValidationError("Metadata update must be a dictionary.")
        collection_data = await self._get_collection_internal(collection_name)
        # Remove reserved keys from update
        metadata_update.pop("description", None)
        metadata_update.pop("settings", None) # Ensure settings structure isn't directly added
        # Update only non-prefixed keys
        for k, v in metadata_update.items():
            if not k.startswith("chroma:setting:"):
                collection_data["metadata"][k] = v
        return await self.chroma_get_collection(collection_name)
        
    async def chroma_rename_collection(
        self,
        collection_name: str, 
        new_name: str
    ) -> Dict[str, Any]:
        """Mock rename collection."""
        # Basic validation (simplified but including character check)
        if not new_name or len(new_name) > 64 or not re.match(r'^[a-zA-Z0-9_-]+$', new_name):
            raise ValidationError(f"Invalid new name: {new_name}")
        if new_name in self.collections:
            raise Exception(f"Collection {new_name} already exists")
        collection_data = await self._get_collection_internal(collection_name)
        self.collections[new_name] = collection_data
        del self.collections[collection_name]
        return await self.chroma_get_collection(new_name)

    async def chroma_delete_collection(
        self,
        collection_name: str
    ) -> Dict[str, Any]:
        """Mock delete a collection."""
        if collection_name not in self.collections:
            return {"status": "not_found", "message": f"Collection '{collection_name}' does not exist."}
        del self.collections[collection_name]
        return {
            "status": "deleted",
            "collection_name": collection_name
        }

    async def chroma_peek_collection(
        self,
        collection_name: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Mock peek at documents in a collection."""
        if collection_name not in self.collections:
            raise Exception(f"Collection {collection_name} not found")
        # Generate mock peek results
        limit = min(limit, 5) # Max 5 mock items
        peek_result = {
            "ids": [f"id_{i}" for i in range(limit)],
            "embeddings": None, # Mocking embeddings is complex
            "documents": [f"Doc {i}" for i in range(limit)],
            "metadatas": [{f"key_{i}": i} for i in range(limit)]
        }
        return {"peek_result": peek_result}

@pytest.fixture
def mcp():
    """
    Return a mock MCP instance for testing.
    """
    return MockMCP()

@pytest.fixture
def mock_chroma_client_collections():
    """Fixture to mock the Chroma client and its methods for collection tests."""
    with patch("src.chroma_mcp.tools.collection_tools.get_chroma_client") as mock_get_client, \
         patch("src.chroma_mcp.tools.collection_tools.get_collection_settings") as mock_get_settings, \
         patch("src.chroma_mcp.tools.collection_tools.validate_collection_name") as mock_validate_name:

        mock_client_instance = AsyncMock()
        mock_collection_instance = AsyncMock()
        
        # --- Configure mock methods for collection --- 
        # Use simple return values or side_effects as needed for tests
        mock_collection_instance.name = "mock_coll"
        mock_collection_instance.id = str(uuid.uuid4())
        # Store metadata within the mock instance to simulate state changes
        # Get defaults by calling the actual function
        default_settings_dict = get_collection_settings()
        mock_collection_instance.metadata = { # Default state
             f"chroma:setting:{k.replace(':', '_')}": v for k, v in default_settings_dict.items()
        }
        mock_collection_instance.count = AsyncMock(return_value=0)
        mock_collection_instance.peek = AsyncMock(return_value={"ids": [], "documents": []})
        mock_collection_instance.modify = AsyncMock() # Tracks calls
        
        # --- Configure mock methods for client --- 
        mock_client_instance.create_collection = AsyncMock(return_value=mock_collection_instance) 
        mock_client_instance.get_collection = AsyncMock(return_value=mock_collection_instance)
        mock_client_instance.list_collections = AsyncMock(return_value=["existing_coll1", "existing_coll2"]) # Default list
        mock_client_instance.delete_collection = AsyncMock() # Tracks calls
        
        mock_get_client.return_value = mock_client_instance
        
        # Mock config/validation helpers
        # Get actual defaults and set the patched function to return them
        default_settings_dict = get_collection_settings()
        mock_get_settings.return_value = default_settings_dict
        mock_validate_name.return_value = None # Assume valid by default
        
        # Use the defaults to set the initial metadata on the mock collection instance
        # Manually corrected f-string syntax:
        mock_collection_instance.metadata = {
            f"chroma:setting:{k.replace(':', '_')}": v for k, v in default_settings_dict.items()
        }
        
        yield mock_client_instance, mock_collection_instance, mock_validate_name

class TestCollectionTools:
    """Test cases for collection management tools."""

    # --- _create_collection_impl Tests ---
    @pytest.mark.asyncio
    async def test_create_collection_success(self, mock_chroma_client_collections):
        """Test successful collection creation."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_collections
        collection_name = "test_create_new"
        
        # Mock the collection returned by create_collection to have the correct name/id
        created_collection_mock = AsyncMock()
        created_collection_mock.name = collection_name
        created_collection_mock.id = str(uuid.uuid4())
        # Store metadata within the mock instance to simulate state changes
        # Get defaults by calling the actual function
        default_settings_dict = get_collection_settings()
        created_collection_mock.metadata = { # Match initial metadata used in _impl
             f"chroma:setting:{k.replace(':', '_')}": v for k, v in default_settings_dict.items()
        }
        mock_client.create_collection.return_value = created_collection_mock
        
        result = await _create_collection_impl(collection_name=collection_name)
        
        mock_validate.assert_called_once_with(collection_name)
        mock_client.create_collection.assert_awaited_once()
        # Check args passed to create_collection if necessary
        call_args = mock_client.create_collection.call_args
        assert call_args.kwargs["name"] == collection_name
        # Assertions on the returned dict
        assert result["name"] == collection_name
        assert "id" in result
        assert result["id"] == created_collection_mock.id
        assert "metadata" in result
        assert "settings" in result["metadata"]
        assert result["metadata"]["settings"]["hnsw:space"] == default_settings_dict["hnsw:space"]

    @pytest.mark.asyncio
    async def test_create_collection_invalid_name(self, mock_chroma_client_collections):
        """Test collection creation with invalid name (validation failure)."""
        mock_client, _, mock_validate = mock_chroma_client_collections
        error_data = ErrorData(code=INVALID_PARAMS, message="Invalid name")
        mock_validate.side_effect = McpError(error_data)
        
        with pytest.raises(McpError) as exc_info:
            await _create_collection_impl(collection_name="invalid@name")
        assert "Invalid name" in str(exc_info.value)
        mock_client.create_collection.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_collection_chroma_error(self, mock_chroma_client_collections):
        """Test handling of ChromaDB error during creation."""
        mock_client, _, _ = mock_chroma_client_collections
        mock_client.create_collection.side_effect = Exception("Chroma duplicate error")
        
        with pytest.raises(McpError) as exc_info:
            await _create_collection_impl(collection_name="test_chroma_fail")
        assert "Chroma duplicate error" in str(exc_info.value)

    # --- _list_collections_impl Tests ---
    @pytest.mark.asyncio
    async def test_list_collections_success(self, mock_chroma_client_collections):
        """Test successful default collection listing."""
        mock_client, _, _ = mock_chroma_client_collections
        mock_client.list_collections.return_value = ["coll_a", "coll_b"]
        
        result = await _list_collections_impl()
        
        mock_client.list_collections.assert_awaited_once()
        assert result["collection_names"] == ["coll_a", "coll_b"]
        assert result["total_count"] == 2
        assert result["limit"] == 0
        assert result["offset"] == 0

    @pytest.mark.asyncio
    async def test_list_collections_with_filter_pagination(self, mock_chroma_client_collections):
        """Test listing with name filter and pagination."""
        mock_client, _, _ = mock_chroma_client_collections
        mock_client.list_collections.return_value = ["apple", "banana", "apricot", "avocado"]
        
        result = await _list_collections_impl(limit=2, offset=1, name_contains="ap")
        
        mock_client.list_collections.assert_awaited_once()
        # Filtered: ["apple", "apricot"] -> Offset 1: ["apricot"] -> Limit 2: ["apricot"]
        assert result["collection_names"] == ["apricot"]
        assert result["total_count"] == 2 # Count after filtering, before pagination
        assert result["limit"] == 2
        assert result["offset"] == 1
        
    @pytest.mark.asyncio
    async def test_list_collections_validation_error(self, mock_chroma_client_collections):
        """Test validation errors for list parameters."""
        # Expect McpError because handle_chroma_error wraps ValidationError
        with pytest.raises(McpError) as exc_info_limit:
            await _list_collections_impl(limit=-1)
        assert "limit cannot be negative" in str(exc_info_limit.value)
        
        with pytest.raises(McpError) as exc_info_offset:
            await _list_collections_impl(offset=-1)
        assert "offset cannot be negative" in str(exc_info_offset.value)

    # --- _get_collection_impl Tests ---
    @pytest.mark.asyncio
    async def test_get_collection_success(self, mock_chroma_client_collections):
        """Test getting existing collection info."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        collection_name = "my_coll"
        # Set specific metadata on the mock collection for this test
        mock_collection.name = collection_name
        mock_collection.id = "test-id-123"
        mock_collection.metadata = {"description": "test desc", "chroma:setting:hnsw_space": "l2"}
        mock_collection.count.return_value = 42
        mock_collection.peek.return_value = {"ids": ["p1"], "documents": ["peek doc"]}
        mock_client.get_collection.return_value = mock_collection
        
        result = await _get_collection_impl(collection_name)
        
        mock_client.get_collection.assert_awaited_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.count.assert_awaited_once()
        mock_collection.peek.assert_awaited_once()
        assert result["name"] == collection_name
        assert result["id"] == "test-id-123"
        assert result["count"] == 42
        assert result["metadata"] == {"description": "test desc", "settings": {"hnsw:space": "l2"}}
        assert result["sample_entries"] == {"ids": ["p1"], "documents": ["peek doc"]}

    @pytest.mark.asyncio
    async def test_get_collection_not_found(self, mock_chroma_client_collections):
        """Test getting a non-existent collection."""
        mock_client, _, _ = mock_chroma_client_collections
        mock_client.get_collection.side_effect = ValueError("Collection 'not_found' not found") # Simulate Chroma error
        
        with pytest.raises(McpError) as exc_info:
            await _get_collection_impl("not_found")
        assert "Collection 'not_found' not found" in str(exc_info.value)

    # --- _set_collection_description_impl Tests ---
    @pytest.mark.asyncio
    async def test_set_collection_description_success(self, mock_chroma_client_collections):
        """Test setting a collection description."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        collection_name = "desc_coll"
        new_description = "My new description"
        
        # Mock get_collection to return our mock collection
        mock_client.get_collection.return_value = mock_collection
        # Reset modify mock to check its call
        mock_collection.modify.reset_mock()
        
        # Assume _get_collection_impl works (tested elsewhere) 
        # or mock its behavior if complex interactions are needed
        with patch("src.chroma_mcp.tools.collection_tools._get_collection_impl") as mock_get_impl:
             mock_get_impl.return_value = {"name": collection_name, "metadata": {"description": new_description}}
             
             result = await _set_collection_description_impl(collection_name, new_description)

        mock_client.get_collection.assert_awaited_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.modify.assert_awaited_once()
        # Check that modify was called with the correct updated metadata
        call_args = mock_collection.modify.call_args
        assert call_args.kwargs["metadata"]["description"] == new_description
        # Check the final returned result (comes from the mocked _get_collection_impl)
        assert result["metadata"]["description"] == new_description 

    # --- _set_collection_settings_impl Tests ---
    @pytest.mark.asyncio
    async def test_set_collection_settings_success(self, mock_chroma_client_collections):
        """Test setting collection settings."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        collection_name = "settings_coll"
        new_settings = {"hnsw:space": "ip", "hnsw:construction_ef": 200}
        
        mock_client.get_collection.return_value = mock_collection
        mock_collection.modify.reset_mock()
        
        # Assume _get_collection_impl works
        with patch("src.chroma_mcp.tools.collection_tools._get_collection_impl") as mock_get_impl:
             mock_get_impl.return_value = {"name": collection_name, "metadata": {"settings": new_settings}}
             
             result = await _set_collection_settings_impl(collection_name, new_settings)
             
        mock_collection.modify.assert_awaited_once()
        call_args = mock_collection.modify.call_args
        expected_metadata = {f"chroma:setting:{k.replace(':', '_')}": v for k, v in new_settings.items()}
        assert call_args.kwargs["metadata"] == expected_metadata # Modify expects flattened
        assert result["metadata"]["settings"] == new_settings # Return value has reconstructed

    @pytest.mark.asyncio
    async def test_set_collection_settings_invalid_type(self, mock_chroma_client_collections):
        """Test error when settings are not a dict."""
        with pytest.raises(McpError) as exc_info:
            await _set_collection_settings_impl("any_coll", ["not", "a"]) # Pass list
        assert "settings parameter must be a dictionary" in str(exc_info.value)

    # --- _update_collection_metadata_impl Tests ---
    @pytest.mark.asyncio
    async def test_update_collection_metadata_success(self, mock_chroma_client_collections):
        """Test updating custom metadata."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        collection_name = "meta_coll"
        metadata_update = {"custom_key": "new_value", "another": 123}
        # Set initial metadata on the mock collection
        mock_collection.metadata = {"existing": "data"}
        mock_client.get_collection.return_value = mock_collection
        mock_collection.modify.reset_mock()

        with patch("src.chroma_mcp.tools.collection_tools._get_collection_impl") as mock_get_impl:
            # Mock the return to reflect the update
            updated_meta_result = {"existing": "data", **metadata_update}
            mock_get_impl.return_value = {"name": collection_name, "metadata": updated_meta_result}
            
            result = await _update_collection_metadata_impl(collection_name, metadata_update)

        mock_collection.modify.assert_awaited_once()
        call_args = mock_collection.modify.call_args
        # Check metadata passed includes original and update
        assert call_args.kwargs["metadata"]["existing"] == "data"
        assert call_args.kwargs["metadata"]["custom_key"] == "new_value"
        assert result["metadata"] == updated_meta_result

    @pytest.mark.asyncio
    async def test_update_collection_metadata_rejects_reserved(self, mock_chroma_client_collections):
        """Test that updating reserved keys fails."""
        with pytest.raises(McpError) as exc_info:
            await _update_collection_metadata_impl("any_coll", {"description": "no!"})
        assert "Cannot update reserved keys" in str(exc_info.value)
        
        with pytest.raises(McpError) as exc_info_settings:
             await _update_collection_metadata_impl("any_coll", {"settings": {"a":1}})
        assert "Cannot update reserved keys" in str(exc_info_settings.value)

        with pytest.raises(McpError) as exc_info_prefix:
             await _update_collection_metadata_impl("any_coll", {"chroma:setting:x": "y"})
        assert "Cannot update reserved keys" in str(exc_info_prefix.value)

    # --- _rename_collection_impl Tests ---
    @pytest.mark.asyncio
    async def test_rename_collection_success(self, mock_chroma_client_collections):
        """Test successful collection renaming."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_collections
        old_name = "old_name"
        new_name = "new_name_valid"
        mock_client.get_collection.return_value = mock_collection
        mock_collection.modify.reset_mock()

        with patch("src.chroma_mcp.tools.collection_tools._get_collection_impl") as mock_get_impl:
            mock_get_impl.return_value = {"name": new_name} # Mock return after rename
            result = await _rename_collection_impl(old_name, new_name)

        mock_validate.assert_called_once_with(new_name)
        mock_client.get_collection.assert_awaited_once_with(name=old_name, embedding_function=ANY)
        mock_collection.modify.assert_awaited_once_with(name=new_name)
        mock_get_impl.assert_awaited_once_with(new_name)
        assert result["name"] == new_name

    @pytest.mark.asyncio
    async def test_rename_collection_invalid_new_name(self, mock_chroma_client_collections):
        """Test renaming with invalid new name."""
        _, _, mock_validate = mock_chroma_client_collections
        error_data = ErrorData(code=INVALID_PARAMS, message="Invalid name")
        mock_validate.side_effect = McpError(error_data)
        with pytest.raises(McpError) as exc_info:
            await _rename_collection_impl("old", "new@invalid")
        assert "Invalid name" in str(exc_info.value)

    # --- _delete_collection_impl Tests ---
    @pytest.mark.asyncio
    async def test_delete_collection_success(self, mock_chroma_client_collections):
        """Test successful collection deletion."""
        mock_client, _, _ = mock_chroma_client_collections
        collection_name = "to_delete"
        result = await _delete_collection_impl(collection_name)
        mock_client.delete_collection.assert_awaited_once_with(name=collection_name)
        assert result["success"] is True
        assert result["deleted_collection"] == collection_name

    @pytest.mark.asyncio
    async def test_delete_collection_chroma_error(self, mock_chroma_client_collections):
        """Test handling Chroma error during deletion (e.g., not found handled by impl)."""
        mock_client, _, _ = mock_chroma_client_collections
        # Simulate error like concurrent deletion or other issue
        mock_client.delete_collection.side_effect = Exception("Generic Chroma Delete Error") 
        with pytest.raises(McpError) as exc_info:
            await _delete_collection_impl("delete_fail")
        assert "Generic Chroma Delete Error" in str(exc_info.value)

    # --- _peek_collection_impl Tests ---
    @pytest.mark.asyncio
    async def test_peek_collection_success(self, mock_chroma_client_collections):
        """Test peeking into a collection."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        collection_name = "peek_coll"
        limit = 5
        mock_peek_data = {"ids": ["p1", "p2"]}
        mock_collection.peek.return_value = mock_peek_data
        mock_client.get_collection.return_value = mock_collection
        
        result = await _peek_collection_impl(collection_name, limit)
        
        mock_client.get_collection.assert_awaited_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.peek.assert_awaited_once_with(limit=limit)
        assert result["collection_name"] == collection_name
        assert result["limit"] == limit
        assert result["peek_result"] == mock_peek_data

    @pytest.mark.asyncio
    async def test_peek_collection_invalid_limit(self, mock_chroma_client_collections):
        """Test peeking with invalid limit."""
        with pytest.raises(McpError) as exc_info:
            await _peek_collection_impl("peek_invalid", limit=0)
        assert "limit must be a positive integer" in str(exc_info.value)

        with pytest.raises(McpError) as exc_info_neg:
            await _peek_collection_impl("peek_invalid", limit=-1)
        assert "limit must be a positive integer" in str(exc_info_neg.value)