"""
Document management tools for ChromaDB operations.
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INVALID_PARAMS

from ..utils.logger_setup import LoggerSetup
from ..utils.client import get_chroma_client, get_embedding_function
from ..utils.errors import handle_chroma_error, validate_input, raise_validation_error

# Initialize logger
logger = LoggerSetup.create_logger(
    "ChromaDocuments",
    log_file="chroma_documents.log"
)

@dataclass
class DocumentMetadata:
    """Document metadata structure."""
    source: Optional[str] = None
    timestamp: Optional[int] = None
    tags: List[str] = None
    custom_data: Dict[str, Any] = None

def register_document_tools(mcp: FastMCP) -> None:
    """Register document management tools with the MCP server."""
    
    @mcp.tool()
    async def chroma_add_documents(
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        increment_index: bool = True
    ) -> Dict[str, Any]:
        """
        Add documents to a ChromaDB collection.
        
        Args:
            collection_name: Name of the collection to add documents to
            documents: List of text documents to add
            metadatas: Optional list of metadata dictionaries for each document
            ids: Optional list of IDs for the documents
            increment_index: Whether to increment index for auto-generated IDs
            
        Returns:
            Dictionary containing operation results
        """
        try:
            # Input validation
            if not documents:
                raise_validation_error("No documents provided")
            
            # Get or create collection
            client = get_chroma_client()
            collection = client.get_or_create_collection(
                name=collection_name,
                embedding_function=get_embedding_function()
            )
            
            # Generate IDs if not provided
            if ids is None:
                current_count = collection.count() if increment_index else 0
                timestamp = int(time.time())
                ids = [f"doc_{timestamp}_{current_count + i}" for i in range(len(documents))]
            
            # Add documents
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(documents)} documents to collection {collection_name}")
            return {
                "success": True,
                "added_count": len(documents),
                "collection_name": collection_name,
                "document_ids": ids
            }
            
        except Exception as e:
            raise handle_chroma_error(e, "add_documents")
    
    @mcp.tool()
    async def chroma_query_documents(
        collection_name: str,
        query_texts: List[str],
        n_results: int = 5,
        where: Optional[Dict] = None,
        where_document: Optional[Dict] = None,
        include: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Query documents from a ChromaDB collection with advanced filtering.
        
        Args:
            collection_name: Name of the collection to query
            query_texts: List of query texts to search for
            n_results: Number of results to return per query
            where: Optional metadata filters using Chroma's query operators
                   Examples:
                   - Simple equality: {"metadata_field": "value"}
                   - Comparison: {"metadata_field": {"$gt": 5}}
                   - Logical AND: {"$and": [{"field1": "value1"}, {"field2": {"$gt": 5}}]}
                   - Logical OR: {"$or": [{"field1": "value1"}, {"field1": "value2"}]}
            where_document: Optional document content filters
            include: Optional list of what to include in response
                    Can contain: ["documents", "embeddings", "metadatas", "distances"]
            
        Returns:
            Dictionary containing query results
        """
        try:
            # Input validation
            if not query_texts:
                raise_validation_error("No query texts provided")
            
            # Get collection
            client = get_chroma_client()
            collection = client.get_collection(
                name=collection_name,
                embedding_function=get_embedding_function()
            )
            
            # Set default includes if not specified
            if not include:
                include = ["documents", "metadatas", "distances"]
            
            # Query documents
            results = collection.query(
                query_texts=query_texts,
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=include
            )
            
            # Format results
            formatted_results = []
            for i, query in enumerate(query_texts):
                query_result = {
                    "query": query,
                    "matches": []
                }
                
                for j in range(len(results["ids"][i])):
                    match = {
                        "id": results["ids"][i][j],
                        "distance": results["distances"][i][j] if "distances" in results else None
                    }
                    
                    if "documents" in results:
                        match["document"] = results["documents"][i][j]
                    if "metadatas" in results:
                        match["metadata"] = results["metadatas"][i][j]
                    if "embeddings" in results:
                        match["embedding"] = results["embeddings"][i][j]
                        
                    query_result["matches"].append(match)
                    
                formatted_results.append(query_result)
            
            return {
                "results": formatted_results,
                "total_queries": len(query_texts)
            }
            
        except Exception as e:
            raise handle_chroma_error(e, "query_documents")
    
    @mcp.tool()
    async def chroma_get_documents(
        collection_name: str,
        ids: Optional[List[str]] = None,
        where: Optional[Dict] = None,
        where_document: Optional[Dict] = None,
        include: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get documents from a ChromaDB collection with optional filtering.
        
        Args:
            collection_name: Name of the collection to get documents from
            ids: Optional list of document IDs to retrieve
            where: Optional metadata filters using Chroma's query operators
            where_document: Optional document content filters
            include: Optional list of what to include in response
                    Can contain: ["documents", "embeddings", "metadatas"]
            limit: Optional maximum number of documents to return
            offset: Optional number of documents to skip
            
        Returns:
            Dictionary containing matching documents
        """
        try:
            client = get_chroma_client()
            collection = client.get_collection(
                name=collection_name,
                embedding_function=get_embedding_function()
            )
            
            # Set default includes if not specified
            if not include:
                include = ["documents", "metadatas"]
            
            # Get documents
            results = collection.get(
                ids=ids,
                where=where,
                where_document=where_document,
                include=include,
                limit=limit,
                offset=offset
            )
            
            # Format results
            formatted_documents = []
            for i in range(len(results["ids"])):
                document = {
                    "id": results["ids"][i]
                }
                
                if "documents" in results:
                    document["content"] = results["documents"][i]
                if "metadatas" in results:
                    document["metadata"] = results["metadatas"][i]
                if "embeddings" in results:
                    document["embedding"] = results["embeddings"][i]
                    
                formatted_documents.append(document)
            
            return {
                "documents": formatted_documents,
                "total_found": len(formatted_documents),
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            raise handle_chroma_error(e, "get_documents")
    
    @mcp.tool()
    async def chroma_update_documents(
        collection_name: str,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Update existing documents in a ChromaDB collection.
        
        Args:
            collection_name: Name of the collection
            ids: List of document IDs to update
            documents: Optional list of new document contents
            metadatas: Optional list of new metadata dictionaries
            
        Returns:
            Dictionary containing update results
        """
        try:
            # Input validation
            if not ids:
                raise_validation_error("No document IDs provided")
            if not documents and not metadatas:
                raise_validation_error("No updates provided (documents or metadatas required)")
            
            client = get_chroma_client()
            collection = client.get_collection(
                name=collection_name,
                embedding_function=get_embedding_function()
            )
            
            # Update documents
            collection.update(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"Updated {len(ids)} documents in collection {collection_name}")
            return {
                "success": True,
                "updated_count": len(ids),
                "collection_name": collection_name,
                "document_ids": ids
            }
            
        except Exception as e:
            raise handle_chroma_error(e, "update_documents")
    
    @mcp.tool()
    async def chroma_delete_documents(
        collection_name: str,
        ids: List[str],
        where: Optional[Dict] = None,
        where_document: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Delete documents from a ChromaDB collection.
        
        Args:
            collection_name: Name of the collection
            ids: List of document IDs to delete
            where: Optional metadata filters for deletion
            where_document: Optional document content filters for deletion
            
        Returns:
            Dictionary containing deletion results
        """
        try:
            # Input validation
            if not ids and not where and not where_document:
                raise_validation_error("No deletion criteria provided (ids, where, or where_document required)")
            
            client = get_chroma_client()
            collection = client.get_collection(
                name=collection_name,
                embedding_function=get_embedding_function()
            )
            
            # Get count before deletion
            initial_count = collection.count()
            
            # Delete documents
            collection.delete(
                ids=ids,
                where=where,
                where_document=where_document
            )
            
            # Get count after deletion
            final_count = collection.count()
            deleted_count = initial_count - final_count
            
            logger.info(f"Deleted {deleted_count} documents from collection {collection_name}")
            return {
                "success": True,
                "deleted_count": deleted_count,
                "collection_name": collection_name,
                "initial_count": initial_count,
                "final_count": final_count
            }
            
        except Exception as e:
            raise handle_chroma_error(e, "delete_documents")
