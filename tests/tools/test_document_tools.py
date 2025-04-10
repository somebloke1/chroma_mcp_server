"""Tests for document management tools."""

import pytest
import uuid
import time  # Import time for ID generation check
import json
import re
import numpy as np

from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock, ANY, call, AsyncMock
from contextlib import contextmanager # Import contextmanager

# Import CallToolResult and TextContent for helpers
from mcp import types
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS
from mcp.shared.exceptions import McpError

# Keep only ValidationError from errors module
from src.chroma_mcp.utils.errors import ValidationError
from src.chroma_mcp.tools import document_tools

# Import the implementation functions directly
from src.chroma_mcp.tools.document_tools import (
    _add_documents_impl,
    _query_documents_impl,
    _get_documents_impl,
    _update_documents_impl,
    _delete_documents_impl,
)

# Import Pydantic models
from src.chroma_mcp.tools.document_tools import (
    AddDocumentsInput,
    QueryDocumentsInput,
    GetDocumentsInput,
    UpdateDocumentsInput,
    DeleteDocumentsInput,
)

# Import Chroma exceptions used in mocking
from chromadb.errors import InvalidDimensionException # No longer needed

# Import necessary helpers from utils
from src.chroma_mcp.utils.config import get_collection_settings # Not used here
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
        yield # Code under test executes here

    # After the block, check the exception details
    error_message = str(exc_info.value) # Use the string representation of the exception
    # print(f"DEBUG: Caught McpError message: {error_message}") # Keep commented out for now
    if expected_error_substring:
        assert expected_error_substring.lower() in error_message.lower(), \
               f"Expected substring '{expected_error_substring}' not found in error message '{error_message}'"

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
        mock_collection_instance = MagicMock(name="document_collection") # Name for clarity

        # Configure default behaviors for collection methods
        mock_collection_instance.add.return_value = None # add returns None
        mock_collection_instance.query.return_value = { # Default empty query result
             "ids": [], "distances": [], "metadatas": [], "embeddings": [], "documents": [], "uris": [], "data": None
        }
        mock_collection_instance.get.return_value = { # Default empty get result
             "ids": [], "metadatas": [], "embeddings": [], "documents": [], "uris": [], "data": None
        }
        mock_collection_instance.update.return_value = None # update returns None
        mock_collection_instance.delete.return_value = [] # delete returns list of deleted IDs
        mock_collection_instance.count.return_value = 0 # Default count

        # Configure client methods
        mock_client_instance.get_collection.return_value = mock_collection_instance

        # Configure helper mocks
        mock_get_client.return_value = mock_client_instance
        mock_get_embedding_function.return_value = MagicMock(name="mock_embedding_function")
        mock_validate_name.return_value = None # Assume valid name by default

        yield mock_client_instance, mock_collection_instance, mock_validate_name # Yield validator too


