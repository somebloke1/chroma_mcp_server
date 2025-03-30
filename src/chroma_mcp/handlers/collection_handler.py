"""
Collection Handler for Chroma MCP Server

This module provides functionality for managing collections in ChromaDB.
"""

import os
import asyncio
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS

from ..utils.logger_setup import LoggerSetup
from ..utils.client import get_chroma_client
from ..utils.config import validate_collection_name, get_collection_settings
from ..utils.errors import ValidationError, CollectionNotFoundError

# Initialize logger
logger = LoggerSetup.create_logger(
    "CollectionHandler",
    log_file="collection_handler.log",
    log_level=os.getenv("LOG_LEVEL", "INFO")
)

@dataclass
class CollectionHandler:
    """Handler for ChromaDB collection operations."""

    def __init__(self, config=None):
        """Initialize the collection handler."""
        self._client = get_chroma_client(config)
        logger.info("Collection handler initialized")

    async def create_collection(
        self,
        collection_name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        hnsw_space: Optional[str] = None,
        hnsw_construction_ef: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a new ChromaDB collection with optional settings."""
        try:
            # Validate collection name
            validate_collection_name(collection_name)

            # Get collection settings
            settings = get_collection_settings(
                collection_name=collection_name,
                hnsw_space=hnsw_space,
                hnsw_construction_ef=hnsw_construction_ef,
                **kwargs
            )

            # Create collection with settings
            collection = self._client.create_collection(
                name=collection_name,
                metadata={
                    "description": description,
                    **(metadata or {})
                },
                **settings
            )

            logger.info(f"Created collection: {collection_name}")
            return {
                "name": collection_name,
                "id": collection.id,
                "metadata": collection.metadata
            }

        except ValidationError as e:
            logger.error(f"Invalid collection parameters: {str(e)}")
            raise
        except chromadb.errors.InvalidDimensionException as e:
            logger.error(f"Invalid dimensions for collection {collection_name}: {str(e)}")
            raise McpError(ErrorData(
                code=INVALID_PARAMS,
                message=f"Invalid dimensions: {str(e)}"
            ))
        except Exception as e:
            logger.error(f"Error creating collection {collection_name}: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to create collection: {str(e)}"
            ))

    async def list_collections(
        self,
        offset: Optional[int] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """List all collections with optional pagination."""
        try:
            collections = self._client.list_collections()
            
            # Apply pagination if provided
            if offset is not None or limit is not None:
                start = offset or 0
                end = None if limit is None else start + limit
                collections = collections[start:end]
            
            return {
                "collections": [
                    {
                        "name": c.name,
                        "id": c.id,
                        "metadata": c.metadata
                    }
                    for c in collections
                ]
            }

        except Exception as e:
            logger.error(f"Error listing collections: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to list collections: {str(e)}"
            ))

    async def get_collection(
        self,
        collection_name: str
    ) -> Dict[str, Any]:
        """Get information about a specific collection."""
        try:
            collection = self._client.get_collection(collection_name)
            return {
                "name": collection.name,
                "id": collection.id,
                "metadata": collection.metadata,
                "count": collection.count()
            }

        except chromadb.errors.InvalidCollectionException:
            logger.error(f"Collection not found: {collection_name}")
            raise CollectionNotFoundError(f"Collection not found: {collection_name}")
        except Exception as e:
            logger.error(f"Error getting collection {collection_name}: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to get collection: {str(e)}"
            ))

    async def modify_collection(
        self,
        collection_name: str,
        new_name: Optional[str] = None,
        new_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Modify a collection's name or metadata."""
        try:
            collection = self._client.get_collection(collection_name)

            if new_name:
                validate_collection_name(new_name)
                # Rename collection
                self._client.rename_collection(collection_name, new_name)
                collection_name = new_name
                logger.info(f"Renamed collection to: {new_name}")

            if new_metadata:
                # Update metadata
                collection = self._client.get_collection(collection_name)
                current_metadata = collection.metadata or {}
                updated_metadata = {**current_metadata, **new_metadata}
                collection.modify(metadata=updated_metadata)
                logger.info(f"Updated metadata for collection: {collection_name}")

            # Get updated collection info
            collection = self._client.get_collection(collection_name)
            return {
                "name": collection.name,
                "id": collection.id,
                "metadata": collection.metadata
            }

        except ValidationError as e:
            logger.error(f"Invalid collection parameters: {str(e)}")
            raise
        except chromadb.errors.InvalidCollectionException:
            logger.error(f"Collection not found: {collection_name}")
            raise CollectionNotFoundError(f"Collection not found: {collection_name}")
        except Exception as e:
            logger.error(f"Error modifying collection {collection_name}: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to modify collection: {str(e)}"
            ))

    async def delete_collection(
        self,
        collection_name: str
    ) -> Dict[str, Any]:
        """Delete a collection and return its information."""
        try:
            # Get collection info before deletion
            collection = self._client.get_collection(collection_name)
            info = {
                "name": collection.name,
                "id": collection.id,
                "metadata": collection.metadata
            }

            # Delete the collection
            self._client.delete_collection(collection_name)
            logger.info(f"Deleted collection: {collection_name}")

            return {
                "success": True,
                "deleted_collection": info
            }

        except chromadb.errors.InvalidCollectionException:
            logger.error(f"Collection not found: {collection_name}")
            raise CollectionNotFoundError(f"Collection not found: {collection_name}")
        except Exception as e:
            logger.error(f"Error deleting collection {collection_name}: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to delete collection: {str(e)}"
            ))

    async def peek_collection(
        self,
        collection_name: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """Get a sample of documents from a collection."""
        try:
            collection = self._client.get_collection(collection_name)

            # Get collection info
            count = collection.count()
            if count == 0:
                return {
                    "name": collection_name,
                    "count": 0,
                    "sample": {
                        "ids": [],
                        "documents": [],
                        "metadatas": [],
                        "embeddings": None
                    }
                }

            # Get sample documents
            result = collection.get(limit=min(limit, count))

            return {
                "name": collection_name,
                "count": count,
                "sample": {
                    "ids": result["ids"],
                    "documents": result["documents"],
                    "metadatas": result["metadatas"],
                    "embeddings": result["embeddings"] if "embeddings" in result else None
                }
            }

        except chromadb.errors.InvalidCollectionException:
            logger.error(f"Collection not found: {collection_name}")
            raise CollectionNotFoundError(f"Collection not found: {collection_name}")
        except Exception as e:
            logger.error(f"Error peeking collection {collection_name}: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to peek collection: {str(e)}"
            ))
