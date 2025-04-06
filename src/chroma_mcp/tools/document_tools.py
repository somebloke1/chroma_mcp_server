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

# --- Implementation Functions ---

async def _add_documents_impl(
    collection_name: str,
    documents: List[str],
    metadatas: List[Dict[str, Any]] = None,
    ids: List[str] = None,
    increment_index: bool = True
) -> Dict[str, Any]:
    """Implementation logic for adding documents."""
    try:
        # Handle None defaults for lists
        effective_metadatas = metadatas if metadatas is not None else []
        effective_ids = ids if ids is not None else []
        
        # Input validation
        if not documents:
            raise_validation_error("No documents provided")
        if effective_metadatas and len(effective_metadatas) != len(documents):
            raise_validation_error("Number of metadatas must match number of documents")
        if effective_ids and len(effective_ids) != len(documents):
            raise_validation_error("Number of IDs must match number of documents")
        
        # Get or create collection - Await the client call
        client = get_chroma_client()
        collection = await client.get_or_create_collection(
            name=collection_name,
            embedding_function=get_embedding_function()
        )
        
        # Generate IDs if not provided (use effective_ids)
        generated_ids = False
        final_ids = effective_ids
        if not final_ids:
            generated_ids = True
            # Await the count() call
            current_count = await collection.count() if increment_index else 0
            timestamp = int(time.time())
            final_ids = [f"doc_{timestamp}_{current_count + i}" for i in range(len(documents))]
        
        # Prepare metadatas (use effective_metadatas)
        final_metadatas = effective_metadatas if effective_metadatas else None
        
        # Add documents - Await the add() call
        await collection.add(
            documents=documents,
            metadatas=final_metadatas, # Pass None if list was empty
            ids=final_ids
        )
        
        logger.info(f"Added {len(documents)} documents to collection {collection_name}")
        return {
            "success": True,
            "added_count": len(documents),
            "collection_name": collection_name,
            "document_ids": final_ids,
            "ids_generated": generated_ids
        }
        
    except Exception as e:
        raise handle_chroma_error(e, "add_documents")

async def _query_documents_impl(
    collection_name: str,
    query_texts: List[str],
    n_results: int = 5,
    where: Dict[str, Any] = None,
    where_document: Dict[str, Any] = None,
    include: List[str] = None
) -> Dict[str, Any]:
    """Implementation logic for querying documents."""
    try:
        # Handle None defaults for dicts/lists
        effective_where = where if where is not None else {}
        effective_where_document = where_document if where_document is not None else {}
        effective_include = include if include is not None else []
        
        # Input validation
        if not query_texts:
            raise_validation_error("No query texts provided")
        if n_results <= 0:
            raise_validation_error("n_results must be a positive integer")
            
        # Validate include values if provided
        valid_includes = ["documents", "embeddings", "metadatas", "distances"]
        if effective_include and not all(item in valid_includes for item in effective_include):
            raise_validation_error(f"Invalid item in include list. Valid items are: {valid_includes}")
        
        # Get collection - Await the client call
        client = get_chroma_client()
        collection = await client.get_collection(
            name=collection_name,
            embedding_function=get_embedding_function()
        )
        
        # Set default includes if list was empty
        final_include = effective_include if effective_include else ["documents", "metadatas", "distances"]
        
        # Query documents using effective filters (pass None if dicts were empty)
        # Await the query() call
        results = await collection.query(
            query_texts=query_texts,
            n_results=n_results,
            where=effective_where if effective_where else None,
            where_document=effective_where_document if effective_where_document else None,
            include=final_include
        )
        
        # Format results - Check if keys exist in results dict
        formatted_results = []
        if results: # Ensure results is not None
            for i, query in enumerate(query_texts):
                query_result = {
                    "query": query,
                    "matches": []
                }
                
                # Check if index i exists in result lists
                ids_list = results.get("ids")
                if ids_list and i < len(ids_list) and ids_list[i]:
                    num_matches = len(ids_list[i])
                    for j in range(num_matches):
                        match = {
                            "id": ids_list[i][j]
                        }
                        
                        distances_list = results.get("distances")
                        if "distances" in final_include and distances_list and i < len(distances_list) and j < len(distances_list[i]):
                            match["distance"] = distances_list[i][j]
                        
                        documents_list = results.get("documents")
                        if "documents" in final_include and documents_list and i < len(documents_list) and j < len(documents_list[i]):
                            match["document"] = documents_list[i][j]
                            
                        metadatas_list = results.get("metadatas")
                        if "metadatas" in final_include and metadatas_list and i < len(metadatas_list) and j < len(metadatas_list[i]):
                            match["metadata"] = metadatas_list[i][j]
                            
                        embeddings_list = results.get("embeddings")
                        if "embeddings" in final_include and embeddings_list and i < len(embeddings_list) and j < len(embeddings_list[i]):
                            match["embedding"] = embeddings_list[i][j] # May be None if not stored
                            
                        query_result["matches"].append(match)
                        
                formatted_results.append(query_result)
        
        return {
            "results": formatted_results,
            "total_queries": len(query_texts)
        }
        
    except Exception as e:
        raise handle_chroma_error(e, "query_documents")

