"""
Document management tools for ChromaDB operations.
"""

import time
import json
import logging

from typing import Dict, List, Optional, Any, Union, cast
from dataclasses import dataclass

from mcp import types
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INVALID_PARAMS, INTERNAL_ERROR
from pydantic import BaseModel, Field, field_validator  # Import Pydantic

# Use relative imports
from ..utils.errors import ValidationError
from ..types import DocumentMetadata

from chromadb.errors import InvalidDimensionException

# --- Imports ---
import chromadb
import chromadb.errors as chroma_errors
from ..utils import (
    get_logger,
    get_chroma_client,
    get_embedding_function,
    ValidationError,
)
from ..utils.config import validate_collection_name

# REMOVE invalid validation imports
# from ..utils.validation import validate_collection_name, validate_document_ids, validate_metadata
# REMOVE invalid error imports (commented out or non-existent)
# from ..utils.errors import handle_chroma_error, is_collection_not_found_error, CollectionNotFoundError
# REMOVE invalid helper imports
# from ..utils.helpers import (
#     dict_to_text_content,
#     prepare_metadata_for_chroma,
#     process_chroma_results,
#     format_add_result,
#     format_update_result,
#     format_delete_result,
#     MAX_DOC_LENGTH_FOR_PEEK
# )

# --- Constants ---
# Existing constants...
DEFAULT_QUERY_N_RESULTS = 10

# Get logger instance for this module
# logger = get_logger("tools.document")

# --- Pydantic Input Models for Document Tools ---


class AddDocumentsInput(BaseModel):
    collection_name: str = Field(description="Name of the collection to add documents to.")
    documents: List[str] = Field(description="List of document contents (strings).")
    ids: Optional[List[str]] = Field(
        default=None, description="Optional list of unique IDs. If None, IDs are generated."
    )
    metadatas: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Optional list of metadata dictionaries."
    )
    increment_index: Optional[bool] = Field(default=True, description="Whether to immediately index added documents.")

    # TODO: Consider adding validators to ensure lists (if provided) match document count?
    # Pydantic can do this, but it adds complexity. Current impl checks this.


class QueryDocumentsInput(BaseModel):
    collection_name: str = Field(description="Name of the collection to query.")
    query_texts: List[str] = Field(description="List of query strings for semantic search.")
    n_results: Optional[int] = Field(default=10, ge=1, description="Number of results per query.")
    where: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filter (e.g., {'source': 'pdf'}).")
    where_document: Optional[Dict[str, Any]] = Field(
        default=None, description="Document content filter (e.g., {'$contains': 'keyword'})."
    )
    include: Optional[List[str]] = Field(
        default=None, description="Fields to include (documents, metadatas, distances). Defaults to ChromaDB standard."
    )

    # TODO: Add validator for 'include' list contents?
    # Current impl checks this.


class GetDocumentsInput(BaseModel):
    collection_name: str = Field(description="Name of the collection to get documents from.")
    ids: Optional[List[str]] = Field(default=None, description="List of document IDs to retrieve.")
    where: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filter.")
    where_document: Optional[Dict[str, Any]] = Field(default=None, description="Document content filter.")
    limit: Optional[int] = Field(default=None, ge=1, description="Maximum number of documents to return.")
    offset: Optional[int] = Field(default=None, ge=0, description="Number of documents to skip.")
    include: Optional[List[str]] = Field(default=None, description="Fields to include.")

    # Note: Logically, at least one of ids, where, or where_document should be provided for a targeted get.
    # A Pydantic root_validator could enforce this, but is omitted for simplicity for now.


class UpdateDocumentsInput(BaseModel):
    collection_name: str = Field(description="Name of the collection to update documents in.")
    ids: List[str] = Field(description="List of document IDs to update.")
    documents: Optional[List[str]] = Field(default=None, description="Optional new list of document contents.")
    metadatas: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Optional new list of metadata dictionaries."
    )

    # Note: Logically, at least one of documents or metadatas must be provided.
    # A Pydantic root_validator could enforce this.
    # TODO: Consider adding validators to ensure lists (if provided) match ID count?


