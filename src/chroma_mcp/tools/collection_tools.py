"""
Collection management tools for ChromaDB operations.
"""

import json
import logging
import chromadb
import chromadb.errors as chroma_errors
from chromadb.api.client import ClientAPI
from chromadb.errors import InvalidDimensionException
import numpy as np

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union, cast
from dataclasses import dataclass

from chromadb.api.types import CollectionMetadata, GetResult, QueryResult
from chromadb.errors import InvalidDimensionException

from mcp import types
from mcp.types import ErrorData, INVALID_PARAMS, INTERNAL_ERROR
from mcp.shared.exceptions import McpError

from ..utils import (
    get_logger,
    get_chroma_client,
    get_embedding_function,
    ValidationError,
    ClientError,
    ConfigurationError,
)
from ..utils.config import get_collection_settings, validate_collection_name

# Ensure mcp instance is imported/available for decorators
# Might need to adjust imports if mcp is not globally accessible here.
# Assuming FastMCP instance is created elsewhere and decorators register to it.
# We need to import the mcp instance or pass it.
# Let's assume FastMCP handles registration implicitly upon import.
# Need to ensure FastMCP is imported here:
# REMOVE: from mcp.server.fastmcp import FastMCP

# It's more likely the mcp instance is needed. Let's assume it's globally accessible
# or passed to a setup function that imports this module. For now, leave as is.
# If errors persist, we might need to import the global _mcp_instance from server.py.

# --- Pydantic Input Models for Collection Tools ---


class CreateCollectionInput(BaseModel):
    collection_name: str = Field(
        description="The name for the new collection. Must adhere to ChromaDB naming conventions."
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata and settings (e.g., {'description': '...', 'settings': {'hnsw:space': 'cosine'}}). Uses server defaults if None.",
    )


class ListCollectionsInput(BaseModel):
    limit: Optional[int] = Field(
        default=None, ge=0, description="Maximum number of collections to return (0 or None for no limit)."
    )
    offset: Optional[int] = Field(default=None, ge=0, description="Number of collections to skip.")
    name_contains: Optional[str] = Field(
        default=None, description="Filter collections by name (case-insensitive contains)."
    )


class GetCollectionInput(BaseModel):
    collection_name: str = Field(description="The name of the collection to retrieve information for.")


class SetCollectionDescriptionInput(BaseModel):
    collection_name: str = Field(description="The name of the collection to update.")
    description: str = Field(description="The new description for the collection.")


class SetCollectionSettingsInput(BaseModel):
    collection_name: str = Field(description="The name of the collection to update.")
    settings: Dict[str, Any] = Field(
        description="A dictionary containing the new settings (e.g., HNSW parameters). Replaces existing settings."
    )


class UpdateCollectionMetadataInput(BaseModel):
    collection_name: str = Field(description="The name of the collection to update.")
    metadata_update: Dict[str, Any] = Field(
        description="Key-value pairs to add/update in the collection's custom metadata block. Replaces existing custom metadata."
    )


class RenameCollectionInput(BaseModel):
    collection_name: str = Field(description="The current name of the collection to rename.")
    new_name: str = Field(description="The new name for the collection.")


class DeleteCollectionInput(BaseModel):
    collection_name: str = Field(description="The name of the collection to delete.")


class PeekCollectionInput(BaseModel):
    collection_name: str = Field(description="The name of the collection to peek into.")
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum number of documents to return (defaults to ChromaDB's internal default, often 10). Must be >= 1.",
    )


# --- End Pydantic Input Models ---


