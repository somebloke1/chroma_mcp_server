"""Chroma MCP Server Package."""

# Import key types for easier access, but be careful about circular dependencies
from .types import (
    # Document, # Removed: Not defined in types.py
    DocumentMetadata,
    # QueryResult, # Removed: Not defined in types.py
    ThoughtMetadata,
)
from .utils import (
    config,
    client,
    errors,
)

# from .handlers import (
#     CollectionHandler,
#     DocumentHandler,
#     ThinkingHandler
# )
from .tools import collection_tools, document_tools, thinking_tools

# Only import get_mcp from server
# from .server import get_mcp
# Removed: main, config_server, create_parser
# from .server import (
#     main,
#     config_server,
#     create_parser,
#     get_mcp
# )

# Import key components for easier access from outside
from .utils import get_logger, get_chroma_client, get_embedding_function
from .utils.errors import McpError, ValidationError  # Assuming McpError is defined here or imported

# REMOVE this line as get_mcp no longer exists in server.py
# from .server import get_mcp

# Optionally import the app instance if needed globally (use with caution)
# from .app import mcp

__version__ = "0.1.0"


# Define __all__ to control what `from chroma_mcp import *` imports
__all__ = [
    # Types
    "DocumentMetadata",
    "ThoughtMetadata",
    # Handlers - Removed
    # "CollectionHandler",
    # "DocumentHandler",
    # "ThinkingHandler",
    # Utils
    "config",
    "client",
    "errors",
    # Tools
    "collection_tools",
    "document_tools",
    "thinking_tools",
    # Server - Only expose get_mcp
    # "main", # Removed
    # "config_server", # Removed
    # "create_parser", # Removed
    "get_mcp",
    # Version
    "__version__",
]

__author__ = "Nold Coaching & Consulting"
__license__ = "MIT"
