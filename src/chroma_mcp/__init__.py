"""ChromaMCP package initialization."""

from .types import (
    ChromaClientConfig,
    ThoughtMetadata
)

from .handlers import (
    CollectionHandler,
    DocumentHandler,
    ThinkingHandler
)

from .utils.errors import (
    McpError,
    ValidationError,
    CollectionNotFoundError,
    DocumentNotFoundError,
    EmbeddingError,
    ClientError,
    ConfigurationError
)

__all__ = [
    'CollectionHandler',
    'DocumentHandler',
    'ThinkingHandler',
    'ChromaClientConfig',
    'ThoughtMetadata',
    'McpError',
    'ValidationError',
    'CollectionNotFoundError',
    'DocumentNotFoundError',
    'EmbeddingError',
    'ClientError',
    'ConfigurationError'
]

__version__ = '0.1.0'
