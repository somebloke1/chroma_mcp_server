"""
Chroma MCP Server - Main Implementation

This module provides the core server implementation for the Chroma MCP service,
integrating ChromaDB with the Model Context Protocol (MCP).
"""

import os
import argparse
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

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
from .utils.errors import handle_chroma_error, validate_input, raise_validation_error

# Add this near the top of the file, after imports but before any other code
CHROMA_AVAILABLE = False
try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    print("ChromaDB not available. Some features will be limited.")

FASTMCP_AVAILABLE = False
try:
    import fastmcp
    FASTMCP_AVAILABLE = True
except ImportError:
    print("FastMCP not available. Some features will be limited.")

# Initialize logger - will be properly configured in config_server
logger = None

# Initialize handlers lazily
_collection_handler = None
_document_handler = None
_thinking_handler = None
_mcp = None

def get_mcp() -> FastMCP:
    """Get or create the FastMCP instance."""
    global _mcp
    if _mcp is None:
        try:
            _mcp = FastMCP("chroma")
            # Register tools after MCP instance is created
            register_collection_tools(_mcp)
            register_document_tools(_mcp)
            register_thinking_tools(_mcp)
            if logger:
                logger.debug("Successfully registered MCP tools")
        except Exception as e:
            if logger:
                logger.error(f"Failed to initialize MCP: {str(e)}")
            _mcp = None  # Reset the instance on failure
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to initialize MCP: {str(e)}"
            ))
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
    
    parser.add_argument('--log-dir',
                       default=os.getenv('CHROMA_LOG_DIR'),
                       help='Directory for log files (default: current directory)')
    
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
                       default=os.getenv('CHROMA_DOTENV_PATH', '.env'),
                       help='Path to .env file (optional)')
    
    # Embedding function options
    parser.add_argument('--cpu-execution-provider',
                       choices=['auto', 'true', 'false'],
                       default=os.getenv('CHROMA_CPU_EXECUTION_PROVIDER', 'auto'),
                       help='Force CPU execution provider for embedding functions. "auto" will detect based on system (default), "true" forces CPU, "false" uses default providers')
    
    return parser

def config_server(args: argparse.Namespace) -> None:
    """
    Configure the server with the provided configuration.
    
    Args:
        args: Parsed command line arguments
        
    Raises:
        McpError: If configuration fails
    """
    global logger
    
    try:
        # Load environment variables if dotenv file exists
        if args.dotenv_path and os.path.exists(args.dotenv_path):
            load_dotenv(dotenv_path=args.dotenv_path)
        
        # Initialize logger with custom log directory if provided
        log_dir = args.log_dir
        
        # Setup the logger
        logger = LoggerSetup.create_logger(
            "ChromaMCP",
            log_file="chroma_mcp_server.log",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_dir=log_dir
        )
        
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
        
        # Log the configuration details
        if log_dir:
            logger.info(f"Logs will be saved to: {log_dir}")
        if args.data_dir:
            logger.info(f"Data directory: {args.data_dir}")
        
        # Check for required dependencies
        if not CHROMA_AVAILABLE:
            print("WARNING: ChromaDB is not installed. Vector database operations will not be available.")
            print("To enable full functionality, install the optional dependencies:")
            print("pip install chroma-mcp-server[full]")
        
        if not FASTMCP_AVAILABLE:
            print("WARNING: FastMCP is not installed. MCP tools will not be available.")
            print("To enable full functionality, install the optional dependencies:")
            print("pip install chroma-mcp-server[full]")
            
    except Exception as e:
        # If logger isn't initialized yet, use print for critical errors
        error_msg = f"Failed to configure server: {str(e)}"
        if logger:
            logger.error(error_msg)
        else:
            print(f"ERROR: {error_msg}")
        
        # Wrap the exception in McpError
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=error_msg
        ))

def main() -> None:
    """Entry point for the Chroma MCP server."""
    try:
        # Parse arguments
        parser = create_parser()
        args = parser.parse_args()
        
        # Initialize server
        config_server(args)
        
        if logger:
            logger.debug("Starting Chroma MCP server with stdio transport")
        
        # Start server with stdio transport
        get_mcp().run(transport='stdio')
        
    except McpError as e:
        if logger:
            logger.error(f"MCP Error: {str(e)}")
        raise
    except Exception as e:
        error_msg = f"Critical error running MCP server: {str(e)}"
        if logger:
            logger.error(error_msg)
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=error_msg
        ))

if __name__ == "__main__":
    main() 