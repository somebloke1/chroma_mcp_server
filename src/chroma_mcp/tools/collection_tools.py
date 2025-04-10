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

from typing import Any, Dict, List, Optional, Union, cast
from dataclasses import dataclass

from chromadb.api.types import CollectionMetadata, GetResult, QueryResult
from chromadb.errors import InvalidDimensionException

from mcp import types
from mcp.types import ErrorData, INVALID_PARAMS, INTERNAL_ERROR
from mcp.shared.exceptions import McpError

from ..app import mcp
from ..utils import (
    get_logger, 
    get_chroma_client, 
    get_embedding_function, 
    validate_input, 
    ValidationError, # Keep this if used
    ClientError, # Keep this if used
    ConfigurationError # Keep this if used
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
            original_key = key[len("chroma:setting:"):].replace('_', ':')
            setting_key_to_store = original_key
        # Also recognize common raw keys like hnsw:*
        elif key.startswith("hnsw:"):
            setting_key_to_store = key
        
        if setting_key_to_store:
            settings[setting_key_to_store] = value
        # Explicitly check for 'description' as it's handled separately
        elif key == 'description':
            reconstructed[key] = value
        # Store other keys directly (custom user keys)
        elif not key.startswith("chroma:"): # Avoid other potential internal chroma keys
            reconstructed[key] = value
    
    if settings:
        reconstructed["settings"] = settings
        
    return reconstructed

# Get logger instance for this module
logger = get_logger("tools.collection")

# --- Implementation Functions ---

@mcp.tool(name="chroma_create_collection", description="Create a new ChromaDB collection with specific or default settings. If `metadata` is provided, it overrides the default settings (e.g., HNSW parameters). If `metadata` is None or omitted, default settings are used. Use other tools like 'set_collection_description' to modify mutable metadata later.")
async def _create_collection_impl(collection_name: str, metadata: Dict[str, Any] = None) -> types.CallToolResult:
    """Creates a new ChromaDB collection.

    Args:
        collection_name: The name for the new collection. Must adhere to ChromaDB
                         naming conventions (e.g., length, allowed characters).
        metadata: An optional dictionary containing metadata and settings.
                  Keys like 'description' or 'settings' (containing HNSW params like 'hnsw:space')
                  can be provided. If omitted, default settings are used.

    Returns:
        A CallToolResult object.
        On success, content contains a TextContent object with a JSON string
        detailing the created collection's name, id, metadata, count, and
        sample entries (up to 5).
        On error (e.g., validation error, collection exists, unexpected issue),
        isError is True and content contains a TextContent object with an
        error message.
    """

    try:
        validate_collection_name(collection_name)
        client = get_chroma_client()
        
        # Determine metadata: Use provided or get defaults
        metadata_to_use = None
        log_msg_suffix = ""
        if metadata is not None:
            if not isinstance(metadata, dict):
                logger.warning(f"Invalid metadata type provided: {type(metadata)}")
                return types.CallToolResult(isError=True, content=[types.TextContent(type="text", text="Tool Error: metadata must be a dictionary.")])
            metadata_to_use = metadata
            log_msg_suffix = "with provided metadata."
        else:
            metadata_to_use = get_collection_settings()
            log_msg_suffix = "with default settings."

        # Call create_collection directly with embedding function and target metadata
        logger.debug(f"Attempting to create collection '{collection_name}' with embedding function and metadata: {metadata_to_use}")
        collection = client.create_collection(
            name=collection_name,
            metadata=metadata_to_use,
            embedding_function=get_embedding_function(),
            get_or_create=False
        )
        logger.info(f"Created collection: {collection_name} {log_msg_suffix}")

        # Get the count (should be 0)
        count = collection.count()
        # REMOVED: peek_results = collection.peek(limit=5) # Useless on a new collection

        # REMOVED: Process peek_results logic is no longer needed here
        # processed_peek = peek_results.copy() if peek_results else {}
        # if processed_peek.get("embeddings"):
        #     # Convert numpy arrays (or anything with a tolist() method) to lists
        #     processed_peek["embeddings"] = [
        #         arr.tolist() if hasattr(arr, 'tolist') and callable(arr.tolist) else arr 
        #         for arr in processed_peek["embeddings"] if arr is not None # Added check for None elements
        #     ]

        result_data = {
            "name": collection.name,
            "id": str(collection.id), # Ensure ID is string if it's UUID
            "metadata": _reconstruct_metadata(collection.metadata),
            "count": count,
            # REMOVED: "sample_entries": processed_peek
        }
        # Serialize success result to JSON
        result_json = json.dumps(result_data, indent=2)
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=result_json)]
        )

    except ValidationError as e:
        logger.warning(f"Validation error creating collection '{collection_name}': {e}")
        return types.CallToolResult(
            isError=True,
            content=[types.TextContent(type="text", text=f"Validation Error: {str(e)}")]
        )
    except ValueError as e:
        # Check if the error message indicates a duplicate collection
        if f"Collection {collection_name} already exists." in str(e):
            logger.warning(f"Collection '{collection_name}' already exists.")
            return types.CallToolResult(
                isError=True,
                content=[types.TextContent(type="text", text=f"Tool Error: Collection '{collection_name}' already exists.")]
            )
        else:
            # Handle other ValueErrors as likely invalid parameters
            logger.error(f"Validation error during collection creation '{collection_name}': {e}", exc_info=True)
            return types.CallToolResult(
                isError=True,
                content=[types.TextContent(type="text", text=f"Tool Error: Invalid parameter during collection creation. Details: {e}")]
            )
    except InvalidDimensionException as e: # Example of another specific Chroma error
        logger.error(f"Dimension error creating collection '{collection_name}': {e}", exc_info=True)
        return types.CallToolResult(
            isError=True,
            content=[types.TextContent(type="text", text=f"ChromaDB Error: Invalid dimension configuration. {str(e)}")]
        )
    except Exception as e:
        # Log the full unexpected error server-side
        logger.error(f"Unexpected error creating collection '{collection_name}': {e}", exc_info=True)
        # Return a Tool Error instead of raising McpError
        return types.CallToolResult(
            isError=True,
            content=[types.TextContent(type="text", text=f"Tool Error: An unexpected error occurred while creating collection '{collection_name}'. Details: {str(e)}")]
        )

