"""Tests for collection management tools."""

import pytest
import uuid
import re
import json
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock, ANY, call

from mcp import types
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS, INTERNAL_ERROR, ErrorData

# Import specific errors if needed, or rely on ValidationError/Exception
from src.chroma_mcp.utils.errors import ValidationError
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
    _peek_collection_impl,
)
# Correct import for get_collection_settings
from src.chroma_mcp.utils.config import get_collection_settings

DEFAULT_SIMILARITY_THRESHOLD = 0.7

# --- Helper Functions ---

def assert_successful_json_result(result: types.CallToolResult, expected_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Asserts the tool result is successful and contains valid JSON, returning the parsed data."""
    assert isinstance(result, types.CallToolResult)
    assert result.isError is False
    assert isinstance(result.content, list)
    assert len(result.content) == 1
    assert isinstance(result.content[0], types.TextContent)
    assert result.content[0].type == "text"

    try:
        result_data = json.loads(result.content[0].text)
    except json.JSONDecodeError:
        pytest.fail(f"Failed to parse JSON content: {result.content[0].text}")

    assert isinstance(result_data, dict)
    if expected_data is not None:
        assert result_data == expected_data
    return result_data # Return parsed data for further specific assertions

def assert_error_result(result: types.CallToolResult, expected_error_substring: str):
    """Asserts the tool result is an error and contains the expected substring."""
    assert isinstance(result, types.CallToolResult)
    assert result.isError is True
    assert isinstance(result.content, list)
    assert len(result.content) == 1
    assert isinstance(result.content[0], types.TextContent)
    assert result.content[0].type == "text"
    assert expected_error_substring in result.content[0].text


@pytest.fixture
def mock_chroma_client_collections():
    """Fixture to mock the Chroma client and its methods for collection tests (Synchronous)."""
    with patch("src.chroma_mcp.tools.collection_tools.get_chroma_client") as mock_get_client, \
         patch("src.chroma_mcp.tools.collection_tools.get_embedding_function") as mock_get_embedding_function, \
         patch("src.chroma_mcp.tools.collection_tools.get_collection_settings") as mock_get_settings, \
         patch("src.chroma_mcp.tools.collection_tools.validate_collection_name") as mock_validate_name:

        # Use MagicMock for synchronous behavior
        mock_client_instance = MagicMock()
        mock_collection_instance = MagicMock()

        # Configure mock methods for collection (synchronous)
        mock_collection_instance.name = "mock_collection"
        mock_collection_instance.id = "mock_id_123"
        # Set more realistic initial metadata
        mock_collection_instance.metadata = {"description": "Fixture Desc"} 
        mock_collection_instance.count.return_value = 0
        mock_collection_instance.peek.return_value = {"ids": [], "documents": []}

        # Configure mock methods for client (synchronous)
        mock_client_instance.create_collection.return_value = mock_collection_instance
        mock_client_instance.get_collection.return_value = mock_collection_instance
        mock_client_instance.list_collections.return_value = ["existing_coll1", "existing_coll2"]
        # Explicitly configure methods used in collection tests that were missing
        mock_client_instance.delete_collection.return_value = None # For delete tests

        # Configure modify on the collection instance mock (used by set/update/rename)
        mock_collection_instance.modify.return_value = None

        mock_get_client.return_value = mock_client_instance
        mock_get_embedding_function.return_value = None
        mock_get_settings.return_value = {"hnsw:space": "cosine"} # Default settings if needed
        mock_validate_name.return_value = None

        yield mock_client_instance, mock_collection_instance, mock_validate_name

class TestCollectionTools:
    """Test cases for collection management tools."""

    # --- _create_collection_impl Tests ---
    @pytest.mark.asyncio
    async def test_create_collection_success(self, mock_chroma_client_collections):
        """Test successful collection creation."""
        mock_client, _, mock_validate = mock_chroma_client_collections # mock_collection fixture not directly needed here
        collection_name = "test_create_new"
        mock_collection_id = str(uuid.uuid4())

        # Mock the collection returned by create_collection
        created_collection_mock = MagicMock()
        created_collection_mock.name = collection_name
        created_collection_mock.id = mock_collection_id # Use a fixed UUID for assertion
        
        # Simulate the metadata as stored by ChromaDB (flattened, used by _reconstruct_metadata)
        # We'll need to get the *actual* default settings used by the implementation.
        # For now, let's mock it based on what the reconstruct expects.
        # Call get_collection_settings() with no args to get the defaults
        actual_default_settings = get_collection_settings()
        created_collection_mock.metadata = {
             f"chroma:setting:{k.replace(':', '_')}": v for k, v in actual_default_settings.items()
        }
        created_collection_mock.count.return_value = 0 # Simulate count after creation
        # Simulate peek result structure (limit 5 is used in impl)
        mock_peek_result = {"ids": [], "documents": [], "metadatas": None, "embeddings": None}
        created_collection_mock.peek.return_value = mock_peek_result
        mock_client.create_collection.return_value = created_collection_mock

        # --- Act ---
        result = await _create_collection_impl(collection_name=collection_name, metadata=None)

        # --- Assert ---
        # Mock calls
        mock_validate.assert_called_once_with(collection_name)
        mock_client.create_collection.assert_called_once()
        call_args = mock_client.create_collection.call_args
        assert call_args.kwargs["name"] == collection_name
        # Check metadata passed to create_collection (should be the reconstructed default settings)
        assert "metadata" in call_args.kwargs
        # Based on error, impl seems to pass only hnsw:space default when metadata is None
        assert call_args.kwargs["metadata"] == {"hnsw:space": "cosine"}
        assert call_args.kwargs["get_or_create"] is False

        # Result structure and content assertions using helper
        result_data = assert_successful_json_result(result)
        assert result_data.get("name") == collection_name
        assert result_data.get("id") == mock_collection_id
        assert "metadata" in result_data
        # Check reconstructed metadata in result
        assert result_data["metadata"] == _reconstruct_metadata(created_collection_mock.metadata)
        # Check reconstructed settings match the defaults used by the implementation
        # Reconstructed keys use :, compare against a dict with expected : keys
        expected_reconstructed_settings = {k.replace("_", ":"): v for k, v in actual_default_settings.items()}
        assert result_data["metadata"].get("settings") == expected_reconstructed_settings
        assert result_data.get("count") == 0 # Based on mock count

    @pytest.mark.asyncio
    async def test_create_collection_invalid_name(self, mock_chroma_client_collections):
        """Test collection creation with invalid name (validation failure handled in impl)."""
        mock_client, _, mock_validate = mock_chroma_client_collections
        invalid_name = "invalid@name"
        validation_error_message = f"Invalid collection name: {invalid_name}"
        # Mock the validation function to raise the specific exception
        mock_validate.side_effect = ValidationError(validation_error_message)
        
        # --- Act ---
        result = await _create_collection_impl(collection_name=invalid_name)
        
        # --- Assert ---
        # Mock calls
        mock_validate.assert_called_once_with(invalid_name)
        mock_client.create_collection.assert_not_called() # Should fail before calling client
        
        # Assert error result using helper
        assert_error_result(result, f"Validation Error: {validation_error_message}")

    @pytest.mark.asyncio
    async def test_create_collection_with_custom_metadata(self, mock_chroma_client_collections):
        """Test creating a collection with custom metadata provided."""
        mock_client, _, mock_validate = mock_chroma_client_collections
        collection_name = "custom_meta_coll"
        custom_metadata_input = {"hnsw:space": "ip", "custom_field": "value1"}
        mock_collection_id = str(uuid.uuid4())
        
        # Mock the collection returned by create_collection
        created_collection_mock = MagicMock()
        created_collection_mock.name = collection_name
        created_collection_mock.id = mock_collection_id
        # Metadata stored internally might be slightly different if flattened
        created_collection_mock.metadata = custom_metadata_input 
        created_collection_mock.count.return_value = 0
        mock_peek_result = {"ids": [], "documents": [], "metadatas": None, "embeddings": None}
        created_collection_mock.peek.return_value = mock_peek_result
        mock_client.create_collection.return_value = created_collection_mock

        # --- Act ---
        result = await _create_collection_impl(collection_name=collection_name, metadata=custom_metadata_input)

        # --- Assert ---
        # Mock calls
        mock_validate.assert_called_once_with(collection_name)
        mock_client.create_collection.assert_called_once()
        call_args = mock_client.create_collection.call_args
        assert call_args.kwargs["name"] == collection_name
        # Verify the custom metadata was passed to create_collection
        assert call_args.kwargs["metadata"] == custom_metadata_input
        assert call_args.kwargs["get_or_create"] is False
        
        # Result structure and content assertions using helper
        result_data = assert_successful_json_result(result)
        # Verify the result reflects the custom metadata (after reconstruction)
        assert result_data.get("name") == collection_name
        assert result_data.get("id") == mock_collection_id
        assert "metadata" in result_data
        # Use the helper to ensure reconstruction logic is matched
        assert result_data["metadata"] == _reconstruct_metadata(custom_metadata_input)
        assert result_data["metadata"].get("settings", {}).get("hnsw:space") == "ip"
        assert result_data["metadata"].get("custom_field") == "value1"
        assert result_data.get("count") == 0

    @pytest.mark.asyncio
    async def test_create_collection_chroma_duplicate_error(self, mock_chroma_client_collections):
        """Test handling of ChromaDB duplicate error during creation."""
        mock_client, _, mock_validate = mock_chroma_client_collections
        collection_name = "test_duplicate"
        # Mock the client call to raise the specific error
        mock_client.create_collection.side_effect = ValueError(f"Collection {collection_name} already exists.")
        
        # --- Act ---
        result = await _create_collection_impl(collection_name=collection_name)
        
        # --- Assert ---
        # Mock calls
        mock_validate.assert_called_once_with(collection_name)
        mock_client.create_collection.assert_called_once_with(name=collection_name, metadata=ANY, embedding_function=ANY, get_or_create=False)
        
        # Assert error result using helper
        assert_error_result(result, f"Tool Error: Collection '{collection_name}' already exists.")

    @pytest.mark.asyncio
    async def test_create_collection_unexpected_error(self, mock_chroma_client_collections):
        """Test handling of unexpected error during creation."""
        mock_client, _, mock_validate = mock_chroma_client_collections
        collection_name = "test_unexpected"
        error_message = "Something broke badly"
        mock_client.create_collection.side_effect = Exception(error_message)

        # --- Act ---
        # No longer raises McpError, returns CallToolResult
        # with pytest.raises(McpError) as exc_info:
        #     await _create_collection_impl(collection_name=collection_name)
        result = await _create_collection_impl(collection_name=collection_name)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.create_collection.assert_called_once()
        # Assert error result using helper
        assert_error_result(result, f"Tool Error: An unexpected error occurred while creating collection '{collection_name}'. Details: {error_message}")
        # Optional: Check logs if needed, but the result check is primary

    # --- _peek_collection_impl Tests ---
    @pytest.mark.asyncio
    async def test_peek_collection_success(self, mock_chroma_client_collections):
        """Test successful peeking into a collection."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        collection_name = "test_peek_exists"
        limit = 3
        expected_peek_result = {
            "ids": ["id1", "id2", "id3"],
            "documents": ["doc1", "doc2", "doc3"],
            "metadatas": [{"m": 1}, {"m": 2}, {"m": 3}],
            "embeddings": None # Assuming embeddings are not included by default peek
        }
        
        # Configure get_collection mock
        mock_client.get_collection.return_value = mock_collection
        # Configure the collection's peek method
        mock_collection.peek.return_value = expected_peek_result
        
        # --- Act ---
        result = await _peek_collection_impl(collection_name=collection_name, limit=limit)
        
        # --- Assert ---
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.peek.assert_called_once_with(limit=limit)
        
        # Assert result using helper, comparing directly with expected dict
        assert_successful_json_result(result, expected_peek_result)

    # --- _list_collections_impl Tests ---
    @pytest.mark.asyncio
    async def test_list_collections_success(self, mock_chroma_client_collections):
        """Test successful default collection listing."""
        mock_client, _, _ = mock_chroma_client_collections
        # Simulate the return value from the actual Chroma client method
        mock_collection_a = MagicMock()
        mock_collection_a.name = "coll_a"
        mock_collection_b = MagicMock()
        mock_collection_b.name = "coll_b"
        mock_client.list_collections.return_value = [mock_collection_a, mock_collection_b]

        # --- Act ---
        # Call with default args (limit=0, offset=0, name_contains="")
        result = await _list_collections_impl(limit=0, offset=0, name_contains="")

        # --- Assert ---
        mock_client.list_collections.assert_called_once()

        # Assert result structure and content using helper
        result_data = assert_successful_json_result(result)
        assert result_data.get("collection_names") == ["coll_a", "coll_b"]
        assert result_data.get("total_count") == 2
        assert result_data.get("limit") == 0
        assert result_data.get("offset") == 0

    @pytest.mark.asyncio
    async def test_list_collections_with_filter_pagination(self, mock_chroma_client_collections):
        """Test listing with name filter and pagination."""
        mock_client, _, _ = mock_chroma_client_collections
        # Simulate Chroma client return with MagicMock objects having a 'name' attribute
        collections_data = ["apple", "banana", "apricot", "avocado"]
        mock_collections = [MagicMock(spec=['name']) for _ in collections_data]
        for mock_coll, name_val in zip(mock_collections, collections_data):
            mock_coll.name = name_val # Set the name attribute directly

        mock_client.list_collections.return_value = mock_collections

        # --- Act ---
        result = await _list_collections_impl(limit=2, offset=1, name_contains="ap")

        # --- Assert ---
        mock_client.list_collections.assert_called_once()

        # Assert result structure and content using helper
        result_data = assert_successful_json_result(result)
        # Filtering happens *after* list_collections in the _impl
        # The mock returns all, the filter selects ["apple", "apricot"]
        # Offset 1 skips "apple", limit 2 takes "apricot"
        assert result_data.get("collection_names") == ["apricot"]
        assert result_data.get("total_count") == 2 # Total matching filter "ap"
        assert result_data.get("limit") == 2
        assert result_data.get("offset") == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "limit, offset, expected_error_msg",
        [
            (-1, 0, "Validation Error: limit cannot be negative"),
            (0, -1, "Validation Error: offset cannot be negative"),
        ],
        ids=["negative_limit", "negative_offset"]
    )
    async def test_list_collections_validation_error(self, mock_chroma_client_collections, limit, offset, expected_error_msg):
        """Test validation errors for list parameters are handled in _impl."""
        result = await _list_collections_impl(limit=limit, offset=offset, name_contains="")
        assert_error_result(result, expected_error_msg)

    # --- _get_collection_impl Tests ---
    @pytest.mark.asyncio
    async def test_get_collection_success(self, mock_chroma_client_collections):
        """Test getting existing collection info."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        collection_name = "my_coll"
        mock_collection_id = "test-id-123"
        mock_metadata = {"description": "test desc", "chroma:setting:hnsw_space": "l2"}
        mock_count = 42
        mock_peek = {"ids": ["p1"], "documents": ["peek doc"]}
        
        # Configure the mock collection returned by get_collection
        mock_collection.name = collection_name
        mock_collection.id = mock_collection_id
        mock_collection.metadata = mock_metadata
        mock_collection.count.return_value = mock_count
        mock_collection.peek.return_value = mock_peek
        mock_client.get_collection.return_value = mock_collection
        
        # --- Act ---
        result = await _get_collection_impl(collection_name)
        
        # --- Assert ---
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.count.assert_called_once()
        mock_collection.peek.assert_called_once_with(limit=5) # Check limit used in _impl
        
        # Assert result structure and content using helper
        result_data = assert_successful_json_result(result)
        assert result_data.get("name") == collection_name
        assert result_data.get("id") == mock_collection_id
        assert result_data.get("count") == mock_count
        # Assert reconstructed metadata
        assert result_data.get("metadata") == _reconstruct_metadata(mock_metadata)
        assert result_data.get("sample_entries") == mock_peek

    @pytest.mark.asyncio
    async def test_get_collection_not_found(self, mock_chroma_client_collections):
        """Test getting a non-existent collection (handled in impl)."""
        mock_client, _, _ = mock_chroma_client_collections
        collection_name = "not_found_coll"
        error_message = f"Collection {collection_name} does not exist."
        mock_client.get_collection.side_effect = ValueError(error_message) 
        
        # --- Act ---
        result = await _get_collection_impl(collection_name)
        
        # --- Assert ---
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        
        # Assert error result using helper
        assert_error_result(result, f"ChromaDB Error: Collection '{collection_name}' not found.")

    @pytest.mark.asyncio
    async def test_get_collection_unexpected_error(self, mock_chroma_client_collections):
        """Test handling of unexpected error during get collection."""
        mock_client, _, _ = mock_chroma_client_collections
        collection_name = "test_unexpected_get"
        error_message = "Connection failed"
        mock_client.get_collection.side_effect = Exception(error_message)

        # --- Act ---
        # No longer raises McpError
        # with pytest.raises(McpError) as exc_info:
        #     await _get_collection_impl(collection_name=collection_name)
        result = await _get_collection_impl(collection_name=collection_name)

        # --- Assert ---
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        assert_error_result(result, f"Tool Error: An unexpected error occurred while getting collection '{collection_name}'. Details: {error_message}")

    # --- _set_collection_description_impl Tests ---
    @pytest.mark.asyncio
    async def test_set_collection_description_success(self, mock_chroma_client_collections):
        """Test setting a collection description successfully."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        collection_name = "desc_coll"
        new_description = "A new description"
        
        mock_peek_result = {"ids": ["id1"], "documents": ["doc1"], "metadatas": None, "embeddings": None}

        # Configure mocks for DIFFERENT return values on get_collection
        initial_collection_mock = MagicMock(name="initial_collection")
        initial_collection_mock.name = collection_name
        initial_collection_mock.id = "desc-id"
        initial_collection_mock.metadata = {"custom_key": "value"} # State BEFORE update

        final_collection_mock = MagicMock(name="final_collection")
        final_collection_mock.name = collection_name
        final_collection_mock.id = "desc-id"
        # Simulate the metadata *after* the description is set
        final_collection_mock.metadata = {"custom_key": "value", "description": new_description} # State AFTER update
        final_collection_mock.count.return_value = 5
        final_collection_mock.peek.return_value = mock_peek_result

        # Make get_collection return the initial mock first, then the final mock
        mock_client.get_collection.side_effect = [initial_collection_mock, final_collection_mock]

        # --- Act ---
        result = await _set_collection_description_impl(collection_name, new_description)

        # --- Assert ---
        # Check get_collection was called twice (once inside set, once by the return call)
        assert mock_client.get_collection.call_count == 2
        # Check the modify call
        expected_metadata_for_modify = {"description": new_description} # Modify is called on the initial mock
        initial_collection_mock.modify.assert_called_once_with(metadata=expected_metadata_for_modify)

        # Check count/peek called by the final get (these are called by _get_collection_impl)
        final_collection_mock.count.assert_called_once()
        final_collection_mock.peek.assert_called_once_with(limit=5)
        
        # Assert result structure (should be the result of _get_collection_impl)
        assert isinstance(result, types.CallToolResult)
        assert result.isError is False
        assert len(result.content) == 1
        assert isinstance(result.content[0], types.TextContent)

        # Assert result structure and content using helper
        result_data = assert_successful_json_result(result)
        # Assertions on the returned data (reflecting the state *after* update)
        assert result_data.get("name") == collection_name
        assert result_data.get("id") == "desc-id"
        # Metadata should now include the description and original custom key
        # Assert directly against the expected final reconstructed metadata
        assert "metadata" in result_data
        final_metadata = result_data["metadata"]
        assert final_metadata.get("description") == new_description
        assert final_metadata.get("custom_key") == "value" # Original metadata preserved in final state
        assert result_data.get("count") == 5
        assert result_data.get("sample_entries") == mock_peek_result

    @pytest.mark.asyncio
    async def test_set_collection_description_not_found(self, mock_chroma_client_collections):
        """Test setting description when the collection doesn't exist."""
        mock_client, _, _ = mock_chroma_client_collections
        collection_name = "nonexistent_set_desc"
        error_message = f"Collection {collection_name} does not exist."
        mock_client.get_collection.side_effect = ValueError(error_message)
        
        # --- Act ---
        result = await _set_collection_description_impl(collection_name, "some desc")

        # --- Assert ---
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        
        # Assert error result using helper
        assert_error_result(result, f"Tool Error: Collection '{collection_name}' not found.")
        
    @pytest.mark.asyncio
    async def test_set_collection_description_immutable(self, mock_chroma_client_collections):
        """Test setting description fails if immutable settings exist."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        collection_name = "immutable_coll"
        # Simulate metadata with an immutable key
        mock_collection.metadata = {"hnsw:space": "cosine", "other": "data"}
        mock_client.get_collection.return_value = mock_collection
        
        # --- Act ---
        result = await _set_collection_description_impl(collection_name, "new desc")
        
        # --- Assert ---
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.modify.assert_not_called() # Modify should not be called
        
        # Assert error result using helper
        assert_error_result(result, "Cannot set description on collections with existing immutable settings")

    @pytest.mark.asyncio
    async def test_set_collection_description_unexpected_error(self, mock_chroma_client_collections):
        """Test handling of unexpected error during set description."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        collection_name = "test_desc_unexpected"
        description = "new desc"
        error_message = "Network timeout"
        mock_collection.modify.side_effect = Exception(error_message)

        # --- Act ---
        # No longer raises McpError
        # with pytest.raises(McpError) as exc_info:
        #     await _set_collection_description_impl(collection_name=collection_name, description=description)
        result = await _set_collection_description_impl(collection_name=collection_name, description=description)

        # --- Assert ---
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.modify.assert_called_once_with(metadata={**mock_collection.metadata, 'description': description})
        assert_error_result(result, f"Tool Error: An unexpected error occurred while setting description for '{collection_name}'. Details: {error_message}")

    # --- _set_collection_settings_impl Tests ---
    @pytest.mark.asyncio
    async def test_set_collection_settings_success(self, mock_chroma_client_collections):
        """Test setting collection settings successfully."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        collection_name = "settings_coll"
        new_settings = {"hnsw:space": "l2", "hnsw:construction_ef": 200}
        
        # Configure get_collection mock - This needs the same multi-return pattern
        mock_collection.name = collection_name
        mock_collection.id = "settings-id"
        # Simulate metadata *before* update (e.g., with a description)
        mock_collection.metadata = {"description": "Original Desc"} 
        mock_client.get_collection.return_value = mock_collection
        # Mock count/peek for the final get
        mock_collection.count.return_value = 10
        mock_peek_result = {"ids": ["s1"], "documents": ["s doc"], "metadatas": None, "embeddings": None}
        mock_collection.peek.return_value = mock_peek_result

        # Configure mocks for DIFFERENT return values on get_collection
        initial_collection_mock = MagicMock(name="initial_collection_settings")
        initial_collection_mock.name = collection_name
        initial_collection_mock.id = "settings-id"
        initial_collection_mock.metadata = {"description": "Original Desc"} # State BEFORE update

        final_collection_mock = MagicMock(name="final_collection_settings")
        final_collection_mock.name = collection_name
        final_collection_mock.id = "settings-id"
        # Simulate the metadata *after* the settings are applied (includes flattened keys)
        final_collection_mock.metadata = {"description": "Original Desc", "chroma:setting:hnsw_space": "l2", "chroma:setting:hnsw_construction_ef": 200} # State AFTER update
        final_collection_mock.count.return_value = 10
        final_collection_mock.peek.return_value = mock_peek_result

        mock_client.get_collection.side_effect = [initial_collection_mock, final_collection_mock]

        # --- Act ---
        result = await _set_collection_settings_impl(collection_name, new_settings)

        # --- Assert ---
        assert mock_client.get_collection.call_count == 2
        # Check modify call with flattened and prefixed keys, preserving description
        expected_metadata_for_modify = {
            "description": "Original Desc", # Preserved
            "chroma:setting:hnsw_space": "l2",
            "chroma:setting:hnsw_construction_ef": 200
        }
        initial_collection_mock.modify.assert_called_once_with(metadata=expected_metadata_for_modify)

        # Check count/peek called by the final get
        final_collection_mock.count.assert_called_once()
        final_collection_mock.peek.assert_called_once_with(limit=5)
        
        # Assert result structure (from _get_collection_impl)
        assert isinstance(result, types.CallToolResult)
        assert result.isError is False
        assert len(result.content) == 1
        assert isinstance(result.content[0], types.TextContent)

        # Assert result structure and content using helper
        result_data = assert_successful_json_result(result)
        # Assertions on the returned data (state *after* update)
        assert result_data.get("name") == collection_name
        assert result_data.get("id") == "settings-id"
        # Metadata should reflect the new settings and preserved description
        # Assert directly against the expected final reconstructed metadata
        assert "metadata" in result_data
        final_metadata = result_data["metadata"]
        assert final_metadata.get("description") == "Original Desc" # Preserved
        assert "settings" in final_metadata
        final_settings = final_metadata["settings"]
        assert final_settings.get("hnsw:space") == "l2"
        assert final_settings.get("hnsw:construction:ef") == 200 # Use colon key for reconstructed settings
        assert result_data.get("count") == 10
        assert result_data.get("sample_entries") == mock_peek_result
        
    @pytest.mark.asyncio
    async def test_set_collection_settings_invalid_type(self, mock_chroma_client_collections):
        """Test setting settings with invalid input type."""
        # --- Act ---
        result = await _set_collection_settings_impl("any_coll", settings="not_a_dict")
        
        # --- Assert ---
        assert_error_result(result, "Tool Error: settings parameter must be a dictionary.")

    @pytest.mark.asyncio
    async def test_set_collection_settings_not_found(self, mock_chroma_client_collections):
        """Test setting settings when the collection doesn't exist."""
        mock_client, _, _ = mock_chroma_client_collections
        collection_name = "nonexistent_set_settings"
        error_message = f"Collection {collection_name} does not exist."
        mock_client.get_collection.side_effect = ValueError(error_message)
        
        # --- Act ---
        result = await _set_collection_settings_impl(collection_name, {"hnsw:space": "l2"})

        # --- Assert ---
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        assert_error_result(result, f"Tool Error: Collection '{collection_name}' not found.")

    @pytest.mark.asyncio
    async def test_set_collection_settings_immutable(self, mock_chroma_client_collections):
        """Test setting settings fails if immutable settings exist."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        collection_name = "immutable_settings_coll"
        mock_collection.metadata = {"hnsw:space": "cosine"} # Existing immutable
        mock_client.get_collection.return_value = mock_collection
        
        # --- Act ---
        result = await _set_collection_settings_impl(collection_name, {"hnsw:construction_ef": 50})
        
        # --- Assert ---
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.modify.assert_not_called()
        
        assert_error_result(result, "Cannot set settings on collections with existing immutable settings")

    @pytest.mark.asyncio
    async def test_set_collection_settings_unexpected_error(self, mock_chroma_client_collections):
        """Test handling of unexpected error during set settings."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        collection_name = "test_settings_unexpected"
        settings = {"hnsw:ef_construction": 200}
        error_message = "Disk full"
        mock_collection.modify.side_effect = Exception(error_message)

        # --- Act ---
        # No longer raises McpError
        # with pytest.raises(McpError) as exc_info:
        #     await _set_collection_settings_impl(collection_name=collection_name, settings=settings)
        result = await _set_collection_settings_impl(collection_name=collection_name, settings=settings)

        # --- Assert ---
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        # Construct expected metadata for modify call using FLATTENED key
        expected_metadata_for_modify = {**mock_collection.metadata, f"chroma:setting:{list(settings.keys())[0].replace(':', '_')}": list(settings.values())[0]}
        # Note: This assumes only one setting key for simplicity in the test.
        # A more robust test might iterate through settings dict if multiple keys were involved.
        mock_collection.modify.assert_called_once_with(metadata=expected_metadata_for_modify)
        assert_error_result(result, f"Tool Error: An unexpected error occurred while setting settings for '{collection_name}'. Details: {error_message}")

    # --- _update_collection_metadata_impl Tests ---
    @pytest.mark.asyncio
    async def test_update_collection_metadata_success(self, mock_chroma_client_collections):
        """Test updating collection metadata successfully."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        collection_name = "update_meta_coll"
        metadata_update = {"user_key": "new_value", "another": 123}

        # Configure get_collection mock - needs multi-return pattern
        mock_collection.name = collection_name
        mock_collection.id = "update-id"
        initial_metadata = {"description": "Keep me", "user_key": "old_value", "chroma:setting:hnsw_space": "l1"} # Include a setting
        mock_collection.metadata = initial_metadata.copy() # Remove this line later
        mock_client.get_collection.return_value = mock_collection # Remove this line later
        mock_collection.count.return_value = 1
        mock_peek_result = {"ids": ["u1"], "documents": ["u doc"], "metadatas": None, "embeddings": None}
        mock_collection.peek.return_value = mock_peek_result

        # Configure mocks for DIFFERENT return values on get_collection
        initial_collection_mock = MagicMock(name="initial_collection_meta")
        initial_collection_mock.name = collection_name
        initial_collection_mock.id = "update-id"
        initial_collection_mock.metadata = initial_metadata.copy() # State BEFORE update

        final_collection_mock = MagicMock(name="final_collection_meta")
        final_collection_mock.name = collection_name
        final_collection_mock.id = "update-id"
        # Simulate the metadata *after* the update (includes merged keys and preserved settings/desc)
        final_collection_mock.metadata = {"description": "Keep me", "chroma:setting:hnsw_space": "l1", "user_key": "new_value", "another": 123} # State AFTER update
        final_collection_mock.count.return_value = 1
        final_collection_mock.peek.return_value = mock_peek_result

        mock_client.get_collection.side_effect = [initial_collection_mock, final_collection_mock]

        # --- Act ---
        result = await _update_collection_metadata_impl(collection_name, metadata_update)

        # --- Assert ---
        assert mock_client.get_collection.call_count == 2
        # Check modify call with merged metadata (settings and description preserved)
        expected_metadata_for_modify = {
            "description": "Keep me",
            "chroma:setting:hnsw_space": "l1",
            "user_key": "new_value", # Updated
            "another": 123 # Added
        }
        initial_collection_mock.modify.assert_called_once_with(metadata=expected_metadata_for_modify)

        # Check count/peek called by the final get
        final_collection_mock.count.assert_called_once()
        final_collection_mock.peek.assert_called_once_with(limit=5)

        # Assert result structure (from _get_collection_impl)
        assert isinstance(result, types.CallToolResult)
        assert result.isError is False
        assert len(result.content) == 1
        assert isinstance(result.content[0], types.TextContent)

        # Assert result structure and content using helper
        result_data = assert_successful_json_result(result)
        # Assertions on the returned data (state *after* update)
        assert result_data.get("name") == collection_name
        assert result_data.get("id") == "update-id"
        # Assert directly against the expected final reconstructed metadata
        assert "metadata" in result_data
        final_metadata = result_data["metadata"]
        assert final_metadata.get("description") == "Keep me" # Preserved
        assert "settings" in final_metadata
        assert final_metadata["settings"].get("hnsw:space") == "l1" # Preserved setting
        assert final_metadata.get("user_key") == "new_value" # Updated
        assert final_metadata.get("another") == 123 # Added
        assert result_data.get("count") == 1
        assert result_data.get("sample_entries") == mock_peek_result

    @pytest.mark.asyncio
    async def test_update_collection_metadata_invalid_type(self, mock_chroma_client_collections):
        """Test updating metadata with invalid input type."""
        # --- Act ---
        result = await _update_collection_metadata_impl("any_coll", metadata_update="not_a_dict")

        # --- Assert ---
        assert_error_result(result, "Tool Error: metadata_update parameter must be a dictionary.")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("reserved_key_update", [
        {"description": "new desc"},
        {"settings": {"hnsw:x": 1}},
        {"chroma:setting:abc": "xyz"},
        {"hnsw:space": "l2"},
        {"user_key": "ok", "description": "bad"} # Mix
    ],
    ids=[
        "description_key", 
        "settings_key", 
        "chroma_setting_prefix",
        "hnsw_setting_prefix", 
        "mixed_keys"
    ])
    async def test_update_collection_metadata_reserved_keys(self, mock_chroma_client_collections, reserved_key_update):
        """Test updating metadata fails if reserved keys are included."""
        result = await _update_collection_metadata_impl("any_coll", metadata_update=reserved_key_update)
        assert_error_result(result, "Cannot update reserved keys")

    @pytest.mark.asyncio
    async def test_update_collection_metadata_not_found(self, mock_chroma_client_collections):
        """Test updating metadata when the collection doesn't exist."""
        mock_client, _, _ = mock_chroma_client_collections
        collection_name = "nonexistent_update_meta"
        error_message = f"Collection {collection_name} does not exist."
        mock_client.get_collection.side_effect = ValueError(error_message)

        # --- Act ---
        result = await _update_collection_metadata_impl(collection_name, {"user_key": "val"})

        # --- Assert ---
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        assert_error_result(result, f"Tool Error: Collection '{collection_name}' not found.")

    @pytest.mark.asyncio
    async def test_update_collection_metadata_immutable(self, mock_chroma_client_collections):
        """Test updating metadata fails if immutable settings exist (redundant check)."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        collection_name = "immutable_update_meta_coll"
        mock_collection.metadata = {"hnsw:space": "cosine"} # Existing immutable
        mock_client.get_collection.return_value = mock_collection

        # --- Act ---
        # Attempting to update a non-reserved key should still fail because hnsw:* exists
        result = await _update_collection_metadata_impl(collection_name, {"user_key": "new"})

        # --- Assert ---
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.modify.assert_not_called()

        # Assert error result using helper
        # Check message (could be the reserved key message or the immutable settings message depending on impl order)
        # We need to check for either error message possibility
        assert isinstance(result, types.CallToolResult)
        assert result.isError is True
        assert ("Cannot update reserved keys" in result.content[0].text or
                "Cannot update metadata on collections with existing immutable settings" in result.content[0].text)

    @pytest.mark.asyncio
    async def test_update_collection_metadata_unexpected_error(self, mock_chroma_client_collections):
        """Test handling of unexpected error during update metadata."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        collection_name = "test_meta_unexpected"
        metadata_update = {"user_key": "updated"}
        error_message = "Database corruption"
        mock_collection.modify.side_effect = Exception(error_message)

        # --- Act ---
        # No longer raises McpError
        # with pytest.raises(McpError) as exc_info:
        #     await _update_collection_metadata_impl(collection_name=collection_name, metadata_update=metadata_update)
        result = await _update_collection_metadata_impl(collection_name=collection_name, metadata_update=metadata_update)

        # --- Assert ---
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        expected_metadata = {**mock_collection.metadata, **metadata_update} # Combine existing and update
        mock_collection.modify.assert_called_once_with(metadata=expected_metadata)
        assert_error_result(result, f"Tool Error: An unexpected error occurred while updating metadata for '{collection_name}'. Details: {error_message}")

    # --- _rename_collection_impl Tests ---
    @pytest.mark.asyncio
    async def test_rename_collection_success(self, mock_chroma_client_collections):
        """Test renaming a collection successfully."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_collections
        original_name = "rename_me"
        new_name = "renamed_coll"
        mock_id = "rename-id"
        mock_meta = {"info": "data"}
        mock_count_after = 3
        mock_peek_after = {"ids": ["r1"], "documents": ["r doc"]}

        # Mock initial get for original name
        mock_collection.name = original_name
        mock_collection.id = mock_id
        mock_collection.metadata = mock_meta.copy()

        # Mock the collection object state *after* rename for the final get call
        # Simulate the behavior of _get_collection_impl which calls client.get_collection
        renamed_mock = MagicMock()
        renamed_mock.name = new_name
        renamed_mock.id = mock_id
        renamed_mock.metadata = mock_meta.copy()
        renamed_mock.count.return_value = mock_count_after
        renamed_mock.peek.return_value = mock_peek_after

        # Configure get_collection side effect: first return original, then renamed
        mock_client.get_collection.side_effect = [mock_collection, renamed_mock]
        mock_collection.modify.reset_mock() # Reset modify mock from fixture

        # --- Act ---
        result = await _rename_collection_impl(original_name, new_name)

        # --- Assert ---
        mock_validate.assert_called_once_with(new_name)
        # Check get_collection was called twice
        assert mock_client.get_collection.call_count == 2
        # Check the calls: first for original, second for new name (by _get_collection_impl)
        mock_client.get_collection.assert_has_calls([
            call(name=original_name, embedding_function=ANY),
            call(name=new_name, embedding_function=ANY)
        ])
        mock_collection.modify.assert_called_once_with(name=new_name)

        # Assert result structure (from final _get_collection_impl call)
        assert isinstance(result, types.CallToolResult)
        assert result.isError is False
        assert len(result.content) == 1
        assert isinstance(result.content[0], types.TextContent)

        # Assert result structure and content using helper
        result_data = assert_successful_json_result(result)
        assert result_data.get("name") == new_name
        assert result_data.get("id") == mock_id
        assert result_data.get("metadata") == _reconstruct_metadata(mock_meta)
        assert result_data.get("count") == mock_count_after
        assert result_data.get("sample_entries") == mock_peek_after

    @pytest.mark.asyncio
    async def test_rename_collection_invalid_new_name(self, mock_chroma_client_collections):
        """Test renaming with an invalid new name."""
        _, _, mock_validate = mock_chroma_client_collections
        original_name = "rename_me_fail"
        invalid_new_name = "new@name!"
        validation_error_message = f"Invalid new collection name: {invalid_new_name}"
        mock_validate.side_effect = ValidationError(validation_error_message)
        
        # --- Act ---
        result = await _rename_collection_impl(original_name, invalid_new_name)
        
        # --- Assert ---
        mock_validate.assert_called_once_with(invalid_new_name)
        assert_error_result(result, f"Validation Error: Invalid new collection name '{invalid_new_name}'")

    @pytest.mark.asyncio
    async def test_rename_collection_original_not_found(self, mock_chroma_client_collections):
        """Test renaming when the original collection doesn't exist."""
        mock_client, _, mock_validate = mock_chroma_client_collections
        original_name = "original_not_exist"
        new_name = "valid_new_name"
        error_message = f"Collection {original_name} does not exist."
        # Mock get_collection to fail on the *first* call
        mock_client.get_collection.side_effect = ValueError(error_message)
        
        # --- Act ---
        result = await _rename_collection_impl(original_name, new_name)
        
        # --- Assert ---
        mock_validate.assert_called_once_with(new_name) # Validation still runs
        mock_client.get_collection.assert_called_once_with(name=original_name, embedding_function=ANY)
        assert_error_result(result, f"Tool Error: Original collection '{original_name}' not found.")

    @pytest.mark.asyncio
    async def test_rename_collection_new_name_exists(self, mock_chroma_client_collections):
        """Test renaming when the new name already exists."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_collections
        original_name = "rename_me_again"
        new_name = "already_exists"
        # Mock initial get success
        mock_client.get_collection.return_value = mock_collection
        # Mock modify call failure (simulating new_name exists)
        error_message = f"Collection with name {new_name} already exists."
        mock_collection.modify.side_effect = ValueError(error_message)
        
        # --- Act ---
        result = await _rename_collection_impl(original_name, new_name)
        
        # --- Assert ---
        mock_validate.assert_called_once_with(new_name)
        mock_client.get_collection.assert_called_once_with(name=original_name, embedding_function=ANY)
        mock_collection.modify.assert_called_once_with(name=new_name)
        assert_error_result(result, f"ChromaDB Error: Cannot rename to '{new_name}' because a collection with that name already exists.")

    @pytest.mark.asyncio
    async def test_rename_collection_unexpected_error(self, mock_chroma_client_collections):
        """Test handling of unexpected error during rename."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_collections
        collection_name = "test_rename_unexpected"
        new_name = "new_unexpected_name"
        error_message = "Filesystem error"
        mock_collection.modify.side_effect = Exception(error_message)

        # --- Act ---
        # No longer raises McpError
        # with pytest.raises(McpError) as exc_info:
        #     await _rename_collection_impl(collection_name=collection_name, new_name=new_name)
        result = await _rename_collection_impl(collection_name=collection_name, new_name=new_name)

        # --- Assert ---
        mock_validate.assert_called_once_with(new_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.modify.assert_called_once_with(name=new_name)
        assert_error_result(result, f"Tool Error: An unexpected error occurred while renaming collection '{collection_name}'. Details: {error_message}")

    # --- _delete_collection_impl Tests ---
    @pytest.mark.asyncio
    async def test_delete_collection_success(self, mock_chroma_client_collections):
        """Test deleting a collection successfully."""
        mock_client, _, _ = mock_chroma_client_collections
        collection_name = "delete_me"
        # Mock delete_collection to not raise error
        mock_client.delete_collection.return_value = None 
        
        # --- Act ---
        result = await _delete_collection_impl(collection_name)
        
        # --- Assert ---
        mock_client.delete_collection.assert_called_once_with(name=collection_name)
        
        assert_successful_json_result(result)
        assert result.content[0].text == '{"status": "deleted", "collection_name": "delete_me"}'

    @pytest.mark.asyncio
    async def test_delete_collection_not_found(self, mock_chroma_client_collections):
        """Test deleting a non-existent collection."""
        mock_client, _, _ = mock_chroma_client_collections
        collection_name = "not_found_delete"
        # Simulate Chroma raising ValueError for not found
        error_message = f"Collection {collection_name} not found."
        mock_client.delete_collection.side_effect = ValueError(error_message)

        # --- Act ---
        result = await _delete_collection_impl(collection_name)

        # --- Assert ---
        mock_client.delete_collection.assert_called_once_with(name=collection_name)

        assert_error_result(result, f"Tool Error: Collection '{collection_name}' not found, cannot delete.")

    @pytest.mark.asyncio
    async def test_delete_collection_unexpected_error(self, mock_chroma_client_collections):
        """Test handling of unexpected error during delete."""
        mock_client, _, _ = mock_chroma_client_collections
        collection_name = "test_delete_unexpected"
        error_message = "Authentication failed"
        mock_client.delete_collection.side_effect = Exception(error_message)

        # --- Act ---
        # No longer raises McpError
        # with pytest.raises(McpError) as exc_info:
        #     await _delete_collection_impl(collection_name=collection_name)
        result = await _delete_collection_impl(collection_name=collection_name)

        # --- Assert ---
        mock_client.delete_collection.assert_called_once_with(name=collection_name)
        assert_error_result(result, f"Tool Error: An unexpected error occurred while deleting collection '{collection_name}'. Details: {error_message}")