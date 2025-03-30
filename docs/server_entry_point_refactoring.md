# Server Entry Point Refactoring Guide

This document outlines how to refactor the server.py file to include a proper main() function that works with both direct command-line invocation and MCP protocol integration through Hatch and Smithery.

## Current State Analysis

Currently, our server implementation might not have a clearly defined entry point function that's compatible with the way Hatch and Smithery expect to invoke Python packages. This guide addresses how to refactor the server.py file to provide a clean and consistent interface.

## Requirements for the Refactored Entry Point

1. Must work when invoked directly as a module (`python -m chroma_mcp.server`)
2. Must work when invoked via console script entry point (`chroma-mcp-server`)
3. Must work when invoked through Smithery's MCP protocol layer
4. Must handle command-line arguments properly
5. Must configure logging appropriately
6. Must initialize all necessary components

## Refactoring Steps

### 1. Create a Proper `main()` Function

```python
def main():
    """
    Main entry point for the Chroma MCP Server.
    
    This function handles argument parsing, server configuration,
    and startup. It can be invoked through various methods:
    - Direct module execution: python -m chroma_mcp.server
    - Console script: chroma-mcp-server
    - MCP protocol integration (e.g., Smithery)
    
    Returns:
        int: Exit code (0 for success, non-zero for errors)
    """
    # Parse command-line arguments
    args = parse_arguments()
    
    # Configure logging
    configure_logging(args.log_dir, args.log_level)
    
    # Initialize server components
    try:
        server = initialize_server(
            client_type=args.client_type,
            data_dir=args.data_dir,
            host=args.host,
            port=args.port,
            ssl=args.ssl,
            tenant=args.tenant,
            database=args.database,
            api_key=args.api_key,
        )
        
        # Start the server (this should be a blocking call)
        server.start()
        
        # If we get here, the server was stopped gracefully
        return 0
    except Exception as e:
        logger.error(f"Server initialization failed: {str(e)}")
        return 1
```

### 2. Add Argument Parsing Function

```python
def parse_arguments():
    """
    Parse command-line arguments for the server.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Chroma MCP Server")
    
    # Basic server configuration
    parser.add_argument(
        "--client-type",
        choices=["ephemeral", "persistent", "http", "cloud"],
        default="ephemeral",
        help="Type of Chroma client to use",
    )
    
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Path to data directory for persistent client",
    )
    
    parser.add_argument(
        "--log-dir",
        default=None,
        help="Path to directory for log files",
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Log level",
    )
    
    # HTTP client configuration
    parser.add_argument(
        "--host",
        default=None,
        help="Host address for HTTP client",
    )
    
    parser.add_argument(
        "--port",
        default=None,
        help="Port for HTTP client",
    )
    
    parser.add_argument(
        "--ssl",
        type=lambda x: x.lower() == "true",
        default=False,
        help="Whether to use SSL for HTTP client (true/false)",
    )
    
    # Cloud client configuration
    parser.add_argument(
        "--tenant",
        default=None,
        help="Tenant ID for Cloud client",
    )
    
    parser.add_argument(
        "--database",
        default=None,
        help="Database name for Cloud client",
    )
    
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key for Cloud client",
    )
    
    # Parse environment variables as fallbacks
    args = parser.parse_args()
    
    # Apply environment variable fallbacks
    import os
    
    if args.client_type is None:
        args.client_type = os.environ.get("CHROMA_CLIENT_TYPE", "ephemeral")
    
    if args.data_dir is None:
        args.data_dir = os.environ.get("CHROMA_DATA_DIR")
    
    if args.log_dir is None:
        args.log_dir = os.environ.get("CHROMA_LOG_DIR")
    
    if args.host is None:
        args.host = os.environ.get("CHROMA_HOST")
    
    if args.port is None:
        args.port = os.environ.get("CHROMA_PORT")
    
    if not args.ssl:
        args.ssl = os.environ.get("CHROMA_SSL", "").lower() == "true"
    
    if args.tenant is None:
        args.tenant = os.environ.get("CHROMA_TENANT")
    
    if args.database is None:
        args.database = os.environ.get("CHROMA_DATABASE")
    
    if args.api_key is None:
        args.api_key = os.environ.get("CHROMA_API_KEY")
    
    return args
```

### 3. Add Logging Configuration Function

```python
def configure_logging(log_dir=None, log_level="INFO"):
    """
    Configure logging for the server.
    
    Args:
        log_dir (str, optional): Directory to write log files to.
        log_level (str, optional): Log level. Defaults to "INFO".
    """
    import logging
    import os
    import sys
    from logging.handlers import RotatingFileHandler
    
    # Create logger
    logger = logging.getLogger("chroma_mcp")
    
    # Convert string log level to actual log level
    level = getattr(logging, log_level)
    logger.setLevel(level)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    simple_formatter = logging.Formatter("%(levelname)s - %(message)s")
    
    # Always add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # Add file handler if log_dir is specified
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "chroma_mcp.log"),
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    
    # Suppress overly verbose logs from libraries
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    
    return logger
```

