"""
ChromaDB client utility module for managing client instances and configuration.
"""

import os
import platform
from typing import Optional, Union, Any
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings

# Import specific embedding function for compatibility with Intel Macs
try:
    from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
except ImportError:
    ONNXMiniLM_L6_V2 = None  # type: ignore

from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS

# Local application imports
# Import ChromaClientConfig from types
from ..types import ChromaClientConfig

# Import errors from siblings
from .errors import EmbeddingError, ConfigurationError

# Import loggers/config getters directly from parent utils package (__init__.py)
from . import get_logger, get_server_config

# --- Constants ---
SUPPORTED_EF_PROVIDERS = {"openai", "huggingface", "onnx"}

# --- Embedding Function Helper ---

# REMOVE logger assignment from module level
# logger = get_logger("utils.client")


def should_use_cpu_provider() -> bool:
    """
    Detect if we should use CPU provider based on system information.

    Returns:
        bool: True if we should use CPU provider (newer macOS on Intel)
    """
    try:
        # ADD logger assignment inside the function
        logger = get_logger("utils.client")

        # Check if we're on macOS
        if platform.system() != "Darwin":
            return False

        # Get macOS version (e.g., 13.0.0 for Ventura)
        mac_version = tuple(map(int, platform.mac_ver()[0].split(".")))

        # Check if we're on Intel
        is_intel = platform.processor() == "i386" or "Intel" in platform.processor()

        # If we're on macOS 12 (Monterey) or later and running on Intel,
        # we should use CPU provider as these versions are primarily for Apple Silicon
        needs_cpu_provider = mac_version >= (12, 0, 0) and is_intel

        if needs_cpu_provider:
            logger.info(f"Detected macOS {platform.mac_ver()[0]} on Intel CPU - will use CPU provider")

        return needs_cpu_provider

    except Exception as e:
        logger.warning(f"Error detecting system info, defaulting to standard provider: {e}")
        return False


# Module-level cache for the client and embedding function
_chroma_client: Optional[Union[chromadb.PersistentClient, chromadb.HttpClient, chromadb.EphemeralClient]] = None
_embedding_function: Optional[Any] = None


def initialize_embedding_function(use_cpu_provider: Optional[bool] = None) -> None:
    """
    Initialize the embedding function with optional CPU provider enforcement.

    Args:
        use_cpu_provider: If True, forces CPU provider. If None, auto-detects based on system.

    Raises:
        McpError: If embedding function initialization fails
    """
    global _embedding_function

    # ADD logger assignment inside the function
    logger = get_logger("utils.client")

    try:
        # If use_cpu_provider is None, auto-detect
        should_use_cpu = use_cpu_provider if use_cpu_provider is not None else should_use_cpu_provider()

        if should_use_cpu:
            if ONNXMiniLM_L6_V2 is None:
                raise EmbeddingError(
                    "ONNXMiniLM_L6_V2 embedding function not available. Please install chroma-mcp-server[full]"
                )
            _embedding_function = ONNXMiniLM_L6_V2(preferred_providers=["CPUExecutionProvider"])
            logger.info("Initialized embedding function with CPU provider")
        else:
            _embedding_function = ONNXMiniLM_L6_V2()
            logger.info("Initialized embedding function with default providers")
    except Exception as e:
        error_msg = f"Failed to initialize embedding function: {str(e)}"
        logger.error(error_msg)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=error_msg))


def get_chroma_client(
    config: Optional[ChromaClientConfig] = None,
) -> Union[chromadb.PersistentClient, chromadb.HttpClient, chromadb.EphemeralClient]:
    """Get a ChromaDB client based on configuration."""
    global _chroma_client

    # ADD logger assignment inside the function
    logger = get_logger("utils.client")

    # If client already exists, return it
    if _chroma_client is not None:
        return _chroma_client

    # If client doesn't exist, initialize it (should only happen once)
    if config is None:
        # Import getter locally within the function
        config = get_server_config()  # Get the config set during server startup

    # Ensure config is actually set (should be by server startup)
    if config is None:
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message="Chroma client configuration not found during initialization.")
        )

    # Initialize embedding function if not already initialized (part of first client init)
    if _embedding_function is None:
        initialize_embedding_function(use_cpu_provider=config.use_cpu_provider)

    # Create ChromaDB settings with telemetry disabled
    chroma_settings = Settings(
        anonymized_telemetry=False
        # Potentially add other settings here if needed, e.g., from config
    )

    # Validate configuration
    if config.client_type == "persistent" and not config.data_dir:
        raise ValueError("data_dir is required for persistent client")
    elif config.client_type == "http" and not config.host:
        raise ValueError("host is required for http client")

    try:
        if config.client_type == "persistent":
            _chroma_client = chromadb.PersistentClient(path=config.data_dir, settings=chroma_settings)
        elif config.client_type == "http":
            _chroma_client = chromadb.HttpClient(
                host=config.host,
                port=config.port,
                ssl=config.ssl,
                tenant=config.tenant,
                database=config.database,
                settings=chroma_settings
                # Note: API key might be handled separately or via headers
            )
        else:  # ephemeral
            _chroma_client = chromadb.EphemeralClient(settings=chroma_settings)

        # Set the embedding function for the client
        _chroma_client._embedding_function = _embedding_function
        return _chroma_client

    except Exception as e:
        error_msg = f"Failed to initialize ChromaDB client: {str(e)}"
        logger.error(error_msg)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=error_msg))


def get_embedding_function(
    # REMOVE config parameter as it's not used here
) -> Optional[chromadb.EmbeddingFunction]:
    """
    Retrieves the globally initialized ChromaDB embedding function.

    Assumes `initialize_embedding_function` has been called previously
    (typically triggered by the first call to `get_chroma_client`).

    Returns:
        The initialized chromadb.EmbeddingFunction instance, or None if it hasn't
        been initialized yet (which shouldn't happen in normal operation after
        server startup).
    """
    logger = get_logger("utils.client")

    # Return the global variable
    if _embedding_function is None:
        logger.warning("get_embedding_function called before initialization!")
    return _embedding_function


def reset_client() -> None:
    """Reset the global client instance."""
    logger = get_logger("utils.client")

    global _chroma_client
    if _chroma_client is not None:
        try:
            _chroma_client.reset()
        except Exception as e:
            if "Resetting is not allowed" in str(e):
                logger.warning(f"Client reset failed gracefully (allow_reset=False): {e}")
            else:
                logger.error(f"Error resetting client: {e}")
        _chroma_client = None