def _reconstruct_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Reconstructs the structured metadata (with 'settings') from ChromaDB's internal format."""
    if not metadata:
        return {}

    reconstructed = {}
    settings = {}
    for key, value in metadata.items():
        setting_key_to_store = None
        # Check for flattened setting keys
        if key.startswith("chroma:setting:"):
            # Convert 'chroma_setting_hnsw_space' back to 'hnsw:space'
            original_key = key[len("chroma:setting:") :].replace("_", ":")
            setting_key_to_store = original_key
        # Also recognize common raw keys like hnsw:*
        elif key.startswith("hnsw:"):
            setting_key_to_store = key

        if setting_key_to_store:
            settings[setting_key_to_store] = value
        # Explicitly check for 'description' as it's handled separately
        elif key == "description":
            reconstructed[key] = value
        # Store other keys directly (custom user keys)
        elif not key.startswith("chroma:"):  # Avoid other potential internal chroma keys
            reconstructed[key] = value

    if settings:
        reconstructed["settings"] = settings

    return reconstructed


# --- Implementation Functions ---


# Signature changed to return List[Content]
async def _create_collection_impl(input_data: CreateCollectionInput) -> List[types.TextContent]:
    """Implementation for creating a new collection.

    Returns:
        List containing a single TextContent object with JSON details of the created collection.
    Raises:
        McpError: If validation fails, the collection already exists, or another error occurs.
    """
    logger = get_logger("tools.collection")
    collection_name = input_data.collection_name
    metadata = input_data.metadata

    try:
        validate_collection_name(collection_name)

        client = get_chroma_client()
        embedding_function = get_embedding_function()

        # Handle metadata and default settings
        final_metadata = {}
        if metadata:
            final_metadata.update(metadata)
            # Warn if user provided metadata might conflict with settings pattern
            if any(k.startswith("chroma:setting:") for k in metadata):
                logger.warning(
                    f"Metadata for '{collection_name}' contains keys matching 'chroma:setting:'. Use set_collection_settings tool for settings."
                )
        else:
            # Apply default settings if no metadata provided
            default_settings = get_collection_settings()
            # Use the internal format ChromaDB expects for default settings via metadata
            final_metadata = {f"chroma:setting:{k.replace(':', '_')}": v for k, v in default_settings.items()}
            logger.debug(f"Creating collection '{collection_name}' with default settings: {final_metadata}")

        # Create the collection
        collection = client.create_collection(
            name=collection_name,
            metadata=final_metadata, # Pass the processed metadata
            embedding_function=embedding_function, # Ensure EF is passed if needed by client
            get_or_create=False, # Explicitly False to ensure creation error
        )

        # Prepare success result data
        count = collection.count()
        result_data = {
            "name": collection.name,
            "id": str(collection.id), # Ensure ID is string if it's UUID
            "metadata": _reconstruct_metadata(collection.metadata),
            "count": count,
        }
        result_json = json.dumps(result_data, indent=2)
        # Return content list directly
        return [types.TextContent(type="text", text=result_json)]

    except ValidationError as e:
        logger.warning(f"Validation error creating collection '{collection_name}': {e}")
        # Raise McpError
        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Validation Error: {str(e)}"))
    except ValueError as e:
        if f"Collection {collection_name} already exists." in str(e):
            logger.warning(f"Collection '{collection_name}' already exists.")
            # Raise McpError
            raise McpError(
                ErrorData(code=INVALID_PARAMS, message=f"Tool Error: Collection '{collection_name}' already exists.")
            )
        else:
            logger.error(f"Validation error during collection creation '{collection_name}': {e}", exc_info=True)
            # Raise McpError
            raise McpError(
                ErrorData(
                    code=INVALID_PARAMS,
                    message=f"Tool Error: Invalid parameter during collection creation. Details: {e}",
                )
            )
    except InvalidDimensionException as e:
        logger.error(f"Dimension error creating collection '{collection_name}': {e}", exc_info=True)
        # Raise McpError
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message=f"ChromaDB Error: Invalid dimension configuration. {str(e)}")
        )
    except Exception as e:
        logger.error(f"Unexpected error creating collection '{collection_name}': {e}", exc_info=True)
        # Raise McpError
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message=f"Tool Error: An unexpected error occurred while creating collection '{collection_name}'. Details: {str(e)}",
            )
        )


