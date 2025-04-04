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

def register_collection_tools(mcp: FastMCP) -> None:
    """Register collection management tools with the MCP server."""
    
    @mcp.tool()
    async def chroma_create_collection(
        collection_name: str
    ) -> Dict[str, Any]:
        """
        Create a new ChromaDB collection with default settings.
        Use other tools like 'chroma_set_collection_description' or 
        'chroma_set_collection_settings' to modify it after creation.

        Args:
            collection_name: Name of the collection to create

        Returns:
            Dictionary containing basic collection information
        """
        try:
            # Validate collection name (raises McpError on failure)
            validate_collection_name(collection_name)
            
            # Get client and default settings
            client = get_chroma_client()
            settings = get_collection_settings(collection_name) # Default settings
            
            # Initial metadata: flatten settings with a prefix
            initial_metadata = {f"chroma:setting:{k.replace(':', '_')}": v for k, v in settings.items()}
            
            # Create collection
            collection = client.create_collection(
                name=collection_name,
                metadata=initial_metadata, # Use only initial settings metadata
                embedding_function=get_embedding_function()
            )
            
            logger.info(f"Created collection: {collection_name}")
            return {
                "name": collection.name,
                "id": collection.id,
                "metadata": _reconstruct_metadata(collection.metadata) # Reconstruct metadata
            }
            
        except McpError: # Catch validation errors specifically
            raise # Re-raise validation errors directly
        except Exception as e: # Catch other errors (likely from ChromaDB)
            raise handle_chroma_error(e, f"create_collection({collection_name})")
    
    @mcp.tool()
    async def chroma_list_collections(
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        name_contains: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List all collections with optional filtering and pagination.
        
        Args:
            limit: Maximum number of collections to return
            offset: Number of collections to skip
            name_contains: Filter collections by name substring
            
        Returns:
            Dictionary containing list of collection names and total count
        """
        try:
            client = get_chroma_client()
            # Chroma v0.6.0+ might return only names strings directly
            collection_names = client.list_collections() # Assume list of strings
            
            # Ensure it's a list (handle potential None or other types)
            if not isinstance(collection_names, list):
                 logger.warning(f"client.list_collections() returned unexpected type: {type(collection_names)}")
                 collection_names = []
            
            # Filter by name if specified
            if name_contains:
                filtered_names = [name for name in collection_names if name_contains.lower() in name.lower()]
            else:
                filtered_names = collection_names
            
            # Get total count before pagination
            total_count = len(filtered_names)
            
            # Apply pagination
            start_index = offset if offset else 0
            end_index = (start_index + limit) if limit else None
            
            paginated_names = filtered_names[start_index:end_index]
            
            # Format response (just names)
            return {
                "collection_names": paginated_names,
                "total_count": total_count,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            raise handle_chroma_error(e, "list_collections")
    
    @mcp.tool()
    async def chroma_get_collection(collection_name: str) -> Dict[str, Any]:
        """
        Get information about a specific collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Dictionary containing collection information
        """
        try:
            client = get_chroma_client()
            collection = client.get_collection(
                name=collection_name,
                embedding_function=get_embedding_function()
            )
            
            # Get collection stats
            count = collection.count()
            peek = collection.peek() # Keep peek for basic info
            
            return {
                "name": collection.name,
                "id": collection.id,
                "metadata": _reconstruct_metadata(collection.metadata), # Reconstruct metadata
                "count": count,
                "sample_entries": peek # Return peek results directly
            }
            
        except Exception as e:
            raise handle_chroma_error(e, f"get_collection({collection_name})")
    
    @mcp.tool()
    async def chroma_set_collection_description(
        collection_name: str,
        description: str
    ) -> Dict[str, Any]:
        """
        Sets or updates the description of a collection.

        Args:
            collection_name: Name of the collection to modify
            description: The new description string

        Returns:
            Dictionary containing updated collection information
        """
        try:
            client = get_chroma_client()
            collection = client.get_collection(
                name=collection_name,
                embedding_function=get_embedding_function()
            )
            
            current_metadata = collection.metadata or {}
            updated_metadata = {**current_metadata, "description": description}
            
            collection.modify(metadata=updated_metadata)
            logger.info(f"Set description for collection: {collection_name}")
            
            # Return updated info
            return await chroma_get_collection(collection_name)
            
        except Exception as e:
            raise handle_chroma_error(e, f"set_collection_description({collection_name})")
    
    @mcp.tool()
    async def chroma_set_collection_settings(
        collection_name: str, 
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sets or updates the settings (e.g., HNSW parameters) of a collection.
        Warning: This replaces the existing 'settings' sub-dictionary in the metadata.

        Args:
            collection_name: Name of the collection to modify
            settings: Dictionary containing the new settings (e.g., {"hnsw:space": "cosine"})

        Returns:
            Dictionary containing updated collection information
        """
        try:
            client = get_chroma_client()
            collection = client.get_collection(
                name=collection_name,
                embedding_function=get_embedding_function()
            )
            
            current_metadata = collection.metadata or {}
            # Validate settings - basic check for dict type
            if not isinstance(settings, dict):
                raise_validation_error("Settings must be a dictionary.")
            
            # Remove existing prefixed settings from current metadata
            filtered_metadata = {k: v for k, v in current_metadata.items() if not k.startswith("chroma:setting:")}
            
            # Flatten and prefix new settings
            new_prefixed_settings = {f"chroma:setting:{k.replace(':', '_')}": v for k, v in settings.items()}

            # Merge filtered old metadata with new settings
            updated_metadata = {**filtered_metadata, **new_prefixed_settings}
            
            collection.modify(metadata=updated_metadata)
            logger.info(f"Set settings for collection: {collection_name}")
            
            # Return updated info
            return await chroma_get_collection(collection_name)
            
        except Exception as e:
            raise handle_chroma_error(e, f"set_collection_settings({collection_name})")
    
    @mcp.tool()
    async def chroma_update_collection_metadata(
        collection_name: str,
        metadata_update: Dict[str, Any]
    ) -> Dict[str, Any]:
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
        try:
            client = get_chroma_client()
            collection = client.get_collection(
                name=collection_name,
                embedding_function=get_embedding_function()
            )
            
            # Validate update data - basic check for dict type
            if not isinstance(metadata_update, dict):
                raise_validation_error("Metadata update must be a dictionary.")
            
            current_metadata = collection.metadata or {}
            # Prevent overwriting reserved keys if they exist in the update dict
            metadata_update.pop("description", None) 
            metadata_update.pop("settings", None)
            
            updated_metadata = {**current_metadata, **metadata_update}
            
            collection.modify(metadata=updated_metadata)
            logger.info(f"Updated metadata for collection: {collection_name}")
            
            # Return updated info
            return await chroma_get_collection(collection_name)
            
        except Exception as e:
            raise handle_chroma_error(e, f"update_collection_metadata({collection_name})")
    
    @mcp.tool()
    async def chroma_rename_collection(
        collection_name: str, 
        new_name: str
    ) -> Dict[str, Any]:
        """
        Renames an existing collection.

        Args:
            collection_name: Current name of the collection
            new_name: New name for the collection

        Returns:
            Dictionary containing updated collection information (under the new name)
        """
        try:
            client = get_chroma_client()
            collection = client.get_collection(
                name=collection_name,
                embedding_function=get_embedding_function()
            )
            
            # Validate the new name (raises McpError on failure)
            validate_collection_name(new_name)
            
            collection.modify(name=new_name)
            logger.info(f"Renamed collection '{collection_name}' to '{new_name}'")
            
            # Return updated info using the *new* name
            return await chroma_get_collection(new_name)
            
        except Exception as e:
            raise handle_chroma_error(e, f"rename_collection({collection_name})")
    
    @mcp.tool()
    async def chroma_delete_collection(collection_name: str) -> Dict[str, Any]:
        """
        Delete a collection.
        
        Args:
            collection_name: Name of the collection to delete
            
        Returns:
            Dictionary containing deletion status
        """
        try:
            client = get_chroma_client()
            
            # Check if collection exists before attempting deletion
            try:
                collection = client.get_collection(name=collection_name)
                collection_exists = True
            except Exception: # Catch broad exception for collection not found
                collection_exists = False
            
            if not collection_exists:
                logger.warning(f"Attempted to delete non-existent collection: {collection_name}")
                return {"status": "not_found", "message": f"Collection '{collection_name}' does not exist."}
            
            client.delete_collection(name=collection_name)
            logger.info(f"Deleted collection: {collection_name}")
            return {"status": "deleted", "collection_name": collection_name}
            
        except Exception as e:
            raise handle_chroma_error(e, f"delete_collection({collection_name})")
    
    @mcp.tool()
    async def chroma_peek_collection(
        collection_name: str,
        limit: int = 10 # Use default value directly, no Optional needed for signature
    ) -> Dict[str, Any]:
        """
        Peek at the first few entries in a collection.

        Args:
            collection_name: Name of the collection
            limit: Maximum number of entries to return (default: 10)

        Returns:
            Dictionary containing the peek results
        """
        try:
            # Validate limit
            if not isinstance(limit, int) or limit <= 0:
                raise_validation_error("Limit must be a positive integer.")
            
            client = get_chroma_client()
            collection = client.get_collection(
                name=collection_name,
                embedding_function=get_embedding_function()
            )
            
            peek_result = collection.peek(limit=limit)
            return {"peek_result": peek_result} # Return the result directly
            
        except Exception as e:
            raise handle_chroma_error(e, f"peek_collection({collection_name})")
