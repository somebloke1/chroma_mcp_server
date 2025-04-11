"""Tests for document management tools."""

import pytest
import uuid
import time  # Import time for ID generation check
import json
import re
import numpy as np

from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock, ANY, call, AsyncMock
from contextlib import contextmanager  # Import contextmanager

# Import CallToolResult and TextContent for helpers
from mcp import types
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS
from mcp.shared.exceptions import McpError

# Keep only ValidationError from errors module
from src.chroma_mcp.utils.errors import ValidationError
from src.chroma_mcp.tools import document_tools

# Import the implementation functions directly - Updated for variants
from src.chroma_mcp.tools.document_tools import (
    # Add variants (Singular)
    _add_document_impl,
    _add_document_with_id_impl,
    _add_document_with_metadata_impl,
    _add_document_with_id_and_metadata_impl,
    # Query variants (Keep multi)
    _query_documents_impl,
    _query_documents_with_where_filter_impl,
    _query_documents_with_document_filter_impl,
    # Get variants (Keep multi/filter)
    _get_documents_by_ids_impl,
    _get_documents_with_where_filter_impl,
    _get_documents_with_document_filter_impl,
    _get_all_documents_impl,
    # Update variants (Singular)
    _update_document_content_impl,
    _update_document_metadata_impl,
    # Delete variants (Singular ID only)
    _delete_document_by_id_impl,
)

# Import Pydantic models - Updated for variants
from src.chroma_mcp.tools.document_tools import (
    # Add variants (Singular)
    AddDocumentInput,
    AddDocumentWithIDInput,
    AddDocumentWithMetadataInput,
    AddDocumentWithIDAndMetadataInput,
    # Query variants (Keep multi/filter)
    QueryDocumentsInput,
    QueryDocumentsWithWhereFilterInput,
    QueryDocumentsWithDocumentFilterInput,
    # Get variants (Keep multi/filter)
    GetDocumentsByIdsInput,
    GetDocumentsWithWhereFilterInput,
    GetDocumentsWithDocumentFilterInput,
    GetAllDocumentsInput,
    # Update variants (Singular)
    UpdateDocumentContentInput,
    UpdateDocumentMetadataInput,
    # Delete variants (Singular ID only)
    DeleteDocumentByIdInput,
)

# Import Chroma exceptions used in mocking
from chromadb.errors import InvalidDimensionException  # No longer needed

# Import necessary helpers from utils
from src.chroma_mcp.utils.config import get_collection_settings  # Not used here
from src.chroma_mcp.utils import get_logger, get_chroma_client, get_embedding_function, ValidationError
from src.chroma_mcp.utils.config import validate_collection_name

DEFAULT_SIMILARITY_THRESHOLD = 0.7

# --- Helper Functions (Consider moving to a shared conftest.py) ---


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
        # Basic check: Ensure all keys in expected_data exist in parsed_data
        # More thorough checks might be needed depending on the tool
        for key in expected_data:
            assert key in parsed_data, f"Expected key '{key}' not found in result JSON"
            # Optionally add value comparison: assert parsed_data[key] == expected_data[key]
    return parsed_data


# Define the helper context manager for McpError
@contextmanager
def assert_raises_mcp_error(expected_error_substring: Optional[str] = None):
    """Asserts that McpError is raised and optionally checks the error message."""
    with pytest.raises(McpError) as exc_info:
        yield  # Code under test executes here

    # After the block, check the exception details
    error_message = str(exc_info.value)  # Use the string representation of the exception
    # print(f"DEBUG: Caught McpError message: {error_message}") # Keep commented out for now
    if expected_error_substring:
        assert (
            expected_error_substring.lower() in error_message.lower()
        ), f"Expected substring '{expected_error_substring}' not found in error message '{error_message}'"


# --- End Helper Functions ---