# Signature changed to accept Pydantic model and return List[TextContent]
async def _list_collections_impl(input_data: ListCollectionsInput) -> List[types.TextContent]:
    """Lists collections, optionally filtering by name and applying pagination.

    Args:
        input_data: A ListCollectionsInput object containing validated arguments.

    Returns:
        A list containing a single TextContent object with a JSON string
        detailing the paginated collection names and counts.

    Raises:
        McpError: If a validation error occurs or an unexpected exception
                  happens during client interaction.
    """
    logger = get_logger("tools.collection")
    limit = input_data.limit
    offset = input_data.offset
    name_contains = input_data.name_contains

    try:
        # Pydantic handles validation for limit/offset >= 0

        client = get_chroma_client()
        # Chroma >= 0.6.0 returns List[str] directly
        all_collection_names: List[str] = client.list_collections()

        # Apply filtering if name_contains is provided
        filtered_names = [
            name for name in all_collection_names if name_contains and name_contains.lower() in name.lower()
        ] if name_contains else all_collection_names

        total_matching_count = len(filtered_names)

        # Apply pagination
        paginated_names = filtered_names
        start_index = offset if offset is not None else 0
        end_index = (start_index + limit) if limit is not None else None

        if start_index < 0:
             start_index = 0 # Ensure start index is not negative

        paginated_names = filtered_names[start_index:end_index]

        # Prepare result
        result_data = {
            "collection_names": paginated_names,
            "total_count": total_matching_count,
            "limit": limit,
            "offset": offset,
        }
        result_json = json.dumps(result_data, indent=2)
        # Return content list directly
        return [types.TextContent(type="text", text=result_json)]

    except Exception as e:
        logger.error(f"Error listing collections: {e}", exc_info=True)
        # Raise McpError
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message=f"Tool Error: Error listing collections. Details: {str(e)}")
        )


# Signature changed to return List[Content]
async def _get_collection_impl(input_data: GetCollectionInput) -> List[types.TextContent]:
    """Retrieves details about a specific ChromaDB collection.

    Returns:
        A list containing a single TextContent object with JSON details of the collection.

    Raises:
        McpError: If the collection is not found or another error occurs.
    """
    logger = get_logger("tools.collection")
    collection_name = input_data.collection_name

    try:
        validate_collection_name(collection_name)
        client = get_chroma_client()
        # Use get_collection which raises an error if not found
        collection = client.get_collection(name=collection_name, embedding_function=get_embedding_function())

        count = collection.count()
        # Process peek results carefully, handle potential large embeddings
        peek_results = None
        try:
            # Limit peek to avoid large payloads
            peek_results = collection.peek(limit=5)
            # Remove embeddings if present, as they can be large and aren't needed for info
            if peek_results and "embeddings" in peek_results:
                del peek_results["embeddings"]
        except Exception as peek_err:
            logger.warning(f"Could not peek into collection '{collection_name}': {peek_err}")
            peek_results = {"error": f"Could not peek: {str(peek_err)}"}

        result_data = {
            "name": collection.name,
            "id": str(collection.id),
            "metadata": _reconstruct_metadata(collection.metadata),
            "count": count,
            "sample_entries": peek_results, # Include processed/limited peek
        }
        result_json = json.dumps(result_data, indent=2)
        # Return content list directly
        return [types.TextContent(type="text", text=result_json)]

    except ValueError as e:
        # Handle case where collection is not found
        error_str = str(e).lower()
        not_found = False
        if f"collection {collection_name} does not exist." in error_str:
            not_found = True
        if f"collection {collection_name} not found" in error_str:
             not_found = True
        
        if not_found:
            logger.warning(f"Collection '{collection_name}' not found.")
            raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Tool Error: Collection '{collection_name}' not found."))
        else:
            # Handle other ValueErrors
            logger.error(f"Value error getting collection '{collection_name}': {e}", exc_info=True)
            raise McpError(
                ErrorData(code=INVALID_PARAMS, message=f"Tool Error: Invalid parameter getting collection. Details: {e}")
            )
    except Exception as e:
        logger.error(f"Unexpected error getting collection '{collection_name}': {e}", exc_info=True)
        # Raise McpError
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message=f"Tool Error: An unexpected error occurred while getting collection '{collection_name}'. Details: {str(e)}",
            )
        )