@mcp.tool(name="chroma_list_collections", description="List all collections with optional filtering and pagination.")
async def _list_collections_impl(limit: Optional[int] = None, offset: Optional[int] = None, name_contains: Optional[str] = None) -> types.CallToolResult:
    """Lists available ChromaDB collections.

    Args:
        limit: The maximum number of collection names to return. 0 means no limit.
               Defaults to 0 (no limit). Must be non-negative.
        offset: The number of collection names to skip from the beginning.
                Defaults to 0. Must be non-negative.
        name_contains: An optional string to filter collections by name (case-insensitive).
                       Only collections whose names contain this string will be returned.
                       Defaults to None (no filtering).

    Returns:
        A CallToolResult object.
        On success, content contains a TextContent object with a JSON string
        containing a list of 'collection_names', the 'total_count' (before pagination),
        and the requested 'limit' and 'offset'.
        On error (e.g., validation error, unexpected issue), isError is True and
        content contains a TextContent object with an error message.
    """

    try:
        # Assign effective defaults if None
        effective_limit = 0 if limit is None else limit
        effective_offset = 0 if offset is None else offset

        # Input validation
        if effective_limit < 0:
            raise ValidationError("limit cannot be negative")
        if effective_offset < 0:
            raise ValidationError("offset cannot be negative")
            
        client = get_chroma_client()
        # In ChromaDB v0.5+, list_collections returns Collection objects
        # The code needs to handle this correctly.
        all_collections = client.list_collections()
        
        # Correctly extract names from Collection objects
        collection_names = []
        if isinstance(all_collections, list):
            for col in all_collections:
                try:
                    # Access the name attribute of the Collection object
                    collection_names.append(col.name)
                except AttributeError:
                    logger.warning(f"Object in list_collections result does not have a .name attribute: {type(col)}")
        else:
             logger.warning(f"client.list_collections() returned unexpected type: {type(all_collections)}")
            
        # Safety check, though Chroma client should return a list of Collections (already handled above)
        # if not isinstance(collection_names, list): # This check is redundant now
        #     logger.warning(f"client.list_collections() yielded unexpected structure, processing as empty list.")
        #     collection_names = []
            
        # Explicitly check for None before filtering
        if name_contains is not None:
            filtered_names = [name for name in collection_names if name_contains.lower() in name.lower()]
        else:
            filtered_names = collection_names
            
        total_count = len(filtered_names)
        start_index = effective_offset
        # Apply limit only if it's positive; 0 means no limit
        end_index = (start_index + effective_limit) if effective_limit > 0 else len(filtered_names)
        paginated_names = filtered_names[start_index:end_index]
        
        result_data = {
            "collection_names": paginated_names,
            "total_count": total_count,
            "limit": effective_limit, # Return the effective limit used
            "offset": effective_offset # Return the effective offset used
        }
        result_json = json.dumps(result_data, indent=2)
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=result_json)]
        )
        
    except ValidationError as e:
        logger.warning(f"Validation error listing collections: {e}")
        return types.CallToolResult(
            isError=True,
            content=[types.TextContent(type="text", text=f"Validation Error: {str(e)}")]
        )
    # Catch other potential ChromaDB or client connection errors if necessary
    # except SomeChromaError as e: ... return CallToolResult(isError=True, ...)
    except Exception as e:
        logger.error(f"Unexpected error listing collections: {e}", exc_info=True)
        # Return a Tool Error instead of raising McpError
        return types.CallToolResult(
            isError=True,
            content=[types.TextContent(type="text", text=f"Tool Error: An unexpected error occurred while listing collections. Details: {str(e)}")]
        )