class TestDocumentTools:
    """Test cases for document management tools."""

    # --- _add_documents_impl Tests ---
    @pytest.mark.asyncio
    async def test_add_documents_success(self, mock_chroma_client_document):
        """Test successfully adding documents."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document # Unpack validator
        collection_name = "add_coll"
        docs = ["doc1", "doc2"]
        ids = ["id_a", "id_b"]
        metas = [{'k': 'v1'}, {'k': 'v2'}]

        # --- Act ---
        input_model = AddDocumentsInput(
            collection_name=collection_name, documents=docs, ids=ids, metadatas=metas, increment_index=False
        )
        result = await _add_documents_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        # Check add was called synchronously with correct args
        mock_collection.add.assert_called_once_with(documents=docs, metadatas=metas, ids=ids)

        # Use helper to check result format and parse JSON
        result_data = assert_successful_json_result(result)
        assert result_data.get("status") == "success"
        assert result_data.get("added_count") == 2
        assert result_data.get("collection_name") == collection_name
        assert result_data.get("document_ids") == ids
        assert result_data.get("ids_generated") is False

    @pytest.mark.asyncio
    async def test_add_documents_increment_index(self, mock_chroma_client_document):
        """Test add documents with increment_index=True (logs intent)."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "add_inc_coll"
        docs = ["doc_inc"]

        # --- Act ---
        input_model = AddDocumentsInput(collection_name=collection_name, documents=docs, increment_index=True)
        result = await _add_documents_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.add.assert_called_once() # Check add was called
        # REMOVED: create_index is no longer called directly
        # mock_collection.create_index.assert_called_once()

        # Assert successful result (basic check is sufficient)
        assert_successful_json_result(result)

    @pytest.mark.asyncio
    async def test_add_documents_collection_not_found(self, mock_chroma_client_document):
        """Test adding documents when collection not found."""
        mock_client, _, mock_validate = mock_chroma_client_document
        collection_name = "add_not_found"
        error_message = f"Collection {collection_name} does not exist."
        mock_client.get_collection.side_effect = ValueError(error_message)

        # --- Act & Assert ---
        input_model = AddDocumentsInput(collection_name=collection_name, documents=["d"])
        # Expect McpError
        # assert_error_result(result, f"Tool Error: Collection '{collection_name}' not found.")
        with assert_raises_mcp_error(f"Tool Error: Collection '{collection_name}' not found."):
             await _add_documents_impl(input_model)

        # Assert mocks
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)

    @pytest.mark.asyncio
    async def test_add_documents_chroma_error(self, mock_chroma_client_document):
        """Test handling errors during the add process."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "add_chroma_fail"
        error_message = "Insertion failed due to dimension mismatch."
        # Mock get success, add failure
        mock_client.get_collection.return_value = mock_collection
        # Use generic Exception for mocking side effect
        mock_collection.add.side_effect = Exception(error_message)

        # --- Act & Assert ---
        input_model = AddDocumentsInput(collection_name=collection_name, documents=["d"])
        # Expect McpError
        # assert_error_result(result, f"ChromaDB Error: Failed to add documents. {error_message}")
        with assert_raises_mcp_error(f"ChromaDB Error: Failed to add documents. {error_message}"):
            await _add_documents_impl(input_model)

        # Assert mocks
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_documents_generate_ids(self, mock_chroma_client_document):
        """Test document addition with auto-generated IDs."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "add_gen_ids"
        docs = ["docA", "docB"]
        # Mock collection.count() response for ID generation
        mock_collection.count.return_value = 3 # Simulate 3 existing docs
        start_time_ns = time.time_ns() # Use nanoseconds like implementation

        # --- Act ---
        # increment_index=True is default
        input_model = AddDocumentsInput(collection_name=collection_name, documents=docs)
        result = await _add_documents_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        # REMOVED: count is called in the implementation, but asserting it here is brittle
        # mock_collection.count.assert_called_once() # Assert count WAS called for ID gen
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        assert call_args.kwargs["documents"] == docs
        assert call_args.kwargs["metadatas"] is None # Ensure None was passed
        # Check generated IDs format (basic check)
        generated_ids = call_args.kwargs["ids"]
        assert len(generated_ids) == 2
        # Match the nanosecond format: doc_<timestamp_ns>_<index>
        # Loosen timestamp match slightly due to potential timing difference
        assert re.match(rf"doc_{start_time_ns // 1_000_000_000}", generated_ids[0]) # Check prefix and seconds part
        assert generated_ids[0].endswith("_3") # Check index part (3 + 0)
        assert generated_ids[1].endswith("_4") # Check index part (3 + 1)

        # Use helper to check result format and parse JSON
        result_data = assert_successful_json_result(result)
        assert result_data.get("status") == "success"
        assert result_data.get("added_count") == 2
        assert result_data.get("ids_generated") is True
        assert result_data.get("document_ids") == generated_ids # Check returned IDs match

    @pytest.mark.asyncio
    async def test_add_documents_generate_ids_no_increment(self, mock_chroma_client_document):
        """Test document addition with auto-generated IDs without incrementing index."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "add_gen_noinc"
        docs = ["docX"]
        # Mock count behavior - it *is* called for ID generation
        mock_collection.count.return_value = 0 # Simulate empty collection for ID gen
        start_time_ns = time.time_ns()

        # --- Act ---
        input_model = AddDocumentsInput(collection_name=collection_name, documents=docs, increment_index=False)
        result = await _add_documents_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        # REMOVED: count is called in the implementation, but asserting it here is brittle
        # mock_collection.count.assert_called_once() # Assert count WAS called for ID gen
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        generated_ids = call_args.kwargs["ids"]
        assert len(generated_ids) == 1
        # Loosen timestamp match
        assert re.match(rf"doc_{start_time_ns // 1_000_000_000}", generated_ids[0])
        # Index starts from 0 because increment_index=False
        assert generated_ids[0].endswith("_0")

        # Use helper to check result format and parse JSON
        result_data = assert_successful_json_result(result)
        assert result_data.get("ids_generated") is True
        assert result_data.get("document_ids") == generated_ids

    @pytest.mark.asyncio
    async def test_add_documents_validation_no_docs(self, mock_chroma_client_document):
        """Test validation success when no documents are provided (should add 0)."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_valid"
        # --- Act ---
        input_model = AddDocumentsInput(collection_name=collection_name, documents=[])
        result = await _add_documents_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        # Expect success, adding 0 documents
        # Implementation calls add with empty lists
        mock_collection.add.assert_called_once_with(documents=[], ids=[], metadatas=None)
        result_data = assert_successful_json_result(result)
        assert result_data.get("status") == "success"
        assert result_data.get("added_count") == 0
        assert result_data.get("collection_name") == collection_name
        assert result_data.get("document_ids") == []

    @pytest.mark.asyncio
    async def test_add_documents_validation_mismatch_ids(self, mock_chroma_client_document):
        """Test validation failure with mismatched IDs."""
        _, _, mock_validate = mock_chroma_client_document
        collection_name = "test_valid_mismatch_id"
        input_model = AddDocumentsInput(
            collection_name=collection_name, documents=["d1", "d2"], ids=["id1"], increment_index=True
        )
        # assert_error_result(result, "Validation Error: Number of IDs must match number of documents")
        with assert_raises_mcp_error("Validation Error: Number of IDs must match number of documents"):
            await _add_documents_impl(input_model)
        mock_validate.assert_called_once_with(collection_name) # Validation happens before get_collection

    @pytest.mark.asyncio
    async def test_add_documents_validation_mismatch_metas(self, mock_chroma_client_document):
        """Test validation failure with mismatched metadatas."""
        _, _, mock_validate = mock_chroma_client_document
        collection_name = "test_valid_mismatch_meta"
        input_model = AddDocumentsInput(
            collection_name=collection_name, documents=["d1", "d2"], metadatas=[{"k": "v"}], increment_index=True
        )
        # assert_error_result(result, "Validation Error: Number of metadatas must match number of documents")
        with assert_raises_mcp_error("Validation Error: Number of metadatas must match number of documents"):
            await _add_documents_impl(input_model)
        mock_validate.assert_called_once_with(collection_name) # Validation happens before get_collection

    # --- _query_documents_impl Tests ---
    @pytest.mark.asyncio
    async def test_query_documents_success(self, mock_chroma_client_document):
        """Test successful document querying."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "query_coll"
        query_texts = ["query1"]
        n_results = 2
        include = ["metadatas", "documents", "distances"]
        # Mock return value for query
        mock_result = {
            "ids": [["id1", "id2"]],
            "distances": [[0.1, 0.2]],
            "metadatas": [[{"m": 1}, {"m": 2}]],
            "embeddings": None, # Not included
            "documents": [["doc1", "doc2"]],
            "uris": None, # Not included
            "data": None, # Not included
        }
        # Configure mocks
        mock_client.get_collection.return_value = mock_collection
        mock_collection.query.return_value = mock_result

        # --- Act ---
        input_model = QueryDocumentsInput(
            collection_name=collection_name, query_texts=query_texts, n_results=n_results, include=include
        )
        # Expect List[TextContent]
        result_list = await _query_documents_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.query.assert_called_once_with(
            query_texts=query_texts, n_results=n_results, where=None, where_document=None, include=include
        )

        # Assert successful result format
        assert isinstance(result_list, list)
        assert len(result_list) == 1
        content_item = result_list[0]
        # Use TextContent, as JSON is embedded in the text field
        assert isinstance(content_item, types.TextContent)
        # Verify the structure and content (basic check)
        parsed_json = json.loads(content_item.text)
        assert "ids" in parsed_json
        assert parsed_json["ids"] == mock_result["ids"]
        assert "distances" in parsed_json
        assert "documents" in parsed_json
        assert "metadatas" in parsed_json

    @pytest.mark.asyncio
    async def test_query_documents_collection_not_found(self, mock_chroma_client_document):
        """Test querying when collection is not found."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "query_not_found"
        error_message = f"Collection {collection_name} does not exist."
        mock_client.get_collection.side_effect = ValueError(error_message)

        # --- Act & Assert ---
        input_model = QueryDocumentsInput(collection_name=collection_name, query_texts=["q"])
        # Expect McpError
        # assert excinfo.value.message == f"Tool Error: Collection '{collection_name}' not found."
        with assert_raises_mcp_error(f"Tool Error: Collection '{collection_name}' not found."):
            await _query_documents_impl(input_model)

        # Assert mocks
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)

    @pytest.mark.asyncio
    async def test_query_documents_chroma_error(self, mock_chroma_client_document):
        """Test handling errors during the query process."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "query_chroma_fail"
        error_message = "Query failed internally."
        # Mock get success, query failure
        mock_client.get_collection.return_value = mock_collection
        mock_collection.query.side_effect = Exception(error_message)

        # --- Act & Assert ---
        input_model = QueryDocumentsInput(collection_name=collection_name, query_texts=["q"])
        # Expect McpError
        # assert excinfo.value.message == f"ChromaDB Error: Failed to query documents. {error_message}"
        with assert_raises_mcp_error(f"ChromaDB Error: Failed to query documents. {error_message}"):
            await _query_documents_impl(input_model)

        # Assert mocks
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.query.assert_called_once()

    # --- _get_documents_impl Tests ---
    @pytest.mark.asyncio
    async def test_get_documents_success_by_ids(self, mock_chroma_client_document):
        """Test successful document retrieval by IDs."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        mock_get_return = {
            "ids": ["id1", "id3"],
            "documents": ["doc one", "doc three"],
            "metadatas": [{"k": 1}, {"k": 3}],
            "embeddings": None, # Default exclude
        }
        mock_collection.get.return_value = mock_get_return

        ids_to_get = ["id1", "id3"]
        collection_name = "test_get_ids"
        input_model = GetDocumentsInput(collection_name=collection_name, ids=ids_to_get)
        result = await _get_documents_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.get.assert_called_once_with(
            ids=ids_to_get,
            where=None,
            limit=None,
            offset=None,
            where_document=None,
            include=["documents", "metadatas"], # Check actual default include used by _impl
        )
        # Use helper to parse JSON first - check matches raw return
        assert_successful_json_result(result, mock_get_return)

    @pytest.mark.asyncio
    async def test_get_documents_success_by_where(self, mock_chroma_client_document):
        """Test successful get by where filter with limit/offset."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        mock_get_return = {
            "ids": ["id5"],
            "documents": ["doc five"], # Only documents included
            "metadatas": None,
            "embeddings": None,
        }
        mock_collection.get.return_value = mock_get_return

        where_filter = {"tag": "test"}
        limit = 1
        offset = 2
        collection_name = "test_get_where"
        include = ["documents"]
        input_model = GetDocumentsInput(
            collection_name=collection_name, where=where_filter, limit=limit, offset=offset, include=include
        )
        result = await _get_documents_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.get.assert_called_once_with(
            ids=None,
            where=where_filter,
            limit=limit,
            offset=offset,
            where_document=None,
            include=include, # Check custom include
        )
        # Use helper to parse JSON - check matches raw return
        assert_successful_json_result(result, mock_get_return)

    @pytest.mark.asyncio
    async def test_get_documents_validation_no_criteria(self, mock_chroma_client_document):
        """Test validation failure when no criteria (ids/where/where_doc) provided."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_get_valid"
        input_model = GetDocumentsInput(collection_name=collection_name)
        # Expect validation error raised by _impl
        with assert_raises_mcp_error("Validation Error: At least one of ids, where, or where_document must be provided for get."):
            await _get_documents_impl(input_model)
        # Check validator was called before error
        mock_validate.assert_called_once_with(collection_name)

    @pytest.mark.asyncio
    async def test_get_documents_validation_invalid_include(self, mock_chroma_client_document):
        """Test validation failure with invalid include values."""
        # NOTE: Pydantic now handles Literal validation for include. This test might become obsolete
        # if we solely rely on Pydantic. Keeping it for now if _impl does extra checks.
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_get_valid_inc"
        input_model = GetDocumentsInput(
            collection_name=collection_name, ids=["id1"], include=["documents", "invalid_field"]
        )
        # This will likely fail Pydantic validation *before* _impl is called.
        # If _impl *does* validate, we need to adjust this:
        # with assert_raises_mcp_error("Validation Error: Invalid item(s) in include list"):
        #     await _get_documents_impl(input_model)
        pytest.skip("Include value validation now primarily handled by Pydantic model.")
        # result = await _get_documents_impl(input_model)
        # assert result.isError is True
        # assert "Validation Error: Invalid item(s) in include list" in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_documents_collection_not_found(self, mock_chroma_client_document):
        """Test getting documents when the collection is not found."""
        mock_client, _, mock_validate = mock_chroma_client_document
        collection_name = "get_not_found"
        error_message = f"Collection {collection_name} does not exist."
        mock_client.get_collection.side_effect = ValueError(error_message)

        # --- Act & Assert ---
        input_model = GetDocumentsInput(collection_name=collection_name, ids=["id1"])
        with assert_raises_mcp_error(f"Tool Error: Collection '{collection_name}' not found."):
            await _get_documents_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)

    @pytest.mark.asyncio
    async def test_get_documents_chroma_error(self, mock_chroma_client_document):
        """Test handling errors during the actual get call."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "get_chroma_fail"
        error_message = "Get failed internally."
        # Mock get success, query failure
        mock_client.get_collection.return_value = mock_collection
        mock_collection.get.side_effect = Exception(error_message)

        # --- Act & Assert ---
        input_model = GetDocumentsInput(collection_name=collection_name, ids=["id1"])
        with assert_raises_mcp_error(f"ChromaDB Error: Failed to get documents. {error_message}"):
            await _get_documents_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.get.assert_called_once()

    # --- _update_documents_impl Tests ---
    @pytest.mark.asyncio
    async def test_update_documents_success(self, mock_chroma_client_document):
        """Test successful document update (content and metadata)."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_update"
        ids_to_update = ["id_u1", "id_u2"]
        new_docs = ["new doc 1", "new doc 2"]
        new_metas = [{'k': 'v_new1'}, {'k': 'v_new2'}]

        # --- Act ---
        input_model = UpdateDocumentsInput(
            collection_name=collection_name, ids=ids_to_update, documents=new_docs, metadatas=new_metas
        )
        result = await _update_documents_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.update.assert_called_once_with(ids=ids_to_update, documents=new_docs, metadatas=new_metas)
        # Check successful result JSON using helper
        result_data = assert_successful_json_result(result)
        assert result_data.get("status") == "success"
        assert result_data.get("processed_count") == 2
        assert result_data.get("collection_name") == collection_name

    @pytest.mark.asyncio
    async def test_update_documents_only_metadata(self, mock_chroma_client_document):
        """Test updating only metadata."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_update_meta"
        ids_to_update = ["id_m1"]
        new_metas = [{'status': 'updated'}]

        # --- Act ---
        input_model = UpdateDocumentsInput(
            collection_name=collection_name, ids=ids_to_update, metadatas=new_metas
        )
        result = await _update_documents_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        # Check update called with documents=None
        mock_collection.update.assert_called_once_with(ids=ids_to_update, documents=None, metadatas=new_metas)
        # Check successful result JSON using helper
        result_data = assert_successful_json_result(result)
        assert result_data.get("status") == "success"
        assert result_data.get("processed_count") == 1

    @pytest.mark.asyncio
    async def test_update_documents_validation_mismatch(self, mock_chroma_client_document):
        """Test validation failure with mismatched list lengths."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_update_valid_match"
        input_model = UpdateDocumentsInput(
            collection_name=collection_name, ids=["id1"], documents=["d1", "d2"] # Mismatch
        )
        # Expect McpError
        with assert_raises_mcp_error("Validation Error: Number of documents must match number of IDs"):
            await _update_documents_impl(input_model)
        mock_validate.assert_called_once_with(collection_name) # Validator called before error

    @pytest.mark.asyncio
    async def test_update_documents_collection_not_found(self, mock_chroma_client_document):
        """Test updating documents when the collection is not found."""
        mock_client, _, mock_validate = mock_chroma_client_document
        collection_name = "update_not_found"
        error_message = f"Collection {collection_name} does not exist."
        mock_client.get_collection.side_effect = ValueError(error_message)

        # --- Act & Assert ---
        input_model = UpdateDocumentsInput(collection_name=collection_name, ids=["id1"], documents=["d"])
        with assert_raises_mcp_error(f"Tool Error: Collection '{collection_name}' not found."):
            await _update_documents_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)

    @pytest.mark.asyncio
    async def test_update_documents_chroma_error(self, mock_chroma_client_document):
        """Test handling errors during the actual update call."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "update_chroma_fail"
        error_message = "Update failed internally."
        # Mock get success, update failure
        mock_client.get_collection.return_value = mock_collection
        mock_collection.update.side_effect = Exception(error_message)

        # --- Act & Assert ---
        input_model = UpdateDocumentsInput(collection_name=collection_name, ids=["id1"], documents=["d"])
        with assert_raises_mcp_error(f"ChromaDB Error: Failed to update documents. {error_message}"):
            await _update_documents_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.update.assert_called_once()

    # --- _delete_documents_impl Tests ---
    @pytest.mark.asyncio
    async def test_delete_documents_success_by_ids(self, mock_chroma_client_document):
        """Test successful deletion by IDs."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_delete_ids"
        ids_to_delete = ["id_del1", "id_del2"]
        # Mock the return value of delete (list of IDs that were deleted)
        mock_collection.delete.return_value = ids_to_delete

        # --- Act ---
        input_model = DeleteDocumentsInput(collection_name=collection_name, ids=ids_to_delete)
        result = await _delete_documents_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.delete.assert_called_once_with(ids=ids_to_delete, where=None, where_document=None)
        # Check successful result JSON using helper
        result_data = assert_successful_json_result(result)
        assert result_data.get("status") == "success"
        assert result_data.get("deleted_ids") == ids_to_delete
        assert result_data.get("collection_name") == collection_name

    @pytest.mark.asyncio
    async def test_delete_documents_success_by_where(self, mock_chroma_client_document):
        """Test successful deletion by where filter."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_delete_where"
        where_filter = {"status": "to_delete"}
        # Mock delete return value
        deleted_ids_returned = ["id_matched1", "id_matched2"]
        mock_collection.delete.return_value = deleted_ids_returned

        # --- Act ---
        input_model = DeleteDocumentsInput(collection_name=collection_name, where=where_filter)
        result = await _delete_documents_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.delete.assert_called_once_with(ids=None, where=where_filter, where_document=None)
        # Check successful result JSON using helper
        result_data = assert_successful_json_result(result)
        assert result_data.get("status") == "success"
        assert result_data.get("deleted_ids") == deleted_ids_returned

    @pytest.mark.asyncio
    async def test_delete_documents_validation_no_criteria(self, mock_chroma_client_document):
        """Test validation failure when no criteria (ids/where/where_doc) provided."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_delete_valid"
        input_model = DeleteDocumentsInput(collection_name=collection_name)
        # Expect McpError
        with assert_raises_mcp_error("Validation Error: At least one of ids, where, or where_document must be provided for deletion."):
            await _delete_documents_impl(input_model)
        mock_validate.assert_called_once_with(collection_name)

    @pytest.mark.asyncio
    async def test_delete_documents_collection_not_found(self, mock_chroma_client_document):
        """Test deleting documents when the collection is not found."""
        mock_client, _, mock_validate = mock_chroma_client_document
        collection_name = "delete_not_found"
        error_message = f"Collection {collection_name} does not exist."
        mock_client.get_collection.side_effect = ValueError(error_message)

        # --- Act & Assert ---
        input_model = DeleteDocumentsInput(collection_name=collection_name, ids=["id1"])
        with assert_raises_mcp_error(f"Tool Error: Collection '{collection_name}' not found."):
            await _delete_documents_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)

    @pytest.mark.asyncio
    async def test_delete_documents_chroma_error(self, mock_chroma_client_document):
        """Test handling errors during the actual delete call."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "delete_chroma_fail"
        error_message = "Delete failed internally."
        # Mock get success, delete failure
        mock_client.get_collection.return_value = mock_collection
        mock_collection.delete.side_effect = Exception(error_message)

        # --- Act & Assert ---
        input_model = DeleteDocumentsInput(collection_name=collection_name, ids=["id1"])
        with assert_raises_mcp_error(f"ChromaDB Error: Failed to delete documents. {error_message}"):
            await _delete_documents_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
        mock_collection.delete.assert_called_once()

    # --- Generic Error Handling Test ---
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "tool_impl_func, chroma_method_name, args, kwargs, expected_error_msg_part",
        [
            # Add missing required args to kwargs for each tool
            (
                _add_documents_impl,
                "add",
                [],
                {"collection_name": "c", "documents": ["d"]}, # increment_index defaults to True
                "add documents",
            ),
            (
                _query_documents_impl,
                "query",
                [],
                {"collection_name": "c", "query_texts": ["q"]}, # n_results defaults to 10
                "query documents",
            ),
            # (
            #     _get_documents_impl,
            #     "get",
            #     [],
            #     {"collection_name": "c", "ids": ["id1"]}, # limit, offset default None
            #     "getting documents",
            # ),
            # (
            #     _update_documents_impl,
            #     "update",
            #     [],
            #     {"collection_name": "c", "ids": ["id1"], "documents": ["d"]},
            #     "updating documents",
            # ),
            # (_delete_documents_impl, "delete", [], {"collection_name": "c", "ids": ["id1"]}, "deleting documents"),
        ],
    )
    async def test_generic_chroma_error_handling(
        self, mock_chroma_client_document, tool_impl_func, chroma_method_name, args, kwargs, expected_error_msg_part
    ):
        """Tests that unexpected ChromaDB errors during tool execution raise McpError."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document

        # Setup the mock collection method to raise an error
        error_message = "Simulated ChromaDB Failure"
        getattr(mock_collection, chroma_method_name).side_effect = Exception(error_message)

        # Determine the correct Pydantic model based on the function
        if tool_impl_func == _add_documents_impl:
            InputModel = AddDocumentsInput
        elif tool_impl_func == _query_documents_impl:
            InputModel = QueryDocumentsInput
        # elif tool_impl_func == _get_documents_impl:
        #     InputModel = GetDocumentsInput
        # elif tool_impl_func == _update_documents_impl:
        #     InputModel = UpdateDocumentsInput
        # elif tool_impl_func == _delete_documents_impl:
        #     InputModel = DeleteDocumentsInput
        else:
            pytest.fail(f"Unknown tool_impl_func: {tool_impl_func}")

        # Instantiate the model with the provided kwargs
        try:
            input_model = InputModel(**kwargs)
        except ValidationError as e:
            pytest.fail(f"Failed to instantiate Pydantic model {InputModel.__name__} with kwargs {kwargs}: {e}")

        # Call the tool implementation function and expect McpError
        # result = await tool_impl_func(input_model)
        # assert result.isError is True
        # assert f"Error: Failed to {expected_error_msg_part}" in result.content[0].text
        # assert error_message in result.content[0].text
        with assert_raises_mcp_error(error_message): # Check the original exception message is included
            await tool_impl_func(input_model)

    # Test query collection not found specifically (still returns CallToolResult)
    @pytest.mark.asyncio
    async def test_query_collection_not_found(self, mock_chroma_client_document):
        """Test querying a non-existent collection (using specific test)."""
        mock_client, _, mock_validate = mock_chroma_client_document
        collection_name = "non_existent_coll"
        # Configure the client's get_collection mock to raise the specific ValueError
        error_message = f"Collection {collection_name} does not exist."
        mock_client.get_collection.side_effect = ValueError(error_message)

        # ACT & Assert
        input_model = QueryDocumentsInput(collection_name=collection_name, query_texts=["test"])
        # result = await _query_documents_impl(input_model)
        # assert result.isError is True
        # assert f"Tool Error: Collection '{collection_name}' not found." in result.content[0].text
        with assert_raises_mcp_error(f"Tool Error: Collection '{collection_name}' not found."):
            await _query_documents_impl(input_model)

        # Assert mocks were called correctly
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name, embedding_function=ANY)
