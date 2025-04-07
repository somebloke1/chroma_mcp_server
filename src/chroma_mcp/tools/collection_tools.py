"""
Collection management tools for ChromaDB operations.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INVALID_PARAMS

from ..utils.errors import ValidationError, CollectionNotFoundError, raise_validation_error, handle_chroma_error
from ..utils.config import get_collection_settings, validate_collection_name

def _reconstruct_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Helper to reconstruct nested settings dict from flattened metadata."""
    if not metadata:
        return {}
    
    reconstructed = {}
    settings = {}
    for key, value in metadata.items():
        if key.startswith("chroma:setting:"):
            setting_key = key[len("chroma:setting:"):]
            # Replace only the first underscore back to colon if needed for keys like hnsw:space
            if '_' in setting_key:
                 parts = setting_key.split('_', 1)
                 if len(parts) == 2 and parts[0] == 'hnsw': # Assume only hnsw keys used colons
                     original_key = parts[0] + ':' + parts[1]
                 else:
                     original_key = setting_key # Keep underscores for other keys
            else:
                original_key = setting_key
            settings[original_key] = value
        else:
            reconstructed[key] = value
    
    if settings:
        reconstructed["settings"] = settings
        
    return reconstructed

# --- Implementation Functions ---

async def _create_collection_impl(collection_name: str) -> Dict[str, Any]:
    """Implementation logic for creating a collection."""
    from ..server import get_logger
    logger = get_logger("tools.collection")
    from ..utils.client import get_chroma_client, get_embedding_function

    try:
        validate_collection_name(collection_name)
        client = get_chroma_client()
        settings = get_collection_settings()
        collection = client.create_collection(
            name=collection_name, 
            metadata=settings,
            embedding_function=get_embedding_function(),
            get_or_create=False
        )
        logger.info(f"Created collection: {collection_name} with settings: {settings}")
        count = collection.count()
        peek = collection.peek()
        return {
            "name": collection.name,
            "id": collection.id,
            "metadata": _reconstruct_metadata(collection.metadata),
            "count": count,
            "sample_entries": peek
        }
    except McpError:
        raise
    except Exception as e:
        raise handle_chroma_error(e, f"create_collection({collection_name})")