class DeleteDocumentsInput(BaseModel):
    collection_name: str = Field(description="Name of the collection to delete documents from.")
    ids: Optional[List[str]] = Field(default=None, description="List of document IDs to delete.")
    where: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filter for deletion.")
    where_document: Optional[Dict[str, Any]] = Field(default=None, description="Document content filter for deletion.")

    # Note: Logically, at least one of ids, where, or where_document must be provided.
    # A Pydantic root_validator could enforce this.


# --- End Pydantic Input Models ---

# --- Implementation Functions ---


# Signature changed to return List[Content]
async def _add_documents_impl(input_data: AddDocumentsInput) -> List[types.TextContent]:
    """Implementation logic for adding documents to a collection."""
    logger = get_logger("tools.document")
    collection_name = input_data.collection_name
    documents = input_data.documents
    ids = input_data.ids
    metadatas = input_data.metadatas
    increment_index = input_data.increment_index

    try:
        # Basic validation (Pydantic handles most schema checks)
        validate_collection_name(collection_name)
        if ids and len(ids) != len(documents):
            raise ValidationError("Number of IDs must match number of documents")
        if metadatas and len(metadatas) != len(documents):
            raise ValidationError("Number of metadatas must match number of documents")

        client = get_chroma_client()
        collection = client.get_collection(name=collection_name, embedding_function=get_embedding_function())

        ids_generated = False
        if not ids:
            # Generate IDs if none provided
            ids_generated = True
            start_index = collection.count() if increment_index else 0
            current_time_ns = time.time_ns() # Use nanoseconds for better uniqueness
            ids = [
                f"doc_{current_time_ns}_{start_index + i}" for i, _ in enumerate(documents)
            ] # Use timestamp and index
            logger.info(f"Generated {len(ids)} document IDs for collection '{collection_name}'.")

        # Add documents
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        added_count = len(documents)
        logger.info(f"Added {added_count} documents to collection '{collection_name}'.")

        # Increment index if requested (ChromaDB doesn't have a direct equivalent, log intent)
        if increment_index:
            logger.info(f"increment_index=True: Signaling intent to ensure index is updated (though add() usually handles this).")
            # Previously, this might have called collection.create_index().
            # This is generally NOT needed after `add` in modern ChromaDB versions.
            # If specific index refresh logic is required, it would go here.
            # For now, we assume add() is sufficient and just log.

        # Construct success message JSON
        result_data = {
            "status": "success",
            "added_count": added_count,
            "collection_name": collection_name,
            "document_ids": ids,
            "ids_generated": ids_generated,
        }
        result_json = json.dumps(result_data, indent=2)
        # Return content list directly
        return [types.TextContent(type="text", text=result_json)]

    except ValidationError as e:
        logger.warning(f"Validation error adding documents to '{collection_name}': {e}")
        # Raise McpError
        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Validation Error: {str(e)}"))
    except ValueError as e: # Typically collection not found
        error_str = str(e).lower()
        not_found = False
        if f"collection {collection_name} does not exist." in error_str:
            not_found = True
        if f"collection {collection_name} not found" in error_str:
            not_found = True

        if not_found:
            logger.warning(f"Cannot add documents: Collection '{collection_name}' not found.")
            # Raise McpError
            raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Tool Error: Collection '{collection_name}' not found."))
        else:
             # Reraise other ValueErrors as generic tool errors
            logger.error(f"Value error adding documents to '{collection_name}': {e}", exc_info=True)
            # Raise McpError
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Tool Error: Unexpected value error. Details: {e}"))
    except Exception as e: # Catch other ChromaDB errors (e.g., from add)
        logger.error(f"ChromaDB error adding documents to '{collection_name}': {e}", exc_info=True)
        # Raise McpError
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"ChromaDB Error: Failed to add documents. {str(e)}"))