# Fixture to mock client and collection for document tools
@pytest.fixture
def mock_chroma_client_document():
    """Fixture to mock Chroma client, collection, and helpers for document tests."""
    with patch("src.chroma_mcp.tools.document_tools.get_chroma_client") as mock_get_client, patch(
        "src.chroma_mcp.tools.document_tools.get_embedding_function"
    ) as mock_get_embedding_function, patch(
        "src.chroma_mcp.tools.document_tools.validate_collection_name"
    ) as mock_validate_name:
        # Use AsyncMock for the client and collection methods if they are awaited
        # But the underlying Chroma client is synchronous, so MagicMock is appropriate
        mock_client_instance = MagicMock()
        mock_collection_instance = MagicMock(name="document_collection")  # Name for clarity

        # Configure default behaviors for collection methods
        mock_collection_instance.add.return_value = None  # add returns None
        mock_collection_instance.query.return_value = {  # Default empty query result
            "ids": [],
            "distances": [],
            "metadatas": [],
            "embeddings": [],
            "documents": [],
            "uris": [],
            "data": None,
        }
        mock_collection_instance.get.return_value = {  # Default empty get result
            "ids": [],
            "metadatas": [],
            "embeddings": [],
            "documents": [],
            "uris": [],
            "data": None,
        }
        mock_collection_instance.update.return_value = None  # update returns None
        mock_collection_instance.delete.return_value = []  # delete returns list of deleted IDs
        mock_collection_instance.count.return_value = 0  # Default count

        # Configure client methods
        mock_client_instance.get_collection.return_value = mock_collection_instance

        # Configure helper mocks
        mock_get_client.return_value = mock_client_instance
        mock_get_embedding_function.return_value = MagicMock(name="mock_embedding_function")
        mock_validate_name.return_value = None  # Assume valid name by default

        yield mock_client_instance, mock_collection_instance, mock_validate_name  # Yield validator too