@mcp.tool(name="chroma_get_collection", description="Get information about a specific collection.")
async def _get_collection_impl(collection_name: str) -> types.CallToolResult:
    """Retrieves details about a specific ChromaDB collection.

    Args:
        collection_name: The name of the collection to retrieve.

    Returns:
        A CallToolResult object.
        On success, content contains a TextContent object with a JSON string
        detailing the collection's name, id, metadata, count, and sample
        entries (up to 5).
        On error (e.g., collection not found, unexpected issue), isError is True
        and content contains a TextContent object with an error message.
    """

    try:
        client = get_chroma_client()
        # get_collection raises ValueError if not found
        collection = client.get_collection(
            name=collection_name,
            embedding_function=get_embedding_function()
        )
        count = collection.count()
        # Limit peek results
        peek_results = collection.peek(limit=5) 

        # Process peek_results to ensure JSON serializability (convert ndarrays)
        processed_peek = peek_results.copy() if peek_results else {}
        if processed_peek.get("embeddings"):
            # Convert numpy arrays (or anything with a tolist() method) to lists
            processed_peek["embeddings"] = [
                arr.tolist() if hasattr(arr, 'tolist') and callable(arr.tolist) else arr 
                for arr in processed_peek["embeddings"] if arr is not None
            ]

        result_data = {
            "name": collection.name,
            "id": str(collection.id), # Ensure ID is string
            "metadata": _reconstruct_metadata(collection.metadata),
            "count": count,
            "sample_entries": processed_peek # Use processed results
        }
        # Convert dict containing potentially non-serializable items to JSON
        # Using a custom handler might be more robust if other types arise
        result_json = json.dumps(result_data, indent=2)
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=result_json)]
        )
        
    except ValueError as e:
        # ChromaDB often raises ValueError for not found
        logger.warning(f"Error getting collection '{collection_name}': {e}")
        # Check if the error message indicates "not found"
        if f"Collection {collection_name} does not exist." in str(e):
            error_msg = f"ChromaDB Error: Collection '{collection_name}' not found."
        else:
             # Keep the original ValueError message if it's something else
            error_msg = f"ChromaDB Value Error: {str(e)}"
        return types.CallToolResult(
            isError=True,
            content=[types.TextContent(type="text", text=error_msg)]
        )
    except Exception as e:
        logger.error(f"Unexpected error getting collection '{collection_name}': {e}", exc_info=True)
        # Return a Tool Error instead of raising McpError
        return types.CallToolResult(
            isError=True,
            content=[types.TextContent(type="text", text=f"Tool Error: An unexpected error occurred while getting collection '{collection_name}'. Details: {str(e)}")]
        )