# Signature changed to return List[Content]
async def _query_documents_impl(input_data: QueryDocumentsInput) -> List[types.TextContent]:
    """Implementation logic for querying documents."""
    logger = get_logger("tools.document")
    collection_name = input_data.collection_name
    query_texts = input_data.query_texts
    n_results = input_data.n_results
    where = input_data.where
    where_document = input_data.where_document
    include = input_data.include

    try:
        validate_collection_name(collection_name)
        # Pydantic validates list presence and include values

        client = get_chroma_client()
        collection = client.get_collection(name=collection_name, embedding_function=get_embedding_function())

        # Perform the query
        results = collection.query(
            query_texts=query_texts,
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=include,
        )

        # Process results to make them JSON serializable (especially embeddings)
        # Convert numpy arrays (or anything with a tolist() method) to lists
        processed_results = results.copy() if results else {}
        if processed_results.get("embeddings"):
            # Embeddings can be List[Optional[List[float]]] or List[Optional[List[List[float]]]]
            # Handle both potential structures
            new_embeddings = []
            for emb_list in processed_results["embeddings"]:
                if emb_list is None:
                    new_embeddings.append(None)
                elif isinstance(emb_list, list) and len(emb_list) > 0 and isinstance(emb_list[0], list):
                     # Handle list of lists (batch query?)
                     new_embeddings.append([arr.tolist() if hasattr(arr, 'tolist') else arr for arr in emb_list])
                else:
                    # Handle single list or numpy array
                     new_embeddings.append(emb_list.tolist() if hasattr(emb_list, 'tolist') else emb_list)
            processed_results["embeddings"] = new_embeddings

        # Distances might also be numpy arrays
        if processed_results.get("distances"):
            processed_results["distances"] = [
                dist_list.tolist() if hasattr(dist_list, "tolist") else dist_list
                for dist_list in processed_results["distances"]
                 if dist_list is not None
            ]


        result_json = json.dumps(processed_results, indent=2)
        # Return content list directly
        return [types.TextContent(type="text", text=result_json)]

    except ValidationError as e:
        logger.warning(f"Validation error querying documents in '{collection_name}': {e}")
        # Raise McpError
        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Validation Error: {str(e)}"))
    except ValueError as e:
        error_str = str(e).lower()
        not_found = False
        if f"collection {collection_name} does not exist." in error_str:
            not_found = True
        if f"collection {collection_name} not found" in error_str:
            not_found = True

        if not_found:
            logger.warning(f"Cannot query documents: Collection '{collection_name}' not found.")
            # Raise McpError
            raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Tool Error: Collection '{collection_name}' not found."))
        else:
            # Reraise other ValueErrors as generic tool errors
            logger.error(f"Value error querying documents in '{collection_name}': {e}", exc_info=True)
            # Raise McpError
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Tool Error: Unexpected value error during query. Details: {e}"))
    except Exception as e:
        logger.error(f"Unexpected error querying documents in '{collection_name}': {e}", exc_info=True)
        # Raise McpError
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"ChromaDB Error: Failed to query documents. {str(e)}"))


