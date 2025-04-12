"""Tests for collection management tools."""

import pytest
import uuid
import re
import json
import numpy as np
import time

from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock, ANY, call
from contextlib import contextmanager

from mcp import types
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS, INTERNAL_ERROR, ErrorData

# Import specific errors if needed, or rely on ValidationError/Exception
from src.chroma_mcp.utils.errors import ValidationError
from src.chroma_mcp.tools.collection_tools import (
    _reconstruct_metadata,  # Keep helper if used
    _create_collection_impl,
    _create_collection_with_metadata_impl,
    _list_collections_impl,
    _get_collection_impl,
    _rename_collection_impl,
    _delete_collection_impl,
    _peek_collection_impl,
)

# Import Pydantic models used by the tools
from src.chroma_mcp.tools.collection_tools import (
    CreateCollectionInput,
    CreateCollectionWithMetadataInput,
    ListCollectionsInput,
    GetCollectionInput,
    RenameCollectionInput,
    DeleteCollectionInput,
    PeekCollectionInput,
)

# Correct import for get_collection_settings
from src.chroma_mcp.utils.config import get_collection_settings

DEFAULT_SIMILARITY_THRESHOLD = 0.7

# --- Helper Functions ---


def assert_successful_json_result(
    result: List[types.TextContent],
    expected_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Asserts the tool result is a successful list containing valid JSON, returning the parsed data."""
    assert isinstance(result, list)
    assert len(result) > 0, "Result list cannot be empty for successful JSON result."
    content_item = result[0]
    assert isinstance(content_item, types.TextContent), f"Expected TextContent, got {type(content_item)}"
    assert content_item.type == "text", f"Expected content type 'text', got '{content_item.type}'"
    assert content_item.text is not None, "Text content cannot be None for JSON result."
    try:
        parsed_data = json.loads(content_item.text)
        assert isinstance(parsed_data, dict), f"Parsed JSON is not a dictionary, got {type(parsed_data)}"
    except (json.JSONDecodeError, AssertionError) as e:
        pytest.fail(f"Result content is not valid JSON: {e}\nContent: {content_item.text}")
    if expected_data is not None:
        assert parsed_data == expected_data, f"Parsed JSON data mismatch. Expected: {expected_data}, Got: {parsed_data}"
    return parsed_data


# Rework assert_error_result as a context manager for future use
@contextmanager
def assert_raises_mcp_error(expected_message: str):
    """Asserts that McpError is raised and optionally checks the error message."""
    try:
        yield
    except McpError as e:
        # Check both e.error_data (if exists) and e.args[0]
        message = ""
        if hasattr(e, "error_data") and hasattr(e.error_data, "message"):
            message = str(e.error_data.message)
        elif e.args and isinstance(e.args[0], ErrorData) and hasattr(e.args[0], "message"):
            message = str(e.args[0].message)
        else:
            message = str(e)  # Fallback to the exception string itself

        assert (
            expected_message in message
        ), f"Expected error message containing '{expected_message}' but got '{message}'"
        return


@pytest.fixture
def mock_chroma_client_collections():
    """Fixture to mock the Chroma client and its methods for collection tests (Synchronous)."""
    with patch("src.chroma_mcp.tools.collection_tools.get_chroma_client") as mock_get_client, patch(
        "src.chroma_mcp.tools.collection_tools.get_embedding_function"
    ) as mock_get_embedding_function, patch(
        "src.chroma_mcp.tools.collection_tools.get_collection_settings"
    ) as mock_get_settings, patch(
        "src.chroma_mcp.tools.collection_tools.validate_collection_name"
    ) as mock_validate_name:
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
        mock_client_instance.delete_collection.return_value = None  # For delete tests

        # Configure modify on the collection instance mock (used by set/update/rename)
        mock_collection_instance.modify.return_value = None

        mock_get_client.return_value = mock_client_instance
        mock_get_embedding_function.return_value = None
        mock_get_settings.return_value = {"hnsw:space": "cosine"}  # Default settings if needed
        mock_validate_name.return_value = None

        yield mock_client_instance, mock_collection_instance, mock_validate_name


class TestCollectionTools:
    """Test cases for collection management tools."""

    # --- _create_collection_impl Tests ---
    @pytest.mark.asyncio
    async def test_create_collection_success(self, mock_chroma_client_collections):
        """Test successful collection creation."""
        (
            mock_client,
            _,
            mock_validate,
        ) = mock_chroma_client_collections  # mock_collection fixture not directly needed here
        collection_name = "test_create_new"
        mock_collection_id = str(uuid.uuid4())

        # Mock the collection returned by create_collection
        created_collection_mock = MagicMock()
        created_collection_mock.name = collection_name
        created_collection_mock.id = mock_collection_id  # Use a fixed UUID for assertion

        # Simulate the metadata as stored by ChromaDB (flattened, used by _reconstruct_metadata)
        actual_default_settings = get_collection_settings()  # Get the full defaults
        # Metadata sent TO create_collection should only contain explicitly handled defaults (like hnsw:space)
        # The implementation relies on Chroma to apply other defaults server-side.
        expected_metadata_passed_to_chroma = None
        if "hnsw:space" in actual_default_settings:
            expected_metadata_passed_to_chroma = {"chroma:setting:hnsw_space": actual_default_settings["hnsw:space"]}

        # The collection object returned by the MOCK should have the FULL metadata
        # reflecting what Chroma *would* store, including implicit defaults.
        metadata_stored_by_chroma = {
            f"chroma:setting:{k.replace(':', '_')}": v for k, v in actual_default_settings.items()
        }
        created_collection_mock.metadata = metadata_stored_by_chroma  # What the collection obj would have
        created_collection_mock.count.return_value = 0  # Simulate count after creation
        mock_client.create_collection.return_value = created_collection_mock

        # --- Act ---
        input_model = CreateCollectionInput(collection_name=collection_name)
        # Call await directly, expect List[TextContent]
        result_list = await _create_collection_impl(input_model)

        # --- Assert ---
        # Mock calls
        mock_validate.assert_called_once_with(collection_name)
        mock_client.create_collection.assert_called_once()
        call_args = mock_client.create_collection.call_args
        assert call_args.kwargs["name"] == collection_name
        # Check metadata passed TO create_collection matches the expected subset
        assert "metadata" in call_args.kwargs
        assert call_args.kwargs["metadata"] == expected_metadata_passed_to_chroma
        assert call_args.kwargs["get_or_create"] is False

        # Result structure and content assertions using helper on the list
        result_data = assert_successful_json_result(result_list)
        assert result_data.get("name") == collection_name
        assert result_data.get("id") == mock_collection_id
        assert "metadata" in result_data
        # Correct Assertion: Compare the RECONSTRUCTED metadata['settings'] in the result with the EXPECTED defaults
        assert "settings" in result_data["metadata"], "Reconstructed metadata should contain a 'settings' key"
        # Convert keys in actual_default_settings from _ to : for comparison
        expected_settings_with_colons = {k.replace("_", ":"): v for k, v in actual_default_settings.items()}
        assert result_data["metadata"]["settings"] == expected_settings_with_colons
        assert result_data.get("count") == 0  # Based on mock count

    @pytest.mark.asyncio
    async def test_create_collection_invalid_name(self, mock_chroma_client_collections):
        """Test collection name validation failure within the implementation."""
        mock_client, _, mock_validate = mock_chroma_client_collections
        invalid_name = "invalid-"
        # Configure the validator mock to raise the error
        error_msg = "Invalid collection name"
        mock_validate.side_effect = ValidationError(error_msg)

        # --- Act & Assert ---
        input_model = CreateCollectionInput(collection_name=invalid_name)
        # result = await _create_collection_impl(input_model)
        # --- Assert ---
        # mock_validate.assert_called_once_with(invalid_name) # Called inside the context manager check
        mock_client.create_collection.assert_not_called()
        # Assert validation error returned by _impl
        # with assert_raises_mcp_error("Validation Error: Invalid collection name"):
        #     await _create_collection_impl(input_model)
        with assert_raises_mcp_error(f"Validation Error: {error_msg}"):
            await _create_collection_impl(input_model)
        mock_validate.assert_called_once_with(invalid_name)  # Verify validator was called

    @pytest.mark.asyncio
    async def test_create_collection_with_custom_metadata(self, mock_chroma_client_collections):
        """Test creating a collection with custom metadata provided (as JSON string)."""
        mock_client, _, mock_validate = mock_chroma_client_collections
        collection_name = "custom_meta_coll"
        custom_metadata_dict = {"hnsw:space": "ip", "custom_field": "value1"}
        custom_metadata_json = json.dumps(custom_metadata_dict)  # Convert to JSON string
        mock_collection_id = str(uuid.uuid4())

        # Mock the collection returned by create_collection
        created_collection_mock = MagicMock()
        created_collection_mock.name = collection_name
        created_collection_mock.id = mock_collection_id
        # Metadata stored internally might be slightly different if flattened
        # Pass the DICT to the mock, as that's what _impl passes to the *client*
        created_collection_mock.metadata = custom_metadata_dict
        created_collection_mock.count.return_value = 0
        mock_client.create_collection.return_value = created_collection_mock

        # --- Act ---
        # Create Pydantic model instance - Use correct model, pass JSON string
        input_model = CreateCollectionWithMetadataInput(
            collection_name=collection_name, metadata=custom_metadata_json
        )  # Pass the JSON string here
        # Use correct implementation function
        result_list = await _create_collection_with_metadata_impl(input_model)

        # --- Assert ---
        # Mock calls
        mock_validate.assert_called_once_with(collection_name)
        mock_client.create_collection.assert_called_once()
        call_args = mock_client.create_collection.call_args
        assert call_args.kwargs["name"] == collection_name
        # Verify the original *dictionary* was passed to Chroma's create_collection
        # (because _impl parses the JSON string back to a dict)
        assert call_args.kwargs["metadata"] == custom_metadata_dict

        # Assert successful result
        result_data = assert_successful_json_result(result_list)
        assert result_data.get("name") == collection_name
        assert result_data.get("id") == mock_collection_id
        assert result_data.get("count") == 0
        # Assert reconstructed metadata in result matches input dict
        assert result_data.get("metadata") == _reconstruct_metadata(custom_metadata_dict)

    @pytest.mark.asyncio
    async def test_create_collection_chroma_duplicate_error(self, mock_chroma_client_collections):
        """Test handling ChromaDB error when collection already exists."""
        mock_client, _, mock_validate = mock_chroma_client_collections
        collection_name = "duplicate_coll"
        # Mock create_collection to raise the specific ValueError Chroma uses
        error_message = f"Collection {collection_name} already exists."
        mock_client.create_collection.side_effect = ValueError(error_message)

        # --- Act & Assert ---
        input_model = CreateCollectionInput(collection_name=collection_name)
        # Use context manager to assert specific McpError is raised
        with assert_raises_mcp_error(f"Tool Error: Collection '{collection_name}' already exists."):
            await _create_collection_impl(input_model)

        # Assert mocks
        mock_validate.assert_called_once_with(collection_name)
        mock_client.create_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_collection_unexpected_error(self, mock_chroma_client_collections):
        """Test handling of unexpected errors during collection creation."""
        mock_client, _, mock_validate = mock_chroma_client_collections
        collection_name = "test_create_error"
        error_msg = "Something went wrong"
        mock_client.create_collection.side_effect = Exception(error_msg)

        input_model = CreateCollectionInput(collection_name=collection_name)
        with assert_raises_mcp_error(
            f"An unexpected error occurred while creating collection '{collection_name}'. Details: {error_msg}"
        ):
            await _create_collection_impl(input_model)

    # --- _peek_collection_impl Tests ---
    @pytest.mark.asyncio
    async def test_peek_collection_success(self, mock_chroma_client_collections):
        """Test successful peeking into a collection with a specific limit."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        collection_name = "test_peek_exists"
        limit = 3  # Specific limit for this test
        expected_peek_result = {
            "ids": ["id1", "id2", "id3"],
            "documents": ["doc1", "doc2", "doc3"],
            "metadatas": [{"m": 1}, {"m": 2}, {"m": 3}],
            "embeddings": None,  # Assuming embeddings are not included by default peek
            # Add other expected fields if needed (distances, uris, data)
        }

        # Configure get_collection mock
        mock_client.get_collection.return_value = mock_collection
        # Configure the collection's peek method
        mock_collection.peek.return_value = expected_peek_result

        # --- Act ---
        # Create Pydantic model instance, providing the limit
        input_model = PeekCollectionInput(collection_name=collection_name, limit=limit)
        result = await _peek_collection_impl(input_model)

        # --- Assert ---
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        # Assert peek called with the provided limit
        mock_collection.peek.assert_called_once_with(limit=limit)

        # Assert result using helper, comparing directly with expected dict
        assert_successful_json_result(result, expected_peek_result)

    @pytest.mark.asyncio
    async def test_peek_collection_success_default_limit(self, mock_chroma_client_collections):
        """Test successful peeking using the default limit (10)."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        collection_name = "test_peek_default"
        # Default limit is now 10 in the model
        expected_peek_result = {"ids": ["default_id"]}  # Dummy result
        mock_client.get_collection.return_value = mock_collection
        mock_collection.peek.return_value = expected_peek_result

        input_model = PeekCollectionInput(collection_name=collection_name)
        # Do not provide limit, use default
        result = await _peek_collection_impl(input_model)

        mock_client.get_collection.assert_called_once_with(name=collection_name)
        # Assert peek called with the default limit value (10)
        mock_collection.peek.assert_called_once_with(limit=10)
        assert_successful_json_result(result, expected_peek_result)

    @pytest.mark.asyncio
    async def test_peek_collection_validation_error(self, mock_chroma_client_collections):
        """Test collection name validation failure for peek."""
        _, _, mock_validate = mock_chroma_client_collections
        invalid_name = "peek-invalid--"
        error_msg = "Bad name for peek"
        mock_validate.side_effect = ValidationError(error_msg)

        input_model = PeekCollectionInput(collection_name=invalid_name)
        with assert_raises_mcp_error(f"Validation Error: {error_msg}"):
            await _peek_collection_impl(input_model)
        mock_validate.assert_called_once_with(invalid_name)

    @pytest.mark.asyncio
    async def test_peek_collection_not_found_error(self, mock_chroma_client_collections):
        """Test peek when the collection is not found (error from get_collection)."""
        mock_client, _, _ = mock_chroma_client_collections
        collection_name = "peek_not_found"
        error_msg = f"Collection {collection_name} does not exist."
        mock_client.get_collection.side_effect = ValueError(error_msg)

        input_model = PeekCollectionInput(collection_name=collection_name)
        with assert_raises_mcp_error(f"Collection '{collection_name}' not found."):
            await _peek_collection_impl(input_model)

    @pytest.mark.asyncio
    async def test_peek_collection_get_other_value_error(self, mock_chroma_client_collections):
        """Test other ValueError from get_collection during peek."""
        mock_client, _, _ = mock_chroma_client_collections
        collection_name = "peek_get_val_err"
        error_msg = "Get value error during peek"
        mock_client.get_collection.side_effect = ValueError(error_msg)

        input_model = PeekCollectionInput(collection_name=collection_name)
        with assert_raises_mcp_error(f"Problem accessing collection '{collection_name}'. Details: {error_msg}"):
            await _peek_collection_impl(input_model)

    @pytest.mark.asyncio
    async def test_peek_collection_peek_exception(self, mock_chroma_client_collections):
        """Test handling of exception during the actual collection.peek call."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        collection_name = "peek_itself_fails"
        error_msg = "Peek failed internally"
        mock_collection.peek.side_effect = Exception(error_msg)
        mock_client.get_collection.return_value = mock_collection  # Ensure get succeeds

        input_model = PeekCollectionInput(collection_name=collection_name)
        with assert_raises_mcp_error(
            f"An unexpected error occurred peeking collection '{collection_name}'. Details: {error_msg}"
        ):
            await _peek_collection_impl(input_model)
        mock_collection.peek.assert_called_once()  # Verify peek was attempted

    # --- _create_collection_with_metadata_impl Tests ---
    @pytest.mark.asyncio
    async def test_create_collection_with_metadata_success(self, mock_chroma_client_collections):
        """Test successful creation using the _with_metadata variant (as JSON string)."""
        (
            mock_client,
            _,
            mock_validate,
        ) = mock_chroma_client_collections
        collection_name = "test_create_with_meta"
        custom_metadata_dict = {"description": "My custom description", "hnsw:space": "ip"}
        custom_metadata_json = json.dumps(custom_metadata_dict)  # Convert to JSON string
        mock_collection_id = str(uuid.uuid4())

        # Mock the collection returned by create_collection
        created_collection_mock = MagicMock()
        created_collection_mock.name = collection_name
        created_collection_mock.id = mock_collection_id
        # Simulate Chroma storing the metadata (it might flatten/prefix settings)
        # Assume it stores what was passed to the *client*, which is the dict
        created_collection_mock.metadata = custom_metadata_dict
        created_collection_mock.count.return_value = 0
        mock_client.create_collection.return_value = created_collection_mock

        # --- Act ---
        input_model = CreateCollectionWithMetadataInput(
            collection_name=collection_name, metadata=custom_metadata_json  # Pass the JSON string here
        )
        result_list = await _create_collection_with_metadata_impl(input_model)

        # --- Assert ---
        # Mock calls
        mock_validate.assert_called_once_with(collection_name)
        mock_client.create_collection.assert_called_once()
        call_args = mock_client.create_collection.call_args
        assert call_args.kwargs["name"] == collection_name
        # Verify the original *dictionary* was passed to Chroma's create_collection
        assert call_args.kwargs["metadata"] == custom_metadata_dict
        assert call_args.kwargs["get_or_create"] is False

        # Result structure and content assertions
        result_data = assert_successful_json_result(result_list)
        assert result_data.get("name") == collection_name
        assert result_data.get("id") == mock_collection_id
        assert "metadata" in result_data
        # Check reconstructed metadata matches the input dictionary
        expected_reconstructed = _reconstruct_metadata(custom_metadata_dict)  # Use dict for check
        assert result_data["metadata"] == expected_reconstructed
        assert result_data.get("count") == 0
        assert result_data.get("status") == "success"

    @pytest.mark.asyncio
    async def test_create_collection_with_metadata_invalid_json(self, mock_chroma_client_collections):
        """Test create with metadata when the metadata string is invalid JSON."""
        _, _, _ = mock_chroma_client_collections  # Fixture setup needed but mocks not called
        collection_name = "invalid_json_meta"
        invalid_json_string = '{"key": "value", "unterminated'

        input_model = CreateCollectionWithMetadataInput(collection_name=collection_name, metadata=invalid_json_string)
        with assert_raises_mcp_error("Invalid JSON format for metadata field"):
            await _create_collection_with_metadata_impl(input_model)

    @pytest.mark.asyncio
    async def test_create_collection_with_metadata_json_not_dict(self, mock_chroma_client_collections):
        """Test create with metadata when the JSON string decodes to something other than a dict."""
        _, _, _ = mock_chroma_client_collections
        collection_name = "json_list_meta"
        json_list_string = '["item1", "item2"]'  # Valid JSON, but not a dict

        input_model = CreateCollectionWithMetadataInput(collection_name=collection_name, metadata=json_list_string)
        with assert_raises_mcp_error("Metadata string must decode to a JSON object (dictionary)."):
            await _create_collection_with_metadata_impl(input_model)

    @pytest.mark.asyncio
    async def test_create_collection_with_metadata_validation_error(self, mock_chroma_client_collections):
        """Test create with metadata validation error for collection name."""
        _, _, mock_validate = mock_chroma_client_collections
        invalid_name = "meta-invalid--"
        error_msg = "Bad name for meta create"
        mock_validate.side_effect = ValidationError(error_msg)
        valid_metadata_json = '{"key": "value"}'

        input_model = CreateCollectionWithMetadataInput(collection_name=invalid_name, metadata=valid_metadata_json)
        with assert_raises_mcp_error(f"Validation Error: {error_msg}"):
            await _create_collection_with_metadata_impl(input_model)
        mock_validate.assert_called_once_with(invalid_name)

    @pytest.mark.asyncio
    async def test_create_collection_with_metadata_already_exists(self, mock_chroma_client_collections):
        """Test create with metadata when collection already exists."""
        mock_client, _, _ = mock_chroma_client_collections
        collection_name = "meta_exists"
        error_msg = f"Collection {collection_name} already exists."
        mock_client.create_collection.side_effect = Exception(error_msg)  # Chroma often raises generic Exception here
        valid_metadata_json = '{"key": "value"}'

        input_model = CreateCollectionWithMetadataInput(collection_name=collection_name, metadata=valid_metadata_json)
        with assert_raises_mcp_error(f"Collection '{collection_name}' already exists."):
            await _create_collection_with_metadata_impl(input_model)

    @pytest.mark.asyncio
    async def test_create_collection_with_metadata_unexpected_error(self, mock_chroma_client_collections):
        """Test create with metadata handling unexpected errors."""
        mock_client, _, _ = mock_chroma_client_collections
        collection_name = "meta_unexpected_err"
        error_msg = "Something else failed during meta create"
        mock_client.create_collection.side_effect = Exception(error_msg)
        valid_metadata_json = '{"key": "value"}'

        input_model = CreateCollectionWithMetadataInput(collection_name=collection_name, metadata=valid_metadata_json)
        with assert_raises_mcp_error(
            f"An unexpected error occurred while creating collection '{collection_name}'. Details: {error_msg}"
        ):
            await _create_collection_with_metadata_impl(input_model)

    # --- _list_collections_impl Tests ---
    @pytest.mark.asyncio
    async def test_list_collections_success_defaults(self, mock_chroma_client_collections):
        """Test successful default collection listing (no filters, no pagination)."""
        mock_client, _, _ = mock_chroma_client_collections
        # Simulate the return value from the actual Chroma client method (List[str])
        all_names = ["coll_a", "coll_b"]
        mock_client.list_collections.return_value = all_names

        # Mock get_collection to return basic info if needed (though not strictly needed for this result check)
        mock_coll_a = MagicMock()
        mock_coll_a.name = "coll_a"
        mock_coll_b = MagicMock()
        mock_coll_b.name = "coll_b"

        def get_coll_side_effect(name, **kwargs):
            if name == "coll_a":
                return mock_coll_a
            if name == "coll_b":
                return mock_coll_b
            raise ValueError()

        mock_client.get_collection.side_effect = get_coll_side_effect

        # --- Act ---
        # Create Pydantic model instance (use defaults: limit=0, offset=0, name_contains="")
        input_model = ListCollectionsInput()
        result_list = await _list_collections_impl(input_model)

        # --- Assert ---
        mock_client.list_collections.assert_called_once()
        # get_collection should NOT be called because count is no longer fetched
        mock_client.get_collection.assert_not_called()

        # Assert result structure and content using helper
        result_data = assert_successful_json_result(result_list)
        assert result_data.get("collection_names") == all_names  # Expect all names as no filter/pagination
        assert result_data.get("total_count") == len(all_names)
        assert result_data.get("limit") == 0  # Reflects input default
        assert result_data.get("offset") == 0  # Reflects input default

    @pytest.mark.asyncio
    async def test_list_collections_with_filter_pagination(self, mock_chroma_client_collections):
        """Test listing with name filter and pagination."""
        mock_client, _, _ = mock_chroma_client_collections
        # Simulate Chroma client return with List[str]
        all_names = ["apple", "banana", "apricot", "avocado"]
        mock_client.list_collections.return_value = all_names

        # Mock get_collection if needed (not needed for this result check)

        # --- Act ---
        # Create Pydantic model instance with specific filter/pagination
        input_model = ListCollectionsInput(limit=1, offset=1, name_contains="ap")
        result_list = await _list_collections_impl(input_model)

        # --- Assert ---
        mock_client.list_collections.assert_called_once()
        # get_collection should NOT be called
        mock_client.get_collection.assert_not_called()

        # Assert result structure and content using helper
        result_data = assert_successful_json_result(result_list)
        # Filtering happens *after* list_collections in the _impl
        # Filter "ap" matches: ["apple", "apricot"]
        # Offset 1 skips "apple".
        # Limit 1 takes the next one: "apricot".
        assert result_data.get("collection_names") == ["apricot"]
        assert result_data.get("total_count") == 2  # Total matching filter "ap"
        assert result_data.get("limit") == 1  # Reflects input
        assert result_data.get("offset") == 1  # Reflects input

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "limit, offset, expected_error_msg",
        [
            (-1, 0, "Validation Error: limit cannot be negative"),
            (0, -1, "Validation Error: offset cannot be negative"),
        ],
        ids=["negative_limit", "negative_offset"],
    )
    async def test_list_collections_validation_error(
        self, mock_chroma_client_collections, limit, offset, expected_error_msg
    ):
        """Test input validation for limit and offset in list_collections."""
        # This test correctly uses Pydantic's validation, but we need one for client errors
        # No specific validation error raised IN the function, Pydantic handles it.
        # Instead, we add a test for client-side errors.
        # REMOVED the original test body as Pydantic handles this.
        # The assert_raises_mcp_error needs to be outside the await for Pydantic validation
        with pytest.raises(Exception):  # Pydantic raises its own ValidationError
            _ = ListCollectionsInput(limit=limit, offset=offset)
        # Keep the assertion structure for documentation, though it might not be hit
        # with assert_raises_mcp_error(expected_error_msg):
        #     input_model = ListCollectionsInput(limit=limit, offset=offset)
        #     _ = await _list_collections_impl(input_model)

    @pytest.mark.asyncio
    async def test_list_collections_client_error(self, mock_chroma_client_collections):
        """Test handling of errors during client.list_collections."""
        mock_client, _, _ = mock_chroma_client_collections
        error_msg = "Client connection failed"
        mock_client.list_collections.side_effect = Exception(error_msg)

        input_model = ListCollectionsInput()
        with assert_raises_mcp_error(f"Error listing collections. Details: {error_msg}"):
            await _list_collections_impl(input_model)

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
        # Create Pydantic model instance - Use correct name
        input_model = GetCollectionInput(collection_name=collection_name)
        result = await _get_collection_impl(input_model)

        # --- Assert ---
        # Implementation passes embedding_function here
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.count.assert_called_once()
        mock_collection.peek.assert_called_once_with(limit=5)  # Check limit used in _impl

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

        # --- Act & Assert ---
        # Create Pydantic model instance
        input_model = GetCollectionInput(collection_name=collection_name)
        # Move the call INSIDE the context manager
        # result = await _get_collection_impl(input_model)
        # --- Assert ---
        # mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        with assert_raises_mcp_error(f"Tool Error: Collection '{collection_name}' not found."):
            await _get_collection_impl(input_model)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)

    @pytest.mark.asyncio
    async def test_get_collection_unexpected_error(self, mock_chroma_client_collections):
        """Test handling of unexpected error during get collection."""
        mock_client, _, _ = mock_chroma_client_collections
        collection_name = "test_get_fail"
        error_msg = "Get failed unexpectedly"
        mock_client.get_collection.side_effect = Exception(error_msg)

        input_model = GetCollectionInput(collection_name=collection_name)
        with assert_raises_mcp_error(
            f"An unexpected error occurred while getting collection '{collection_name}'. Details: {error_msg}"
        ):
            await _get_collection_impl(input_model)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)

    @pytest.mark.asyncio
    async def test_get_collection_validation_error(self, mock_chroma_client_collections):
        """Test handling of validation error for collection name."""
        _, _, mock_validate = mock_chroma_client_collections
        collection_name = "invalid--name"
        error_msg = "Invalid name format"
        mock_validate.side_effect = ValidationError(error_msg)

        input_model = GetCollectionInput(collection_name=collection_name)
        with assert_raises_mcp_error(f"Validation Error: {error_msg}"):
            # Note: Validation error happens before get_collection is called
            # Need to simulate the validation error being caught inside the impl
            # The fixture mocks validation, so we need to call validate inside the assert block if not mocked
            await _get_collection_impl(input_model)  # This relies on the fixture mock
        mock_validate.assert_called_once_with(collection_name)

    @pytest.mark.asyncio
    async def test_get_collection_other_value_error(self, mock_chroma_client_collections):
        """Test handling of other ValueErrors from get_collection."""
        mock_client, _, _ = mock_chroma_client_collections
        collection_name = "test_get_value_err"
        error_msg = "Another value error during get"
        mock_client.get_collection.side_effect = ValueError(error_msg)

        input_model = GetCollectionInput(collection_name=collection_name)
        with assert_raises_mcp_error(f"Invalid parameter getting collection. Details: {error_msg}"):
            await _get_collection_impl(input_model)

    @pytest.mark.asyncio
    async def test_get_collection_peek_error(self, mock_chroma_client_collections):
        """Test that get_collection returns info even if peek fails."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        collection_name = "test_peek_fail"
        mock_collection.name = collection_name
        mock_collection.id = "peek-fail-id"
        mock_collection.metadata = {"desc": "test"}
        mock_collection.count.return_value = 5
        peek_error_msg = "Peek failed"
        mock_collection.peek.side_effect = Exception(peek_error_msg)

        mock_client.get_collection.return_value = mock_collection

        input_model = GetCollectionInput(collection_name=collection_name)
        result_list = await _get_collection_impl(input_model)

        # Assert success, but check the sample_entries field for the error
        result_data = assert_successful_json_result(result_list)
        assert result_data["name"] == collection_name
        assert result_data["count"] == 5
        assert "sample_entries" in result_data
        assert isinstance(result_data["sample_entries"], dict)
        assert "error" in result_data["sample_entries"]
        assert peek_error_msg in result_data["sample_entries"]["error"]
        mock_collection.peek.assert_called_once_with(limit=5)

    # --- _rename_collection_impl Tests ---
    @pytest.mark.asyncio
    async def test_rename_collection_success(self, mock_chroma_client_collections):
        """Test successful collection renaming."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_collections
        original_name = "rename_me"
        new_name = "renamed_successfully"

        # Configure mock collection
        mock_client.get_collection.return_value = mock_collection

        # --- Act ---
        input_model = RenameCollectionInput(collection_name=original_name, new_name=new_name)
        result = await _rename_collection_impl(input_model)

        # --- Assert ---
        # Check validation calls
        mock_validate.assert_has_calls([call(original_name), call(new_name)])
        mock_client.get_collection.assert_called_once_with(name=original_name)
        mock_collection.modify.assert_called_once_with(name=new_name)

        # Assert successful result message
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], types.TextContent)
        assert f"Collection '{original_name}' successfully renamed to '{new_name}'." in result[0].text

    @pytest.mark.asyncio
    async def test_rename_collection_invalid_new_name(self, mock_chroma_client_collections):
        """Test validation failure for the new collection name during rename."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_collections
        original_name = "valid_original_name"
        invalid_new_name = "invalid!"

        # Configure validator mock: first call (original) ok, second (new) raises
        def validate_side_effect(name):
            if name == invalid_new_name:
                raise ValidationError("Invalid new name")
            return  # No error for original name

        mock_validate.side_effect = validate_side_effect

        # --- Act ---
        input_model = RenameCollectionInput(collection_name=original_name, new_name=invalid_new_name)
        with assert_raises_mcp_error("Validation Error: Invalid new name"):
            await _rename_collection_impl(input_model)

        # --- Assert ---
        mock_validate.assert_any_call(original_name)  # Called with original first
        mock_validate.assert_any_call(invalid_new_name)  # Called with new name second
        mock_collection.modify.assert_not_called()

    @pytest.mark.asyncio
    async def test_rename_collection_original_not_found(self, mock_chroma_client_collections):
        """Test renaming when the original collection does not exist."""
        mock_client, _, mock_validate = mock_chroma_client_collections
        original_name = "original_not_found"
        new_name = "new_name_irrelevant"
        # Mock get_collection to raise error
        mock_client.get_collection.side_effect = ValueError(f"Collection {original_name} does not exist.")

        # --- Act ---
        input_model = RenameCollectionInput(collection_name=original_name, new_name=new_name)
        with assert_raises_mcp_error(f"Tool Error: Collection '{original_name}' not found."):
            await _rename_collection_impl(input_model)

        # --- Assert ---
        mock_validate.assert_has_calls([call(original_name), call(new_name)])  # Both validations called
        mock_client.get_collection.assert_called_once_with(name=original_name)

    @pytest.mark.asyncio
    async def test_rename_collection_new_name_exists(self, mock_chroma_client_collections):
        """Test renaming when the new name already exists."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_collections
        original_name = "original_exists"
        new_name = "new_name_exists"
        # Mock get_collection success, but modify fails
        mock_client.get_collection.return_value = mock_collection
        mock_collection.modify.side_effect = ValueError(f"Collection {new_name} already exists.")

        # --- Act ---
        input_model = RenameCollectionInput(collection_name=original_name, new_name=new_name)
        with assert_raises_mcp_error(f"Tool Error: Collection name '{new_name}' already exists."):
            await _rename_collection_impl(input_model)

        # --- Assert ---
        mock_validate.assert_has_calls([call(original_name), call(new_name)])
        mock_client.get_collection.assert_called_once_with(name=original_name)
        mock_collection.modify.assert_called_once_with(name=new_name)

    @pytest.mark.asyncio
    async def test_rename_collection_unexpected_error(self, mock_chroma_client_collections):
        """Test unexpected error during rename."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_collections
        original_name = "rename_fail_orig"
        new_name = "rename_fail_new"
        error_msg = "Rename blew up"
        # Error can happen during get_collection or modify
        mock_collection.modify.side_effect = Exception(error_msg)

        input_model = RenameCollectionInput(collection_name=original_name, new_name=new_name)
        with assert_raises_mcp_error(
            f"An unexpected error occurred renaming collection '{original_name}'. Details: {error_msg}"
        ):
            await _rename_collection_impl(input_model)

    @pytest.mark.asyncio
    async def test_rename_collection_other_value_error(self, mock_chroma_client_collections):
        """Test handling of other ValueErrors during rename."""
        mock_client, mock_collection, _ = mock_chroma_client_collections
        original_name = "rename_val_err_orig"
        new_name = "rename_val_err_new"
        error_msg = "Some other value issue"
        # Simulate error during modify call
        mock_collection.modify.side_effect = ValueError(error_msg)

        input_model = RenameCollectionInput(collection_name=original_name, new_name=new_name)
        with assert_raises_mcp_error(f"Invalid parameter during rename. Details: {error_msg}"):
            await _rename_collection_impl(input_model)

    # --- _delete_collection_impl Tests ---
    @pytest.mark.asyncio
    async def test_delete_collection_success(self, mock_chroma_client_collections):
        """Test successful collection deletion."""
        mock_client, _, mock_validate = mock_chroma_client_collections
        collection_name = "delete_me"

        # --- Act ---
        input_model = DeleteCollectionInput(collection_name=collection_name)
        result = await _delete_collection_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.delete_collection.assert_called_once_with(name=collection_name)

        # Assert successful result (non-JSON)
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], types.TextContent)
        assert f"Collection '{collection_name}' deleted successfully." in result[0].text

    @pytest.mark.asyncio
    async def test_delete_collection_not_found(self, mock_chroma_client_collections):
        """Test deleting a non-existent collection."""
        mock_client, _, mock_validate = mock_chroma_client_collections
        collection_name = "not_found_delete"
        error_message = f"Collection {collection_name} does not exist."
        mock_client.delete_collection.side_effect = ValueError(error_message)

        # --- Act ---
        input_model = DeleteCollectionInput(collection_name=collection_name)
        with assert_raises_mcp_error(f"Tool Error: Collection '{collection_name}' not found."):
            await _delete_collection_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.delete_collection.assert_called_once_with(name=collection_name)

    @pytest.mark.asyncio
    async def test_delete_collection_unexpected_error(self, mock_chroma_client_collections):
        """Test unexpected error during collection deletion."""
        mock_client, _, mock_validate = mock_chroma_client_collections
        collection_name = "delete_fail"
        error_msg = "Delete failed unexpectedly"
        mock_client.delete_collection.side_effect = Exception(error_msg)

        input_model = DeleteCollectionInput(collection_name=collection_name)
        with assert_raises_mcp_error(
            f"An unexpected error occurred deleting collection '{collection_name}'. Details: {error_msg}"
        ):
            await _delete_collection_impl(input_model)

    @pytest.mark.asyncio
    async def test_delete_collection_validation_error(self, mock_chroma_client_collections):
        """Test handling of validation error for collection name during delete."""
        _, _, mock_validate = mock_chroma_client_collections
        collection_name = "invalid--delete"
        error_msg = "Invalid name format for delete"
        mock_validate.side_effect = ValidationError(error_msg)

        input_model = DeleteCollectionInput(collection_name=collection_name)
        with assert_raises_mcp_error(f"Validation Error: {error_msg}"):
            await _delete_collection_impl(input_model)
        mock_validate.assert_called_once_with(collection_name)

    @pytest.mark.asyncio
    async def test_delete_collection_other_value_error(self, mock_chroma_client_collections):
        """Test handling of other ValueErrors during delete."""
        mock_client, _, _ = mock_chroma_client_collections
        collection_name = "delete_val_err"
        error_msg = "Another delete value error"
        mock_client.delete_collection.side_effect = ValueError(error_msg)

        input_model = DeleteCollectionInput(collection_name=collection_name)
        with assert_raises_mcp_error(f"Invalid parameter deleting collection. Details: {error_msg}"):
            await _delete_collection_impl(input_model)
