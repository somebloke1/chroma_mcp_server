"""
Document Handler for Chroma MCP Server

This module provides functionality for managing documents in ChromaDB collections.
"""

import os
import asyncio
import uuid
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import numpy as np

import chromadb
from chromadb.api import Collection
from chromadb.config import Settings
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS

from ..utils.logger_setup import LoggerSetup
from ..utils.client import get_chroma_client
from ..utils.config import validate_collection_name
from ..utils.errors import ValidationError, CollectionNotFoundError

# Initialize logger
logger = LoggerSetup.create_logger(
    "DocumentHandler",
    log_file="document_handler.log",
    log_level=os.getenv("LOG_LEVEL", "INFO")
)

@dataclass
class DocumentHandler:
    """Handler for ChromaDB document operations."""

    def __init__(self, config=None):
        """Initialize the document handler."""
        self._client = get_chroma_client(config)
        logger.info("Document handler initialized")

    def _get_collection(self, collection_name: str) -> Collection:
        """Get a collection by name, with error handling."""
        try:
            return self._client.get_collection(collection_name)
        except ValueError as e:
            logger.error(f"Collection not found: {collection_name}")
            raise CollectionNotFoundError(f"Collection not found: {str(e)}")

    async def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None,
    ) -> Dict[str, Any]:
        """Add documents to a collection."""
        try:
            collection = self._get_collection(collection_name)

            # Validate inputs
            if not documents:
                raise ValidationError("No documents provided")
            if metadatas and len(metadatas) != len(documents):
                raise ValidationError("Number of metadatas must match number of documents")
            if ids and len(ids) != len(documents):
                raise ValidationError("Number of ids must match number of documents")
            if embeddings and len(embeddings) != len(documents):
                raise ValidationError("Number of embeddings must match number of documents")

            # Add documents
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )

            logger.info(f"Added {len(documents)} documents to collection: {collection_name}")
            return {
                "success": True,
                "count": len(documents),
                "collection_name": collection_name
            }

        except ValidationError as e:
            logger.error(f"Invalid parameters: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error adding documents to {collection_name}: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to add documents: {str(e)}"
            ))

    async def query_documents(
        self,
        collection_name: str,
        query_texts: Optional[List[str]] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Query documents from a collection."""
        try:
            collection = self._get_collection(collection_name)

            # Validate query inputs
            if not query_texts and not query_embeddings:
                raise ValidationError("Either query_texts or query_embeddings must be provided")

            # Execute query
            results = collection.query(
                query_texts=query_texts,
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=include or ["documents", "metadatas", "distances"]
            )

            logger.info(f"Queried documents from collection: {collection_name}")
            return {
                "ids": results["ids"],
                "documents": results.get("documents"),
                "metadatas": results.get("metadatas"),
                "distances": results.get("distances"),
                "embeddings": results.get("embeddings")
            }

        except ValidationError as e:
            logger.error(f"Invalid query parameters: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error querying documents from {collection_name}: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to query documents: {str(e)}"
            ))

    # Alias for query_documents to maintain API compatibility
    async def query_collection(
        self,
        collection_name: str,
        query_texts: Optional[List[str]] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Alias for query_documents to maintain API compatibility."""
        return await self.query_documents(
            collection_name=collection_name,
            query_texts=query_texts,
            query_embeddings=query_embeddings,
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=include
        )

    async def get_documents(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        include: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get documents from a collection."""
        try:
            collection = self._get_collection(collection_name)

            # Get documents
            results = collection.get(
                ids=ids,
                where=where,
                limit=limit,
                offset=offset,
                include=include or ["documents", "metadatas"]
            )

            logger.info(f"Retrieved documents from collection: {collection_name}")
            return {
                "ids": results["ids"],
                "documents": results.get("documents"),
                "metadatas": results.get("metadatas"),
                "embeddings": results.get("embeddings")
            }

        except ValidationError as e:
            logger.error(f"Invalid parameters: {str(e)}")
            raise
        except CollectionNotFoundError as e:
            logger.error(f"Collection not found: {collection_name}")
            raise
        except Exception as e:
            logger.error(f"Error getting documents from {collection_name}: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to get documents: {str(e)}"
            ))

    async def update_documents(
        self,
        collection_name: str,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None
    ) -> Dict[str, Any]:
        """Update documents in a collection."""
        try:
            collection = self._get_collection(collection_name)

            # Validate inputs
            if not any([documents, metadatas, embeddings]):
                raise ValidationError("At least one of documents, metadatas, or embeddings must be provided")
            
            # Validate lengths match
            length = len(ids)
            if documents and len(documents) != length:
                raise ValidationError("Number of documents must match number of ids")
            if metadatas and len(metadatas) != length:
                raise ValidationError("Number of metadatas must match number of ids")
            if embeddings and len(embeddings) != length:
                raise ValidationError("Number of embeddings must match number of ids")

            # Update documents
            collection.update(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )

            logger.info(f"Updated {len(ids)} documents in collection: {collection_name}")
            return {
                "success": True,
                "count": len(ids),
                "collection_name": collection_name
            }

        except ValidationError as e:
            logger.error(f"Invalid parameters: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error updating documents in {collection_name}: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to update documents: {str(e)}"
            ))

    async def delete_documents(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Delete documents from a collection."""
        try:
            collection = self._get_collection(collection_name)

            # Validate inputs
            if not any([ids, where, where_document]):
                raise ValidationError("At least one of ids, where, or where_document must be provided")

            # Get documents to be deleted for return value
            include = ["documents", "metadatas"]
            if ids:
                deleted_docs = collection.get(ids=ids, include=include)
            elif where:
                deleted_docs = collection.get(where=where, include=include)
            else:
                deleted_docs = collection.get(where_document=where_document, include=include)

            # Delete documents
            collection.delete(
                ids=ids,
                where=where,
                where_document=where_document
            )

            logger.info(f"Deleted documents from collection: {collection_name}")
            return {
                "success": True,
                "deleted_documents": {
                    "ids": deleted_docs["ids"],
                    "documents": deleted_docs.get("documents"),
                    "metadatas": deleted_docs.get("metadatas")
                }
            }

        except ValidationError as e:
            logger.error(f"Invalid parameters: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error deleting documents from {collection_name}: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to delete documents: {str(e)}"
            ))