# Signature changed to return List[Content]
async def _set_collection_description_impl(input_data: SetCollectionDescriptionInput) -> List[types.TextContent]:
    """Implementation for setting a collection's description.

    Returns:
        List containing a single TextContent object confirming the attempt.

    Raises:
        McpError: If the collection is not found or another error occurs.
    """
    logger = get_logger("tools.collection")
    collection_name = input_data.collection_name
    description = input_data.description

    try:
        validate_collection_name(collection_name)
        client = get_chroma_client()

        # Get the collection first
        collection = client.get_collection(name=collection_name)

        # Construct metadata update
        metadata_update = {"description": description}

        # Call modify with the new description in metadata
        logger.warning(
            f"Attempting to set description for '{collection_name}'. This operation might replace other metadata."
        )
        collection.modify(metadata=metadata_update)
        logger.info(f"Description set attempt for collection '{collection_name}' completed.")

        # Return confirmation message in content list
        return [
            types.TextContent(
                type="text", text=f"Attempted to set description for collection '{collection_name}' to '{description}'."
            )
        ]

    except ValueError as e:
        if (
            f"Collection {collection_name} does not exist." in str(e) or 
            f"Collection {collection_name} not found" in str(e).lower()
        ): # Added lower() for safety
            logger.warning(f"Cannot set description: Collection '{collection_name}' not found.")
            # Raise McpError
            raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Tool Error: Collection '{collection_name}' not found."))
        else:
            logger.error(f"Value error setting description for '{collection_name}': {e}", exc_info=True)
            # Raise McpError
            raise McpError(
                ErrorData(
                    code=INVALID_PARAMS, message=f"Tool Error: Invalid parameter setting description. Details: {e}"
                )
            )
    except Exception as e:
        # Catch errors during the modify operation specifically
        logger.error(f"Error during collection.modify for description on '{collection_name}': {e}", exc_info=True)
        # Raise McpError
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message=f"Tool Error: Failed during modify operation for '{collection_name}'. Details: {str(e)}",
            )
        )


# Signature changed to return List[Content]
async def _set_collection_settings_impl(input_data: SetCollectionSettingsInput) -> List[types.TextContent]:
    """Implementation for setting a collection's settings.

    Returns:
        List containing a single TextContent object confirming the attempt.

    Raises:
        McpError: If the collection is not found or another error occurs.
    """
    logger = get_logger("tools.collection")
    collection_name = input_data.collection_name
    settings = input_data.settings

    try:
        validate_collection_name(collection_name)

        client = get_chroma_client()
        collection = client.get_collection(name=collection_name)

        # Get current metadata (optional, depends on whether modify merges or replaces)
        # Assuming modify MERGES or we handle merging here if needed.
        # If modify REPLACES, we MUST fetch existing non-setting metadata first.
        # Current Chroma `modify` seems to merge, but let's be safe if behavior changes.
        current_metadata = collection.metadata or {}

        # Prepare the metadata update block with prefixed setting keys
        # Only include keys from the input settings
        settings_update = {f"chroma:setting:{k.replace(':', '_')}": v for k, v in settings.items()}

        # Merge new settings with existing metadata
        # Prioritize new settings if keys overlap (though settings keys shouldn't overlap with user meta)
        final_metadata = {**current_metadata, **settings_update}

        logger.warning(
            f"Attempting to set settings for '{collection_name}'. This operation might replace other metadata or fail depending on ChromaDB version."
        )
        collection.modify(metadata=final_metadata) # Modify with merged data
        logger.info(f"Settings update attempt for collection '{collection_name}' completed.")

        # Return confirmation message
        return [
            types.TextContent(
                type="text", text=f"Attempted to set settings for collection '{collection_name}'. Verify persistence."
            )
        ]

    except ValueError as e:
        error_str = str(e).lower()
        not_found = False
        if f"collection {collection_name} does not exist." in error_str:
            not_found = True
        if f"collection {collection_name} not found" in error_str:
            not_found = True
        
        if not_found:
            logger.warning(f"Cannot set settings: Collection '{collection_name}' not found.")
            raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Tool Error: Collection '{collection_name}' not found."))
        else:
            logger.error(f"Value error setting settings for '{collection_name}': {e}", exc_info=True)
            raise McpError(
                ErrorData(code=INVALID_PARAMS, message=f"Tool Error: Invalid parameter setting settings. Details: {e}")
            )
    except Exception as e:
        logger.error(f"Error during collection.modify for settings on '{collection_name}': {e}", exc_info=True)
        # Raise McpError
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message=f"Tool Error: Failed during modify operation for '{collection_name}'. Details: {str(e)}",
            )
        )