@mcp.tool(name="chroma_set_collection_description", description="Sets or updates the description of a collection. Note: Due to ChromaDB limitations, this tool will likely fail on existing collections. Set description during creation via metadata instead.")
async def _set_collection_description_impl(collection_name: str, description: str) -> types.CallToolResult:
    """Sets the description metadata field for a collection.

    Warning: This operation might fail if the collection has immutable settings
             (like HNSW parameters) already defined.

    Args:
        collection_name: The name of the collection to modify.
        description: The new description string to set.

    Returns:
        A CallToolResult object.
        On success, content contains a TextContent object with a JSON string
        detailing the updated collection's info (name, id, metadata, etc.).
        On error (e.g., collection not found, immutable settings conflict,
        unexpected issue), isError is True and content contains a TextContent
        object with an error message.
    """

    try:
        client = get_chroma_client()

        # Try to get the collection first, handle not found error
        try:
            collection = client.get_collection(name=collection_name, embedding_function=get_embedding_function())
        except ValueError as e:
             # Check if it's the specific "not found" error
            if f"Collection {collection_name} does not exist." in str(e):
                logger.warning(f"Cannot set description: Collection '{collection_name}' not found.")
                return types.CallToolResult(
                    isError=True,
                    content=[types.TextContent(type="text", text=f"Tool Error: Collection '{collection_name}' not found.")]
                )
            else:
                # Re-raise other ValueErrors to be caught by the generic handler below
                raise e

        # Check for immutable settings (example: hnsw)
        current_metadata = collection.metadata or {}
        if any(k.startswith("hnsw:") for k in current_metadata):
            logger.warning(f"Attempted to set description on collection '{collection_name}' with immutable settings.")
            # Return MCP-compliant error
            return types.CallToolResult( 
                isError=True,
                content=[types.TextContent(type="text", text="Tool Error: Cannot set description on collections with existing immutable settings (e.g., hnsw:*). Modify operation aborted.")]
            )

        # If no immutable settings, proceed with modify
        # Note: modify might raise its own errors, caught by generic Exception handler
        collection.modify(metadata={ "description": description })
        logger.info(f"Set description for collection: {collection_name}")

        # Return the updated collection info by calling the refactored get function
        return await _get_collection_impl(collection_name)

    except ValueError as e: # Catch ValueErrors re-raised from the inner try block
        logger.error(f"Value error during set description for '{collection_name}': {e}", exc_info=False) # No need for full trace here usually
        # It's likely not the "not found" error if it reached here
        return types.CallToolResult(
             isError=True,
             content=[types.TextContent(type="text", text=f"ChromaDB Value Error: {str(e)}")]
         )
    except Exception as e:
        logger.error(f"Unexpected error setting description for collection '{collection_name}': {e}", exc_info=True)
        # Return a Tool Error instead of raising McpError
        return types.CallToolResult(
            isError=True,
            content=[types.TextContent(type="text", text=f"Tool Error: An unexpected error occurred while setting description for '{collection_name}'. Details: {str(e)}")]
        )

