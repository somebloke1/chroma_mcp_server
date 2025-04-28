"""
Tests for the chroma_mcp_client.connection module.
"""

import pytest
from unittest.mock import patch, MagicMock, call
from chroma_mcp_client.connection import get_client_and_ef, ChromaClientConfig, DEFAULT_COLLECTION_NAME
# We also need chromadb for type hints in mocks
import chromadb
from chromadb.config import Settings

# --- Test Cases ---

@patch('chroma_mcp_client.connection.get_chroma_client') # Patch where it's *used*
@patch('chroma_mcp_client.connection.get_embedding_function') # Patch where it's *used*
def test_get_client_and_ef_success_and_caching(mock_get_embedding_function, mock_get_chroma_client, monkeypatch, tmp_path):
    """Test successful client/EF retrieval and caching."""
    # Setup mock env vars and a dummy .env file
    fake_env_path = tmp_path / ".env"
    fake_data_path = tmp_path / "chroma_data"
    fake_data_path.mkdir()
    fake_env_path.write_text(f"CHROMA_CLIENT_TYPE=persistent\nCHROMA_DATA_DIR={fake_data_path}\nCHROMA_EMBEDDING_FUNCTION=default\n")

    # Mock return values for the *creation* functions
    mock_client_instance = MagicMock(spec=chromadb.ClientAPI)
    mock_ef_instance = MagicMock(spec=chromadb.EmbeddingFunction)
    mock_get_chroma_client.return_value = mock_client_instance # Correct mock
    mock_get_embedding_function.return_value = mock_ef_instance

    # Clear cache before test
    get_client_and_ef.cache_clear()

    # --- First Call --- 
    client1, ef1 = get_client_and_ef(env_path=str(fake_env_path))

    # Expected config based on .env
    # The config read from .env will have the relative path
    expected_config = ChromaClientConfig(
        client_type="persistent", # From .env
        embedding_function_name='default', # Seems to be included in the actual config
        data_dir='./chroma_data', # Explicitly match traceback expectation
        host="localhost", # Default
        port="8000",    # Default
        ssl=False,      # Default
        tenant=chromadb.DEFAULT_TENANT,
        database=chromadb.DEFAULT_DATABASE,
        api_key=None, # Add default/None fields for comparison
        use_cpu_provider=None # Add default/None fields for comparison
    )

    # Assertions for first call
    assert client1 is mock_client_instance
    assert ef1 is mock_ef_instance
    mock_get_chroma_client.assert_called_once_with(config=expected_config)

    mock_get_embedding_function.assert_called_once_with("default") # Name comes from .env file

    # --- Second Call (should hit cache) ---
    client2, ef2 = get_client_and_ef(env_path=str(fake_env_path))

    # Assertions for second call
    assert client2 is client1 # Should be the same cached instance
    assert ef2 is ef1       # Should be the same cached instance

    # Verify mocks were NOT called again
    mock_get_chroma_client.assert_called_once() # Still called only once total
    mock_get_embedding_function.assert_called_once()     # Still called only once total

# Add more tests for edge cases, different client types, error handling etc.
