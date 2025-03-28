"""
Sequential thinking tools for managing thought chains and context in ChromaDB.
"""

import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INVALID_PARAMS, INTERNAL_ERROR

from ..utils.logger_setup import LoggerSetup
from ..utils.client import get_chroma_client, get_embedding_function
from ..utils.errors import handle_chroma_error, validate_input, raise_validation_error
from ..types import ThoughtMetadata

# Initialize logger
logger = LoggerSetup.create_logger(
    "ChromaThinking",
    log_file="chroma_thinking.log"
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

def register_thinking_tools(mcp: FastMCP) -> None:
    """Register sequential thinking tools with the MCP server."""
    
    @mcp.tool()
    async def chroma_sequential_thinking(
        thought: str,
        thought_number: int,
        total_thoughts: int,
        session_id: Optional[str] = None,
        branch_from_thought: Optional[int] = None,
        branch_id: Optional[str] = None,
        next_thought_needed: bool = False,
        custom_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record a thought in a sequential thinking process.
        
        Args:
            thought: The current thought content
            thought_number: Position in the thought sequence (1-based)
            total_thoughts: Total expected thoughts in the sequence
            session_id: Optional session identifier (generated if not provided)
            branch_from_thought: Optional thought number this branches from
            branch_id: Optional branch identifier for parallel thought paths
            next_thought_needed: Whether another thought is needed after this
            custom_data: Optional additional metadata
            
        Returns:
            Dictionary containing thought information and context
        """
        try:
            # Input validation
            if not thought:
                raise_validation_error("Thought content is required")
            if thought_number < 1 or thought_number > total_thoughts:
                raise_validation_error(f"Invalid thought number: {thought_number}")
            
            # Generate or validate session ID
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Create metadata
            timestamp = int(time.time())
            metadata = ThoughtMetadata(
                session_id=session_id,
                thought_number=thought_number,
                total_thoughts=total_thoughts,
                timestamp=timestamp,
                branch_from_thought=branch_from_thought,
                branch_id=branch_id,
                next_thought_needed=next_thought_needed,
                custom_data=custom_data
            )
            
            # Get or create thoughts collection
            client = get_chroma_client()
            collection = client.get_or_create_collection(
                name=THOUGHTS_COLLECTION,
                embedding_function=get_embedding_function()
            )
            
            # Generate unique ID for the thought
            thought_id = f"thought_{session_id}_{thought_number}"
            if branch_id:
                thought_id += f"_branch_{branch_id}"
            
            # Add thought to collection
            collection.add(
                documents=[thought],
                metadatas=[metadata.__dict__],
                ids=[thought_id]
            )
            
            # Get previous thoughts in the session for context
            previous_thoughts = []
            if thought_number > 1:
                where_clause = {
                    "session_id": session_id,
                    "thought_number": {"$lt": thought_number}
                }
                if branch_id:
                    where_clause["branch_id"] = branch_id
                
                results = collection.get(
                    where=where_clause,
                    include=["documents", "metadatas"]
                )
                
                for i in range(len(results["ids"])):
                    previous_thoughts.append({
                        "content": results["documents"][i],
                        "metadata": results["metadatas"][i]
                    })
            
            logger.info(f"Recorded thought {thought_number}/{total_thoughts} for session {session_id}")
            return {
                "success": True,
                "thought_id": thought_id,
                "session_id": session_id,
                "thought_number": thought_number,
                "total_thoughts": total_thoughts,
                "previous_thoughts": previous_thoughts,
                "next_thought_needed": next_thought_needed
            }
            
        except Exception as e:
            raise handle_chroma_error(e, "sequential_thinking")
    
    @mcp.tool()
    async def chroma_find_similar_thoughts(
        query: str,
        n_results: int = 5,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        session_id: Optional[str] = None,
        include_branches: bool = True
    ) -> Dict[str, Any]:
        """
        Find similar thoughts across all or specific thinking sessions.
        
        Args:
            query: The thought or concept to search for
            n_results: Number of similar thoughts to return
            threshold: Similarity threshold (0-1)
            session_id: Optional session ID to limit search scope
            include_branches: Whether to include thoughts from branch paths
            
        Returns:
            Dictionary containing similar thoughts and their metadata
        """
        try:
            client = get_chroma_client()
            collection = client.get_collection(
                name=THOUGHTS_COLLECTION,
                embedding_function=get_embedding_function()
            )
            
            # Prepare where clause for filtering
            where = None
            if session_id:
                where = {"session_id": session_id}
            
            # Query similar thoughts
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"]
            )
            
            # Filter by similarity threshold and format results
            similar_thoughts = []
            for i in range(len(results["ids"][0])):
                distance = results["distances"][0][i]
                similarity = 1 - distance  # Convert distance to similarity
                
                if similarity >= threshold:
                    thought = {
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "similarity": similarity
                    }
                    similar_thoughts.append(thought)
            
            return {
                "similar_thoughts": similar_thoughts,
                "total_found": len(similar_thoughts),
                "threshold": threshold
            }
            
        except Exception as e:
            raise handle_chroma_error(e, "find_similar_thoughts")
    
    @mcp.tool()
    async def chroma_get_session_summary(
        session_id: str,
        include_branches: bool = True
    ) -> Dict[str, Any]:
        """
        Get a summary of all thoughts in a thinking session.
        
        Args:
            session_id: The session identifier
            include_branches: Whether to include branching thought paths
            
        Returns:
            Dictionary containing session thoughts and metadata
        """
        try:
            client = get_chroma_client()
            collection = client.get_collection(
                name=THOUGHTS_COLLECTION,
                embedding_function=get_embedding_function()
            )
            
            # Get all thoughts in the session
            where = {"session_id": session_id}
            results = collection.get(
                where=where,
                include=["documents", "metadatas"]
            )
            
            # Organize thoughts by main path and branches
            main_path = []
            branches = {}
            
            for i in range(len(results["ids"])):
                thought = {
                    "content": results["documents"][i],
                    "metadata": results["metadatas"][i]
                }
                
                metadata = results["metadatas"][i]
                if metadata.get("branch_id"):
                    if include_branches:
                        branch_id = metadata["branch_id"]
                        if branch_id not in branches:
                            branches[branch_id] = []
                        branches[branch_id].append(thought)
                else:
                    main_path.append(thought)
            
            # Sort thoughts by number
            main_path.sort(key=lambda x: x["metadata"]["thought_number"])
            for branch in branches.values():
                branch.sort(key=lambda x: x["metadata"]["thought_number"])
            
            return {
                "session_id": session_id,
                "main_path": main_path,
                "branches": branches if include_branches else None,
                "total_thoughts": len(main_path) + sum(len(b) for b in branches.values())
            }
            
        except Exception as e:
            raise handle_chroma_error(e, "get_session_summary")
    
    @mcp.tool()
    async def chroma_find_similar_sessions(
        query: str,
        n_results: int = 3,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD
    ) -> Dict[str, Any]:
        """
        Find thinking sessions with similar content or patterns.
        
        Args:
            query: The concept or pattern to search for
            n_results: Number of similar sessions to return
            threshold: Similarity threshold (0-1)
            
        Returns:
            Dictionary containing similar sessions and their summaries
        """
        try:
            # First, find similar thoughts
            similar_thoughts = await chroma_find_similar_thoughts(
                query=query,
                n_results=n_results * 3,  # Get more thoughts to ensure coverage
                threshold=threshold,
                include_branches=True
            )
            
            # Group thoughts by session and calculate session similarity
            session_similarities = {}
            for thought in similar_thoughts["similar_thoughts"]:
                session_id = thought["metadata"]["session_id"]
                similarity = thought["similarity"]
                
                if session_id not in session_similarities:
                    session_similarities[session_id] = {
                        "max_similarity": similarity,
                        "total_similarity": similarity,
                        "thought_count": 1
                    }
                else:
                    stats = session_similarities[session_id]
                    stats["max_similarity"] = max(stats["max_similarity"], similarity)
                    stats["total_similarity"] += similarity
                    stats["thought_count"] += 1
            
            # Calculate average similarity and sort sessions
            session_scores = []
            for session_id, stats in session_similarities.items():
                avg_similarity = stats["total_similarity"] / stats["thought_count"]
                combined_score = (stats["max_similarity"] + avg_similarity) / 2
                
                if combined_score >= threshold:
                    session_scores.append({
                        "session_id": session_id,
                        "similarity_score": combined_score,
                        "max_similarity": stats["max_similarity"],
                        "avg_similarity": avg_similarity
                    })
            
            # Sort by combined score and limit results
            session_scores.sort(key=lambda x: x["similarity_score"], reverse=True)
            session_scores = session_scores[:n_results]
            
            # Get full summaries for top sessions
            similar_sessions = []
            for score in session_scores:
                summary = await chroma_get_session_summary(
                    session_id=score["session_id"],
                    include_branches=True
                )
                similar_sessions.append({
                    "session_summary": summary,
                    "similarity_metrics": score
                })
            
            return {
                "similar_sessions": similar_sessions,
                "total_found": len(similar_sessions),
                "threshold": threshold
            }
            
        except Exception as e:
            raise handle_chroma_error(e, "find_similar_sessions")

async def record_thought(
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
        client = get_chroma_client()
        thoughts_collection = client.get_collection(THOUGHTS_COLLECTION)
        sessions_collection = client.get_collection(SESSIONS_COLLECTION)

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

        return {
            "success": True,
            "thought_id": thought_id,
            "session_id": session_id,
            "thought_number": thought_number,
            "total_thoughts": total_thoughts,
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
        raise McpError(ErrorData(
            code=INVALID_PARAMS,
            message=f"Invalid parameters: {str(e)}"
        ))
    except Exception as e:
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=f"Failed to record thought: {str(e)}"
        ))