@mcp.tool(name="chroma_set_collection_settings", description="Sets or updates the settings (e.g., HNSW parameters) of a collection. Warning: This replaces existing settings. This will likely fail on existing collections due to immutable settings. Define settings during creation via metadata.")
async def _set_collection_settings_impl(collection_name: str, settings: Dict[str, Any]) -> types.CallToolResult:
    """Sets the 'settings' metadata block for a collection.

    Warning: This replaces any existing 'settings' and might fail if the
             collection has immutable settings (like HNSW parameters) already defined.

    Args:
        collection_name: The name of the collection to modify.
        settings: A dictionary containing the settings key-value pairs (e.g.,
                  {'hnsw:space': 'cosine'}).

    Returns:
        A CallToolResult object.
        On success, content contains a TextContent object with a JSON string
        detailing the updated collection's info (name, id, metadata including
        the new settings, etc.).
        On error (e.g., collection not found, invalid settings format, immutable
        settings conflict, unexpected issue), isError is True and content contains
        a TextContent object with an error message.
    """

    try:
        # Input validation for settings type
        if not isinstance(settings, dict):
            logger.warning(f"Invalid settings type provided for set_collection_settings: {type(settings)}")
            return types.CallToolResult(
                isError=True,
                content=[types.TextContent(type="text", text="Tool Error: settings parameter must be a dictionary.")]
            )

        client = get_chroma_client()

        # Try to get the collection first, handle not found error
        try:
            collection = client.get_collection(name=collection_name, embedding_function=get_embedding_function())
        except ValueError as e:
             # Check if it's the specific "not found" error
            if f"Collection {collection_name} does not exist." in str(e):
                logger.warning(f"Cannot set settings: Collection '{collection_name}' not found.")
                return types.CallToolResult(
                    isError=True,
                    content=[types.TextContent(type="text", text=f"Tool Error: Collection '{collection_name}' not found.")]
                )
            else:
                # Re-raise other ValueErrors
                raise e

        # Check for immutable settings (existing hnsw:* keys in current metadata)
        current_metadata = collection.metadata or {}
        if any(k.startswith("hnsw:") for k in current_metadata):
            logger.warning(f"Attempted to set settings on collection '{collection_name}' with immutable settings.")
            return types.CallToolResult(
                isError=True,
                content=[types.TextContent(type="text", text="Tool Error: Cannot set settings on collections with existing immutable settings (e.g., hnsw:*). Modify operation aborted.")]
            )

        # Prepare metadata, preserving description and other custom keys
        current_metadata_safe = collection.metadata or {}
        preserved_metadata = { 
            k: v for k, v in current_metadata_safe.items() 
            # Keep description and any non-setting, non-hnsw keys
            if k == 'description' or (not k.startswith(("chroma:setting:", "hnsw:")))
        }
        # Format new settings keys correctly for storing
        formatted_settings = {f"chroma:setting:{k.replace(':', '_')}": v for k, v in settings.items()}
        # Combine preserved data with new flattened settings
        updated_metadata = {**preserved_metadata, **formatted_settings}
        
        # Modify the collection
        collection.modify(metadata=updated_metadata)
        logger.info(f"Set settings for collection: {collection_name}")

        # Return updated collection info by calling get_collection_impl
        # which will use _reconstruct_metadata
        return await _get_collection_impl(collection_name)

    except ValueError as e: # Catch ValueErrors re-raised from the inner try block
        logger.error(f"Value error during set settings for '{collection_name}': {e}", exc_info=False)
        return types.CallToolResult(
             isError=True,
             content=[types.TextContent(type="text", text=f"ChromaDB Value Error: {str(e)}")]
         )
    except Exception as e:
        logger.error(f"Unexpected error setting settings for collection '{collection_name}': {e}", exc_info=True)
        # Return a Tool Error instead of raising McpError
        return types.CallToolResult(
            isError=True,
            content=[types.TextContent(type="text", text=f"Tool Error: An unexpected error occurred while setting settings for '{collection_name}'. Details: {str(e)}")]
        )

