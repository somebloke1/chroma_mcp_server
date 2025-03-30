"""
Thinking Handler for Chroma MCP Server

This module provides functionality for storing and retrieving thoughts
for sequential thinking in AI applications using ChromaDB.
"""

import os
import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import uuid
import time
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
from ..types import ChromaClientConfig, ThoughtMetadata

# Initialize logger
logger = LoggerSetup.create_logger(
    "ThinkingHandler",
    log_file="thinking_handler.log", 
    log_level=os.getenv("LOG_LEVEL", "INFO")
)

# Constants
THOUGHTS_COLLECTION = "thoughts"
SESSIONS_COLLECTION = "thinking_sessions"
DEFAULT_SIMILARITY_THRESHOLD = 0.75

@dataclass
class ThoughtMetadata:
    """Metadata structure for thoughts."""
    session_id: str
    thought_number: int
    total_thoughts: int
    timestamp: int
    branch_from_thought: Optional[int] = None
    branch_id: Optional[str] = None
    next_thought_needed: bool = False
    custom_data: Optional[Dict[str, Any]] = None

@dataclass
class ThinkingHandler:
    """Handler for managing sequential thinking operations."""

    def __init__(self, config: Optional[ChromaClientConfig] = None):
        """Initialize the thinking handler."""
        self._client = get_chroma_client(config)
        self._ensure_collections()
        logger.info("Thinking handler initialized")

    def _ensure_collections(self):
        """Ensure required collections exist."""
        try:
            # Create thoughts collection if it doesn't exist
            try:
                self._client.get_collection(THOUGHTS_COLLECTION)
            except ValueError:
                self._client.create_collection(THOUGHTS_COLLECTION)
                logger.info(f"Created collection: {THOUGHTS_COLLECTION}")

            # Create sessions collection if it doesn't exist
            try:
                self._client.get_collection(SESSIONS_COLLECTION)
            except ValueError:
                self._client.create_collection(SESSIONS_COLLECTION)
                logger.info(f"Created collection: {SESSIONS_COLLECTION}")

        except Exception as e:
            logger.error(f"Error ensuring collections: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to ensure collections: {str(e)}"
            ))

    def _get_collection(self, collection_name: str) -> Collection:
        """Get a collection by name, with error handling."""
        try:
            return self._client.get_collection(collection_name)
        except ValueError as e:
            logger.error(f"Collection not found: {collection_name}")
            raise McpError(ErrorData(
                code=INVALID_PARAMS,
                message=f"Collection not found: {collection_name}"
            ))

    async def record_thought(
        self,
        thought: str,
        thought_number: int,
        total_thoughts: int,
        session_id: Optional[str] = None,
        branch_from_thought: Optional[int] = None,
        branch_id: Optional[str] = None,
        next_thought_needed: bool = False,
        custom_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record a thought in a sequential thinking process."""
        try:
            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
                logger.info(f"Created new thinking session: {session_id}")

            # Validate inputs
            if thought_number < 1 or thought_number > total_thoughts:
                raise ValueError("Invalid thought number")
            if branch_from_thought and branch_from_thought >= thought_number:
                raise ValueError("Branch must come from an earlier thought")

            # Create thought metadata
            metadata = ThoughtMetadata(
                session_id=session_id,
                thought_number=thought_number,
                total_thoughts=total_thoughts,
                timestamp=int(time.time()),
                branch_from_thought=branch_from_thought,
                branch_id=branch_id,
                next_thought_needed=next_thought_needed,
                custom_data=custom_data
            )

            # Get collections
            thoughts_collection = self._get_collection(THOUGHTS_COLLECTION)
            sessions_collection = self._get_collection(SESSIONS_COLLECTION)

            # Generate thought ID
            thought_id = f"{session_id}_{thought_number}"
            if branch_id:
                thought_id = f"{thought_id}_{branch_id}"

            # Add thought to thoughts collection
            thoughts_collection.add(
                documents=[thought],
                metadatas=[metadata.__dict__],
                ids=[thought_id]
            )

            # Update session metadata if first thought
            if thought_number == 1 and not branch_id:
                sessions_collection.add(
                    documents=[f"Session started: {thought}"],
                    metadatas=[{
                        "session_id": session_id,
                        "total_thoughts": total_thoughts,
                        "start_time": metadata.timestamp,
                        "status": "in_progress"
                    }],
                    ids=[session_id]
                )

            # Get previous thoughts in the chain
            where = {"session_id": session_id}
            if branch_id:
                where["branch_id"] = branch_id
            previous_thoughts = thoughts_collection.get(
                where=where,
                include=["documents", "metadatas"]
            )

            logger.info(f"Recorded thought {thought_number} in session: {session_id}")
            return {
                "success": True,
                "thought_id": thought_id,
                "session_id": session_id,
                "thought_number": thought_number,
                "total_thoughts": total_thoughts,
                "branch_id": branch_id,
                "previous_thoughts": [
                    {
                        "id": id,
                        "thought": doc,
                        "metadata": meta
                    }
                    for id, doc, meta in zip(
                        previous_thoughts["ids"],
                        previous_thoughts["documents"],
                        previous_thoughts["metadatas"]
                    )
                ],
                "next_thought_needed": next_thought_needed
            }

        except ValueError as e:
            logger.error(f"Invalid parameters: {str(e)}")
            raise McpError(ErrorData(
                code=INVALID_PARAMS,
                message=f"Invalid parameters: {str(e)}"
            ))
        except Exception as e:
            logger.error(f"Error recording thought: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to record thought: {str(e)}"
            ))

    async def find_similar_thoughts(
        self,
        query: str,
        n_results: int = 5,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Find similar thoughts based on semantic similarity."""
        try:
            collection = self._get_collection(THOUGHTS_COLLECTION)

            # Prepare query parameters
            where = {"session_id": session_id} if session_id else None
            
            # Execute query
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"]
            )

            # Filter by similarity threshold
            filtered_results = []
            for i, distance in enumerate(results["distances"][0]):
                similarity = 1 - distance  # Convert distance to similarity
                if similarity >= threshold:
                    filtered_results.append({
                        "id": results["ids"][0][i],
                        "thought": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "similarity": similarity
                    })

            logger.info(f"Found {len(filtered_results)} similar thoughts")
            return {
                "query": query,
                "results": filtered_results,
                "total": len(filtered_results)
            }

        except Exception as e:
            logger.error(f"Error finding similar thoughts: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to find similar thoughts: {str(e)}"
            ))

    async def get_session_summary(
        self,
        session_id: str,
        include_branches: bool = True
    ) -> Dict[str, Any]:
        """Get a summary of all thoughts in a thinking session."""
        try:
            thoughts_collection = self._get_collection(THOUGHTS_COLLECTION)
            sessions_collection = self._get_collection(SESSIONS_COLLECTION)

            # Get session metadata
            session = sessions_collection.get(
                ids=[session_id],
                include=["metadatas"]
            )
            if not session["ids"]:
                raise ValueError(f"Session not found: {session_id}")

            # Get all thoughts in the session
            thoughts = thoughts_collection.get(
                where={"session_id": session_id},
                include=["documents", "metadatas"]
            )

            # Organize thoughts into main path and branches
            main_path = []
            branches = {}

            for id, thought, metadata in zip(
                thoughts["ids"],
                thoughts["documents"],
                thoughts["metadatas"]
            ):
                thought_data = {
                    "id": id,
                    "thought": thought,
                    "metadata": metadata
                }

                if metadata.get("branch_id"):
                    branch_id = metadata["branch_id"]
                    if branch_id not in branches:
                        branches[branch_id] = []
                    branches[branch_id].append(thought_data)
                else:
                    main_path.append(thought_data)

            # Sort thoughts by number
            main_path.sort(key=lambda x: x["metadata"]["thought_number"])
            for branch in branches.values():
                branch.sort(key=lambda x: x["metadata"]["thought_number"])

            logger.info(f"Generated summary for session: {session_id}")
            return {
                "session_id": session_id,
                "metadata": session["metadatas"][0],
                "main_path": main_path,
                "branches": branches if include_branches else None,
                "total_thoughts": len(thoughts["ids"])
            }

        except ValueError as e:
            logger.error(f"Invalid parameters: {str(e)}")
            raise McpError(ErrorData(
                code=INVALID_PARAMS,
                message=f"Invalid parameters: {str(e)}"
            ))
        except Exception as e:
            logger.error(f"Error getting session summary: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to get session summary: {str(e)}"
            ))

    async def find_similar_sessions(
        self,
        query: str,
        n_results: int = 3,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD
    ) -> Dict[str, Any]:
        """Find thinking sessions with similar content."""
        try:
            sessions_collection = self._get_collection(SESSIONS_COLLECTION)
            thoughts_collection = self._get_collection(THOUGHTS_COLLECTION)

            # Query sessions
            session_results = sessions_collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )

            similar_sessions = []
            for i, session_id in enumerate(session_results["ids"][0]):
                similarity = 1 - session_results["distances"][0][i]
                if similarity >= threshold:
                    # Get thoughts for this session
                    session_thoughts = thoughts_collection.get(
                        where={"session_id": session_id},
                        include=["documents", "metadatas"]
                    )

                    similar_sessions.append({
                        "session_id": session_id,
                        "metadata": session_results["metadatas"][0][i],
                        "similarity": similarity,
                        "thoughts": [
                            {
                                "thought": doc,
                                "metadata": meta
                            }
                            for doc, meta in zip(
                                session_thoughts["documents"],
                                session_thoughts["metadatas"]
                            )
                        ]
                    })

            logger.info(f"Found {len(similar_sessions)} similar sessions")
            return {
                "query": query,
                "results": similar_sessions,
                "total": len(similar_sessions)
            }

        except Exception as e:
            logger.error(f"Error finding similar sessions: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to find similar sessions: {str(e)}"
            ))

    async def add_thoughts(self, collection_name: str, thoughts_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add thoughts to a collection."""
        try:
            collection = self._get_collection(collection_name)

            # Validate inputs
            if not thoughts_data.get("thoughts") or not thoughts_data.get("ids"):
                raise ValidationError("Thoughts and IDs are required")

            # Add thoughts
            collection.add(
                documents=thoughts_data["thoughts"],
                metadatas=thoughts_data.get("metadatas"),
                ids=thoughts_data["ids"],
                embeddings=thoughts_data.get("embeddings")
            )

            logger.info(f"Added {len(thoughts_data['thoughts'])} thoughts to collection: {collection_name}")
            return {
                "success": True,
                "count": len(thoughts_data["thoughts"]),
                "collection_name": collection_name
            }

        except ValidationError as e:
            raise e
        except Exception as e:
            logger.error(f"Error adding thoughts to {collection_name}: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to add thoughts: {str(e)}"
            ))

    async def query_thoughts(self, collection_name: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """Query thoughts from a collection."""
        try:
            collection = self._get_collection(collection_name)

            # Validate inputs
            if not query_params.get("query_texts") and not query_params.get("query_embeddings"):
                raise ValidationError("Either query_texts or query_embeddings must be provided")

            # Query thoughts
            results = collection.query(
                query_texts=query_params.get("query_texts"),
                query_embeddings=query_params.get("query_embeddings"),
                n_results=query_params.get("n_results", 10),
                where=query_params.get("where"),
                where_document=query_params.get("where_document"),
                include=query_params.get("include", ["documents", "metadatas", "distances"])
            )

            logger.info(f"Queried thoughts from collection: {collection_name}")
            return {
                "ids": results["ids"],
                "documents": results.get("documents"),
                "metadatas": results.get("metadatas"),
                "distances": results.get("distances")
            }

        except ValidationError as e:
            raise e
        except Exception as e:
            logger.error(f"Error querying thoughts from {collection_name}: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to query thoughts: {str(e)}"
            ))

    async def get_thoughts(self, collection_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get thoughts from a collection."""
        try:
            collection = self._get_collection(collection_name)

            # Get thoughts
            results = collection.get(
                ids=params.get("ids"),
                where=params.get("where"),
                limit=params.get("limit"),
                offset=params.get("offset"),
                include=params.get("include", ["documents", "metadatas"])
            )

            logger.info(f"Retrieved thoughts from collection: {collection_name}")
            return {
                "ids": results["ids"],
                "documents": results.get("documents"),
                "metadatas": results.get("metadatas"),
                "embeddings": results.get("embeddings")
            }

        except Exception as e:
            logger.error(f"Error getting thoughts from {collection_name}: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to get thoughts: {str(e)}"
            ))

    async def update_thoughts(self, collection_name: str, thoughts_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update thoughts in a collection."""
        try:
            collection = self._get_collection(collection_name)

            # Validate inputs
            if not thoughts_data.get("ids"):
                raise ValidationError("IDs are required for update")
            if thoughts_data.get("documents") and len(thoughts_data["documents"]) != len(thoughts_data["ids"]):
                raise ValidationError("Number of documents must match number of ids")
            if thoughts_data.get("metadatas") and len(thoughts_data["metadatas"]) != len(thoughts_data["ids"]):
                raise ValidationError("Number of metadatas must match number of ids")

            # Update thoughts
            collection.update(
                ids=thoughts_data["ids"],
                documents=thoughts_data.get("documents"),
                metadatas=thoughts_data.get("metadatas"),
                embeddings=thoughts_data.get("embeddings")
            )

            logger.info(f"Updated {len(thoughts_data['ids'])} thoughts in collection: {collection_name}")
            return {
                "success": True,
                "count": len(thoughts_data["ids"]),
                "collection_name": collection_name
            }

        except ValidationError as e:
            raise e
        except Exception as e:
            logger.error(f"Error updating thoughts in {collection_name}: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to update thoughts: {str(e)}"
            ))

    async def delete_thoughts(self, collection_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete thoughts from a collection."""
        try:
            collection = self._get_collection(collection_name)

            # Validate inputs
            if not any([params.get("ids"), params.get("where"), params.get("where_document")]):
                raise ValidationError("At least one of ids, where, or where_document must be provided")

            # Get thoughts to be deleted for return value
            include = ["documents", "metadatas"]
            if params.get("ids"):
                deleted_docs = collection.get(ids=params["ids"], include=include)
            elif params.get("where"):
                deleted_docs = collection.get(where=params["where"], include=include)
            else:
                deleted_docs = collection.get(where_document=params["where_document"], include=include)

            # Delete thoughts
            collection.delete(
                ids=params.get("ids"),
                where=params.get("where"),
                where_document=params.get("where_document")
            )

            logger.info(f"Deleted thoughts from collection: {collection_name}")
            return {
                "success": True,
                "deleted_documents": {
                    "ids": deleted_docs["ids"],
                    "documents": deleted_docs.get("documents"),
                    "metadatas": deleted_docs.get("metadatas")
                }
            }

        except ValidationError as e:
            raise e
        except Exception as e:
            logger.error(f"Error deleting thoughts from {collection_name}: {str(e)}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to delete thoughts: {str(e)}"
            ))
