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
from ..utils.errors import handle_chroma_error, validate_input, raise_validation_error

# Initialize logger
logger = LoggerSetup.create_logger(
    "ChromaCollections",
    log_file="chroma_collections.log"
)

@dataclass
class CollectionMetadata:
    """Collection metadata structure."""
    description: Optional[str] = None
    tags: List[str] = None
    custom_settings: Dict[str, Any] = None

def register_collection_tools(mcp: FastMCP) -> None:
    """Register collection management tools with the MCP server."""
    
    @mcp.tool()
    async def chroma_create_collection(
        collection_name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        hnsw_space: Optional[str] = None,
        hnsw_construction_ef: Optional[int] = None,
        hnsw_search_ef: Optional[int] = None,
        hnsw_M: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new ChromaDB collection.
        
        Args:
            collection_name: Name of the collection to create
            description: Optional description of the collection
            metadata: Optional metadata for the collection
            hnsw_space: Distance function for HNSW index (e.g., 'cosine', 'l2', 'ip')
            hnsw_construction_ef: HNSW construction parameter
            hnsw_search_ef: HNSW search parameter
            hnsw_M: HNSW M parameter
            
        Returns:
            Dictionary containing collection information
        """
        try:
            # Validate collection name
            if not validate_collection_name(collection_name):
                raise_validation_error(f"Invalid collection name: {collection_name}")
            
            # Get client and settings
            client = get_chroma_client()
            settings = get_collection_settings(collection_name)
            
            # Override settings with provided parameters
            if hnsw_space:
                settings["hnsw:space"] = hnsw_space
            if hnsw_construction_ef:
                settings["hnsw:construction_ef"] = hnsw_construction_ef
            if hnsw_search_ef:
                settings["hnsw:search_ef"] = hnsw_search_ef
            if hnsw_M:
                settings["hnsw:M"] = hnsw_M
            
            # Prepare metadata
            full_metadata = {
                "description": description,
                "settings": settings,
                **(metadata or {})
            }
            
            # Create collection
            collection = client.create_collection(
                name=collection_name,
                metadata=full_metadata,
                embedding_function=get_embedding_function()
            )
            
            logger.info(f"Created collection: {collection_name}")
            return {
                "name": collection_name,
                "id": collection.id,
                "metadata": full_metadata
            }
            
        except Exception as e:
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
            Dictionary containing list of collections and total count
        """
        try:
            client = get_chroma_client()
            collections = client.list_collections()
            
            # Filter by name if specified
            if name_contains:
                collections = [c for c in collections if name_contains.lower() in c.name.lower()]
            
            # Get total count before pagination
            total_count = len(collections)
            
            # Apply pagination
            if offset:
                collections = collections[offset:]
            if limit:
                collections = collections[:limit]
            
            # Format response
            collection_list = [{
                "name": c.name,
                "id": c.id,
                "metadata": c.metadata
            } for c in collections]
            
            return {
                "collections": collection_list,
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
            peek = collection.peek()
            
            return {
                "name": collection.name,
                "id": collection.id,
                "metadata": collection.metadata,
                "count": count,
                "sample_entries": peek
            }
            
        except Exception as e:
            raise handle_chroma_error(e, f"get_collection({collection_name})")
    
    @mcp.tool()
    async def chroma_modify_collection(
        collection_name: str,
        new_metadata: Optional[Dict[str, Any]] = None,
        new_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Modify a collection's metadata or rename it.
        
        Args:
            collection_name: Name of the collection to modify
            new_metadata: New metadata to merge with existing
            new_name: New name for the collection
            
        Returns:
            Dictionary containing updated collection information
        """
        try:
            client = get_chroma_client()
            collection = client.get_collection(
                name=collection_name,
                embedding_function=get_embedding_function()
            )
            
            # Update metadata if provided
            if new_metadata:
                current_metadata = collection.metadata or {}
                updated_metadata = {**current_metadata, **new_metadata}
                collection.modify(metadata=updated_metadata)
            
            # Rename collection if new name provided
            if new_name:
                if not validate_collection_name(new_name):
                    raise_validation_error(f"Invalid new collection name: {new_name}")
                collection.modify(name=new_name)
                collection_name = new_name
            
            # Get updated collection info
            return await chroma_get_collection(collection_name)
            
        except Exception as e:
            raise handle_chroma_error(e, f"modify_collection({collection_name})")
    
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
            
            # Get collection info before deletion
            collection = client.get_collection(
                name=collection_name,
                embedding_function=get_embedding_function()
            )
            collection_info = {
                "name": collection.name,
                "id": collection.id,
                "count": collection.count()
            }
            
            # Delete collection
            client.delete_collection(collection_name)
            
            logger.info(f"Deleted collection: {collection_name}")
            return {
                "success": True,
                "deleted_collection": collection_info
            }
            
        except Exception as e:
            raise handle_chroma_error(e, f"delete_collection({collection_name})")
    
    @mcp.tool()
    async def chroma_peek_collection(
        collection_name: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Peek at the contents of a collection.
        
        Args:
            collection_name: Name of the collection
            limit: Maximum number of entries to return
            
        Returns:
            Dictionary containing collection sample data
        """
        try:
            client = get_chroma_client()
            collection = client.get_collection(
                name=collection_name,
                embedding_function=get_embedding_function()
            )
            
            # Get sample entries
            entries = collection.peek(limit)
            
            return {
                "name": collection_name,
                "count": collection.count(),
                "sample_size": len(entries),
                "entries": entries
            }
            
        except Exception as e:
            raise handle_chroma_error(e, f"peek_collection({collection_name})")