@mcp.tool(name="chroma_update_collection_metadata", description="Updates or adds custom key-value pairs to a collection's metadata (merge). Warning: This REPLACES the entire existing custom metadata block. This will likely fail on existing collections due to immutable settings. Set metadata during creation.")
async def _update_collection_metadata_impl(collection_name: str, metadata_update: Dict[str, Any]) -> types.CallToolResult:
    """Updates custom key-value pairs in a collection's metadata.

    Warning: This merges the provided dictionary with existing custom metadata.
             It cannot modify reserved keys like 'description' or 'settings'.
             It might fail if the collection has immutable settings (like HNSW).

    Args:
        collection_name: The name of the collection to modify.
        metadata_update: A dictionary containing the custom key-value pairs
                         to add or update. Keys must not be reserved ('description',
                         'settings', etc.).

    Returns:
        A CallToolResult object.
        On success, content contains a TextContent object with a JSON string
        detailing the updated collection's info (name, id, merged metadata, etc.).
        On error (e.g., collection not found, attempt to update reserved keys,
        immutable settings conflict, unexpected issue), isError is True and
        content contains a TextContent object with an error message.
    """

    try:
        # Input validation for metadata_update type
        if not isinstance(metadata_update, dict):
            logger.warning(f"Invalid metadata_update type provided: {type(metadata_update)}")
            return types.CallToolResult(
                isError=True,
                content=[types.TextContent(type="text", text="Tool Error: metadata_update parameter must be a dictionary.")]
            )
            
        # Input validation for reserved keys
        reserved_keys = ["description", "settings"]
        if any(key in reserved_keys or key.startswith(("chroma:setting:", "hnsw:")) for key in metadata_update):
            logger.warning(f"Attempted to update reserved/immutable keys via update_metadata: {list(metadata_update.keys())}")
            return types.CallToolResult(
                isError=True,
                content=[types.TextContent(type="text", text="Tool Error: Cannot update reserved keys ('description', 'settings', 'chroma:setting:...', 'hnsw:...') via this tool. Use dedicated tools or recreate the collection.")]
            )
            
        client = get_chroma_client()

        # Try to get the collection first, handle not found error
        try:
            collection = client.get_collection(name=collection_name, embedding_function=get_embedding_function())
        except ValueError as e:
             # Check if it's the specific "not found" error
            if f"Collection {collection_name} does not exist." in str(e):
                logger.warning(f"Cannot update metadata: Collection '{collection_name}' not found.")
                return types.CallToolResult(
                    isError=True,
                    content=[types.TextContent(type="text", text=f"Tool Error: Collection '{collection_name}' not found.")]
                )
            else:
                # Re-raise other ValueErrors
                raise e

        # Check for immutable settings (hnsw:*) again
        current_metadata = collection.metadata or {}
        if any(k.startswith("hnsw:") for k in current_metadata):
            logger.warning(f"Attempted to update metadata on collection '{collection_name}' with immutable settings.")
            return types.CallToolResult(
                isError=True,
                content=[types.TextContent(type="text", text="Tool Error: Cannot update metadata on collections with existing immutable settings (e.g., hnsw:*). Modify operation aborted.")]
            )

        # Merge metadata: Start with existing, then update with new keys
        current_metadata_safe = collection.metadata or {}
        merged_metadata = current_metadata_safe.copy()
        # Only add/update keys from metadata_update (don't overwrite description/settings)
        for key, value in metadata_update.items():
            # Double-check against reserved keys just in case
            if key != 'description' and not key.startswith(("chroma:setting:", "hnsw:")):
                 merged_metadata[key] = value
            else:
                 logger.warning(f"Skipping attempt to update reserved key '{key}' via update_metadata in collection '{collection_name}'")

        # Modify the collection
        collection.modify(metadata=merged_metadata)
        logger.info(f"Updated custom metadata for collection: {collection_name}")

        # Return updated collection info
        return await _get_collection_impl(collection_name)

    except ValueError as e: # Catch ValueErrors re-raised from the inner try block
        logger.error(f"Value error during update metadata for '{collection_name}': {e}", exc_info=False)
        return types.CallToolResult(
             isError=True,
             content=[types.TextContent(type="text", text=f"ChromaDB Value Error: {str(e)}")]
         )
    except Exception as e:
        logger.error(f"Unexpected error updating metadata for collection '{collection_name}': {e}", exc_info=True)
        # Return a Tool Error instead of raising McpError
        return types.CallToolResult(
            isError=True,
            content=[types.TextContent(type="text", text=f"Tool Error: An unexpected error occurred while updating metadata for '{collection_name}'. Details: {str(e)}")]
        )