async def _list_collections_impl(limit: int = 0, offset: int = 0, name_contains: str = "") -> Dict[str, Any]:
    """Implementation logic for listing collections."""
    from ..server import get_logger
    logger = get_logger("tools.collection")
    from ..utils.client import get_chroma_client

    try:
        if limit < 0:
            raise_validation_error("limit cannot be negative")
        if offset < 0:
            raise_validation_error("offset cannot be negative")
        client = get_chroma_client()
        collection_names = client.list_collections()
        
        if not isinstance(collection_names, list):
            logger.warning(f"client.list_collections() returned unexpected type: {type(collection_names)}")
            collection_names = []
            
        if name_contains:
            filtered_names = [name for name in collection_names if name_contains.lower() in name.lower()]
        else:
            filtered_names = collection_names
            
        total_count = len(filtered_names)
        start_index = offset
        end_index = (start_index + limit) if limit > 0 else None
        paginated_names = filtered_names[start_index:end_index]
        
        return {
            "collection_names": paginated_names,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise handle_chroma_error(e, "list_collections")

async def _get_collection_impl(collection_name: str) -> Dict[str, Any]:
    """Implementation logic for getting collection info."""
    from ..server import get_logger
    logger = get_logger("tools.collection")
    from ..utils.client import get_chroma_client, get_embedding_function

    try:
        client = get_chroma_client()
        collection = client.get_collection(
            name=collection_name,
            embedding_function=get_embedding_function()
        )
        count = collection.count()
        peek = collection.peek()
        return {
            "name": collection.name,
            "id": collection.id,
            "metadata": _reconstruct_metadata(collection.metadata),
            "count": count,
            "sample_entries": peek
        }
    except Exception as e:
        raise handle_chroma_error(e, f"get_collection({collection_name})")

async def _set_collection_description_impl(collection_name: str, description: str) -> Dict[str, Any]:
    """Implementation logic for setting collection description."""
    from ..server import get_logger
    logger = get_logger("tools.collection")
    from ..utils.client import get_chroma_client, get_embedding_function

    try:
        client = get_chroma_client()
        collection = client.get_collection(
            name=collection_name,
            embedding_function=get_embedding_function()
        )

        # --- Start: Fail Fast Logic (copied from update_collection_metadata) ---
        current_metadata = collection.metadata or {}
        # Define known immutable patterns (adjust if Chroma adds more)
        immutable_patterns = ["hnsw:"] 
        has_immutable_settings = any(
            key.startswith(pattern) 
            for key in current_metadata 
            for pattern in immutable_patterns
        )
        
        if has_immutable_settings:
            raise_validation_error(
                "Cannot set description on collections with immutable settings (e.g., hnsw:*). "
                "Collection settings must be finalized at creation."
            )        
        # --- End: Fail Fast Logic ---

        # Only proceed if no immutable settings were detected
        # current_metadata = collection.metadata or {} # Already fetched above
        updated_metadata = current_metadata.copy()
        updated_metadata["description"] = description
        collection.modify(metadata=updated_metadata)
        logger.info(f"Set description for collection: {collection_name}")
        return await _get_collection_impl(collection_name)
    except Exception as e:
        raise handle_chroma_error(e, f"set_collection_description({collection_name})")

async def _set_collection_settings_impl(collection_name: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    """Implementation logic for setting collection settings."""
    from ..server import get_logger
    logger = get_logger("tools.collection")
    from ..utils.client import get_chroma_client, get_embedding_function

    try:
        client = get_chroma_client()
        collection = client.get_collection(
            name=collection_name,
            embedding_function=get_embedding_function()
        )
        current_metadata = collection.metadata or {}
        if not isinstance(settings, dict):
            raise_validation_error("settings parameter must be a dictionary")
        metadata_without_settings = {k: v for k, v in current_metadata.items() if not k.startswith("chroma:setting:")}
        flattened_settings = {f"chroma:setting:{k.replace(':', '_')}": v for k, v in settings.items()}
        updated_metadata = {**metadata_without_settings, **flattened_settings}
        collection.modify(metadata=updated_metadata)
        logger.info(f"Set settings for collection: {collection_name}")
        return await _get_collection_impl(collection_name)
    except Exception as e:
        raise handle_chroma_error(e, f"set_collection_settings({collection_name})")

async def _update_collection_metadata_impl(collection_name: str, metadata_update: Dict[str, Any]) -> Dict[str, Any]:
    """Implementation logic for updating collection metadata."""
    from ..server import get_logger
    logger = get_logger("tools.collection")
    from ..utils.client import get_chroma_client, get_embedding_function

    try:
        client = get_chroma_client()
        collection = client.get_collection(
            name=collection_name,
            embedding_function=get_embedding_function()
        )
        if not isinstance(metadata_update, dict):
            raise_validation_error("metadata_update parameter must be a dictionary")
        if any(key in ["description", "settings"] or key.startswith("chroma:setting:") for key in metadata_update):
            raise_validation_error("Cannot update reserved keys ('description', 'settings', 'chroma:setting:...') via this tool.")
        
        # --- Start: Fail Fast Logic ---
        current_metadata = collection.metadata or {}
        # Define known immutable patterns (adjust if Chroma adds more)
        immutable_patterns = ["hnsw:"] 
        has_immutable_settings = any(
            key.startswith(pattern) 
            for key in current_metadata 
            for pattern in immutable_patterns
        )
        
        if has_immutable_settings:
            raise_validation_error(
                "Cannot update metadata on collections with immutable settings (e.g., hnsw:*). "
                "Set all custom metadata during collection creation if needed."
            )
        # --- End: Fail Fast Logic ---
        
        # If we reach here, it means no immutable settings were detected.
        # Proceed with replacing the metadata entirely with the update.
        # collection.modify(metadata=metadata_update) # Incorrect: Replaces instead of merging

        # Correct logic: Fetch current, merge update, then modify
        current_metadata_safe = collection.metadata or {} # Fetch again just to be safe
        merged_metadata = current_metadata_safe.copy()
        merged_metadata.update(metadata_update)
        collection.modify(metadata=merged_metadata)

        logger.info(f"Updated custom metadata for collection: {collection_name}")
        return await _get_collection_impl(collection_name)
    except Exception as e:
        raise handle_chroma_error(e, f"update_collection_metadata({collection_name})")

async def _rename_collection_impl(collection_name: str, new_name: str) -> Dict[str, Any]:
    """Implementation logic for renaming a collection."""
    from ..server import get_logger
    logger = get_logger("tools.collection")
    from ..utils.client import get_chroma_client, get_embedding_function

    try:
        validate_collection_name(new_name)
        client = get_chroma_client()
        collection = client.get_collection(
            name=collection_name,
            embedding_function=get_embedding_function()
        )
        collection.modify(name=new_name)
        logger.info(f"Renamed collection '{collection_name}' to '{new_name}'")
        return await _get_collection_impl(new_name)
    except McpError:
        raise
    except Exception as e:
        raise handle_chroma_error(e, f"rename_collection({collection_name} -> {new_name})")

async def _delete_collection_impl(collection_name: str) -> Dict[str, Any]:
    """Implementation logic for deleting a collection."""
    from ..server import get_logger
    logger = get_logger("tools.collection")
    from ..utils.client import get_chroma_client

    try:
        client = get_chroma_client()
        client.delete_collection(name=collection_name)
        logger.info(f"Deleted collection: {collection_name}")
        return {"success": True, "deleted_collection": collection_name}
    except Exception as e:
        raise handle_chroma_error(e, f"delete_collection({collection_name})")

async def _peek_collection_impl(collection_name: str, limit: int = 10) -> Dict[str, Any]:
    """Implementation logic for peeking into a collection."""
    from ..server import get_logger
    logger = get_logger("tools.collection")
    from ..utils.client import get_chroma_client, get_embedding_function

    try:
        if limit <= 0:
            raise_validation_error("limit must be a positive integer")
        client = get_chroma_client()
        collection = client.get_collection(
            name=collection_name,
            embedding_function=get_embedding_function()
        )
        peek_result = collection.peek(limit=limit)
        return {
            "collection_name": collection_name,
            "limit": limit,
            "peek_result": peek_result
        }
    except Exception as e:
        raise handle_chroma_error(e, f"peek_collection({collection_name})")

# --- Tool Registration ---

def register_collection_tools(mcp: FastMCP) -> None:
    """Register collection management tools with the MCP server."""
    
    @mcp.tool()
    async def chroma_create_collection(collection_name: str) -> Dict[str, Any]:
        """
        Create a new ChromaDB collection with default settings.
        Use other tools like 'chroma_set_collection_description' or 
        'chroma_set_collection_settings' to modify it after creation.

        Args:
            collection_name: Name of the collection to create

        Returns:
            Dictionary containing basic collection information
        """
        return await _create_collection_impl(collection_name)
    
    @mcp.tool()
    async def chroma_list_collections(limit: int = 0, offset: int = 0, name_contains: str = "") -> Dict[str, Any]:
        """
        List all collections with optional filtering and pagination.
        
        Args:
            limit: Maximum number of collections to return (0 for no limit)
            offset: Number of collections to skip (0 for no offset)
            name_contains: Filter collections by name substring (empty string for no filter)
            
        Returns:
            Dictionary containing list of collection names and total count
        """
        return await _list_collections_impl(limit=limit, offset=offset, name_contains=name_contains)
    
    @mcp.tool()
    async def chroma_get_collection(collection_name: str) -> Dict[str, Any]:
        """
        Get information about a specific collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Dictionary containing collection information
        """
        return await _get_collection_impl(collection_name)
    
    @mcp.tool()
    async def chroma_set_collection_description(collection_name: str, description: str) -> Dict[str, Any]:
        """
        Sets or updates the description of a collection.

        Args:
            collection_name: Name of the collection to modify
            description: The new description string

        Returns:
            Dictionary containing updated collection information
        """
        return await _set_collection_description_impl(collection_name, description)
    
    @mcp.tool()
    async def chroma_set_collection_settings(collection_name: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sets or updates the settings (e.g., HNSW parameters) of a collection.
        Warning: This replaces the existing 'settings' sub-dictionary in the metadata.

        Args:
            collection_name: Name of the collection to modify
            settings: Dictionary containing the new settings (e.g., {"hnsw:space": "cosine"})

        Returns:
            Dictionary containing updated collection information
        """
        return await _set_collection_settings_impl(collection_name, settings)
    
    @mcp.tool()
    async def chroma_update_collection_metadata(collection_name: str, metadata_update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates or adds custom key-value pairs to a collection's metadata.
        Warning: This REPLACES the entire existing custom metadata block with the provided `metadata_update`.
        It does NOT affect the reserved 'description' or 'settings' keys directly.
        IMPORTANT: This tool will FAIL if the target collection currently has immutable settings 
        (e.g., 'hnsw:space') defined in its metadata, as ChromaDB prevents modification in such cases.
        Set all custom metadata during collection creation if immutable settings are used.

        Args:
            collection_name: Name of the collection to modify
            metadata_update: Dictionary containing key-value pairs to update or add

        Returns:
            Dictionary containing updated collection information
        """
        return await _update_collection_metadata_impl(collection_name, metadata_update)
    
    @mcp.tool()
    async def chroma_rename_collection(collection_name: str, new_name: str) -> Dict[str, Any]:
        """
        Renames an existing collection.

        Args:
            collection_name: Current name of the collection
            new_name: New name for the collection

        Returns:
            Dictionary containing updated collection information (under the new name)
        """
        return await _rename_collection_impl(collection_name, new_name)
    
    @mcp.tool()
    async def chroma_delete_collection(collection_name: str) -> Dict[str, Any]:
        """
        Delete a collection.
        
        Args:
            collection_name: Name of the collection to delete
            
        Returns:
            Dictionary containing deletion status
        """
        return await _delete_collection_impl(collection_name)
    
    @mcp.tool()
    async def chroma_peek_collection(collection_name: str, limit: int = 10) -> Dict[str, Any]:
        """
        Peek at the first few entries in a collection.

        Args:
            collection_name: Name of the collection
            limit: Maximum number of entries to return (default: 10)

        Returns:
            Dictionary containing the peek results
        """
        return await _peek_collection_impl(collection_name, limit)