async def _get_documents_impl(
    collection_name: str,
    ids: List[str] = None,
    where: Dict[str, Any] = None,
    where_document: Dict[str, Any] = None,
    include: List[str] = None,
    limit: int = 0,
    offset: int = 0
) -> Dict[str, Any]:
    """Implementation logic for getting documents."""
    try:
        # Handle None defaults
        effective_ids = ids if ids is not None else []
        effective_where = where if where is not None else {}
        effective_where_document = where_document if where_document is not None else {}
        effective_include = include if include is not None else []
        
        # Basic validation
        if not effective_ids and not effective_where and not effective_where_document:
            raise_validation_error("At least one of ids, where, or where_document must be provided to get documents.")
        
        if limit < 0:
            raise_validation_error("limit cannot be negative")
        if offset < 0:
            raise_validation_error("offset cannot be negative")
            
        # Validate include values if provided
        valid_includes = ["documents", "embeddings", "metadatas"]
        if effective_include and not all(item in valid_includes for item in effective_include):
            raise_validation_error(f"Invalid item in include list. Valid items are: {valid_includes}")
        
        # Get collection - Await the client call
        client = get_chroma_client()
        collection = await client.get_collection(
            name=collection_name,
            embedding_function=get_embedding_function()
        )
        
        # Set default includes if list was empty
        final_include = effective_include if effective_include else ["documents", "metadatas"]
        
        # Convert limit/offset 0 to None for ChromaDB client
        final_limit = limit if limit > 0 else None
        final_offset = offset if offset > 0 else None
        
        # Get documents using effective filters (pass None if empty)
        # Await the get() call
        results = await collection.get(
            ids=effective_ids if effective_ids else None,
            where=effective_where if effective_where else None,
            where_document=effective_where_document if effective_where_document else None,
            include=final_include,
            limit=final_limit,
            offset=final_offset
        )
        
        # Format results
        formatted_documents = []
        if results and results.get("ids"):
            ids_list = results["ids"]
            docs_list = results.get("documents") # Might be None if not included
            metas_list = results.get("metadatas") # Might be None if not included
            embeds_list = results.get("embeddings") # Might be None if not included
            
            for i, doc_id in enumerate(ids_list):
                doc = {"id": doc_id}
                if "documents" in final_include and docs_list and i < len(docs_list):
                    doc["content"] = docs_list[i]
                if "metadatas" in final_include and metas_list and i < len(metas_list):
                    doc["metadata"] = metas_list[i]
                if "embeddings" in final_include and embeds_list and i < len(embeds_list):
                    doc["embedding"] = embeds_list[i]
                formatted_documents.append(doc)
        
        return {
            "documents": formatted_documents,
            "total_found": len(formatted_documents), # Based on returned results
            "limit": limit, # Return original requested limit
            "offset": offset # Return original requested offset
        }
        
    except Exception as e:
        raise handle_chroma_error(e, "get_documents")

