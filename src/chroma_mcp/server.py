"""
Chroma MCP Server - Main Implementation

This module provides the core server implementation for the Chroma MCP service,
integrating ChromaDB with the Model Context Protocol (MCP).
"""

import os
import argparse
import importlib.metadata
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
import logging
import logging.handlers # Add this for FileHandler
import sys # Import sys for stderr output as last resort

from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS
# REMOVE: from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.server import stdio

# ADD: Import the shared mcp instance from app
from .app import mcp

# Import ThoughtMetadata from .types
# Import ChromaClientConfig now also from .types
from .types import ThoughtMetadata, ChromaClientConfig 
# Import config loading and tool registration
from .utils.config import load_config

# Import errors and specific utils (setters/getters for globals)
from .utils import (
    get_logger, 
    set_main_logger, 
    get_server_config, # Keep getter for potential internal use
    set_server_config, 
    BASE_LOGGER_NAME, 
    validate_input, 
    # raise_validation_error # Keep these if used directly in server?
)

# Add this near the top of the file, after imports but before any other code
CHROMA_AVAILABLE = False
try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    # Use logger if available later, print is too early here
    # We will log this warning properly within config_server
    pass

FASTMCP_AVAILABLE = False
try:
    import fastmcp
    FASTMCP_AVAILABLE = True
except ImportError:
    # Use logger if available later, print is too early here
    # We will log this warning properly within config_server
    pass

def config_server(args: argparse.Namespace) -> None:
    """
    Configures the Chroma MCP server based on parsed command-line arguments.

    This involves:
    - Loading environment variables from a specified .env file (if it exists).
    - Setting up logging (console and optional file handlers) with the specified level.
    - Creating a ChromaClientConfig object based on client type, connection details,
      and other settings provided in `args`.
    - Storing the logger and client configuration globally for access by other modules.
    - Logging configuration details and warnings about missing optional dependencies
      (chromadb, fastmcp).

    Args:
        args: An argparse.Namespace object containing the parsed command-line
              arguments from `cli.py`.

    Raises:
        McpError: Wraps any exception that occurs during configuration, ensuring
                  a consistent error format is propagated upwards. Logs critical
                  errors before raising.
    """
    logger = None # Initialize logger to None before try block
    try:
        # Load environment variables if dotenv file exists
        if args.dotenv_path and os.path.exists(args.dotenv_path):
            load_dotenv(dotenv_path=args.dotenv_path)
        
        # --- Start: Logger Configuration --- 
        log_dir = args.log_dir
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        log_level = getattr(logging, log_level_str, logging.INFO)

        # Get the root logger for our application
        logger = logging.getLogger(BASE_LOGGER_NAME)
        logger.setLevel(log_level)

        # Prevent adding handlers multiple times if config_server is called again (e.g., in tests)
        if not logger.hasHandlers():
            # Create formatter
            formatter = logging.Formatter(
                f'%(asctime)s | %(name)-{len(BASE_LOGGER_NAME)+15}s | %(levelname)-8s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # Create console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
            # Create file handler if log_dir is specified
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
                log_file = os.path.join(log_dir, "chroma_mcp_server.log")
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file,
                    maxBytes=10*1024*1024, # 10 MB
                    backupCount=5
                )
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)

        # Store the configured logger instance globally via setter
        set_main_logger(logger)
        # --- End: Logger Configuration ---
        
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
        
        # Store the config globally via setter
        set_server_config(client_config)

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
            logger.warning("ChromaDB is not installed. Vector database operations will not be available.")
            logger.warning("To enable full functionality, install the optional dependencies:")
            logger.warning("pip install chroma-mcp-server[full]")
        
        if not FASTMCP_AVAILABLE:
            logger.warning("FastMCP is not installed. MCP tools will not be available.")
            logger.warning("To enable full functionality, install the optional dependencies:")
            logger.warning("pip install chroma-mcp-server[full]")
            
    except Exception as e:
        # If logger isn't initialized yet, use print for critical errors
        error_msg = f"Failed to configure server: {str(e)}"
        if logger:
            # Use critical level for configuration failures
            logger.critical(error_msg) 
        else:
            # Last resort if logger setup failed completely
            print(f"CRITICAL CONFIG ERROR: {error_msg}", file=sys.stderr) 
        
        # Wrap the exception in McpError
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=error_msg
        ))

def main() -> None:
    """Main execution function for the Chroma MCP server.

    Assumes that `config_server` has already been called (typically by `cli.py`).
    Retrieves the globally configured logger.
    Logs the server start event, including the package version.
    Initiates the MCP server run loop using the configured stdio transport
    and the shared `mcp` instance from `app.py`.

    Catches and logs `McpError` exceptions specifically.
    Catches any other exceptions, logs them as critical errors, and wraps them
    in an `McpError` before raising to ensure a consistent exit status via the CLI.
    """
    logger = None # Initialize logger variable for this scope
    try:
        # Configuration should have been done by cli.py calling config_server
        logger = get_logger()

        if logger:
            try:
                 version = importlib.metadata.version('chroma-mcp-server')
            except importlib.metadata.PackageNotFoundError:
                 version = "unknown"
            logger.debug(
                "Starting Chroma MCP server (version: %s) with stdio transport using shared MCP instance",
                version
            )

        # Start server with stdio transport using the IMPORTED shared 'mcp' instance
        mcp.run(transport='stdio') # Use imported mcp directly

    except McpError as e:
        if logger:
            logger.error(f"MCP Error: {str(e)}")
        # Re-raise McpError to potentially be caught by CLI
        raise
    except Exception as e:
        error_msg = f"Critical error running MCP server: {str(e)}"
        if logger:
            logger.error(error_msg)
        # Convert unexpected errors to McpError for consistent exit
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=error_msg
        ))

if __name__ == "__main__":
    # In a typical setup, cli.py would call config_server then main.
    # For direct execution (if needed for debugging), configuration might be missing.
    # Consider adding basic argument parsing and config call here if direct execution is intended.
    # For now, assume cli.py is the entry point.
    pass 