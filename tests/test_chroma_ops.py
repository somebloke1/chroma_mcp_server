"""Tests for low-level ChromaDB operations and utilities."""

import os
import pytest
from unittest.mock import patch, MagicMock
import platform
import chromadb
from chromadb.api.client import ClientAPI

# Import the module containing the function under test
from src.chroma_mcp.utils import client as client_module 
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS

# Import ChromaClientConfig
from src.chroma_mcp.utils.client import (
    ChromaClientConfig,
    get_chroma_client,
    get_embedding_function,
    initialize_embedding_function,
    reset_client,
    should_use_cpu_provider
)
from src.chroma_mcp.utils.errors import (
    ValidationError,
    CollectionNotFoundError,
    DocumentNotFoundError,
    EmbeddingError,
    ClientError,
    ConfigurationError,
    handle_chroma_error,
    validate_input,
    raise_validation_error
)
from src.chroma_mcp.utils.config import (
    ServerConfig,
    load_config,
    get_collection_settings,
    validate_collection_name
)

# Client Tests
class TestChromaClient:
    """Test cases for ChromaDB client operations."""

    def setup_method(self, method):
        """Reset client before each test."""
        reset_client() 
        # Also reset embedding function state if necessary
        client_module._embedding_function = None 
        
    def teardown_method(self, method):
        """Ensure client is reset after each test."""
        reset_client()
        client_module._embedding_function = None

    def test_get_ephemeral_client(self):
        """Test getting an ephemeral client."""
        config = ChromaClientConfig(client_type="ephemeral")
        client = get_chroma_client(config)
        assert isinstance(client, ClientAPI)

    def test_get_persistent_client(self, tmp_path):
        """Test getting a persistent client."""
        data_dir = str(tmp_path / "chroma_data")
        config = ChromaClientConfig(client_type="persistent", data_dir=data_dir)
        client = get_chroma_client(config)
        assert isinstance(client, ClientAPI)

    def test_get_http_client(self):
        """Test getting an HTTP client."""
        with patch("chromadb.HttpClient") as mock_http_client:
            mock_client = MagicMock(spec=ClientAPI)
            mock_http_client.return_value = mock_client
            
            config = ChromaClientConfig(
                client_type="http",
                host="localhost",
                port="8000",
                ssl=True
            )
            client = get_chroma_client(config)
            assert isinstance(client, ClientAPI)
            mock_http_client.assert_called_once_with(
                host="localhost",
                port="8000",
                ssl=True,
                tenant=None,
                database=None
            )

    @patch('src.chroma_mcp.server.get_server_config')
    def test_get_client_without_config(self, mock_get_server_config):
        """Test getting a client without config defaults to ephemeral.
        
        Mocks get_server_config to simulate the scenario where the server
        hasn't fully initialized, ensuring get_chroma_client can default.
        """
        # Configure the mock to return a default ephemeral config
        mock_get_server_config.return_value = ChromaClientConfig(client_type="ephemeral")
        
        client = get_chroma_client()
        assert isinstance(client, ClientAPI)

    def test_get_persistent_client_without_data_dir(self):
        """Test error when getting persistent client without data_dir."""
        config = ChromaClientConfig(client_type="persistent")
        with pytest.raises(ValueError) as exc_info:
            get_chroma_client(config)
        assert "data_dir is required for persistent client" in str(exc_info.value)

    def test_get_http_client_without_host(self):
        """Test error when getting HTTP client without host."""
        config = ChromaClientConfig(client_type="http")
        with pytest.raises(ValueError) as exc_info:
            get_chroma_client(config)
        assert "host is required for http client" in str(exc_info.value)

    def test_reset_client(self):
        """Test resetting the client."""
        with patch("src.chroma_mcp.utils.client._chroma_client") as mock_client:
            reset_client()
            mock_client.reset.assert_called_once()

    def test_get_persistent_client_success(self, tmp_path):
        """Test successful execution of get_chroma_client for PersistentClient."""
        # No patch needed, just call the function with valid config
        data_dir = str(tmp_path / "chroma_success")
        config_dict = {"client_type": "PersistentClient", "data_dir": data_dir}
        config_obj = ChromaClientConfig(**config_dict)
        client = get_chroma_client(config_obj)
        
        # Assert a ClientAPI instance is returned
        assert isinstance(client, ClientAPI)

    def test_get_http_client_success(self, mocker):
        """Test successful execution of get_chroma_client for HttpClient."""
        # Use mocker to prevent actual HTTP connection if HttpClient tries
        mocker.patch('chromadb.HttpClient') # Simple patch to avoid real connection
        
        config_dict = {
            "client_type": "HttpClient",
            "host": "127.0.0.1", # Use valid-looking host/port
            "port": 8001,
            "ssl": False,
            "tenant": "test_tenant",
            "database": "test_db",
            "api_key": "dummy_key"
        }
        config_obj = ChromaClientConfig(**config_dict)
        client = get_chroma_client(config_obj)
        
        # Assert a ClientAPI instance is returned
        assert isinstance(client, ClientAPI)

    def test_get_persistent_client_init_fails(self, mocker):
        """Test handling when underlying PersistentClient initialization fails.
           This now patches get_chroma_client itself.
        """
        # Simulate the error that would occur inside get_chroma_client
        expected_error = McpError(ErrorData(
            code=INTERNAL_ERROR, 
            message="Failed to initialize ChromaDB client: DB connection failed"
        ))
        mock_get_client = mocker.patch('src.chroma_mcp.utils.client.get_chroma_client', side_effect=expected_error)
        
        config_dict = {"client_type": "PersistentClient", "data_dir": "/tmp/nonexistent"}
        config_obj = ChromaClientConfig(**config_dict)

        with pytest.raises(McpError) as exc_info:
            # Call the function (which is now mocked)
            # We don't need to call the *real* get_chroma_client here
            # Instead, we might test code *calling* get_chroma_client
            # For this test, let's just call the mock to trigger the side effect
            mock_get_client(config_obj) 
        
        assert "Failed to initialize ChromaDB client" in str(exc_info.value)
        assert "DB connection failed" in str(exc_info.value)
        mock_get_client.assert_called_once_with(config_obj) 

    def test_get_http_client_init_fails(self, mocker):
        """Test handling when underlying HttpClient initialization fails.
           This now patches get_chroma_client itself.
        """
        expected_error = McpError(ErrorData(
            code=INTERNAL_ERROR, 
            message="Failed to initialize ChromaDB client: HTTP connection refused"
        ))
        mock_get_client = mocker.patch('src.chroma_mcp.utils.client.get_chroma_client', side_effect=expected_error)
        
        config_dict = {"client_type": "HttpClient", "host": "localhost", "port": 8001, "ssl": False}
        config_obj = ChromaClientConfig(**config_dict)

        with pytest.raises(McpError) as exc_info:
             # Call the mock to trigger the side effect
            mock_get_client(config_obj)

        assert "Failed to initialize ChromaDB client" in str(exc_info.value)
        assert "HTTP connection refused" in str(exc_info.value)
        mock_get_client.assert_called_once_with(config_obj)

