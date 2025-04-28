"""
Handles direct connection to ChromaDB based on .env configuration.
Reuses configuration loading and client creation logic from the server's utils.
"""
import sys
import os
import chromadb
from pathlib import Path
from typing import Tuple, Optional
from chromadb import EmbeddingFunction
from functools import lru_cache

from chroma_mcp.utils.chroma_client import get_chroma_client, get_embedding_function
from chroma_mcp.types import ChromaClientConfig

# Default collection name used by the client
DEFAULT_COLLECTION_NAME = "codebase_v1"

# Use lru_cache to ensure client/EF are initialized only once
@lru_cache(maxsize=1)
def get_client_and_ef(env_path: Optional[str] = None) -> Tuple[chromadb.ClientAPI, Optional[chromadb.EmbeddingFunction]]:
    """Initializes and returns a cached tuple of ChromaDB client and embedding function.

    Reads configuration from environment variables or a .env file.
    Ensures single initialization using lru_cache.

    Args:
        env_path: Optional path to a .env file.

    Returns:
        Tuple[chromadb.ClientAPI, Optional[chromadb.EmbeddingFunction]]

    Raises:
        Exception: If configuration loading or client/EF initialization fails.
    """
    print(f"Initializing ChromaDB connection and embedding function (env_path={env_path})...", file=sys.stderr)

    # 1. Load environment variables directly (if env_path is provided)
    #    The dotenv library handles loading from .env implicitly if installed and present,
    #    or we can explicitly load it if needed.
    #    NOTE: For simplicity, assuming dotenv is handled by the environment or not strictly required here.
    #    If explicit .env loading is needed *here*, add: from dotenv import load_dotenv; load_dotenv(env_path)

    # 2. Construct ChromaClientConfig directly from environment variables
    #    Ensure all necessary fields expected by ChromaClientConfig are mapped.
    client_config = ChromaClientConfig(
        client_type=os.getenv("CHROMA_CLIENT_TYPE", "persistent"),
        data_dir=os.getenv("CHROMA_DATA_DIR", "./chroma_data"),
        host=os.getenv("CHROMA_HOST", "localhost"),
        port=os.getenv("CHROMA_PORT", "8000"), # Keep as string (or None)
        ssl=os.getenv("CHROMA_SSL", "false").lower() in ["true", "1", "yes"],
        tenant=os.getenv("CHROMA_TENANT", chromadb.DEFAULT_TENANT),
        database=os.getenv("CHROMA_DATABASE", chromadb.DEFAULT_DATABASE),
        # embedding_function_name is NOT part of client connection config
        # Add any other required fields from ServerConfig here
    )
    print(f"Client Config from Env - Type: {client_config.client_type}, Host: {client_config.host}, Port: {client_config.port}, Path: {client_config.data_dir}", file=sys.stderr)

    # 3. Get the ChromaDB client using the constructed client_config
    #    get_chroma_client handles the actual client creation logic
    print(f"Getting ChromaDB client (Type: {client_config.client_type})...", file=sys.stderr)
    # Pass the explicitly constructed config
    client: chromadb.ClientAPI = get_chroma_client(config=client_config)

    # 4. Get the embedding function name directly from environment
    #    (EF name is often part of the general config, not client-specific connection)
    ef_name = os.getenv("CHROMA_EMBEDDING_FUNCTION", "default") # Use default if not set
    print(f"Getting Embedding Function ('{ef_name}')...", file=sys.stderr)
    embedding_function: Optional[chromadb.EmbeddingFunction] = get_embedding_function(ef_name)

    print("Client and EF initialization complete.", file=sys.stderr)
    return client, embedding_function

# Example usage (optional, for testing connection module directly)
# if __name__ == "__main__":
