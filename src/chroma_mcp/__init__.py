"""ChromaMCP package initialization."""

from .types import (
    ChromaClientConfig,
    ThoughtMetadata
)
from .utils import (
    config,
    client,
    errors,
    logger_setup
)
# from .handlers import (
#     CollectionHandler,
#     DocumentHandler,
#     ThinkingHandler
# )
from .tools import (
    collection_tools,
    document_tools,
    thinking_tools
)
from .server import (
    main,
    config_server,
    create_parser,
    get_mcp
)

__all__ = [
    # Types
    "ChromaClientConfig",
    "ThoughtMetadata",
    # Handlers - Removed
    # "CollectionHandler",
    # "DocumentHandler",
    # "ThinkingHandler",
    # Utils
    "config",
    "client",
    "errors",
    "logger_setup",
    # Tools
    "collection_tools",
    "document_tools",
    "thinking_tools",
    # Server
    "main",
    "config_server",
    "create_parser",
    "get_mcp"
]

__version__ = '0.1.0'
__author__ = "Nold Coaching & Consulting"
__license__ = "MIT"