@mcp.tool(name="chroma_rename_collection", description="Renames an existing collection.")
async def _rename_collection_impl(collection_name: str, new_name: str) -> types.CallToolResult:
    """Renames an existing ChromaDB collection.

    Args:
        collection_name: The current name of the collection.
        new_name: The desired new name for the collection. Must be valid according
                  to ChromaDB naming rules and not already exist.

    Returns:
        A CallToolResult object.
        On success, content contains a TextContent object with a JSON string
        detailing the collection's info under its *new* name.
        On error (e.g., original collection not found, new name invalid or exists,
        unexpected issue), isError is True and content contains a TextContent
        object with an error message.
    """

    try:
        # 1. Validate the new name first
        try:
            validate_collection_name(new_name)
        except ValidationError as e:
            logger.warning(f"Invalid new collection name provided for rename: '{new_name}'. Error: {e}")
            return types.CallToolResult(
                isError=True,
                content=[types.TextContent(type="text", text=f"Validation Error: Invalid new collection name '{new_name}'. {str(e)}")]
            )

        client = get_chroma_client()

        # 2. Get the original collection, handle not found
        try:
            collection = client.get_collection(
                name=collection_name,
                embedding_function=get_embedding_function()
            )
        except ValueError as e:
            if f"Collection {collection_name} does not exist." in str(e):
                logger.warning(f"Cannot rename: Original collection '{collection_name}' not found.")
                return types.CallToolResult(
                    isError=True,
                    content=[types.TextContent(type="text", text=f"Tool Error: Original collection '{collection_name}' not found.")]
                )
            else:
                # Re-raise other ValueErrors from get_collection
                raise e

        # 3. Attempt the rename via modify, handle potential errors (like new_name exists)
        try:
            collection.modify(name=new_name)
            logger.info(f"Renamed collection '{collection_name}' to '{new_name}'")
        except ValueError as e: # ChromaDB might raise ValueError if new_name exists or is invalid
            logger.warning(f"Failed to rename collection '{collection_name}' to '{new_name}': {e}")
            # Check common error messages if possible, otherwise provide generic
            error_msg = f"ChromaDB Error: Failed to rename to '{new_name}'. It might already exist or be invalid. Details: {str(e)}"
            if "already exists" in str(e).lower():
                 error_msg = f"ChromaDB Error: Cannot rename to '{new_name}' because a collection with that name already exists."
            return types.CallToolResult(
                isError=True,
                content=[types.TextContent(type="text", text=error_msg)]
            )

        # 4. On success, return the info for the collection under its NEW name
        return await _get_collection_impl(new_name)

    except ValueError as e: # Catch ValueErrors re-raised from the get_collection block
        logger.error(f"Value error during rename for '{collection_name}' -> '{new_name}': {e}", exc_info=False)
        return types.CallToolResult(
             isError=True,
             content=[types.TextContent(type="text", text=f"ChromaDB Value Error getting original collection: {str(e)}")]
         )
    except Exception as e:
        logger.error(f"Unexpected error renaming collection '{collection_name}' to '{new_name}': {e}", exc_info=True)
        # Return a Tool Error instead of raising McpError
        return types.CallToolResult(
            isError=True,
            content=[types.TextContent(type="text", text=f"Tool Error: An unexpected error occurred while renaming collection '{collection_name}'. Details: {str(e)}")]
        )

@mcp.tool(name="chroma_delete_collection", description="Delete a collection.")
async def _delete_collection_impl(collection_name: str) -> types.CallToolResult:
    """Deletes a ChromaDB collection.

    Args:
        collection_name: The name of the collection to delete.

    Returns:
        A CallToolResult object.
        On success, content contains a TextContent object with a JSON string
        confirming deletion: {"status": "deleted", "collection_name": ...}.
        On error (e.g., collection not found, unexpected issue), isError is True
        and content contains a TextContent object with an error message.
    """

    try:
        client = get_chroma_client()
        
        # delete_collection raises ValueError if collection doesn't exist
        try:
            client.delete_collection(name=collection_name)
            logger.info(f"Deleted collection: {collection_name}")
            
            # Return success message
            result_data = {"status": "deleted", "collection_name": collection_name}
            result_json = json.dumps(result_data)
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=result_json)]
            )
        except ValueError as e:
            # Check if the error is specifically "not found"
            if f"Collection {collection_name} not found" in str(e):
                logger.warning(f"Attempted to delete non-existent collection: {collection_name}")
                return types.CallToolResult(
                    isError=True,
                    content=[types.TextContent(type="text", text=f"Tool Error: Collection '{collection_name}' not found, cannot delete.")]
                )
            else:
                # Handle other potential ValueErrors from delete_collection
                logger.error(f"ValueError deleting collection '{collection_name}': {e}", exc_info=True)
                return types.CallToolResult(
                    isError=True,
                    content=[types.TextContent(type="text", text=f"ChromaDB Value Error: {str(e)}")]
                )
                
    except Exception as e:
        logger.error(f"Unexpected error deleting collection '{collection_name}': {e}", exc_info=True)
        # Return a Tool Error instead of raising McpError
        return types.CallToolResult(
            isError=True,
            content=[types.TextContent(type="text", text=f"Tool Error: An unexpected error occurred while deleting collection '{collection_name}'. Details: {str(e)}")]
        )

