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


@patch("chroma_mcp_client.connection.get_chroma_client")  # Patch where it's *used*
@patch("chroma_mcp_client.connection.get_embedding_function")  # Patch where it's *used*
def test_get_client_and_ef_success_and_caching(
    mock_get_embedding_function, mock_get_chroma_client, monkeypatch, tmp_path
):
    """Test successful client/EF retrieval and caching."""
    # Setup mock env vars and a dummy .env file
    fake_env_path = tmp_path / ".env"
    fake_data_path = tmp_path / "chroma_data"
    fake_data_path.mkdir()
    fake_env_path.write_text(
        f"CHROMA_CLIENT_TYPE=persistent\nCHROMA_DATA_DIR={fake_data_path}\nCHROMA_EMBEDDING_FUNCTION=default\n"
    )

    # Mock return values for the *creation* functions
    mock_client_instance = MagicMock(spec=chromadb.ClientAPI)
    mock_ef_instance = MagicMock(spec=chromadb.EmbeddingFunction)
    mock_get_chroma_client.return_value = mock_client_instance  # Correct mock
    mock_get_embedding_function.return_value = mock_ef_instance

    # Clear cache before test
    get_client_and_ef.cache_clear()

    # --- First Call ---
    client1, ef1 = get_client_and_ef(env_path=str(fake_env_path))

    # Determine the expected resolved data path based on tmp_path
    # Project root will be grandparent of fake_env_path in this test setup
    expected_project_root = fake_env_path.parent
    # NOTE: The code now resolves ./chroma_data relative to root, not the .env value
    # We need to simulate this resolution for the expected config
    expected_resolved_data_dir = str(expected_project_root / "chroma_data")

    # Expected config based on .env AND resolution logic
    expected_config = ChromaClientConfig(
        client_type="persistent",
        embedding_function_name="default",
        data_dir=expected_resolved_data_dir,
        host="localhost",
        port="8000",
        ssl=False,
        tenant=chromadb.DEFAULT_TENANT,
        database=chromadb.DEFAULT_DATABASE,
        api_key=None,
        use_cpu_provider=None,
    )

    # Assertions for first call
    assert client1 is mock_client_instance
    assert ef1 is mock_ef_instance
    mock_get_chroma_client.assert_called_once_with(config=expected_config)

    mock_get_embedding_function.assert_called_once_with("default")  # Name comes from .env file

    # --- Second Call (should hit cache) ---
    client2, ef2 = get_client_and_ef(env_path=str(fake_env_path))

    # Assertions for second call
    assert client2 is client1  # Should be the same cached instance
    assert ef2 is ef1  # Should be the same cached instance

    # Verify mocks were NOT called again
    mock_get_chroma_client.assert_called_once()  # Still called only once total
    mock_get_embedding_function.assert_called_once()  # Still called only once total


# Add more tests for edge cases, different client types, error handling etc.