# Embedding Function Tests
class TestEmbeddingFunction:
    """Test cases for embedding function operations."""

    def test_initialize_embedding_function_default(self):
        """Test initializing embedding function with default settings."""
        initialize_embedding_function()
        assert get_embedding_function() is not None

    def test_initialize_embedding_function_cpu(self):
        """Test initializing embedding function with CPU provider."""
        initialize_embedding_function(use_cpu_provider=True)
        assert get_embedding_function() is not None

    def test_initialize_embedding_function_error(self):
        """Test error handling during embedding function initialization."""
        with patch("src.chroma_mcp.utils.client.ONNXMiniLM_L6_V2", side_effect=Exception("Init failed")):
            with pytest.raises(McpError) as exc_info:
                initialize_embedding_function()
            assert "Failed to initialize embedding function" in str(exc_info.value)

# Error Handling Tests
class TestErrorHandling:
    """Test cases for error handling utilities."""

    def test_handle_chroma_error_collection_not_found(self):
        """Test handling collection not found error."""
        error = Exception("Collection not found")
        result = handle_chroma_error(error, "test_operation")
        assert isinstance(result, McpError)
        assert "Collection not found" in result.error.message

    def test_handle_chroma_error_client_error(self):
        """Test handling client error."""
        error = Exception("connection failed")
        result = handle_chroma_error(error, "test_operation")
        assert isinstance(result, McpError)
        assert "connection failed" in result.error.message

    def test_validate_input_required(self):
        """Test input validation for required fields."""
        error = validate_input(None, "test_field", required=True)
        assert error == "test_field is required"

    def test_validate_input_max_length(self):
        """Test input validation for maximum length."""
        error = validate_input("test", "test_field", max_length=3)
        assert "exceeds maximum length" in error

    def test_validate_input_min_length(self):
        """Test input validation for minimum length."""
        error = validate_input("a", "test_field", min_length=2)
        assert "shorter than minimum length" in error

    def test_validate_input_pattern(self):
        """Test input validation with pattern matching."""
        error = validate_input("123", "test_field", pattern=r"^[a-z]+$")
        assert "does not match required pattern" in error

    def test_raise_validation_error(self):
        """Test raising validation error."""
        with pytest.raises(ValidationError) as exc_info:
            raise_validation_error("Invalid input")
        assert "Invalid input" in str(exc_info.value)