### 4. Add Server Initialization Function

```python
def initialize_server(
    client_type="ephemeral",
    data_dir=None,
    host=None,
    port=None,
    ssl=False,
    tenant=None,
    database=None,
    api_key=None,
):
    """
    Initialize the Chroma MCP Server with the specified configuration.
    
    Args:
        client_type (str, optional): Type of Chroma client. Defaults to "ephemeral".
        data_dir (str, optional): Path to data directory for persistent client.
        host (str, optional): Host address for HTTP client.
        port (str, optional): Port for HTTP client.
        ssl (bool, optional): Whether to use SSL for HTTP client. Defaults to False.
        tenant (str, optional): Tenant ID for Cloud client.
        database (str, optional): Database name for Cloud client.
        api_key (str, optional): API key for Cloud client.
    
    Returns:
        object: Initialized server instance
    """
    from chroma_mcp.server_core import ChromaMCPServer
    
    # Create server instance with the specified configuration
    server = ChromaMCPServer(
        client_type=client_type,
        data_dir=data_dir,
        host=host,
        port=port,
        ssl=ssl,
        tenant=tenant,
        database=database,
        api_key=api_key,
    )
    
    return server
```

### 5. Add Module Execution Block

```python
if __name__ == "__main__":
    import sys
    sys.exit(main())
```

## Integration Considerations

### Error Handling

Make sure the main function properly handles all exceptions and returns appropriate exit codes.

### Logging

Ensure logging is configured before any other code executes, and that log messages are sent to both console and file (if specified).

### Graceful Shutdown

Implement signal handlers to gracefully shutdown the server when it receives SIGINT, SIGTERM, etc.

```python
def setup_signal_handlers(server):
    """
    Set up signal handlers for graceful shutdown.
    
    Args:
        server: The server instance to shut down
    """
    import signal
    import sys
    
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        server.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
```

### Testing

Test the refactored server with all the invocation methods:

1. Direct module execution:

   ```bash
   python -m chroma_mcp.server
   ```

2. Console script after installation:

   ```bash
   pip install .
   chroma-mcp-server
   ```

3. Through Hatch:

   ```bash
   hatch run python -m chroma_mcp.server
   ```

4. Through Smithery:

   ```bash
   npx -y @smithery/cli run chroma-mcp-server
   ```

## Complete Example

Here's what the refactored `server.py` file should look like with all the components properly integrated:

```python
"""
Chroma MCP Server

This module provides a Model Context Protocol (MCP) server implementation
that interfaces with the Chroma vector database.
"""

import argparse
import logging
import os
import signal
import sys
from logging.handlers import RotatingFileHandler

# Initialize logger at module level
logger = logging.getLogger("chroma_mcp")

def parse_arguments():
    """Parse command-line arguments for the server."""
    # ... (implementation from above)

def configure_logging(log_dir=None, log_level="INFO"):
    """Configure logging for the server."""
    # ... (implementation from above)

def initialize_server(
    client_type="ephemeral",
    data_dir=None,
    host=None,
    port=None,
    ssl=False,
    tenant=None,
    database=None,
    api_key=None,
):
    """Initialize the Chroma MCP Server with the specified configuration."""
    # ... (implementation from above)

def setup_signal_handlers(server):
    """Set up signal handlers for graceful shutdown."""
    # ... (implementation from above)

def main():
    """Main entry point for the Chroma MCP Server."""
    # Parse command-line arguments
    args = parse_arguments()
    
    # Configure logging
    global logger
    logger = configure_logging(args.log_dir, args.log_level)
    
    # Initialize server components
    try:
        logger.info("Initializing Chroma MCP Server...")
        server = initialize_server(
            client_type=args.client_type,
            data_dir=args.data_dir,
            host=args.host,
            port=args.port,
            ssl=args.ssl,
            tenant=args.tenant,
            database=args.database,
            api_key=args.api_key,
        )
        
        # Set up signal handlers
        setup_signal_handlers(server)
        
        # Log server configuration
        logger.info(f"Server configuration: client_type={args.client_type}")
        if args.data_dir:
            logger.info(f"Data directory: {args.data_dir}")
        if args.log_dir:
            logger.info(f"Log directory: {args.log_dir}")
        
        # Start the server
        logger.info("Starting server...")
        server.start()
        
        # If we get here, the server was stopped gracefully
        logger.info("Server stopped gracefully")
        return 0
    except Exception as e:
        logger.error(f"Server initialization failed: {str(e)}", exc_info=True)
        return 1

# Allow direct execution of this module
if __name__ == "__main__":
    sys.exit(main())
```

## Summary

By refactoring your server.py file according to this guide, you'll have a robust entry point that:

1. Works with multiple invocation methods
2. Properly handles command-line arguments
3. Integrates well with Hatch and Smithery
4. Handles logging and error cases gracefully
5. Provides clean separation of concerns

This approach provides a solid foundation for your Chroma MCP Server and makes it easier to distribute and use with various MCP clients.
