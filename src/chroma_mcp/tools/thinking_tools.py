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
        session_id: str = "",
        branch_from_thought: int = 0,
        branch_id: str = "",
        next_thought_needed: bool = False,
        custom_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Record a thought in a sequential thinking process.
        
        Args:
            thought: The current thought content
            thought_number: Position in the thought sequence (1-based)
            total_thoughts: Total expected thoughts in the sequence
            session_id: Optional session identifier (generated if empty string provided)
            branch_from_thought: Optional thought number this branches from (use 0 if none)
            branch_id: Optional branch identifier for parallel thought paths (use empty string if none)
            next_thought_needed: Whether another thought is needed after this
            custom_data: Optional additional metadata
            
        Returns:
            Dictionary containing thought information and context
        """
        try:
            # Handle default custom_data
            if custom_data is None:
                custom_data = {}
                
            # Input validation
            if not thought:
                raise_validation_error("Thought content is required")
            if thought_number < 1 or thought_number > total_thoughts:
                raise_validation_error(f"Invalid thought number: {thought_number}")
            
            # Generate or validate session ID
            effective_session_id = session_id if session_id else str(uuid.uuid4())
            
            # Create metadata - use effective values, handle 0 for branch_from_thought
            timestamp = int(time.time())
            metadata = ThoughtMetadata(
                session_id=effective_session_id,
                thought_number=thought_number,
                total_thoughts=total_thoughts,
                timestamp=timestamp,
                branch_from_thought=branch_from_thought if branch_from_thought > 0 else None,
                branch_id=branch_id if branch_id else None,
                next_thought_needed=next_thought_needed,
                custom_data=custom_data if custom_data else None # Store None if empty
            )
            
            # Get or create thoughts collection
            client = get_chroma_client()
            collection = client.get_or_create_collection(
                name=THOUGHTS_COLLECTION,
                embedding_function=get_embedding_function()
            )
            
            # Generate unique ID for the thought
            thought_id = f"thought_{effective_session_id}_{thought_number}"
            if branch_id:
                thought_id += f"_branch_{branch_id}"
            
            # Add thought to collection
            # Convert metadata dataclass to dict for Chroma
            metadata_dict = metadata.__dict__
            # Filter out None values before sending to Chroma
            metadata_dict = {k: v for k, v in metadata_dict.items() if v is not None}
            # Special handling for custom_data - flatten if present
            if 'custom_data' in metadata_dict and metadata_dict['custom_data']:
                custom = metadata_dict.pop('custom_data')
                for ck, cv in custom.items():
                    # Prefix custom keys to avoid collision
                    metadata_dict[f"custom:{ck}"] = cv 
            
            collection.add(
                documents=[thought],
                metadatas=[metadata_dict], # Use the cleaned dict
                ids=[thought_id]
            )
            
            # Get previous thoughts in the session for context
            previous_thoughts = []
            if thought_number > 1:
                where_clause = {
                    "session_id": effective_session_id,
                    "thought_number": {"$lt": thought_number}
                }
                if branch_id:
                    where_clause["branch_id"] = branch_id
                
                results = collection.get(
                    where=where_clause,
                    include=["documents", "metadatas"]
                )
                
                # Reconstruct metadata from flat structure if needed for previous thoughts
                for i in range(len(results["ids"])):
                    raw_meta = results["metadatas"][i] or {}
                    # Reconstruct custom data if prefixed keys exist
                    reconstructed_custom = {k[len('custom:'):]: v for k, v in raw_meta.items() if k.startswith('custom:')}
                    # Filter out prefixed custom keys from main metadata
                    base_meta = {k: v for k, v in raw_meta.items() if not k.startswith('custom:')}
                    if reconstructed_custom:
                        base_meta['custom_data'] = reconstructed_custom
                        
                    previous_thoughts.append({
                        "content": results["documents"][i],
                        "metadata": base_meta
                    })
            
            logger.info(f"Recorded thought {thought_number}/{total_thoughts} for session {effective_session_id}")
            return {
                "success": True,
                "thought_id": thought_id,
                "session_id": effective_session_id,
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
        session_id: str = "",
        include_branches: bool = True
    ) -> Dict[str, Any]:
        """
        Find similar thoughts across all or specific thinking sessions.
        
        Args:
            query: The thought or concept to search for
            n_results: Number of similar thoughts to return
            threshold: Similarity threshold (0-1)
            session_id: Optional session ID to limit search scope (use empty string for all)
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
            
            # Prepare where clause for filtering only if session_id is provided
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
            if results and results.get("ids") and results["ids"][0]: # Check if results exist
                for i in range(len(results["ids"][0])):
                    distance = results["distances"][0][i]
                    similarity = 1 - distance  # Convert distance to similarity
                    
                    if similarity >= threshold:
                        raw_meta = results["metadatas"][0][i] or {}
                        # Reconstruct custom data if prefixed keys exist
                        reconstructed_custom = {k[len('custom:'):]: v for k, v in raw_meta.items() if k.startswith('custom:')}
                        # Filter out prefixed custom keys from main metadata
                        base_meta = {k: v for k, v in raw_meta.items() if not k.startswith('custom:')}
                        if reconstructed_custom:
                            base_meta['custom_data'] = reconstructed_custom
                            
                        thought = {
                            "content": results["documents"][0][i],
                            "metadata": base_meta, # Use reconstructed metadata
                            "similarity": similarity
                        }
                        similar_thoughts.append(thought)
            
            return {
                "similar_thoughts": similar_thoughts,
                "total_found": len(similar_thoughts),
                "threshold": threshold
            }
            
        except Exception as e:
            # Handle collection not found specifically
            if "does not exist" in str(e):
                 logger.warning(f"Collection '{THOUGHTS_COLLECTION}' not found during similar thought search.")
                 return {"similar_thoughts": [], "total_found": 0, "threshold": threshold, "message": f"Collection '{THOUGHTS_COLLECTION}' not found."}
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
            
            if results and results.get("ids"): # Check if results exist
                for i in range(len(results["ids"])):
                    raw_meta = results["metadatas"][i] or {}
                    # Reconstruct custom data if prefixed keys exist
                    reconstructed_custom = {k[len('custom:'):]: v for k, v in raw_meta.items() if k.startswith('custom:')}
                    # Filter out prefixed custom keys from main metadata
                    base_meta = {k: v for k, v in raw_meta.items() if not k.startswith('custom:')}
                    if reconstructed_custom:
                        base_meta['custom_data'] = reconstructed_custom
                        
                    thought = {
                        "content": results["documents"][i],
                        "metadata": base_meta # Use reconstructed metadata
                    }
                    
                    # Check if thought belongs to a branch
                    branch_id = base_meta.get("branch_id")
                    if branch_id and include_branches:
                        if branch_id not in branches:
                            branches[branch_id] = []
                        branches[branch_id].append(thought)
                    elif not branch_id: # Add to main path if not branched
                        main_path.append(thought)
            
            # Sort main path and branches by thought number
            main_path.sort(key=lambda x: x["metadata"].get("thought_number", 0))
            for branch_id in branches:
                branches[branch_id].sort(key=lambda x: x["metadata"].get("thought_number", 0))
            
            return {
                "session_id": session_id,
                "main_path_thoughts": main_path,
                "branched_thoughts": branches if include_branches else {},
                "total_thoughts": len(main_path) + sum(len(b) for b in branches.values())
            }
            
        except Exception as e:
            # Handle collection not found specifically
            if "does not exist" in str(e):
                 logger.warning(f"Collection '{THOUGHTS_COLLECTION}' not found during session summary.")
                 return {"session_id": session_id, "main_path_thoughts": [], "branched_thoughts": {}, "total_thoughts": 0, "message": f"Collection '{THOUGHTS_COLLECTION}' not found."}
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
            client = get_chroma_client()
            
            # 1. Get or create the session summary collection
            try:
                 session_summary_collection = client.get_collection(
                     name=SESSIONS_COLLECTION,
                     embedding_function=get_embedding_function()
                 )
            except Exception as e:
                 # Collection might not exist yet, which is okay for querying
                 logger.warning(f"Session summary collection '{SESSIONS_COLLECTION}' not found. Returning empty results.")
                 return {"similar_sessions": [], "total_found": 0, "threshold": threshold}

            # 2. Query the session summary collection
            results = session_summary_collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["metadatas", "distances"] # Only need metadata (session_id) and distance
            )
            
            # 3. Filter by threshold and format
            similar_sessions = []
            if results and results.get("ids") and results["ids"][0]: # Check if results exist
                for i in range(len(results["ids"][0])):
                    distance = results["distances"][0][i]
                    similarity = 1 - distance
                    
                    if similarity >= threshold:
                        session_id = results["ids"][0][i] # Session ID is the document ID
                        session_metadata = results["metadatas"][0][i] or {}
                        
                        session_info = {
                            "session_id": session_id,
                            "similarity": similarity,
                            # Add any other relevant metadata stored during summary creation
                            "first_thought_timestamp": session_metadata.get("first_thought_timestamp"),
                            "last_thought_timestamp": session_metadata.get("last_thought_timestamp"),
                            "total_thoughts": session_metadata.get("total_thoughts"),
                        }
                        similar_sessions.append(session_info)
            
            return {
                "similar_sessions": similar_sessions,
                "total_found": len(similar_sessions),
                "threshold": threshold
            }
            
        except Exception as e:
            # We already handled collection not found above
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
