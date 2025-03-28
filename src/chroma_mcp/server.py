"""
Chroma MCP Server - Main Implementation

This module provides the core server implementation for the Chroma MCP service,
integrating ChromaDB with the Model Context Protocol (MCP).
"""

import os
import argparse
import ssl

from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from contextlib import asynccontextmanager

from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS
from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError

from .types import ChromaClientConfig, ThoughtMetadata
from .handlers import CollectionHandler, DocumentHandler, ThinkingHandler
from .utils.logger_setup import LoggerSetup
from .utils.client import get_chroma_client, get_embedding_function
from .utils.config import load_config
from .tools.collection_tools import register_collection_tools
from .tools.document_tools import register_document_tools
from .tools.thinking_tools import register_thinking_tools
from .utils.errors import handle_chroma_error, validate_input, raise_validation_error, ValidationError, CollectionNotFoundError

# Initialize logger
logger = LoggerSetup.create_logger(
    "ChromaMCP",
    log_file="chroma_mcp_server.log",
    log_level=os.getenv("LOG_LEVEL", "INFO")
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for the FastAPI app."""
    # Startup
    get_mcp()
    logger.info("MCP instance initialized on server startup")
    yield
    # Shutdown (if needed in the future)
    logger.info("Server shutting down")

# Replace app declaration with lifespan parameter
app = FastAPI(
    title="ChromaMCP Server",
    description="FastAPI server for ChromaMCP operations",
    version="0.1.0",
    lifespan=lifespan
)

# Initialize handlers lazily
_collection_handler = None
_document_handler = None
_thinking_handler = None
_mcp = None

def get_mcp() -> FastMCP:
    """Get or create the FastMCP instance."""
    global _mcp
    if _mcp is None:
        _mcp = FastMCP("chroma")
        # Register tools after MCP instance is created
        register_collection_tools(_mcp)
        register_document_tools(_mcp)
        register_thinking_tools(_mcp)
        logger.info("Successfully registered MCP tools")
    return _mcp

def get_collection_handler():
    """Get or create the collection handler."""
    global _collection_handler
    if _collection_handler is None:
        _collection_handler = CollectionHandler()
    return _collection_handler

def get_document_handler():
    """Get or create the document handler."""
    global _document_handler
    if _document_handler is None:
        _document_handler = DocumentHandler()
    return _document_handler

def get_thinking_handler():
    """Get or create the thinking handler."""
    global _thinking_handler
    if _thinking_handler is None:
        _thinking_handler = ThinkingHandler()
    return _thinking_handler

def create_parser() -> argparse.ArgumentParser:
    """Create and return the argument parser for server configuration."""
    parser = argparse.ArgumentParser(description='Chroma MCP Server')
    
    # Client configuration
    parser.add_argument('--client-type',
                       choices=['http', 'cloud', 'persistent', 'ephemeral'],
                       default=os.getenv('CHROMA_CLIENT_TYPE', 'ephemeral'),
                       help='Type of Chroma client to use')
    
    parser.add_argument('--data-dir',
                       default=os.getenv('CHROMA_DATA_DIR'),
                       help='Directory for persistent client data')
    
    # HTTP client options
    parser.add_argument('--host',
                       default=os.getenv('CHROMA_HOST'),
                       help='Chroma host for HTTP client')
    
    parser.add_argument('--port',
                       default=os.getenv('CHROMA_PORT'),
                       help='Chroma port for HTTP client')
    
    parser.add_argument('--ssl',
                       type=lambda x: x.lower() in ['true', 'yes', '1', 't', 'y'],
                       default=os.getenv('CHROMA_SSL', 'true').lower() in ['true', 'yes', '1', 't', 'y'],
                       help='Use SSL for HTTP client')
    
    # Cloud client options
    parser.add_argument('--tenant',
                       default=os.getenv('CHROMA_TENANT'),
                       help='Chroma tenant for cloud client')
    
    parser.add_argument('--database',
                       default=os.getenv('CHROMA_DATABASE'),
                       help='Chroma database for cloud client')
    
    parser.add_argument('--api-key',
                       default=os.getenv('CHROMA_API_KEY'),
                       help='Chroma API key for cloud client')
    
    # General options
    parser.add_argument('--dotenv-path',
                       default=os.getenv('CHROMA_DOTENV_PATH', '.chroma_env'),
                       help='Path to .env file')
    
    # Embedding function options
    parser.add_argument('--cpu-execution-provider',
                       choices=['auto', 'true', 'false'],
                       default=os.getenv('CHROMA_CPU_EXECUTION_PROVIDER', 'auto'),
                       help='Force CPU execution provider for embedding functions. "auto" will detect based on system (default), "true" forces CPU, "false" uses default providers')
    
    return parser

def config_server(args: argparse.Namespace) -> None:
    """
    Configure the server with the provided configuration without using async.
    
    Args:
        args: Parsed command line arguments
    """
    try:
        # Load environment variables
        load_dotenv(dotenv_path=args.dotenv_path)
        
        # Handle CPU provider setting
        use_cpu_provider = None  # Auto-detect
        if args.cpu_execution_provider != 'auto':
            use_cpu_provider = args.cpu_execution_provider == 'true'
        
        # Create client configuration
        client_config = ChromaClientConfig(
            client_type=args.client_type,
            data_dir=args.data_dir,
            host=args.host,
            port=args.port,
            ssl=args.ssl,
            tenant=args.tenant,
            database=args.database,
            api_key=args.api_key,
            use_cpu_provider=use_cpu_provider
        )
        
        # This will initialize our configurations for later use
        provider_status = 'auto-detected' if use_cpu_provider is None else ('enabled' if use_cpu_provider else 'disabled')
        logger.info(f"Server configured (CPU provider: {provider_status})")
        
    except Exception as e:
        error_msg = f"Failed to configure server: {str(e)}"
        logger.error(error_msg)
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=error_msg
        )) from e

@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint."""
    return {"message": "ChromaMCP Server is running"}

@app.post("/collections")
async def create_collection(
    name: str,
    metadata: Optional[Dict[str, Any]] = None,
    config: Optional[ChromaClientConfig] = None
) -> Dict[str, Any]:
    """Create a new collection."""
    try:
        result = await get_collection_handler().create_collection(name, metadata=metadata)
        return result
    except McpError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"Failed to create collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/collections")