@mcp.tool(name="chroma_peek_collection", description="Get a sample of documents from a collection.")
async def _peek_collection_impl(collection_name: str, limit: Optional[int] = None) -> types.CallToolResult:
    """Retrieves a small sample of entries from a collection.

    Args:
        collection_name: The name of the collection to peek into.
        limit: The maximum number of entries to retrieve. Defaults to 5.

    Returns:
        A CallToolResult object.
        On success, content contains a TextContent object with a JSON string
        representing the peek results (containing lists for ids, embeddings,
        documents, metadatas). Embeddings are returned as lists of floats.
        On error (e.g., collection not found, invalid limit, unexpected issue),
        isError is True and content contains a TextContent object with an error message.
    """

    try:
        # Assign effective default if None
        effective_limit = 5 if limit is None else limit
        
        client = get_chroma_client()

        # 1. Get the collection, handle not found
        try:
            collection = client.get_collection(
                name=collection_name,
                embedding_function=get_embedding_function()
            )
        except ValueError as e:
            if f"Collection {collection_name} does not exist." in str(e):
                logger.warning(f"Cannot peek: Collection '{collection_name}' not found.")
                return types.CallToolResult(
                    isError=True,
                    content=[types.TextContent(type="text", text=f"Tool Error: Collection '{collection_name}' not found.")]
                )
            else:
                # Re-raise other ValueErrors from get_collection
                raise e

        # 2. Perform the peek operation using effective_limit
        try:
            peek_results = collection.peek(limit=effective_limit)
            logger.info(f"Peeked {len(peek_results.get('ids', []))} items from collection: {collection_name}")
            # Serialize peek results to JSON
            result_json = json.dumps(peek_results, indent=2)
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=result_json)]
            )
        except ValueError as e: # Catch potential errors from peek itself (e.g., invalid limit if not caught by schema)
            logger.warning(f"ValueError during peek for collection '{collection_name}' with limit={effective_limit}: {e}")
            return types.CallToolResult(
                isError=True,
                content=[types.TextContent(type="text", text=f"ChromaDB Value Error during peek: {str(e)}")]
            )
            
    except ValueError as e: # Catch ValueErrors re-raised from the get_collection block
        logger.error(f"Value error getting collection for peek '{collection_name}': {e}", exc_info=False)
        return types.CallToolResult(
             isError=True,
             content=[types.TextContent(type="text", text=f"ChromaDB Value Error getting collection: {str(e)}")]
         )
    except Exception as e:
        logger.error(f"Unexpected error peeking collection '{collection_name}': {e}", exc_info=True)
        # Return a Tool Error instead of raising McpError
        return types.CallToolResult(
            isError=True,
            content=[types.TextContent(type="text", text=f"Tool Error: An unexpected error occurred while peeking collection '{collection_name}'. Details: {str(e)}")]
        )

def _get_collection_info(collection) -> dict:
    """Helper to get structured info about a collection."""
    # Use the passed collection object directly
    # Reconstruct metadata first
    reconstructed_meta = _reconstruct_metadata(collection.metadata or {})
    
    # Get sample entries, handle potential errors during peek
    try:
        # Peek might return embeddings as ndarray, convert to list for JSON
        sample_entries = collection.peek(limit=5)
        if isinstance(sample_entries.get('embeddings'), np.ndarray):
             sample_entries['embeddings'] = sample_entries['embeddings'].tolist()
        # Also handle embeddings within lists if peek returns list of lists
        elif isinstance(sample_entries.get('embeddings'), list):
             sample_entries['embeddings'] = [
                 emb.tolist() if isinstance(emb, np.ndarray) else emb 
                 for emb in sample_entries['embeddings']
             ]
    except Exception as peek_err:
        # Log the error if possible, return a placeholder
        # logger = get_logger("collection_tools") # Need to import get_logger if used here
        # logger.warning(f"Could not peek collection '{collection.name}': {peek_err}")
        sample_entries = {"error": f"Could not peek collection: {peek_err}"}

    return {
        "name": collection.name,
        "id": str(collection.id), # Ensure ID is string
        "metadata": reconstructed_meta,
        "count": collection.count(),
        "sample_entries": sample_entries
    }
