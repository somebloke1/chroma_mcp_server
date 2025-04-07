"""
ChromaDB client utility module for managing client instances and configuration.
"""

import os
import ssl
import platform
from typing import Optional, Union
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings
from chromadb.api.types import GetResult
# Import specific embedding function for compatibility with Intel Macs
from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR

# Remove old logger setup
# from .logger_setup import LoggerSetup
# Replace with get_logger from server
from ..server import get_logger
from ..types import ChromaClientConfig

# Initialize logger using the central function
# logger = LoggerSetup.create_logger(
#     "ChromaClient",
#     log_file="chroma_client.log"
# )
logger = get_logger("utils.client")

def should_use_cpu_provider() -> bool:
    """
    Detect if we should use CPU provider based on system information.
    
    Returns:
        bool: True if we should use CPU provider (newer macOS on Intel)
    """
    try:
        # Check if we're on macOS
        if platform.system() != "Darwin":
            return False
            
        # Get macOS version (e.g., 13.0.0 for Ventura)
        mac_version = tuple(map(int, platform.mac_ver()[0].split('.')))
        
        # Check if we're on Intel
        is_intel = platform.processor() == 'i386' or 'Intel' in platform.processor()
        
        # If we're on macOS 12 (Monterey) or later and running on Intel,
        # we should use CPU provider as these versions are primarily for Apple Silicon
        needs_cpu_provider = mac_version >= (12, 0, 0) and is_intel
        
        if needs_cpu_provider:
            logger.info(f"Detected macOS {platform.mac_ver()[0]} on Intel CPU - will use CPU provider")
        
        return needs_cpu_provider
        
    except Exception as e:
        logger.warning(f"Error detecting system info, defaulting to standard provider: {e}")
        return False

@dataclass
class ChromaClientConfig:
    """Configuration for ChromaDB client."""
    client_type: str
    data_dir: Optional[str] = None
    host: Optional[str] = None
    port: Optional[str] = None
    ssl: bool = True
    tenant: Optional[str] = None
    database: Optional[str] = None
    api_key: Optional[str] = None
    use_cpu_provider: Optional[bool] = None  # Flag to force CPU execution provider, None means auto-detect

# Global client instance
_chroma_client: Optional[Union[chromadb.PersistentClient, chromadb.HttpClient, chromadb.EphemeralClient]] = None
_embedding_function = None

def initialize_embedding_function(use_cpu_provider: Optional[bool] = None) -> None:
    """
    Initialize the embedding function with optional CPU provider enforcement.
    
    Args:
        use_cpu_provider: If True, forces CPU provider. If None, auto-detects based on system.
        
    Raises:
        McpError: If embedding function initialization fails
    """
    global _embedding_function
    
    try:
        # If use_cpu_provider is None, auto-detect
        should_use_cpu = use_cpu_provider if use_cpu_provider is not None else should_use_cpu_provider()
        
        if should_use_cpu:
            _embedding_function = ONNXMiniLM_L6_V2(preferred_providers=["CPUExecutionProvider"])
            logger.info("Initialized embedding function with CPU provider")
        else:
            _embedding_function = ONNXMiniLM_L6_V2()
            logger.info("Initialized embedding function with default providers")
    except Exception as e:
        error_msg = f"Failed to initialize embedding function: {str(e)}"
        logger.error(error_msg)
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=error_msg
        ))

def get_chroma_client(config: Optional[ChromaClientConfig] = None) -> Union[chromadb.PersistentClient, chromadb.HttpClient, chromadb.EphemeralClient]:
    """Get a ChromaDB client based on configuration."""
    global _chroma_client
    
    # FIX: Use global config if no specific config is passed
    if config is None:
        # FIX: Import getter locally within the function
        from ..server import get_server_config
        config = get_server_config() # Get the config set during server startup

    # Initialize embedding function if not already initialized
    if _embedding_function is None:
        initialize_embedding_function(use_cpu_provider=config.use_cpu_provider)

    # Validate configuration
    if config.client_type == "persistent" and not config.data_dir:
        raise ValueError("data_dir is required for persistent client")
    elif config.client_type == "http" and not config.host:
        raise ValueError("host is required for http client")

    try:
        if config.client_type == "persistent":
            _chroma_client = chromadb.PersistentClient(path=config.data_dir)
        elif config.client_type == "http":
            _chroma_client = chromadb.HttpClient(
                host=config.host,
                port=config.port,
                ssl=config.ssl,
                tenant=config.tenant,
                database=config.database
            )
        else:  # ephemeral
            _chroma_client = chromadb.EphemeralClient()

        # Set the embedding function for the client
        _chroma_client._embedding_function = _embedding_function
        return _chroma_client
        
    except Exception as e:
        error_msg = f"Failed to initialize ChromaDB client: {str(e)}"
        logger.error(error_msg)
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=error_msg
        ))

def get_embedding_function():
    """Get the default embedding function."""
    return _embedding_function

def reset_client() -> None:
    """Reset the global client instance."""
    global _chroma_client
    if _chroma_client is not None:
        try:
            _chroma_client.reset()
        except Exception as e:
            # Catch the specific reset error or any other exception during reset
            if "Resetting is not allowed" in str(e):
                logger.warning(f"Client reset failed gracefully (allow_reset=False): {e}")
            else:
                logger.error(f"Error resetting client: {e}")
        _chroma_client = None