# Signature changed to return List[Content]
async def _update_collection_metadata_impl(input_data: UpdateCollectionMetadataInput) -> List[types.TextContent]:
    """Updates custom key-value pairs in a collection's metadata.
    Warning: This REPLACES the existing custom metadata block. Likely fails on existing collections.

    Args:
        input_data: An UpdateCollectionMetadataInput object containing validated arguments.

    Returns:
        List containing a single TextContent object confirming the attempt.

    Raises:
        McpError: If validation fails, collection not found, or another error occurs.
    """
    logger = get_logger("tools.collection")
    collection_name = input_data.collection_name
    metadata_update = input_data.metadata_update

    try:
        validate_collection_name(collection_name)

        client = get_chroma_client()
        collection = client.get_collection(name=collection_name)

        # Modify metadata - WARNING: Replaces ENTIRE metadata block in some Chroma versions.
        logger.warning(
            f"Attempting to update metadata for '{collection_name}'. This operation might replace the entire metadata block."
        )
        collection.modify(metadata=metadata_update)  # Use the provided update directly
        logger.info(f"Modify call completed for metadata update on '{collection_name}'. Verification needed.")
        # Return confirmation message in content list
        return [
            types.TextContent(
                type="text",
                text=f"Attempted to update metadata for collection '{collection_name}'. Note: Behavior depends heavily on ChromaDB version (may replace all metadata).",
            )
        ]

    except ValidationError as e:
        logger.warning(f"Validation error updating metadata for '{collection_name}': {e}")
        # Raise McpError
        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Validation Error: {str(e)}"))
    except ValueError as e:  # Catch collection not found from get_collection
        error_str = str(e).lower()
        not_found = False
        if f"collection {collection_name} does not exist." in error_str:
            not_found = True
        if f"collection {collection_name} not found" in error_str:
             not_found = True

        if not_found:
            logger.warning(f"Cannot update metadata: Collection '{collection_name}' not found.")
            # Raise McpError
            raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Tool Error: Collection '{collection_name}' not found."))
        else:
            logger.error(f"Value error updating metadata for '{collection_name}': {e}", exc_info=True)
            # Raise McpError
            raise McpError(
                ErrorData(
                    code=INVALID_PARAMS, message=f"Tool Error: Problem accessing collection '{collection_name}'. Details: {e}"
                )
            )
    except Exception as e: # Catch errors during modify itself
        logger.error(
            f"Error during collection.modify for metadata update on '{collection_name}': {e}", exc_info=True
        )
        # Raise McpError
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message=f"Tool Error: Failed during modify operation for '{collection_name}'. Details: {str(e)}",
            )
        )