async def _update_documents_impl(
    collection_name: str,
    ids: List[str],
    documents: List[str] = None,
    metadatas: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Implementation logic for updating documents."""
    try:
        # Handle None defaults for lists
        effective_documents = documents if documents is not None else []
        effective_metadatas = metadatas if metadatas is not None else []
        
        # Input validation
        if not ids:
            raise_validation_error("List of document IDs is required for update")
        if not effective_documents and not effective_metadatas:
            raise_validation_error("Either documents or metadatas must be provided for update")
        if effective_documents and len(effective_documents) != len(ids):
            raise_validation_error("Number of documents must match number of IDs")
        if effective_metadatas and len(effective_metadatas) != len(ids):
            raise_validation_error("Number of metadatas must match number of IDs")
        
        # Get collection - Await the client call
        client = get_chroma_client()
        collection = await client.get_collection(
            name=collection_name,
            embedding_function=get_embedding_function()
        )
        
        # Update documents (pass None if lists were empty)
        # Await the update() call
        await collection.update(
            ids=ids,
            documents=effective_documents if effective_documents else None,
            metadatas=effective_metadatas if effective_metadatas else None
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

async def _delete_documents_impl(
    collection_name: str,
    ids: List[str] = None,
    where: Dict[str, Any] = None,
    where_document: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Implementation logic for deleting documents."""
    try:
        # Handle None defaults
        effective_ids = ids if ids is not None else []
        effective_where = where if where is not None else {}
        effective_where_document = where_document if where_document is not None else {}
        
        # Input validation: Must provide at least one condition
        if not effective_ids and not effective_where and not effective_where_document:
            raise_validation_error("Either ids, where, or where_document must be provided for deletion")
            
        # Get collection - Await the client call
        client = get_chroma_client()
        collection = await client.get_collection(
            name=collection_name,
            embedding_function=get_embedding_function()
        )
        
        # Determine deletion method for logging and result structure
        delete_by_ids = bool(effective_ids)
        
        # Delete documents (pass None if filters/ids are empty)
        # Await the delete() call
        await collection.delete(
            ids=effective_ids if effective_ids else None,
            where=effective_where if effective_where else None,
            where_document=effective_where_document if effective_where_document else None
        )
        
        # Construct response based on deletion method
        if delete_by_ids:
            deleted_count = len(effective_ids)
            deleted_ids_response = effective_ids
            logger.info(f"Attempted deletion of {deleted_count} documents by ID from collection {collection_name}")
        else:
            deleted_count = -1 # Count is unknown when deleting by filter
            deleted_ids_response = []
            logger.info(f"Attempted deletion of documents by filter from collection {collection_name}")

        return {
            "success": True,
            "collection_name": collection_name,
            "deleted_count": deleted_count,
            "deleted_ids": deleted_ids_response # Return input IDs if deleted by ID, empty list otherwise
        }
        
    except Exception as e:
        raise handle_chroma_error(e, "delete_documents")

# --- Tool Registration ---

def register_document_tools(mcp: FastMCP) -> None:
    """Register document management tools with the MCP server."""
    
    @mcp.tool()
    async def chroma_add_documents(
        collection_name: str,
        documents: List[str],
        metadatas: List[Dict[str, Any]] = None,
        ids: List[str] = None,
        increment_index: bool = True
    ) -> Dict[str, Any]:
        """
        Add documents to a ChromaDB collection.
        
        Args:
            collection_name: Name of the collection to add documents to
            documents: List of text documents to add
            metadatas: Optional list of metadata dictionaries for each document (use None or empty list)
            ids: Optional list of IDs for the documents (use None or empty list)
            increment_index: Whether to increment index for auto-generated IDs
            
        Returns:
            Dictionary containing operation results
        """
        # Call the implementation function
        return await _add_documents_impl(
            collection_name=collection_name,
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            increment_index=increment_index
        )
    
    @mcp.tool()
    async def chroma_query_documents(
        collection_name: str,
        query_texts: List[str],
        n_results: int = 5,
        where: Dict[str, Any] = None,
        where_document: Dict[str, Any] = None,
        include: List[str] = None
    ) -> Dict[str, Any]:
        """
        Query documents from a ChromaDB collection with advanced filtering.
        
        Args:
            collection_name: Name of the collection to query
            query_texts: List of query texts to search for
            n_results: Number of results to return per query
            where: Optional metadata filters (use None or empty dict)
                   Examples:
                   - Simple equality: {"metadata_field": "value"}
                   - Comparison: {"metadata_field": {"$gt": 5}}
                   - Logical AND: {"$and": [{"field1": "value1"}, {"field2": {"$gt": 5}}]}
                   - Logical OR: {"$or": [{"field1": "value1"}, {"field1": "value2"}]}
            where_document: Optional document content filters (use None or empty dict)
            include: Optional list of what to include in response (use None or empty list)
                    Can contain: ["documents", "embeddings", "metadatas", "distances"]
            
        Returns:
            Dictionary containing query results
        """
        # Call the implementation function
        return await _query_documents_impl(
            collection_name=collection_name,
            query_texts=query_texts,
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=include
        )
    
    @mcp.tool()
    async def chroma_get_documents(
        collection_name: str,
        ids: List[str] = None,
        where: Dict[str, Any] = None,
        where_document: Dict[str, Any] = None,
        include: List[str] = None,
        limit: int = 0,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get documents from a ChromaDB collection with optional filtering.
        
        Args:
            collection_name: Name of the collection to get documents from
            ids: Optional list of document IDs to retrieve (use None or empty list)
            where: Optional metadata filters (use None or empty dict)
            where_document: Optional document content filters (use None or empty dict)
            include: Optional list of what to include in response (use None or empty list)
                    Can contain: ["documents", "embeddings", "metadatas"]
            limit: Optional maximum number of documents to return (use 0 for no limit)
            offset: Optional number of documents to skip (use 0 for no offset)
            
        Returns:
            Dictionary containing matching documents
        """
        # Call the implementation function
        return await _get_documents_impl(
            collection_name=collection_name,
            ids=ids,
            where=where,
            where_document=where_document,
            include=include,
            limit=limit,
            offset=offset
        )
    
    @mcp.tool()
    async def chroma_update_documents(
        collection_name: str,
        ids: List[str],
        documents: List[str] = None,
        metadatas: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update existing documents in a ChromaDB collection.
        
        Args:
            collection_name: Name of the collection
            ids: List of document IDs to update
            documents: Optional list of new document contents (use None or empty list)
            metadatas: Optional list of new metadata dictionaries (use None or empty list)
            
        Returns:
            Dictionary containing update results
        """
        # Call the implementation function
        return await _update_documents_impl(
            collection_name=collection_name,
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
    
    @mcp.tool()
    async def chroma_delete_documents(
        collection_name: str,
        ids: List[str] = None,
        where: Dict[str, Any] = None,
        where_document: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Delete documents from a ChromaDB collection.
        
        Args:
            collection_name: Name of the collection
            ids: List of document IDs to delete (use None or empty list)
            where: Optional metadata filters for deletion (use None or empty dict)
            where_document: Optional document content filters for deletion (use None or empty dict)
            
        Returns:
            Dictionary containing deletion results
        """
        # Call the implementation function
        return await _delete_documents_impl(
            collection_name=collection_name,
            ids=ids,
            where=where,
            where_document=where_document
        )