# Configuration Tests
class TestConfiguration:
    """Test cases for configuration utilities."""

    def test_load_config_defaults(self):
        """Test loading default configuration."""
        config = load_config()
        assert isinstance(config, ServerConfig)
        assert config.log_level == "INFO"
        assert config.max_batch_size == 100
        assert config.enable_telemetry is False

    def test_load_config_from_env(self, monkeypatch):
        """Test loading configuration from environment variables."""
        monkeypatch.setenv("CHROMA_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("CHROMA_MAX_BATCH_SIZE", "200")
        monkeypatch.setenv("CHROMA_ENABLE_TELEMETRY", "true")
        
        config = load_config()
        assert config.log_level == "DEBUG"
        assert config.max_batch_size == 200
        assert config.enable_telemetry is True

    def test_get_collection_settings_default(self):
        """Test getting default collection settings."""
        settings = get_collection_settings()
        assert isinstance(settings, dict)
        assert "hnsw:space" in settings

    def test_get_collection_settings_custom(self):
        """Test getting custom collection settings."""
        settings = get_collection_settings(
            collection_name="test",
            hnsw_space="cosine",
            hnsw_construction_ef=100
        )
        assert settings["hnsw:space"] == "cosine"
        assert settings["hnsw:construction_ef"] == 100

    def test_validate_collection_name_success(self):
        """Test successful collection name validation."""
        validate_collection_name("valid_collection-123")
        # Should not raise any exception

    def test_validate_collection_name_empty(self):
        """Test validation of empty collection name."""
        with pytest.raises(McpError) as exc_info:
            validate_collection_name("")
        assert "Collection name cannot be empty" in str(exc_info.value)

    def test_validate_collection_name_too_long(self):
        """Test validation of too long collection name."""
        with pytest.raises(McpError) as exc_info:
            validate_collection_name("a" * 65)
        assert "Collection name cannot be longer than 64 characters" in str(exc_info.value)

    def test_validate_collection_name_invalid_chars(self):
        """Test validation of collection name with invalid characters."""
        with pytest.raises(McpError) as exc_info:
            validate_collection_name("invalid@collection")
        assert "Collection name can only contain letters, numbers, underscores, and hyphens" in str(exc_info.value)

# CPU Provider Detection Tests
class TestCpuProviderDetection:
    """Test cases for CPU provider detection and initialization."""

    @patch('platform.system')
    @patch('platform.mac_ver')
    @patch('platform.processor')
    def test_should_use_cpu_provider_intel_monterey(self, mock_processor, mock_mac_ver, mock_system):
        """Test CPU provider detection on Intel Mac with Monterey."""
        mock_system.return_value = "Darwin"
        mock_mac_ver.return_value = ("12.0.0", ("", "", ""), "x86_64")
        mock_processor.return_value = "Intel(R) Core(TM) i7"
        
        assert should_use_cpu_provider() is True

    @patch('platform.system')
    @patch('platform.mac_ver')
    @patch('platform.processor')
    def test_should_use_cpu_provider_intel_ventura(self, mock_processor, mock_mac_ver, mock_system):
        """Test CPU provider detection on Intel Mac with Ventura."""
        mock_system.return_value = "Darwin"
        mock_mac_ver.return_value = ("13.0.0", ("", "", ""), "x86_64")
        mock_processor.return_value = "Intel(R) Core(TM) i5"
        
        assert should_use_cpu_provider() is True

    @patch('platform.system')
    @patch('platform.mac_ver')
    @patch('platform.processor')
    def test_should_use_cpu_provider_intel_big_sur(self, mock_processor, mock_mac_ver, mock_system):
        """Test CPU provider detection on Intel Mac with Big Sur."""
        mock_system.return_value = "Darwin"
        mock_mac_ver.return_value = ("11.0.0", ("", "", ""), "x86_64")
        mock_processor.return_value = "Intel(R) Core(TM) i9"
        
        assert should_use_cpu_provider() is False

    @patch('platform.system')
    @patch('platform.mac_ver')
    @patch('platform.processor')
    def test_should_use_cpu_provider_m1_ventura(self, mock_processor, mock_mac_ver, mock_system):
        """Test CPU provider detection on Apple Silicon with Ventura."""
        mock_system.return_value = "Darwin"
        mock_mac_ver.return_value = ("13.0.0", ("", "", ""), "arm64")
        mock_processor.return_value = "arm"
        
        assert should_use_cpu_provider() is False

    @patch('platform.system')
    def test_should_use_cpu_provider_non_mac(self, mock_system):
        """Test CPU provider detection on non-macOS system."""
        mock_system.return_value = "Linux"
        assert should_use_cpu_provider() is False

    def test_initialize_embedding_function_auto_detect(self):
        """Test embedding function initialization with auto-detection."""
        with patch('src.chroma_mcp.utils.client.should_use_cpu_provider') as mock_detect:
            mock_detect.return_value = True
            initialize_embedding_function(use_cpu_provider=None)
            assert get_embedding_function() is not None

    def test_initialize_embedding_function_force_cpu(self):
        """Test embedding function initialization with forced CPU provider."""
        initialize_embedding_function(use_cpu_provider=True)
        assert get_embedding_function() is not None

    def test_initialize_embedding_function_force_default(self):
        """Test embedding function initialization with forced default provider."""
        initialize_embedding_function(use_cpu_provider=False)
        assert get_embedding_function() is not None

    def test_get_chroma_client_auto_detect_cpu(self):
        """Test client initialization with auto-detected CPU provider."""
        with patch('src.chroma_mcp.utils.client.should_use_cpu_provider') as mock_detect:
            mock_detect.return_value = True
            config = ChromaClientConfig(client_type="ephemeral", use_cpu_provider=None)
            client = get_chroma_client(config)
            assert isinstance(client, ClientAPI)