# Signature changed to return List[Content]
async def _rename_collection_impl(input_data: RenameCollectionInput) -> List[types.TextContent]:
    """Implementation for renaming a collection.

    Returns:
        List containing a single TextContent object confirming the rename.

    Raises:
        McpError: If validation fails, collection not found, name exists, or another error occurs.
    """
    logger = get_logger("tools.collection")
    original_name = input_data.collection_name
    new_name = input_data.new_name

    try:
        # Validate both names first
        validate_collection_name(original_name)
        validate_collection_name(new_name)

        client = get_chroma_client()

        # Check if original collection exists
        collection = client.get_collection(name=original_name)

        # Attempt to modify the name
        logger.info(f"Attempting to rename collection '{original_name}' to '{new_name}'.")
        collection.modify(name=new_name) # Use modify with the new name
        logger.info(f"Collection rename attempt from '{original_name}' to '{new_name}' completed.")

        # Return confirmation message
        return [
            types.TextContent(
                type="text", text=f"Collection '{original_name}' successfully renamed to '{new_name}'."
            )
        ]

    except ValidationError as e:
        logger.warning(f"Validation error renaming collection '{original_name}': {e}")
        # Raise McpError for validation failure
        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Validation Error: {str(e)}"))
    except ValueError as e:
        error_str = str(e).lower()
        # Check for original not found from get_collection
        original_not_found = False
        if f"collection {original_name} does not exist." in error_str:
            original_not_found = True
        if f"collection {original_name} not found" in error_str:
            original_not_found = True
        
        if original_not_found:
            logger.warning(f"Cannot rename: Collection '{original_name}' not found.")
            raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Tool Error: Collection '{original_name}' not found."))
        
        # Check for new name exists from modify
        new_name_exists = False
        if f"collection {new_name} already exists." in error_str:
             new_name_exists = True

        if new_name_exists:
            logger.warning(f"Cannot rename: New collection name '{new_name}' already exists.")
            raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Tool Error: Collection name '{new_name}' already exists."))
        
        # Handle other ValueErrors
        logger.error(f"Value error renaming collection '{original_name}': {e}", exc_info=True)
        raise McpError(
            ErrorData(code=INVALID_PARAMS, message=f"Tool Error: Invalid parameter during rename. Details: {e}")
        )
    except Exception as e:
        logger.error(f"Unexpected error renaming collection '{original_name}': {e}", exc_info=True)
        # Raise McpError
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message=f"Tool Error: An unexpected error occurred renaming collection '{original_name}'. Details: {str(e)}",
            )
        )


# Signature changed to return List[Content]
async def _delete_collection_impl(input_data: DeleteCollectionInput) -> List[types.TextContent]:
    """Implementation for deleting a collection.

    Returns:
        List containing a single TextContent object confirming deletion.

    Raises:
        McpError: If the collection is not found or another error occurs.
    """
    logger = get_logger("tools.collection")
    collection_name = input_data.collection_name

    try:
        validate_collection_name(collection_name)
        client = get_chroma_client()

        # Attempt to delete the collection
        logger.info(f"Attempting to delete collection '{collection_name}'.")
        client.delete_collection(name=collection_name)
        logger.info(f"Collection '{collection_name}' deleted successfully.")

        # Return confirmation message
        return [
            types.TextContent(
                type="text", text=f"Collection '{collection_name}' deleted successfully."
            )
        ]

    except ValueError as e:
        # Handle collection not found during delete
        error_str = str(e).lower()
        not_found = False
        if f"collection {collection_name} does not exist." in error_str:
            not_found = True
        # Check alternate message format sometimes seen
        if f"collection named {collection_name} does not exist" in error_str:
             not_found = True
        
        if not_found:
            logger.warning(f"Collection '{collection_name}' not found for deletion.")
            raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Tool Error: Collection '{collection_name}' not found."))
        else:
            logger.error(f"Value error deleting collection '{collection_name}': {e}", exc_info=True)
            raise McpError(
                ErrorData(code=INVALID_PARAMS, message=f"Tool Error: Invalid parameter deleting collection. Details: {e}")
            )
    except Exception as e:
        logger.error(f"Unexpected error deleting collection '{collection_name}': {e}", exc_info=True)
        # Raise McpError
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message=f"Tool Error: An unexpected error occurred deleting collection '{collection_name}'. Details: {str(e)}",
            )
        )