# Signature changed to accept Pydantic model
async def _get_documents_impl(input_data: GetDocumentsInput) -> List[types.TextContent]:
    """Retrieves documents from a collection based on IDs or filters.

    Args:
        input_data: A GetDocumentsInput object containing validated arguments.

    Returns:
        A List of TextContent objects.
        On success, content contains a TextContent object with a JSON string
        representing the GetResult (containing lists for ids, documents,
        metadatas, etc.). If IDs are provided and some are not found, they
        will be omitted from the results without an error.
        On error (e.g., collection not found, invalid filter format,
        unexpected issue), isError is True and content contains a TextContent
        object with an error message.
    """

    logger = get_logger("tools.document")
    collection_name = input_data.collection_name
    ids = input_data.ids
    where = input_data.where
    limit = input_data.limit
    offset = input_data.offset
    where_document = input_data.where_document
    include = input_data.include

    try:
        # Validation
        validate_collection_name(collection_name)
        if not ids and not where and not where_document:
            raise ValidationError("At least one of ids, where, or where_document must be provided for get.")
        # Pydantic handles include validation against Literal

        client = get_chroma_client()
        collection = client.get_collection(name=collection_name, embedding_function=get_embedding_function())

        # Default include values if None/empty
        final_include = include if include else ["documents", "metadatas"]

        # Get documents
        results = collection.get(
            ids=ids,
            where=where,
            limit=limit,
            offset=offset,
            where_document=where_document,
            include=final_include,
        )

        # Process results for JSON serialization (embeddings, distances)
        processed_results = results.copy() if results else {}
        # Handle embeddings if included (they might be None even if requested)
        if "embeddings" in final_include and processed_results.get("embeddings"):
             embeddings = processed_results["embeddings"]
             if isinstance(embeddings, list):
                  processed_results["embeddings"] = [
                      emb.tolist() if hasattr(emb, 'tolist') else emb
                      for emb in embeddings if emb is not None
                  ]

        # Distances are not typically returned by get, but handle if they were
        if processed_results.get("distances"):
            distances = processed_results["distances"]
            if isinstance(distances, list):
                 processed_results["distances"] = [
                     dist.tolist() if hasattr(dist, 'tolist') else dist
                     for dist in distances if dist is not None
                 ]


        result_json = json.dumps(processed_results, indent=2)
        # Return content list directly
        return [types.TextContent(type="text", text=result_json)]

    except ValidationError as e:
        logger.warning(f"Validation error getting documents from '{collection_name}': {e}")
        # Raise McpError
        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Validation Error: {str(e)}"))
    except ValueError as e:
        error_str = str(e).lower()
        not_found = False
        if f"collection {collection_name} does not exist." in error_str:
            not_found = True
        if f"collection {collection_name} not found" in error_str:
            not_found = True

        if not_found:
            logger.warning(f"Cannot get documents: Collection '{collection_name}' not found.")
            # Raise McpError
            raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Tool Error: Collection '{collection_name}' not found."))
        else:
            # Reraise other ValueErrors as generic tool errors
            logger.error(f"Value error getting documents from '{collection_name}': {e}", exc_info=True)
            # Raise McpError
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Tool Error: Unexpected value error during get. Details: {e}"))
    except Exception as e:
        logger.error(f"Unexpected error getting documents from '{collection_name}': {e}", exc_info=True)
        # Raise McpError
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"ChromaDB Error: Failed to get documents. {str(e)}"))


# Signature changed to accept Pydantic model
async def _update_documents_impl(input_data: UpdateDocumentsInput) -> List[types.TextContent]:
    """Updates documents in a collection."""
    logger = get_logger("tools.document")
    collection_name = input_data.collection_name
    ids = input_data.ids
    documents = input_data.documents
    metadatas = input_data.metadatas

    try:
        # Validation
        validate_collection_name(collection_name)
        if not ids:
            raise ValidationError("'ids' list cannot be empty for update.")
        if not documents and not metadatas:
            raise ValidationError("Either 'documents' or 'metadatas' must be provided to update.")
        if documents and len(documents) != len(ids):
            raise ValidationError("Number of documents must match number of IDs")
        if metadatas and len(metadatas) != len(ids):
            raise ValidationError("Number of metadatas must match number of IDs")

        client = get_chroma_client()
        collection = client.get_collection(name=collection_name, embedding_function=get_embedding_function())

        # Perform the update
        collection.update(ids=ids, documents=documents, metadatas=metadatas)
        processed_count = len(ids)
        logger.info(f"Attempted update for {processed_count} documents in collection '{collection_name}'")

        # Success result
        result_data = {
            "status": "success",
            "processed_count": processed_count,
            "collection_name": collection_name,
        }
        result_json = json.dumps(result_data, indent=2)
        # Return content list directly
        return [types.TextContent(type="text", text=result_json)]

    except ValidationError as e:
        logger.warning(f"Validation error updating documents in '{collection_name}': {e}")
        # Raise McpError
        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Validation Error: {str(e)}"))
    except ValueError as e:
        error_str = str(e).lower()
        not_found = False
        if f"collection {collection_name} does not exist." in error_str:
            not_found = True
        if f"collection {collection_name} not found" in error_str:
             not_found = True

        if not_found:
            logger.warning(f"Cannot update documents: Collection '{collection_name}' not found.")
            # Raise McpError
            raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Tool Error: Collection '{collection_name}' not found."))
        else:
            # Reraise other ValueErrors as generic tool errors
            logger.error(f"Value error updating documents in '{collection_name}': {e}", exc_info=True)
            # Raise McpError
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Tool Error: Unexpected value error during update. Details: {e}"))
    except Exception as e:
        logger.error(f"Unexpected error updating documents in '{collection_name}': {e}", exc_info=True)
        # Raise McpError
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"ChromaDB Error: Failed to update documents. {str(e)}"))


