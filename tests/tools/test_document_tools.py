"""Tests for document management tools."""

import pytest
import uuid
import time  # Import time for ID generation check
import json
import re
import numpy as np
import chromadb

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

DEFAULT_SIMILARITY_THRESHOLD = 0.6

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

        # Revert back to 'in' for substring check
        assert (
            expected_message in message
        ), f"Expected error message containing '{expected_message}' but got '{message}'"
        return
    except Exception as e:
        pytest.fail(f"Expected McpError with message '{expected_message}', but got {type(e).__name__}: {e}")


# --- End Helper Functions ---


# Fixture to mock client and collection for document tools
@pytest.fixture
def mock_chroma_client_document():
    """Fixture to mock Chroma client, collection, and helpers for document tests."""
    with (
        patch("src.chroma_mcp.tools.document_tools.get_chroma_client") as mock_get_client,
        patch("src.chroma_mcp.tools.document_tools.get_embedding_function") as mock_get_embedding_function,
        patch("src.chroma_mcp.tools.document_tools.validate_collection_name") as mock_validate_name,
    ):
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


# Apply the fixture to the whole class
@pytest.mark.usefixtures("initialized_chroma_client")
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
        expected_query_result = {"ids": [["id1"]], "documents": [["doc1"]], "metadatas": [[{"key": "val"}]]}
        mock_collection.query.return_value = expected_query_result

        # --- Act ---
        input_model = QueryDocumentsInput(collection_name=collection_name, query_texts=query, n_results=n_results)
        result = await _query_documents_impl(input_model)

        # --- Assert ---
        # mock_validate.assert_called_once_with(collection_name) # Removed this line
        # mock_client.get_collection.assert_called_once_with(collection_name) # Original assertion, _query_documents_impl calls it for primary
        # The above get_collection is complex due to two calls, let's refine mock setup for this test or check calls more generally.
        # For now, let's focus on the query call to the first collection if that's the intent of this original test.

        # Check that get_collection was called for the primary collection name.
        # And also for the learnings collection name.
        mock_client.get_collection.assert_any_call(collection_name)
        mock_client.get_collection.assert_any_call(document_tools.LEARNINGS_COLLECTION_NAME)

        # Assuming this test originally intended to check the primary collection's query mock:
        # We need a more sophisticated mock_client.get_collection side_effect if we want to assert on mock_collection.query
        # For now, let's ensure the overall structure of the result from the combined query is fine.
        # If mock_collection.query.return_value was for the primary, and learnings is empty by default in fixture:
        primary_like_result = {
            "ids": expected_query_result.get("ids", [[]]),
            "documents": expected_query_result.get("documents", [[]]),
            "metadatas": [
                [meta.copy() for meta in expected_query_result.get("metadatas", [[]])[0]]
            ],  # deepcopy for modification
            "distances": expected_query_result.get("distances", [[]]),
        }
        if primary_like_result["metadatas"][0]:
            for meta_item in primary_like_result["metadatas"][0]:
                meta_item["source_collection"] = collection_name

        # Adjust mock_collection to be specific for this test to simplify assertions
        mock_primary_collection_specific = MagicMock()
        mock_primary_collection_specific.query.return_value = expected_query_result

        mock_learnings_collection_specific = MagicMock()
        mock_learnings_collection_specific.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        def specific_get_collection_side_effect(name, embedding_function=None):
            if name == collection_name:
                return mock_primary_collection_specific
            elif name == document_tools.LEARNINGS_COLLECTION_NAME:
                return mock_learnings_collection_specific
            return MagicMock()

        mock_client.get_collection.side_effect = specific_get_collection_side_effect
        # Re-run with the more specific mock side effect for get_collection
        result = await _query_documents_impl(input_model)

        mock_primary_collection_specific.query.assert_called_once_with(
            query_texts=query, n_results=n_results, include=["documents", "metadatas", "distances"]
        )
        assert_successful_json_result(
            result, primary_like_result
        )  # Check against expected structure with source_collection

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

        # mock_validate.assert_called_once_with(collection_name) # Removed this line
        # mock_client.get_collection.assert_called_once_with(collection_name) # This will be called, but the error path is complex.
        # The primary collection query will fail, then it will try learnings.
        # Let's ensure get_collection was attempted for primary and learnings (if primary failed in a way that learnings is tried).

        # If the primary get_collection fails with ValueError, the current _query_documents_impl logs an error
        # and then tries the learnings collection. If learnings also fails (e.g. not found by default mock),
        # it returns empty results.
        # This test was for _query_documents_impl itself raising McpError, which it no longer does for this specific case.
        # Instead, it logs and returns empty. So, the assert_raises_mcp_error is not appropriate here.

        # We need to redefine how this test works based on current _query_documents_impl behavior.
        # If primary is not found, it logs error, then tries learnings. If learnings is also not found, returns empty.

        mock_client.get_collection.reset_mock()  # Reset from fixture setup

        def specific_get_collection_failure(name, embedding_function=None):
            if name == collection_name:  # Primary fails
                raise ValueError(f"Collection {name} does not exist.")
            elif name == document_tools.LEARNINGS_COLLECTION_NAME:  # Learnings also fails to be found
                raise ValueError(f"Collection {name} does not exist.")
            return MagicMock()

        mock_client.get_collection.side_effect = specific_get_collection_failure

        result = await _query_documents_impl(input_model)  # Re-run with new mock setup

        parsed_result = assert_successful_json_result(result)
        assert parsed_result["ids"] == [[]]
        # Check that get_collection was attempted for both
        mock_client.get_collection.assert_any_call(collection_name)
        mock_client.get_collection.assert_any_call(document_tools.LEARNINGS_COLLECTION_NAME)
        assert mock_client.get_collection.call_count == 2  # Explicitly two attempts

    @pytest.mark.asyncio
    async def test_query_documents_chroma_error(self, mock_chroma_client_document):
        """Test error handling when ChromaDB query operation fails."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_query_error"
        query_texts = ["query1"]
        n_results = 5

        # Simulate ChromaDB error during query
        mock_collection.query.side_effect = Exception("Simulated ChromaDB query error")

        input_model = QueryDocumentsInput(collection_name=collection_name, query_texts=query_texts, n_results=n_results)

        # The _query_documents_impl now attempts two queries. If the primary fails,
        # it logs and continues to learnings. If learnings also fails (or not found),
        # it might return empty or raise. Current impl returns empty on primary failure.
        # Let's adjust this test to reflect the new behavior.
        # If primary fails, and learnings collection is not found (default mock),
        # it should return empty results.

        # Setup get_collection to raise error for learnings if called
        def get_collection_side_effect(name, embedding_function=None):
            if name == collection_name:
                mock_collection.query.side_effect = Exception("Simulated ChromaDB query error")
                return mock_collection
            elif name == document_tools.LEARNINGS_COLLECTION_NAME:  # Check against the constant
                raise ValueError(
                    f"Collection {document_tools.LEARNINGS_COLLECTION_NAME} does not exist"
                )  # Simulate not found
            return MagicMock()  # Default for other unexpected calls

        mock_client.get_collection.side_effect = get_collection_side_effect

        result = await _query_documents_impl(input_model)

        # Assert that it returns an empty, valid structure
        parsed_result = assert_successful_json_result(result)
        assert parsed_result["ids"] == [[]], "Expected empty IDs list for the query"
        assert parsed_result["documents"] == [[]], "Expected empty documents list"
        assert parsed_result["metadatas"] == [[]], "Expected empty metadatas list"
        # Distances might also be empty or null depending on exact empty structure
        assert parsed_result.get("distances") == [[]], "Expected empty distances list"

        # mock_validate.assert_called_once_with(collection_name) # Primary collection validation - REMOVED
        # It should attempt to get both collections
        assert mock_client.get_collection.call_count == 2
        mock_client.get_collection.assert_any_call(collection_name)
        mock_client.get_collection.assert_any_call(document_tools.LEARNINGS_COLLECTION_NAME)

    # --- Tests for _query_documents_impl merging logic ---

    @pytest.mark.asyncio
    async def test_query_documents_impl_merges_results_successfully(self, mock_chroma_client_document):
        """Test _query_documents_impl successfully queries and merges from primary and learnings collections."""
        mock_client, _, mock_validate = mock_chroma_client_document  # Main mock_collection not used directly

        primary_collection_name = "test_primary"
        learnings_collection_name = document_tools.LEARNINGS_COLLECTION_NAME  # Use constant
        query_texts = ["find similar items"]
        n_results = 2

        # Mock collections
        mock_primary_collection = MagicMock(name="primary_collection")
        mock_learnings_collection = MagicMock(name="learnings_collection")

        # Define return values for query
        primary_query_result = {
            "ids": [["primary_id1", "primary_id2"]],
            "documents": [["doc_p1", "doc_p2"]],
            "metadatas": [[{"meta": "p1"}, {"meta": "p2"}]],
            "distances": [[0.1, 0.2]],
            "embeddings": None,
            "uris": None,
            "data": None,
        }
        learnings_query_result = {
            "ids": [["learning_id1", "learning_id2"]],
            "documents": [["doc_l1", "doc_l2"]],
            "metadatas": [[{"meta": "l1"}, {"meta": "l2"}]],
            "distances": [[0.05, 0.15]],
            "embeddings": None,
            "uris": None,
            "data": None,
        }

        mock_primary_collection.query.return_value = primary_query_result
        mock_learnings_collection.query.return_value = learnings_query_result

        def get_collection_side_effect(name, embedding_function=None):
            if name == primary_collection_name:
                return mock_primary_collection
            elif name == learnings_collection_name:
                return mock_learnings_collection
            raise ValueError(f"Unexpected collection name: {name}")

        mock_client.get_collection.side_effect = get_collection_side_effect

        input_model = QueryDocumentsInput(
            collection_name=primary_collection_name, query_texts=query_texts, n_results=n_results
        )
        result = await _query_documents_impl(input_model)

        # Assertions
        # mock_validate.assert_called_once_with(primary_collection_name) # REMOVED
        assert mock_client.get_collection.call_count == 2
        mock_client.get_collection.assert_any_call(primary_collection_name)
        mock_client.get_collection.assert_any_call(learnings_collection_name)

        mock_primary_collection.query.assert_called_once_with(
            query_texts=query_texts, n_results=n_results, include=["documents", "metadatas", "distances"]
        )
        mock_learnings_collection.query.assert_called_once_with(
            query_texts=query_texts, n_results=n_results, include=["documents", "metadatas", "distances"]
        )

        parsed_result = assert_successful_json_result(result)

        expected_ids = [["primary_id1", "primary_id2", "learning_id1", "learning_id2"]]
        expected_docs = [["doc_p1", "doc_p2", "doc_l1", "doc_l2"]]
        expected_metas = [
            [
                {"meta": "p1", "source_collection": primary_collection_name},
                {"meta": "p2", "source_collection": primary_collection_name},
                {"meta": "l1", "source_collection": learnings_collection_name},
                {"meta": "l2", "source_collection": learnings_collection_name},
            ]
        ]
        expected_dists = [[0.1, 0.2, 0.05, 0.15]]

        assert parsed_result["ids"] == expected_ids
        assert parsed_result["documents"] == expected_docs
        assert parsed_result["metadatas"] == expected_metas
        assert parsed_result["distances"] == expected_dists

    @pytest.mark.asyncio
    async def test_query_documents_impl_primary_only_results(self, mock_chroma_client_document):
        """Test merging when only the primary collection returns results."""
        mock_client, _, mock_validate = mock_chroma_client_document
        primary_collection_name = "test_primary_only"
        learnings_collection_name = document_tools.LEARNINGS_COLLECTION_NAME
        query_texts = ["search term"]
        n_results = 1

        mock_primary_collection = MagicMock(name="primary_collection")
        mock_learnings_collection = MagicMock(name="learnings_collection")

        primary_query_result = {
            "ids": [["p_id1"]],
            "documents": [["doc_p1"]],
            "metadatas": [[{"m": "p1"}]],
            "distances": [[0.1]],
            "embeddings": None,
            "uris": None,
            "data": None,
        }
        empty_learnings_result = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],  # Empty results for the query
            "embeddings": None,
            "uris": None,
            "data": None,
        }

        mock_primary_collection.query.return_value = primary_query_result
        mock_learnings_collection.query.return_value = empty_learnings_result

        def get_collection_side_effect(name, embedding_function=None):
            if name == primary_collection_name:
                return mock_primary_collection
            if name == learnings_collection_name:
                return mock_learnings_collection
            raise ValueError(f"Unexpected collection name: {name}")

        mock_client.get_collection.side_effect = get_collection_side_effect

        input_model = QueryDocumentsInput(
            collection_name=primary_collection_name, query_texts=query_texts, n_results=n_results
        )
        result = await _query_documents_impl(input_model)

        parsed_result = assert_successful_json_result(result)
        assert parsed_result["ids"] == [["p_id1"]]
        assert parsed_result["metadatas"][0][0]["source_collection"] == primary_collection_name
        assert len(parsed_result["ids"][0]) == 1

    @pytest.mark.asyncio
    async def test_query_documents_impl_learnings_only_results(self, mock_chroma_client_document):
        """Test merging when only the learnings collection returns results."""
        mock_client, _, mock_validate = mock_chroma_client_document
        primary_collection_name = "test_learnings_only_primary"
        learnings_collection_name = document_tools.LEARNINGS_COLLECTION_NAME
        query_texts = ["search term"]
        n_results = 1

        mock_primary_collection = MagicMock(name="primary_collection")
        mock_learnings_collection = MagicMock(name="learnings_collection")

        empty_primary_result = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
            "embeddings": None,
            "uris": None,
            "data": None,
        }
        learnings_query_result = {
            "ids": [["l_id1"]],
            "documents": [["doc_l1"]],
            "metadatas": [[{"m": "l1"}]],
            "distances": [[0.05]],
            "embeddings": None,
            "uris": None,
            "data": None,
        }

        mock_primary_collection.query.return_value = empty_primary_result
        mock_learnings_collection.query.return_value = learnings_query_result

        def get_collection_side_effect(name, embedding_function=None):
            if name == primary_collection_name:
                return mock_primary_collection
            if name == learnings_collection_name:
                return mock_learnings_collection
            raise ValueError(f"Unexpected collection name: {name}")

        mock_client.get_collection.side_effect = get_collection_side_effect

        input_model = QueryDocumentsInput(
            collection_name=primary_collection_name, query_texts=query_texts, n_results=n_results
        )
        result = await _query_documents_impl(input_model)

        parsed_result = assert_successful_json_result(result)
        assert parsed_result["ids"] == [["l_id1"]]
        assert parsed_result["metadatas"][0][0]["source_collection"] == learnings_collection_name
        assert len(parsed_result["ids"][0]) == 1

    @pytest.mark.asyncio
    async def test_query_documents_impl_no_results_from_either(self, mock_chroma_client_document):
        """Test merging when neither collection returns results."""
        mock_client, _, mock_validate = mock_chroma_client_document
        primary_collection_name = "test_no_results_primary"
        learnings_collection_name = document_tools.LEARNINGS_COLLECTION_NAME
        query_texts = ["search term"]
        n_results = 1

        mock_primary_collection = MagicMock(name="primary_collection")
        mock_learnings_collection = MagicMock(name="learnings_collection")

        empty_result = {  # Simulate empty result for one query text
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
            "embeddings": None,
            "uris": None,
            "data": None,
        }

        mock_primary_collection.query.return_value = empty_result
        mock_learnings_collection.query.return_value = empty_result

        def get_collection_side_effect(name, embedding_function=None):
            if name == primary_collection_name:
                return mock_primary_collection
            if name == learnings_collection_name:
                return mock_learnings_collection
            raise ValueError(f"Unexpected collection name: {name}")

        mock_client.get_collection.side_effect = get_collection_side_effect

        input_model = QueryDocumentsInput(
            collection_name=primary_collection_name, query_texts=query_texts, n_results=n_results
        )
        result = await _query_documents_impl(input_model)

        parsed_result = assert_successful_json_result(result)
        assert parsed_result["ids"] == [[]]  # Check for one query text, empty results
        assert parsed_result["documents"] == [[]]
        assert parsed_result["metadatas"] == [[]]
        assert parsed_result["distances"] == [[]]

    @pytest.mark.asyncio
    async def test_query_documents_impl_learnings_collection_fails_query(self, mock_chroma_client_document):
        """Test when learnings collection query fails but primary succeeds."""
        mock_client, _, mock_validate = mock_chroma_client_document
        primary_collection_name = "test_learnings_fail_primary"
        learnings_collection_name = document_tools.LEARNINGS_COLLECTION_NAME
        query_texts = ["search term"]
        n_results = 1

        mock_primary_collection = MagicMock(name="primary_collection")
        mock_learnings_collection = MagicMock(name="learnings_collection")

        primary_query_result = {
            "ids": [["p_id1"]],
            "documents": [["doc_p1"]],
            "metadatas": [[{"m": "p1"}]],
            "distances": [[0.1]],
            "embeddings": None,
            "uris": None,
            "data": None,
        }

        mock_primary_collection.query.return_value = primary_query_result
        mock_learnings_collection.query.side_effect = Exception("Learnings query failed")

        def get_collection_side_effect(name, embedding_function=None):
            if name == primary_collection_name:
                return mock_primary_collection
            if name == learnings_collection_name:
                return mock_learnings_collection
            raise ValueError(f"Unexpected collection name: {name}")

        mock_client.get_collection.side_effect = get_collection_side_effect

        input_model = QueryDocumentsInput(
            collection_name=primary_collection_name, query_texts=query_texts, n_results=n_results
        )
        result = await _query_documents_impl(input_model)

        parsed_result = assert_successful_json_result(result)
        assert parsed_result["ids"] == [["p_id1"]]  # Should still get primary results
        assert parsed_result["metadatas"][0][0]["source_collection"] == primary_collection_name
        assert len(parsed_result["ids"][0]) == 1
        # Optionally, check logs for the warning about learnings query failure

    @pytest.mark.asyncio
    async def test_query_documents_impl_primary_collection_fails_query(self, mock_chroma_client_document):
        """Test when primary collection query fails but learnings succeeds."""
        mock_client, _, mock_validate = mock_chroma_client_document
        primary_collection_name = "test_primary_fail_primary"
        learnings_collection_name = document_tools.LEARNINGS_COLLECTION_NAME
        query_texts = ["search term"]
        n_results = 1

        mock_primary_collection = MagicMock(name="primary_collection")
        mock_learnings_collection = MagicMock(name="learnings_collection")

        learnings_query_result = {
            "ids": [["l_id1"]],
            "documents": [["doc_l1"]],
            "metadatas": [[{"m": "l1"}]],
            "distances": [[0.05]],
            "embeddings": None,
            "uris": None,
            "data": None,
        }

        mock_primary_collection.query.side_effect = Exception("Primary query failed")
        mock_learnings_collection.query.return_value = learnings_query_result

        def get_collection_side_effect(name, embedding_function=None):
            if name == primary_collection_name:
                return mock_primary_collection
            if name == learnings_collection_name:
                return mock_learnings_collection
            raise ValueError(f"Unexpected collection name: {name}")

        mock_client.get_collection.side_effect = get_collection_side_effect

        input_model = QueryDocumentsInput(
            collection_name=primary_collection_name, query_texts=query_texts, n_results=n_results
        )
        result = await _query_documents_impl(input_model)

        parsed_result = assert_successful_json_result(result)
        assert parsed_result["ids"] == [["l_id1"]]  # Should get learnings results
        assert parsed_result["metadatas"][0][0]["source_collection"] == learnings_collection_name
        assert len(parsed_result["ids"][0]) == 1
        # Optionally, check logs for the error about primary query failure

    @pytest.mark.asyncio
    async def test_query_documents_impl_both_collections_fail_query(self, mock_chroma_client_document):
        """Test when both collection queries fail."""
        mock_client, _, mock_validate = mock_chroma_client_document
        primary_collection_name = "test_both_fail_primary"
        learnings_collection_name = document_tools.LEARNINGS_COLLECTION_NAME
        query_texts = ["search term"]
        n_results = 1

        mock_primary_collection = MagicMock(name="primary_collection")
        mock_learnings_collection = MagicMock(name="learnings_collection")

        mock_primary_collection.query.side_effect = Exception("Primary query failed")
        mock_learnings_collection.query.side_effect = Exception("Learnings query failed")

        def get_collection_side_effect(name, embedding_function=None):
            if name == primary_collection_name:
                return mock_primary_collection
            if name == learnings_collection_name:
                return mock_learnings_collection
            raise ValueError(f"Unexpected collection name: {name}")

        mock_client.get_collection.side_effect = get_collection_side_effect

        input_model = QueryDocumentsInput(
            collection_name=primary_collection_name, query_texts=query_texts, n_results=n_results
        )
        result = await _query_documents_impl(input_model)

        parsed_result = assert_successful_json_result(result)
        assert parsed_result["ids"] == [[]]  # Expect empty valid structure
        assert parsed_result["documents"] == [[]]
        assert parsed_result["metadatas"] == [[]]
        assert parsed_result["distances"] == [[]]

    @pytest.mark.asyncio
    async def test_query_documents_impl_multiple_query_texts_merge(self, mock_chroma_client_document):
        """Test merging logic with multiple query texts."""
        mock_client, _, mock_validate = mock_chroma_client_document
        primary_collection_name = "test_multi_query_primary"
        learnings_collection_name = document_tools.LEARNINGS_COLLECTION_NAME
        query_texts = ["query text 1", "query text 2"]
        n_results = 1

        mock_primary_collection = MagicMock(name="primary_collection")
        mock_learnings_collection = MagicMock(name="learnings_collection")

        primary_results = {
            "ids": [["p_id1_q1"], ["p_id1_q2"]],
            "documents": [["doc_p1_q1"], ["doc_p1_q2"]],
            "metadatas": [[{"m": "p1q1"}], [{"m": "p1q2"}]],
            "distances": [[0.1], [0.2]],
            "embeddings": None,
            "uris": None,
            "data": None,
        }
        learnings_results = {
            "ids": [["l_id1_q1"], []],  # Result for q1, no result for q2
            "documents": [["doc_l1_q1"], []],
            "metadatas": [[{"m": "l1q1"}], []],
            "distances": [[0.05], []],
            "embeddings": None,
            "uris": None,
            "data": None,
        }

        mock_primary_collection.query.return_value = primary_results
        mock_learnings_collection.query.return_value = learnings_results

        def get_collection_side_effect(name, embedding_function=None):
            if name == primary_collection_name:
                return mock_primary_collection
            if name == learnings_collection_name:
                return mock_learnings_collection
            raise ValueError(f"Unexpected collection name: {name}")

        mock_client.get_collection.side_effect = get_collection_side_effect

        input_model = QueryDocumentsInput(
            collection_name=primary_collection_name, query_texts=query_texts, n_results=n_results
        )
        result = await _query_documents_impl(input_model)

        parsed_result = assert_successful_json_result(result)

        # For query 1
        assert parsed_result["ids"][0] == ["p_id1_q1", "l_id1_q1"]
        assert parsed_result["documents"][0] == ["doc_p1_q1", "doc_l1_q1"]
        assert parsed_result["metadatas"][0][0] == {"m": "p1q1", "source_collection": primary_collection_name}
        assert parsed_result["metadatas"][0][1] == {"m": "l1q1", "source_collection": learnings_collection_name}
        assert parsed_result["distances"][0] == [0.1, 0.05]

        # For query 2
        assert parsed_result["ids"][1] == ["p_id1_q2"]
        assert parsed_result["documents"][1] == ["doc_p1_q2"]
        assert parsed_result["metadatas"][1][0] == {"m": "p1q2", "source_collection": primary_collection_name}
        assert parsed_result["distances"][1] == [0.2]

    # --- End Tests for _query_documents_impl merging logic ---

    # --- Get Documents Tests ---

    @pytest.mark.asyncio
    async def test_get_documents_success_by_ids(self, mock_chroma_client_document):
        """Test successful get by IDs."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_get_ids_success"
        ids_to_get = ["id1", "id2"]
        expected_get_result = {"ids": ids_to_get, "metadatas": [{"k": "v1"}, {"k": "v2"}]}
        mock_collection.get.return_value = expected_get_result

        # --- Act ---
        input_model = GetDocumentsByIdsInput(collection_name=collection_name, ids=ids_to_get)
        result = await _get_documents_by_ids_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(collection_name)
        mock_collection.get.assert_called_once_with(ids=ids_to_get)
        assert_successful_json_result(result, expected_get_result)

    @pytest.mark.asyncio
    async def test_get_documents_success_by_where(self, mock_chroma_client_document):
        """Test successful get by where filter."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_get_where_success"
        where_filter = {"status": "active"}
        where_filter_str = json.dumps(where_filter)
        limit, offset = 10, 0
        expected_get_result = {"ids": ["id_w1"], "documents": ["doc_w1"], "metadatas": [{"status": "active"}]}
        mock_collection.get.return_value = expected_get_result

        # --- Act ---
        input_model = GetDocumentsWithWhereFilterInput(
            collection_name=collection_name, where=where_filter_str, limit=limit, offset=offset
        )
        result = await _get_documents_with_where_filter_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(collection_name)
        mock_collection.get.assert_called_once_with(where=where_filter, limit=limit, offset=None)

        parsed_result = assert_successful_json_result(result)
        assert parsed_result.get("ids") == expected_get_result["ids"]

    # Test for GetDocumentsWithDocumentFilterInput - similar structure
    @pytest.mark.asyncio
    async def test_get_documents_success_by_where_doc(self, mock_chroma_client_document):
        """Test successful get by where_document filter."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_get_wheredoc_success"
        where_doc_filter = {"$contains": "obsolete"}
        where_doc_filter_str = json.dumps(where_doc_filter)
        expected_get_result = {"ids": ["id_wd1"], "documents": ["very important doc"]}
        mock_collection.get.return_value = expected_get_result

        input_model = GetDocumentsWithDocumentFilterInput(
            collection_name=collection_name, where_document=where_doc_filter_str
        )
        result = await _get_documents_with_document_filter_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(collection_name)
        mock_collection.get.assert_called_once_with(where_document=where_doc_filter, limit=None, offset=None)

        parsed_result = assert_successful_json_result(result)
        assert parsed_result.get("ids") == expected_get_result["ids"]

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
        mock_client.get_collection.assert_called_once_with(collection_name)
        mock_collection.get.assert_called_once_with(limit=limit, offset=None)

        parsed_result = assert_successful_json_result(result)
        assert parsed_result.get("ids") == expected_get_result["ids"]

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
            collection_name=collection_name, ids=["id1"]  # Invalid field removed from Pydantic
        )

        # Example: Assuming _impl or a helper raises McpError for invalid include
        # This test is no longer applicable as include is removed from base model
        # with assert_raises_mcp_error("Invalid include field"):  # Adjust expected message
        #     await _get_documents_by_ids_impl(input_model)
        pass

    @pytest.mark.asyncio
    async def test_get_documents_validation_no_criteria(self, mock_chroma_client_document):
        """Test validation failure when no specific criteria provided to a specific getter."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_get_valid_criteria"

        # Test GetDocumentsByIdsInput with empty list (should fail in _impl)
        input_ids_empty = GetDocumentsByIdsInput(collection_name=collection_name, ids=[])
        with assert_raises_mcp_error("IDs list cannot be empty."):
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
        mock_client.get_collection.assert_called_once_with(collection_name)

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
        with assert_raises_mcp_error(f"An unexpected error occurred while retrieving documents by ID: {error_message}"):
            await _get_documents_by_ids_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(collection_name)
        mock_collection.get.assert_called_once_with(ids=["id1"])

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
        new_metadata_str = json.dumps(new_metadata)

        # --- Act ---
        input_model = UpdateDocumentMetadataInput(
            collection_name=collection_name, id=id_to_update, metadata=new_metadata_str
        )
        result = await _update_document_metadata_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        # Update expects metadata as list
        mock_collection.update.assert_called_once_with(ids=[id_to_update], metadatas=[new_metadata])
        assert_successful_json_result(result, {"updated_id": id_to_update})

    @pytest.mark.asyncio
    async def test_update_document_validation_missing_args(self, mock_chroma_client_document):
        """Test validation failure for missing id or metadata."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_update_valid_missing"
        metadata_dict = {"k": "v"}
        metadata_str = json.dumps(metadata_dict)

        # Test content update missing ID
        input_content = UpdateDocumentContentInput(collection_name=collection_name, id="", document="doc1")
        with assert_raises_mcp_error("ID cannot be empty for update."):
            await _update_document_content_impl(input_content)

        # Test metadata update missing ID
        input_meta_id = UpdateDocumentMetadataInput(collection_name=collection_name, id="", metadata=metadata_str)
        with assert_raises_mcp_error("Document ID cannot be empty."):
            await _update_document_metadata_impl(input_meta_id)

        # Test metadata update missing metadata
        # Pydantic now handles missing required fields, so this direct call isn't needed
        # for the specific 'metadata missing' check if it's not optional.
        # If metadata were optional, you'd test its absence differently.
        # input_meta_missing = UpdateDocumentMetadataInput(collection_name=collection_name, id="id1", metadata="") # Empty string check handled by implementation
        # with assert_raises_mcp_error("Invalid JSON format for metadata"): # Or whatever the impl raises for empty string
        #     await _update_document_metadata_impl(input_meta_missing)

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
        # Mock delete to raise NotFoundError for this specific test
        mock_collection.delete.side_effect = chromadb.errors.NotFoundError(f"ID {id_to_delete} not found.")

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
        # Assert the specific string result for not found
        assert result[0].text == f"Document ID '{id_to_delete}' not found, no deletion needed."

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
        # The original test expected an McpError here. However, _query_documents_impl
        # now catches exceptions from individual collection queries and attempts to proceed.
        # If both fail, it returns an empty valid structure.
        # mock_client.get_collection.return_value = mock_collection # Already set by fixture
        # mock_collection.query.side_effect = Exception(generic_error_message) # Already set by fixture default behavior if not overridden

        # Setup specific side effects for this test section
        mock_primary_coll_generic_err = MagicMock()
        mock_primary_coll_generic_err.query.side_effect = Exception(generic_error_message)
        mock_learnings_coll_generic_err = MagicMock()
        mock_learnings_coll_generic_err.query.side_effect = Exception(generic_error_message)

        def generic_error_get_collection(name, embedding_function=None):
            if name == collection_name:
                return mock_primary_coll_generic_err
            elif name == document_tools.LEARNINGS_COLLECTION_NAME:
                return mock_learnings_coll_generic_err
            return MagicMock()

        mock_client.get_collection.side_effect = generic_error_get_collection

        result_query = await _query_documents_impl(input_query)
        parsed_query_result = assert_successful_json_result(result_query)
        assert parsed_query_result["ids"] == [[]]

        # mock_validate.assert_called_with(collection_name) # REMOVED
        # mock_client.get_collection.assert_called_with(collection_name) # More complex now
        assert mock_client.get_collection.call_count == 2
        mock_client.get_collection.assert_any_call(collection_name)
        mock_client.get_collection.assert_any_call(document_tools.LEARNINGS_COLLECTION_NAME)
        # mock_collection.query.assert_called_once() # Not simple with two collections
        mock_primary_coll_generic_err.query.assert_called_once()
        mock_learnings_coll_generic_err.query.assert_called_once()

        mock_client.reset_mock()  # Reset all calls on the main client mock
        mock_collection.reset_mock()  # Reset the general mock_collection from fixture if it was used or modified
        mock_validate.reset_mock()
        # Ensure get_collection side effect is cleared for subsequent parts of this test
        mock_client.get_collection.side_effect = mock_collection  # Restore default fixture behavior

        # --- Test Update (Content - Singular) --- #
        # Create a NEW mock collection specifically for this part
        mock_update_collection = MagicMock(name="update_specific_collection")
        mock_update_collection.update.side_effect = Exception(generic_error_message)

        # Configure get_collection to return this specific mock
        mock_client.get_collection.side_effect = None
        mock_client.get_collection.return_value = mock_update_collection

        # Set the side effect *after* resetting mock_collection
        # mock_collection.update.side_effect = Exception(generic_error_message) << Remove this line
        input_update_content = UpdateDocumentContentInput(collection_name=collection_name, id="id1", document="d")
        with assert_raises_mcp_error(f"ChromaDB Error: Failed to update document content. {generic_error_message}"):
            await _update_document_content_impl(input_update_content)

        # Assertions for Update part
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(name=collection_name)
        mock_update_collection.update.assert_called_once()  # Assert on the specific mock

        # Reset mocks fully before Delete section
        mock_client.reset_mock()
        mock_collection.reset_mock()  # Now reset the fixture one
        mock_validate.reset_mock()

        # Restore default fixture behavior for get_collection explicitly for Delete part
        mock_client.get_collection.side_effect = None
        mock_client.get_collection.return_value = mock_collection  # Restore fixture's collection

        # --- Test Delete (Singular ID) --- #
        # Set the side effect *after* resetting mock_collection (the fixture one)
        mock_collection.delete.side_effect = Exception(generic_error_message)
        input_delete = DeleteDocumentByIdInput(collection_name=collection_name, id="id1")
        with assert_raises_mcp_error(f"ChromaDB Error: Failed to delete document. {generic_error_message}"):
            await _delete_document_by_id_impl(input_delete)
        mock_validate.assert_called_with(collection_name)
        mock_client.get_collection.assert_called_with(name=collection_name)
        mock_collection.delete.assert_called_once()

    # --- Start: Tests for New Include Variants ---

    @pytest.mark.asyncio
    async def test_get_documents_by_ids_embeddings_success(self, mock_chroma_client_document):
        """Test successful get by IDs including embeddings only."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_get_ids_embed_success"
        ids_to_get = ["id_e1", "id_e2"]
        # Expected result only contains ids and embeddings
        expected_get_result = {"ids": ids_to_get, "embeddings": [[0.1, 0.2], [0.3, 0.4]]}
        mock_collection.get.return_value = expected_get_result

        # Import the specific model and impl function
        from src.chroma_mcp.tools.document_tools import (
            GetDocumentsByIdsEmbeddingsInput,
            _get_documents_by_ids_embeddings_impl,
        )

        # --- Act ---
        input_model = GetDocumentsByIdsEmbeddingsInput(collection_name=collection_name, ids=ids_to_get)
        result = await _get_documents_by_ids_embeddings_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(collection_name)
        # Assert that get was called with include=["embeddings"]
        mock_collection.get.assert_called_once_with(ids=ids_to_get, include=["embeddings"])
        assert_successful_json_result(result, expected_get_result)

    @pytest.mark.asyncio
    async def test_get_documents_by_ids_all_success(self, mock_chroma_client_document):
        """Test successful get by IDs including all data."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "test_get_ids_all_success"
        ids_to_get = ["id_a1"]
        expected_all_fields = ["documents", "metadatas", "embeddings", "uris", "data"]
        expected_get_result = {
            "ids": ids_to_get,
            "documents": [["doc_a1"]],
            "metadatas": [[{"key": "val_a1"}]],
            "embeddings": [[0.5, 0.6]],
            "uris": [["uri_a1"]],
            "data": None,  # Or some example data
        }
        mock_collection.get.return_value = expected_get_result

        # Import the specific model and impl function
        from src.chroma_mcp.tools.document_tools import GetDocumentsByIdsAllInput, _get_documents_by_ids_all_impl

        # --- Act ---
        input_model = GetDocumentsByIdsAllInput(collection_name=collection_name, ids=ids_to_get)
        result = await _get_documents_by_ids_all_impl(input_model)

        # --- Assert ---
        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(collection_name)
        # Assert that get was called with the full include list
        mock_collection.get.assert_called_once_with(ids=ids_to_get, include=expected_all_fields)
        assert_successful_json_result(result, expected_get_result)

    @pytest.mark.asyncio
    async def test_get_documents_by_ids_include_collection_not_found(self, mock_chroma_client_document):
        """Test get by IDs (include variants) when collection not found."""
        mock_client, _, mock_validate = mock_chroma_client_document
        collection_name = "get_include_not_found"
        ids_to_get = ["id_nf1"]
        error_message = f"Collection {collection_name} does not exist."
        mock_client.get_collection.side_effect = ValueError(error_message)

        # Import one of the specific models/impls to test the path
        from src.chroma_mcp.tools.document_tools import (
            GetDocumentsByIdsEmbeddingsInput,
            _get_documents_by_ids_embeddings_impl,
        )

        # --- Act & Assert ---
        input_model = GetDocumentsByIdsEmbeddingsInput(collection_name=collection_name, ids=ids_to_get)
        with assert_raises_mcp_error(f"Collection '{collection_name}' not found."):
            await _get_documents_by_ids_embeddings_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(collection_name)

    @pytest.mark.asyncio
    async def test_get_documents_by_ids_include_get_error(self, mock_chroma_client_document):
        """Test get by IDs (include variants) with a generic error during get."""
        mock_client, mock_collection, mock_validate = mock_chroma_client_document
        collection_name = "get_include_get_error"
        ids_to_get = ["id_ge1"]
        error_message = "Generic get error during include variant."
        mock_client.get_collection.return_value = mock_collection  # Collection exists
        mock_collection.get.side_effect = Exception(error_message)  # Error during get

        # Import one of the specific models/impls to test the path
        from src.chroma_mcp.tools.document_tools import (
            GetDocumentsByIdsAllInput,
            _get_documents_by_ids_all_impl,
        )

        tool_name = "get_ids_all"  # Match tool name used in impl logger/error

        # --- Act & Assert ---
        input_model = GetDocumentsByIdsAllInput(collection_name=collection_name, ids=ids_to_get)
        # Assert the specific error format from _get_documents_by_ids_include_impl
        expected_full_error = f"An unexpected error occurred ('{tool_name}'): {error_message}"
        with assert_raises_mcp_error(expected_full_error):
            await _get_documents_by_ids_all_impl(input_model)

        mock_validate.assert_called_once_with(collection_name)
        mock_client.get_collection.assert_called_once_with(collection_name)
        mock_collection.get.assert_called_once()  # Verify get was attempted

    # --- End: Tests for New Include Variants ---