async def list_collections() -> Dict[str, Any]:
    """List all collections."""
    try:
        result = await get_collection_handler().list_collections()
        return result
    except McpError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to list collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/collections/{name}")
async def get_collection(name: str) -> Dict[str, Any]:
    """Get a specific collection."""
    try:
        result = await get_collection_handler().get_collection(name)
        return result
    except CollectionNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except McpError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/collections/{name}")
async def delete_collection(
    name: str,
    config: Optional[ChromaClientConfig] = None
) -> Dict[str, Any]:
    """Delete a collection by name."""
    try:
        return await get_collection_handler().delete_collection(name, config)
    except McpError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/collections/{name}/documents")
async def add_documents(
    name: str,
    documents: List[str],
    metadatas: Optional[List[Dict[str, Any]]] = None,
    ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Add documents to a collection."""
    try:
        result = await get_document_handler().add_documents(
            name,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        return result
    except CollectionNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except McpError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/collections/{name}/documents")
async def get_documents(
    name: str,
    ids: Optional[List[str]] = None,
    where: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    include: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Get documents from a collection."""
    try:
        result = await get_document_handler().get_documents(
            name,
            ids=ids,
            where=where,
            limit=limit,
            offset=offset,
            include=include
        )
        return result
    except CollectionNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except McpError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/collections/{name}/documents")
async def update_documents(
    name: str,
    documents: List[str],
    ids: List[str],
    metadatas: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Update documents in a collection."""
    try:
        result = await get_document_handler().update_documents(
            name,
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )
        return result
    except CollectionNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except McpError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/collections/{name}/documents")
async def delete_documents(
    name: str,
    ids: List[str],
    where: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Delete documents from a collection."""
    try:
        result = await get_document_handler().delete_documents(
            name,
            ids=ids,
            where=where
        )
        return result
    except CollectionNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except McpError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/collections/{name}/query")
async def query_collection(
    name: str,
    query_texts: List[str],
    n_results: int = 10,
    where: Optional[Dict[str, Any]] = None,
    where_document: Optional[Dict[str, Any]] = None,
    include: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Query documents in a collection."""
    try:
        result = await get_document_handler().query_collection(
            name,
            query_texts=query_texts,
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=include
        )
        return result
    except CollectionNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except McpError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to query collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ThoughtRequest(BaseModel):
    """Request model for recording a thought."""
    thought: str
    thought_number: int
    session_id: str
    branch_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@app.post("/thoughts")
async def record_thought(request: ThoughtRequest) -> Dict[str, Any]:
    """Record a thought."""
    try:
        result = await get_thinking_handler().add_thought(
            thought=request.thought,
            thought_number=request.thought_number,
            session_id=request.session_id,
            branch_id=request.branch_id,
            metadata=request.metadata
        )
        return result
    except McpError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to record thought: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/thoughts/sessions/{session_id}")
async def get_session_summary(session_id: str) -> Dict[str, Any]:
    """Get a summary of thoughts for a session."""
    try:
        result = await get_thinking_handler().get_thoughts(session_id=session_id)
        return result
    except McpError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get session summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def main() -> None:
    """Entry point for the Chroma MCP server."""
    try:
        # Parse arguments
        parser = create_parser()
        args = parser.parse_args()
        
        # Initialize server (but don't await the coroutine since we don't need the result)
        # Just call it synchronously to configure the environment
        config_server(args)
        
        # Start server
        logger.info("Starting Chroma MCP server")
        get_mcp().run(transport='stdio')
        
    except Exception as e:
        logger.critical(f"Critical error running MCP server: {e}")
        import traceback
        logger.critical(f"Traceback: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    main() 