# Signature changed to accept Pydantic model
async def _delete_documents_impl(input_data: DeleteDocumentsInput) -> List[types.TextContent]:
    """Deletes documents from a collection based on IDs or filters.

    Args:
        input_data: A DeleteDocumentsInput object containing validated arguments.

    Returns:
        A List of TextContent objects.
        On success, content contains a TextContent object with a JSON string
        containing the list of IDs that were actually deleted.
        On error (e.g., collection not found, invalid filter format,
        unexpected issue), isError is True and content contains a TextContent
        object with an error message.
    """

    logger = get_logger("tools.document")
    collection_name = input_data.collection_name
    ids = input_data.ids
    where = input_data.where
    where_document = input_data.where_document

    try:
        # Validation
        validate_collection_name(collection_name)
        if not ids and not where and not where_document:
            raise ValidationError("At least one of ids, where, or where_document must be provided for deletion.")

        client = get_chroma_client()
        collection = client.get_collection(name=collection_name, embedding_function=get_embedding_function())

        # Perform the delete
        # Note: Chroma's delete returns the IDs of the documents *attempted* to be deleted,
        # not necessarily only those that existed and were successfully deleted.
        deleted_ids = collection.delete(ids=ids, where=where, where_document=where_document)
        # We log the number of IDs returned by ChromaDB for info.
        matched_count = len(deleted_ids) if deleted_ids else 0
        logger.info(f"Delete operation completed for collection '{collection_name}'. Matched IDs: {matched_count}")

        # Success result
        result_data = {
            "status": "success",
            "deleted_ids": deleted_ids if deleted_ids else [], # Return empty list if None
            "collection_name": collection_name,
            # "deleted_count": matched_count # Consider if this count is meaningful
        }
        result_json = json.dumps(result_data, indent=2)
        # Return content list directly
        return [types.TextContent(type="text", text=result_json)]

    except ValidationError as e:
        logger.warning(f"Validation error deleting documents from '{collection_name}': {e}")
        # Raise McpError
        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Validation Error: {str(e)}"))
    except ValueError as e:
        error_str = str(e).lower()
        not_found = False
        if f"collection {collection_name} does not exist." in error_str:
            not_found = True
        if f"collection {collection_name} not found" in error_str:
             not_found = True

        if not_found:
            logger.warning(f"Cannot delete documents: Collection '{collection_name}' not found.")
            # Raise McpError
            raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Tool Error: Collection '{collection_name}' not found."))
        else:
            # Reraise other ValueErrors as generic tool errors
            logger.error(f"Value error deleting documents from '{collection_name}': {e}", exc_info=True)
            # Raise McpError
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Tool Error: Unexpected value error during delete. Details: {e}"))
    except Exception as e:
        logger.error(f"Unexpected error deleting documents from '{collection_name}': {e}", exc_info=True)
        # Raise McpError
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"ChromaDB Error: Failed to delete documents. {str(e)}"))
