"""Utility modules for ChromaDB operations."""

import logging
import sys
from typing import Optional

from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR

# Import necessary types
from ..types import ChromaClientConfig  # Import from parent types

# --- Global State (Moved from server.py) --- #
_main_logger_instance: Optional[logging.Logger] = None
_global_client_config: Optional[ChromaClientConfig] = None
BASE_LOGGER_NAME = "chromamcp"


# --- Accessors and Setters (Moved from server.py) --- #
def set_main_logger(logger: logging.Logger):
    """Set the globally accessible main logger instance."""
    global _main_logger_instance
    _main_logger_instance = logger


def set_server_config(config: ChromaClientConfig):
    """Set the globally accessible server configuration."""
    global _global_client_config
    _global_client_config = config


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance. If a name is provided, it gets a child logger
    under the base 'chromamcp' logger. Otherwise, returns the main logger.
    """
    if _main_logger_instance is None:
        fallback_logger = logging.getLogger(f"{BASE_LOGGER_NAME}.unconfigured")
        # Check if the specific fallback handler already exists
        has_fallback_handler = False
        for h in fallback_logger.handlers:
            if isinstance(h, logging.StreamHandler) and h.stream == sys.stderr:
                has_fallback_handler = True
                break

        if not has_fallback_handler:
            handler = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
            handler.setFormatter(formatter)
            fallback_logger.addHandler(handler)
            # Set level only when adding the handler for the first time
            fallback_logger.setLevel(logging.WARNING)

        fallback_logger.warning("Logger requested before main configuration.")
        return fallback_logger
    if name:
        return logging.getLogger(f"{BASE_LOGGER_NAME}.{name}")
    else:
        return _main_logger_instance


def get_server_config() -> ChromaClientConfig:
    """Return the globally stored server configuration."""
    if _global_client_config is None:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message="Server configuration not initialized"))
    return _global_client_config


# --- JSON Encoder for NumPy types ---
import json
import numpy as np


class NumpyEncoder(json.JSONEncoder):
    """Custom encoder for numpy data types"""

    def default(self, obj):
        if isinstance(
            obj,
            (
                np.int_,
                np.intc,
                np.intp,
                np.int8,
                np.int16,
                np.int32,
                np.int64,
                np.uint8,
                np.uint16,
                np.uint32,
                np.uint64,
            ),
        ):
            return int(obj)
        elif isinstance(obj, (np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)


# --- Original Utils Exports --- #
from .chroma_client import get_chroma_client, get_embedding_function
from .errors import ValidationError, EmbeddingError, ClientError, ConfigurationError

__all__ = [
    # Global Accessors
    "get_logger",
    "get_server_config",
    # Client functions
    "get_chroma_client",
    "get_embedding_function",
    # Validation/Error functions and types
    "ValidationError",
    "EmbeddingError",
    "ClientError",
    "ConfigurationError",
    # Helpers
    "NumpyEncoder",
]