class TestDocumentTools:
    """Test cases for document management tools."""

    # --- _add_documents_impl Tests ---
    @pytest.mark.asyncio
    async def test_add_document_success(self, mock_chroma_client_document):
        """Test successful document addition (auto-ID, no metadata)."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_add_success"
        document_to_add = "doc1"  # Singular

        # --- Act ---
        input_model = AddDocumentInput(collection_name=collection_name, document=document_to_add)
        # Mock add to capture generated ID
        generated_id_capture = None

        def capture_add(*args, **kwargs):
            nonlocal generated_id_capture
            generated_id_capture = kwargs.get("ids", [None])[0]
            return None

        mock_collection.add.side_effect = capture_add

        result = await _add_document_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        # Check add called with list of size 1
        mock_collection.add.assert_called_once_with(documents=[document_to_add], ids=ANY, metadatas=None)
        assert generated_id_capture is not None  # Ensure ID was captured
        assert_successful_json_result(result, {"added_id": generated_id_capture})

    @pytest.mark.asyncio
    async def test_add_document_increment_index(self, mock_chroma_client_document):
        """Test document addition respecting increment_index flag."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_add_increment"
        document_to_add = "doc_inc1"  # Singular

        # --- Act #
        # Test with increment_index=False (explicitly)
        input_model_false = AddDocumentInput(
            collection_name=collection_name, document=document_to_add, increment_index=False
        )
        await _add_document_impl(input_model_false)

        # --- Assert #
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        mock_collection.add.assert_called_once_with(documents=[document_to_add], ids=ANY, metadatas=None)

        # Reset mocks for next call
        mock_validate.reset_mock()
        mock_client.get_collection.reset_mock()
        mock_collection.add.reset_mock()

        # --- Act #
        # Test with increment_index=True (default)
        input_model_true = AddDocumentInput(collection_name=collection_name, document=document_to_add)
        await _add_document_impl(input_model_true)

        # --- Assert #
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        mock_collection.add.assert_called_once_with(documents=[document_to_add], ids=ANY, metadatas=None)

    @pytest.mark.asyncio
    async def test_add_document_collection_not_found(self, mock_chroma_client_document):
        """Test adding document to a non-existent collection."""
        mock_client, _, mock_validate = mock_chroma_client_document
        collection_name = "add_not_found"
        error_message = f"Collection {collection_name} does not exist."
        mock_client.get_collection.side_effect = ValueError(error_message)

        # --- Act & Assert ---
        input_model = AddDocumentInput(collection_name=collection_name, document="doc")
        with assert_raises_mcp_error(f"Collection '{collection_name}' not found."):
            await _add_document_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)

    @pytest.mark.asyncio
    async def test_add_document_chroma_error(self, mock_chroma_client_document):
        """Test handling errors during the actual Chroma add call."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "add_chroma_fail"
        error_message = "Chroma add failure"
        mock_client.get_collection.return_value = mock_collection
        mock_collection.add.side_effect = Exception(error_message)

        # --- Act & Assert ---
        input_model = AddDocumentInput(collection_name=collection_name, document="doc")
        with assert_raises_mcp_error(f"An unexpected error occurred: {error_message}"):
            await _add_document_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        mock_collection.add.assert_called_once()  # Verify add was attempted

    @pytest.mark.asyncio
    async def test_add_document_with_id_success(self, mock_chroma_client_document):
        """Test successful addition using AddDocumentWithIDInput (ID provided)."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_add_with_id"
        document_to_add = "doc_id1"  # Singular
        id_to_add = "id1"  # Singular

        # --- Act ---
        input_model = AddDocumentWithIDInput(collection_name=collection_name, document=document_to_add, id=id_to_add)
        result = await _add_document_with_id_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        # Assert add called with list of size 1
        mock_collection.add.assert_called_once_with(documents=[document_to_add], ids=[id_to_add], metadatas=None)
        # Assert result contains the provided ID
        assert_successful_json_result(result, {"added_id": id_to_add})

    @pytest.mark.asyncio
    async def test_add_document_with_id_no_increment(self, mock_chroma_client_document):
        """Test addition with ID and increment_index=False."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_add_with_id_noinc"
        document_to_add = "doc_id_noinc"  # Singular
        id_to_add = "id_noinc1"  # Singular

        # --- Act ---
        input_model = AddDocumentWithIDInput(
            collection_name=collection_name, document=document_to_add, id=id_to_add, increment_index=False
        )
        result = await _add_document_with_id_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        mock_collection.add.assert_called_once_with(documents=[document_to_add], ids=[id_to_add], metadatas=None)
        assert_successful_json_result(result, {"added_id": id_to_add})

    @pytest.mark.asyncio
    async def test_add_document_validation_no_doc_or_id(self, mock_chroma_client_document):
        """Test validation failure when document or ID is empty."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_add_valid_empties"

        # Test AddDocumentInput with empty document
        input_model_base = AddDocumentInput(collection_name=collection_name, document="")
        with assert_raises_mcp_error("Document content cannot be empty."):
            await _add_document_impl(input_model_base)

        # Test AddDocumentWithIDInput with empty document
        input_model_id_doc = AddDocumentWithIDInput(collection_name=collection_name, document="", id="some_id")
        with assert_raises_mcp_error("Document content cannot be empty."):
            await _add_document_with_id_impl(input_model_id_doc)

        # Test AddDocumentWithIDInput with empty ID
        input_model_id_id = AddDocumentWithIDInput(collection_name=collection_name, document="some_doc", id="")
        with assert_raises_mcp_error("Document ID cannot be empty."):
            await _add_document_with_id_impl(input_model_id_id)

        # Test AddDocumentWithMetadataInput with empty document
        input_model_meta_doc = AddDocumentWithMetadataInput(collection_name=collection_name, document="", metadata="{}")
        with assert_raises_mcp_error("Document content cannot be empty."):
            await _add_document_with_metadata_impl(input_model_meta_doc)

        # Test AddDocumentWithMetadataInput with empty metadata string
        input_model_meta_meta = AddDocumentWithMetadataInput(
            collection_name=collection_name, document="doc", metadata=""
        )
        with assert_raises_mcp_error("Metadata JSON string cannot be empty."):
            await _add_document_with_metadata_impl(input_model_meta_meta)

        # Test AddDocumentWithIDAndMetadataInput (empty doc, id, meta)
        input_full_doc = AddDocumentWithIDAndMetadataInput(
            collection_name=collection_name, document="", id="id", metadata="{}"
        )
        with assert_raises_mcp_error("Document content cannot be empty."):
            await _add_document_with_id_and_metadata_impl(input_full_doc)

        input_full_id = AddDocumentWithIDAndMetadataInput(
            collection_name=collection_name, document="doc", id="", metadata="{}"
        )
        with assert_raises_mcp_error("Document ID cannot be empty."):
            await _add_document_with_id_and_metadata_impl(input_full_id)

        input_full_meta = AddDocumentWithIDAndMetadataInput(
            collection_name=collection_name, document="doc", id="id", metadata=""
        )
        with assert_raises_mcp_error("Metadata JSON string cannot be empty."):
            await _add_document_with_id_and_metadata_impl(input_full_meta)

        # Ensure validation happened before client calls
        assert mock_validate.call_count > 0
        mock_client.get_collection.assert_not_called()
        mock_collection.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_document_with_metadata_success(self, mock_chroma_client_document):
        """Test successful addition using AddDocumentWithMetadataInput."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_add_with_meta"
        document_to_add = "doc_m1"  # Singular
        metadata_str = '{"key": "value1"}'  # Singular JSON string
        parsed_metadata = {"key": "value1"}  # Expected parsed dict

        # Mock add to capture generated ID
        generated_id_capture = None

        def capture_add(*args, **kwargs):
            nonlocal generated_id_capture
            generated_id_capture = kwargs.get("ids", [None])[0]
            return None

        mock_collection.add.side_effect = capture_add

        input_model = AddDocumentWithMetadataInput(
            collection_name=collection_name, document=document_to_add, metadata=metadata_str
        )
        result = await _add_document_with_metadata_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        # Assert add was called with the PARSED metadata and GENERATED IDs in lists
        mock_collection.add.assert_called_once_with(documents=[document_to_add], ids=ANY, metadatas=[parsed_metadata])
        assert generated_id_capture is not None
        assert_successful_json_result(result, {"added_id": generated_id_capture})

    @pytest.mark.asyncio
    async def test_add_document_with_id_and_metadata_success(self, mock_chroma_client_document):
        """Test successful addition using AddDocumentWithIDAndMetadataInput."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_add_full"
        document_to_add = "doc_f1"  # Singular
        id_to_add = "id_f1"  # Singular
        metadata_str = '{"source": "full_test"}'  # Singular JSON string
        parsed_metadata = {"source": "full_test"}  # Expected parsed dict

        input_model = AddDocumentWithIDAndMetadataInput(
            collection_name=collection_name, document=document_to_add, id=id_to_add, metadata=metadata_str
        )
        result = await _add_document_with_id_and_metadata_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        # Assert add was called with the PARSED metadata in list
        mock_collection.add.assert_called_once_with(
            documents=[document_to_add], ids=[id_to_add], metadatas=[parsed_metadata]
        )
        assert_successful_json_result(result, {"added_id": id_to_add})

    @pytest.mark.asyncio
    async def test_add_document_invalid_metadata_json(self, mock_chroma_client_document):
        """Test adding document with invalid metadata JSON string."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_add_invalid_json"
        document_to_add = "doc_ij1"  # Singular
        id_to_add = "id_ij1"  # Singular
        invalid_metadata_str = '{"key": "value1'  # Invalid JSON string

        # Test AddDocumentWithMetadataInput
        input_meta = AddDocumentWithMetadataInput(
            collection_name=collection_name, document=document_to_add, metadata=invalid_metadata_str
        )
        with assert_raises_mcp_error("Invalid JSON format for metadata string"):
            await _add_document_with_metadata_impl(input_meta)

        # Test AddDocumentWithIDAndMetadataInput
        input_full = AddDocumentWithIDAndMetadataInput(
            collection_name=collection_name, document=document_to_add, id=id_to_add, metadata=invalid_metadata_str
        )
        with assert_raises_mcp_error("Invalid JSON format for metadata string"):
            await _add_document_with_id_and_metadata_impl(input_full)

        mock_validate.assert_called()
        mock_client.get_collection.assert_not_called()
        mock_collection.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_document_metadata_not_dict(self, mock_chroma_client_document):
        """Test adding document where metadata string decodes to non-dict."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_add_meta_not_dict"
        document_to_add = "doc_nd1"  # Singular
        id_to_add = "id_nd1"  # Singular
        not_dict_metadata_str = '["list", "not_dict"]'  # Valid JSON, but not an object/dict

        # Test AddDocumentWithMetadataInput
        input_meta = AddDocumentWithMetadataInput(
            collection_name=collection_name, document=document_to_add, metadata=not_dict_metadata_str
        )
        with assert_raises_mcp_error("Metadata string did not decode to a dictionary"):
            await _add_document_with_metadata_impl(input_meta)

        # Test AddDocumentWithIDAndMetadataInput
        input_full = AddDocumentWithIDAndMetadataInput(
            collection_name=collection_name, document=document_to_add, id=id_to_add, metadata=not_dict_metadata_str
        )
        with assert_raises_mcp_error("Metadata string did not decode to a dictionary"):
            await _add_document_with_id_and_metadata_impl(input_full)

        mock_validate.assert_called()
        mock_client.get_collection.assert_not_called()
        mock_collection.add.assert_not_called()

    # --- Query Documents Tests ---

    @pytest.mark.asyncio
    async def test_query_documents_success(self, mock_chroma_client_document):
        """Test successful document query."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_query_success"
        query = ["test query"]
        n_results = 5
        include_fields = ["metadatas", "documents"]
        expected_query_result = {"ids": [["id1"]], "documents": [["doc1"]], "metadatas": [[{"key": "val"}]]}
        mock_collection.query.return_value = expected_query_result

        # --- Act ---
        input_model = QueryDocumentsInput(
            collection_name=collection_name, query_texts=query, n_results=n_results, include=include_fields
        )
        result = await _query_documents_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        mock_collection.query.assert_called_once_with(
            query_texts=query, n_results=n_results, where=None, where_document=None, include=include_fields
        )
        assert_successful_json_result(result, expected_query_result)

    @pytest.mark.asyncio
    async def test_query_documents_collection_not_found(self, mock_chroma_client_document):
        """Test querying a non-existent collection."""
        mock_client, _, mock_validate = mock_chroma_client_document
        collection_name = "query_not_found"
        error_message = f"Collection {collection_name} does not exist."
        mock_client.get_collection.side_effect = ValueError(error_message)

        # --- Act & Assert ---
        input_model = QueryDocumentsInput(collection_name=collection_name, query_texts=["q"])
        with assert_raises_mcp_error(f"Collection '{collection_name}' not found."):
            await _query_documents_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)

    @pytest.mark.asyncio
    async def test_query_documents_chroma_error(self, mock_chroma_client_document):
        """Test handling errors during the actual Chroma query call."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "query_chroma_fail"
        error_message = "Query failed internally."
        mock_client.get_collection.return_value = mock_collection
        mock_collection.query.side_effect = Exception(error_message)

        # --- Act & Assert ---
        input_model = QueryDocumentsInput(collection_name=collection_name, query_texts=["q"])
        # Updated expected message format
        with assert_raises_mcp_error(f"An unexpected error occurred during query: {error_message}"):
            await _query_documents_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        mock_collection.query.assert_called_once()  # Verify query was attempted

    # --- Get Documents Tests ---

    @pytest.mark.asyncio
    async def test_get_documents_success_by_ids(self, mock_chroma_client_document):
        """Test successful get by IDs."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_get_ids_success"
        ids_to_get = ["id1", "id2"]
        include_fields = ["metadatas"]
        expected_get_result = {"ids": ids_to_get, "metadatas": [{"k": "v1"}, {"k": "v2"}]}
        mock_collection.get.return_value = expected_get_result

        # --- Act ---
        input_model = GetDocumentsByIdsInput(collection_name=collection_name, ids=ids_to_get, include=include_fields)
        result = await _get_documents_by_ids_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        mock_collection.get.assert_called_once_with(
            ids=ids_to_get, where=None, where_document=None, limit=None, offset=None, include=include_fields
        )
        assert_successful_json_result(result, expected_get_result)

    @pytest.mark.asyncio
    async def test_get_documents_success_by_where(self, mock_chroma_client_document):
        """Test successful get by where filter."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_get_where_success"
        where_filter = {"status": "active"}
        limit, offset = 10, 0
        expected_get_result = {"ids": ["id_w1"], "documents": ["doc_w1"], "metadatas": [{"status": "active"}]}
        mock_collection.get.return_value = expected_get_result

        # --- Act ---
        input_model = GetDocumentsWithWhereFilterInput(
            collection_name=collection_name, where=where_filter, limit=limit, offset=offset
        )
        result = await _get_documents_with_where_filter_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        mock_collection.get.assert_called_once_with(
            ids=None, where=where_filter, where_document=None, limit=limit, offset=offset, include=[]  # default include
        )
        assert_successful_json_result(result, expected_get_result)

    # Test for GetDocumentsWithDocumentFilterInput - similar structure
    @pytest.mark.asyncio
    async def test_get_documents_success_by_where_doc(self, mock_chroma_client_document):
        """Test successful get by where_document filter."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_get_wheredoc_success"
        where_doc_filter = {"$contains": "obsolete"}
        expected_get_result = {"ids": ["id_wd1"], "documents": ["very important doc"]}
        mock_collection.get.return_value = expected_get_result

        input_model = GetDocumentsWithDocumentFilterInput(
            collection_name=collection_name, where_document=where_doc_filter
        )
        result = await _get_documents_with_document_filter_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        mock_collection.get.assert_called_once_with(
            ids=None, where=None, where_document=where_doc_filter, limit=None, offset=None, include=[]
        )
        assert_successful_json_result(result, expected_get_result)

    # Test for GetAllDocumentsInput - similar structure
    @pytest.mark.asyncio
    async def test_get_all_documents_success(self, mock_chroma_client_document):
        """Test successful get all documents."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_get_all_success"
        limit = 5
        expected_get_result = {
            "ids": [f"id_a{i}" for i in range(limit)],
            "documents": [f"doc_a{i}" for i in range(limit)],
        }
        mock_collection.get.return_value = expected_get_result

        input_model = GetAllDocumentsInput(collection_name=collection_name, limit=limit)
        result = await _get_all_documents_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        mock_collection.get.assert_called_once_with(
            ids=None, where=None, where_document=None, limit=limit, offset=None, include=[]
        )
        assert_successful_json_result(result, expected_get_result)

    @pytest.mark.skip(reason="Include value validation now primarily handled by Pydantic model.")
    @pytest.mark.asyncio
    async def test_get_documents_validation_invalid_include(self, mock_chroma_client_document):
        """Test validation failure for invalid include values."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_get_valid_include"
        # This test needs adjustment based on where include validation happens
        # If Pydantic handles it, test the dispatcher/server level
        # If _impl handles it, mock appropriately

        input_model = GetDocumentsByIdsInput(
            collection_name=collection_name, ids=["id1"], include=["invalid_field"]  # Invalid field
        )

        # Example: Assuming _impl or a helper raises McpError for invalid include
        with assert_raises_mcp_error("Invalid include field"):  # Adjust expected message
            await _get_documents_by_ids_impl(input_model)

    @pytest.mark.asyncio
    async def test_get_documents_validation_no_criteria(self, mock_chroma_client_document):
        """Test validation failure when no specific criteria provided to a specific getter."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_get_valid_criteria"

        # Test GetDocumentsByIdsInput with empty list (should fail in _impl)
        input_ids_empty = GetDocumentsByIdsInput(collection_name=collection_name, ids=[])
        with assert_raises_mcp_error("IDs list cannot be empty for get_documents_by_ids."):
            await _get_documents_by_ids_impl(input_ids_empty)

        # Pydantic ensures where/where_document are provided for other variants, so no test needed here
        # for empty filters on those specific tool variants.

        # Ensure validation happened before client calls
        mock_validate.assert_called()
        mock_client.get_collection.assert_not_called()
        mock_collection.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_documents_collection_not_found(self, mock_chroma_client_document):
        """Test getting documents when the collection is not found."""
        mock_client, _, mock_validate = mock_chroma_client_document
        collection_name = "get_not_found"
        error_message = f"Collection {collection_name} does not exist."
        mock_client.get_collection.side_effect = ValueError(error_message)

        # Test one variant, e.g., GetDocumentsByIdsInput
        input_model = GetDocumentsByIdsInput(collection_name=collection_name, ids=["id1"])
        with assert_raises_mcp_error(f"Collection '{collection_name}' not found."):
            await _get_documents_by_ids_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)

    @pytest.mark.asyncio
    async def test_get_documents_chroma_error(self, mock_chroma_client_document):
        """Test handling errors during the actual Chroma get call."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "get_chroma_fail"
        error_message = "Get failed internally."
        mock_client.get_collection.return_value = mock_collection
        mock_collection.get.side_effect = Exception(error_message)

        # Test one variant, e.g., GetDocumentsByIdsInput
        input_model = GetDocumentsByIdsInput(collection_name=collection_name, ids=["id1"])
        # Updated expected message format
        with assert_raises_mcp_error(f"An unexpected error occurred during get: {error_message}"):
            await _get_documents_by_ids_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        mock_collection.get.assert_called_once()  # Verify get was attempted

    # --- Update Documents Tests ---

    @pytest.mark.asyncio
    async def test_update_document_content_success(self, mock_chroma_client_document):
        """Test successful document update (content only)."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_update_success"
        id_to_update = "id1"  # Singular
        new_doc = "new_doc1"  # Singular

        # --- Act ---
        input_model = UpdateDocumentContentInput(collection_name=collection_name, id=id_to_update, document=new_doc)
        result = await _update_document_content_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        # Assert update called with list of size 1
        mock_collection.update.assert_called_once_with(ids=[id_to_update], documents=[new_doc], metadatas=None)
        # Assert result contains the updated ID
        assert_successful_json_result(result, {"updated_id": id_to_update})

    @pytest.mark.asyncio
    async def test_update_document_metadata_success(self, mock_chroma_client_document):
        """Test successful document update (metadata only)."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_update_meta_success"
        id_to_update = "id_m1"  # Singular
        new_metadata = {"status": "updated"}  # Singular dict

        # --- Act ---
        input_model = UpdateDocumentMetadataInput(
            collection_name=collection_name, id=id_to_update, metadata=new_metadata
        )
        result = await _update_document_metadata_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        # Assert update called with list of size 1
        mock_collection.update.assert_called_once_with(ids=[id_to_update], documents=None, metadatas=[new_metadata])
        assert_successful_json_result(result, {"updated_id": id_to_update})

    @pytest.mark.asyncio
    async def test_update_document_validation_missing_args(self, mock_chroma_client_document):
        """Test validation failure for missing id or metadata."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_update_valid_missing"

        # Test content update missing ID
        input_content = UpdateDocumentContentInput(collection_name=collection_name, id="", document="doc1")
        with assert_raises_mcp_error("ID cannot be empty for update."):
            await _update_document_content_impl(input_content)

        # Test metadata update missing ID
        input_meta_id = UpdateDocumentMetadataInput(collection_name=collection_name, id="", metadata={"k": "v"})
        with assert_raises_mcp_error("ID cannot be empty for update."):
            await _update_document_metadata_impl(input_meta_id)

        # Test metadata update missing metadata (Note: Pydantic handles None, check empty dict? Source code checks for None)
        # Pydantic should prevent None based on model def, test source logic if needed
        # Let's assume Pydantic allows empty dict, test that if required by source
        # input_meta_meta = UpdateDocumentMetadataInput(
        #     collection_name=collection_name, id="id1", metadata={}
        # )
        # with assert_raises_mcp_error("Metadata cannot be empty/null for update."): # Adjust if source allows empty dict
        #     await _update_document_metadata_impl(input_meta_meta)

        mock_validate.assert_called()
        mock_client.get_collection.assert_not_called()
        mock_collection.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_document_collection_not_found(self, mock_chroma_client_document):
        """Test updating document when the collection is not found."""
        mock_client, _, mock_validate = mock_chroma_client_document
        collection_name = "update_not_found"
        error_message = f"Collection {collection_name} does not exist."
        mock_client.get_collection.side_effect = ValueError(error_message)

        input_model = UpdateDocumentContentInput(collection_name=collection_name, id="id1", document="d")
        with assert_raises_mcp_error(f"Collection '{collection_name}' not found."):
            await _update_document_content_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)

    @pytest.mark.asyncio
    async def test_update_document_chroma_error(self, mock_chroma_client_document):
        """Test handling errors during the actual Chroma update call."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "update_chroma_fail"
        error_message = "Update failed internally."
        mock_client.get_collection.return_value = mock_collection
        mock_collection.update.side_effect = Exception(error_message)

        input_model = UpdateDocumentContentInput(collection_name=collection_name, id="id1", document="d")
        with assert_raises_mcp_error(f"ChromaDB Error: Failed to update document content. {error_message}"):
            await _update_document_content_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        mock_collection.update.assert_called_once()  # Verify update was attempted

    # --- Delete Documents Tests ---

    @pytest.mark.asyncio
    async def test_delete_document_by_id_success(self, mock_chroma_client_document):
        """Test successful deletion by ID."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_delete_id"
        id_to_delete = "id_del1"  # Singular
        # Mock delete returns the list of IDs provided if successful
        mock_collection.delete.return_value = [id_to_delete]

        # --- Act ---
        input_model = DeleteDocumentByIdInput(collection_name=collection_name, id=id_to_delete)
        result = await _delete_document_by_id_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        # Assert delete called with only list of IDs (where/where_document default to None)
        mock_collection.delete.assert_called_once_with(ids=[id_to_delete])

        # --- Assert Result ---
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], types.TextContent)
        assert result[0].type == "text"
        # Assert the correct plain text message
        assert result[0].text == f"Deletion requested for document ID: {id_to_delete}"

    @pytest.mark.asyncio
    async def test_delete_document_by_id_not_found_silent(self, mock_chroma_client_document):
        """Test deletion by ID when ID doesn't exist (Chroma returns empty list)."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_delete_id_silent"
        id_to_delete = "non_existent_id"  # Singular
        # Mock delete returns empty list when ID not found
        mock_collection.delete.return_value = []

        # --- Act ---
        input_model = DeleteDocumentByIdInput(collection_name=collection_name, id=id_to_delete)
        result = await _delete_document_by_id_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        # Assert delete called with only list of IDs (where/where_document default to None)
        mock_collection.delete.assert_called_once_with(ids=[id_to_delete])

        # --- Assert Result ---
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], types.TextContent)
        assert result[0].type == "text"
        # Assert the correct plain text message (implementation returns this even if ID not found by Chroma)
        assert result[0].text == f"Deletion requested for document ID: {id_to_delete}"

    @pytest.mark.asyncio
    async def test_delete_document_validation_no_id(self, mock_chroma_client_document):
        """Test validation failure when ID is empty."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_delete_valid"

        input_model = DeleteDocumentByIdInput(collection_name=collection_name, id="")
        with assert_raises_mcp_error("ID cannot be empty for delete_document_by_id."):
            await _delete_document_by_id_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_not_called()
        mock_collection.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_document_collection_not_found(self, mock_chroma_client_document):
        """Test deleting document when the collection is not found."""
        mock_client, _, mock_validate = mock_chroma_client_document
        collection_name = "delete_not_found"
        error_message = f"Collection {collection_name} does not exist."
        mock_client.get_collection.side_effect = ValueError(error_message)

        input_model = DeleteDocumentByIdInput(collection_name=collection_name, id="id1")
        with assert_raises_mcp_error(f"Collection '{collection_name}' not found."):
            await _delete_document_by_id_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)

    @pytest.mark.asyncio
    async def test_delete_document_chroma_error(self, mock_chroma_client_document):
        """Test handling errors during the actual delete call."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "delete_chroma_fail"
        error_message = "Delete failed internally."
        mock_client.get_collection.return_value = mock_collection
        mock_collection.delete.side_effect = Exception(error_message)

        input_model = DeleteDocumentByIdInput(collection_name=collection_name, id="id1")
        with assert_raises_mcp_error(f"ChromaDB Error: Failed to delete document. {error_message}"):
            await _delete_document_by_id_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        mock_collection.delete.assert_called_once()  # Verify delete was attempted

    # --- Generic Error Handling Test (Updated for singular ops) ---

    @pytest.mark.asyncio
    async def test_generic_chroma_error_handling(self, mock_chroma_client_document):
        """Test that generic ChromaDB errors are caught and wrapped in McpError."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "generic_error_test"
        generic_error_message = "A generic ChromaDB internal error occurred."

        # --- Test Add (Singular) --- #
        mock_client.get_collection.reset_mock(side_effect=None)
        mock_client.get_collection.return_value = mock_collection
        # Correctly mock the failure on the collection's add method
        mock_collection.add.side_effect = Exception(generic_error_message)
        input_add = AddDocumentInput(collection_name=collection_name, document="d")  # Singular
        with assert_raises_mcp_error(f"An unexpected error occurred: {generic_error_message}"):
            await _add_document_impl(input_add)
        mock_validate.assert_called_with(collection_name)
        mock_client.get_collection.assert_called_with(name=collection_name)
        mock_collection.add.assert_called_once()
        mock_client.reset_mock()
        mock_collection.reset_mock()
        mock_validate.reset_mock()

        # --- Test Query (Unchanged) --- #
        mock_client.get_collection.return_value = mock_collection
        mock_collection.query.side_effect = Exception(generic_error_message)
        input_query = QueryDocumentsInput(collection_name=collection_name, query_texts=["q"])
        with assert_raises_mcp_error(f"An unexpected error occurred during query: {generic_error_message}"):
            await _query_documents_impl(input_query)
        mock_validate.assert_called_with(collection_name)
        mock_client.get_collection.assert_called_with(name=collection_name)
        mock_collection.query.assert_called_once()
        mock_client.reset_mock()
        mock_collection.reset_mock()
        mock_validate.reset_mock()

        # --- Test Update (Content - Singular) --- #
        mock_client.get_collection.return_value = mock_collection
        mock_collection.update.side_effect = Exception(generic_error_message)
        input_update_content = UpdateDocumentContentInput(
            collection_name=collection_name, id="id1", document="d"
        )  # Singular
        with assert_raises_mcp_error(
            f"ChromaDB Error: Failed to update document content. {generic_error_message}"
        ):  # Updated msg
            await _update_document_content_impl(input_update_content)
        mock_validate.assert_called_with(collection_name)
        mock_client.get_collection.assert_called_with(name=collection_name)
        mock_collection.update.assert_called_once()
        mock_client.reset_mock()
        mock_collection.reset_mock()
        mock_validate.reset_mock()

        # --- Test Delete (Singular ID) --- #
        mock_client.get_collection.return_value = mock_collection
        mock_collection.delete.side_effect = Exception(generic_error_message)
        input_delete = DeleteDocumentByIdInput(collection_name=collection_name, id="id1")  # Singular
        with assert_raises_mcp_error(
            f"ChromaDB Error: Failed to delete document. {generic_error_message}"
        ):  # Updated msg
            await _delete_document_by_id_impl(input_delete)
        mock_validate.assert_called_with(collection_name)
        mock_client.get_collection.assert_called_with(name=collection_name)
        mock_collection.delete.assert_called_once()