# Signature changed to return List[Content]
async def _peek_collection_impl(input_data: PeekCollectionInput) -> List[types.TextContent]:
    """Retrieves a small sample of entries from a collection.

    Returns:
        List containing a single TextContent object with JSON results of the peek.

    Raises:
        McpError: If the collection is not found or another error occurs.
    """
    logger = get_logger("tools.collection")
    collection_name = input_data.collection_name
    limit = input_data.limit

    try:
        validate_collection_name(collection_name)

        client = get_chroma_client()
        collection = client.get_collection(name=collection_name)

        # Call peek with the validated limit (or None if not provided, letting Chroma use its default)
        peek_results = collection.peek(limit=limit if limit is not None else 10) # Pass explicit default if None
        # --- DEBUG LOGGING ---
        logger.debug(f"Peek results raw type: {type(peek_results)}")
        logger.debug(f"Peek results raw content: {peek_results}")
        # --- END DEBUG LOGGING ---

        # Process results to make them JSON serializable if needed
        # Check if peek_results is not None before attempting to copy
        processed_peek = peek_results.copy() if peek_results is not None else {}
        # Convert numpy arrays (or anything with a tolist() method) to lists
        # Check existence and non-None value explicitly before processing
        if "embeddings" in processed_peek and processed_peek["embeddings"] is not None:
            # Embeddings can be List[Optional[np.ndarray]] or List[List[Optional[np.ndarray]]]
            embeddings_list = processed_peek["embeddings"]
            new_embeddings = []
            for item in embeddings_list:
                 if isinstance(item, list): # Handle potential nested lists
                     inner_list = []
                     for emb_arr in item:
                          inner_list.append(emb_arr.tolist() if hasattr(emb_arr, 'tolist') else emb_arr)
                     new_embeddings.append(inner_list)
                 elif hasattr(item, 'tolist'): # Handle top-level numpy arrays
                     new_embeddings.append(item.tolist())
                 else: # Handle other types or None
                      new_embeddings.append(item)
            processed_peek["embeddings"] = new_embeddings

        # Also process distances if present
        # Check existence and non-None value explicitly before processing
        if "distances" in processed_peek and processed_peek["distances"] is not None:
             distances_list = processed_peek["distances"]
             new_distances = []
             for item in distances_list:
                   if isinstance(item, list):
                        inner_list = []
                        for dist_arr in item:
                             inner_list.append(dist_arr.tolist() if hasattr(dist_arr, 'tolist') else dist_arr)
                        new_distances.append(inner_list)
                   elif hasattr(item, 'tolist'):
                        new_distances.append(item.tolist())
                   else:
                        new_distances.append(item)
             processed_peek["distances"] = new_distances


        result_json = json.dumps(processed_peek, indent=2)
        # Return content list directly
        return [types.TextContent(type="text", text=result_json)]

    except ValueError as e:  # Catch collection not found from get_collection
        error_str = str(e).lower()
        not_found = False
        if f"collection {collection_name} does not exist." in error_str:
            not_found = True
        if f"collection {collection_name} not found" in error_str:
             not_found = True

        if not_found:
            logger.warning(f"Cannot peek: Collection '{collection_name}' not found.")
            # Raise McpError
            raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Tool Error: Collection '{collection_name}' not found."))
        else:
            logger.error(f"Value error peeking collection '{collection_name}': {e}", exc_info=True)
            # Raise McpError
            raise McpError(
                ErrorData(
                    code=INVALID_PARAMS, message=f"Tool Error: Problem accessing collection '{collection_name}'. Details: {e}"
                )
            )
    except Exception as e:
        logger.error(f"Unexpected error peeking collection '{collection_name}': {e}", exc_info=True)
        # Raise McpError
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message=f"Tool Error: An unexpected error occurred peeking collection '{collection_name}'. Details: {str(e)}",
            )
        )


def _get_collection_info(collection) -> dict:
    """Helper to get basic info (name, id, metadata) about a collection object."""
    # ADD logger assignment inside the function
    logger = get_logger("tools.collection")
    try:
        return {
            "name": collection.name,
            "id": str(collection.id),
            "metadata": _reconstruct_metadata(collection.metadata),
        }
    except Exception as e:
        logger.error(f"Failed to get info for collection: {e}", exc_info=True)
        return {"error": f"Failed to retrieve collection info: {str(e)}"}
