"""
Collection management tools for ChromaDB operations.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INVALID_PARAMS

from ..utils.logger_setup import LoggerSetup
from ..utils.client import get_chroma_client, get_embedding_function
from ..utils.config import get_collection_settings, validate_collection_name
from ..utils.errors import handle_chroma_error, validate_input, raise_validation_error, ValidationError

# Initialize logger
logger = LoggerSetup.create_logger(
    "ChromaCollections",
    log_file="chroma_collections.log"
)

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
    try:
        validate_collection_name(collection_name)
        client = get_chroma_client()
        settings = get_collection_settings(collection_name)
        initial_metadata = {f"chroma:setting:{k.replace(':', '_')}": v for k, v in settings.items()}
        # Await client call
        collection = await client.create_collection(
            name=collection_name,
            metadata=initial_metadata,
            embedding_function=get_embedding_function()
        )
        logger.info(f"Created collection: {collection_name}")
        return {
            "name": collection.name,
            "id": collection.id,
            "metadata": _reconstruct_metadata(collection.metadata)
        }
    except McpError:
        raise
    except Exception as e:
        raise handle_chroma_error(e, f"create_collection({collection_name})")

async def _list_collections_impl(limit: int = 0, offset: int = 0, name_contains: str = "") -> Dict[str, Any]:
    """Implementation logic for listing collections."""
    try:
        if limit < 0:
            raise_validation_error("limit cannot be negative")
        if offset < 0:
            raise_validation_error("offset cannot be negative")
        client = get_chroma_client()
        # Await client call
        collection_names = await client.list_collections()
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
    try:
        client = get_chroma_client()
        # Await client call
        collection = await client.get_collection(
            name=collection_name,
            embedding_function=get_embedding_function()
        )
        # Await collection calls
        count = await collection.count()
        peek = await collection.peek()
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
    try:
        client = get_chroma_client()
        # Await client call
        collection = await client.get_collection(
            name=collection_name,
            embedding_function=get_embedding_function()
        )
        current_metadata = collection.metadata or {}
        updated_metadata = {**current_metadata, "description": description}
        # Await collection call
        await collection.modify(metadata=updated_metadata)
        logger.info(f"Set description for collection: {collection_name}")
        # Await the call to the implementation function
        return await _get_collection_impl(collection_name)
    except Exception as e:
        raise handle_chroma_error(e, f"set_collection_description({collection_name})")

async def _set_collection_settings_impl(collection_name: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    """Implementation logic for setting collection settings."""
    try:
        client = get_chroma_client()
        # Await client call
        collection = await client.get_collection(
            name=collection_name,
            embedding_function=get_embedding_function()
        )
        current_metadata = collection.metadata or {}
        if not isinstance(settings, dict):
            raise_validation_error("settings parameter must be a dictionary")
        # Remove existing settings keys
        metadata_without_settings = {k: v for k, v in current_metadata.items() if not k.startswith("chroma:setting:")}
        # Add new flattened settings
        flattened_settings = {f"chroma:setting:{k.replace(':', '_')}": v for k, v in settings.items()}
        updated_metadata = {**metadata_without_settings, **flattened_settings}
        # Await collection call
        await collection.modify(metadata=updated_metadata)
        logger.info(f"Set settings for collection: {collection_name}")
        return await _get_collection_impl(collection_name)
    except Exception as e:
        raise handle_chroma_error(e, f"set_collection_settings({collection_name})")

async def _update_collection_metadata_impl(collection_name: str, metadata_update: Dict[str, Any]) -> Dict[str, Any]:
    """Implementation logic for updating collection metadata."""
    try:
        client = get_chroma_client()
        # Await client call
        collection = await client.get_collection(
            name=collection_name,
            embedding_function=get_embedding_function()
        )
        if not isinstance(metadata_update, dict):
            raise_validation_error("metadata_update parameter must be a dictionary")
        # Prevent modification of reserved keys
        if any(key in ["description", "settings"] or key.startswith("chroma:setting:") for key in metadata_update):
            raise_validation_error("Cannot update reserved keys ('description', 'settings', 'chroma:setting:...') via this tool.")
        current_metadata = collection.metadata or {}
        updated_metadata = {**current_metadata, **metadata_update}
        # Await collection call
        await collection.modify(metadata=updated_metadata)
        logger.info(f"Updated custom metadata for collection: {collection_name}")
        return await _get_collection_impl(collection_name)
    except Exception as e:
        raise handle_chroma_error(e, f"update_collection_metadata({collection_name})")

async def _rename_collection_impl(collection_name: str, new_name: str) -> Dict[str, Any]:
    """Implementation logic for renaming a collection."""
    try:
        validate_collection_name(new_name) # Validate the new name
        client = get_chroma_client()
        # Await client call
        collection = await client.get_collection(
            name=collection_name,
            embedding_function=get_embedding_function()
        )
        # Await collection call
        await collection.modify(name=new_name)
        logger.info(f"Renamed collection '{collection_name}' to '{new_name}'")
        # Get the collection info under the new name
        return await _get_collection_impl(new_name)
    except McpError:
        raise
    except Exception as e:
        raise handle_chroma_error(e, f"rename_collection({collection_name} -> {new_name})")

async def _delete_collection_impl(collection_name: str) -> Dict[str, Any]:
    """Implementation logic for deleting a collection."""
    try:
        client = get_chroma_client()
        # Await client call
        await client.delete_collection(name=collection_name)
        logger.info(f"Deleted collection: {collection_name}")
        return {"success": True, "deleted_collection": collection_name}
    except Exception as e:
        raise handle_chroma_error(e, f"delete_collection({collection_name})")

async def _peek_collection_impl(collection_name: str, limit: int = 10) -> Dict[str, Any]:
    """Implementation logic for peeking into a collection."""
    try:
        if limit <= 0:
            raise_validation_error("limit must be a positive integer")
        client = get_chroma_client()
        # Await client call
        collection = await client.get_collection(
            name=collection_name,
            embedding_function=get_embedding_function()
        )
        # Await collection call
        peek_result = await collection.peek(limit=limit)
        return {
            "collection_name": collection_name,
            "limit": limit,
            "peek_result": peek_result # Return raw peek result
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
        This performs a merge, preserving existing keys unless overwritten.
        It does NOT affect the reserved 'description' or 'settings' keys directly.

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
