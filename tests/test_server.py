"""Tests for the ChromaMCP server implementation."""

# Standard library imports
import argparse
import importlib.metadata
import os
from unittest.mock import AsyncMock, MagicMock, call, patch

# Third-party imports
import pytest
# Import McpError and INTERNAL_ERROR from exceptions
from mcp.shared.exceptions import McpError 

# Local application imports
# Import the module itself to allow monkeypatching its attributes
from chroma_mcp import server
from chroma_mcp.server import (
    _initialize_mcp_instance, config_server, create_parser,
    get_mcp
)
from chroma_mcp.utils.errors import (
    CollectionNotFoundError, ValidationError
)

# Mock dependencies globally for simplicity in these tests
@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock external dependencies like ChromaDB and FastMCP availability."""
    with patch("chroma_mcp.server.CHROMA_AVAILABLE", True), \
         patch("chroma_mcp.server.FASTMCP_AVAILABLE", True):
        yield

@pytest.fixture(autouse=True)
def reset_globals():
    """Reset global handlers and MCP instance before each test."""
    server._mcp_instance = None
    server._thinking_handler = None
    yield
    server._mcp_instance = None
    server._thinking_handler = None

@pytest.fixture
def mock_register_collection():
    with patch("chroma_mcp.server.register_collection_tools") as mock:
        yield mock

@pytest.fixture
def mock_register_document():
    with patch("chroma_mcp.server.register_document_tools") as mock:
        yield mock

@pytest.fixture
def mock_register_thinking():
    with patch("chroma_mcp.server.register_thinking_tools") as mock:
        yield mock

@pytest.fixture
def mock_mcp():
    """Mock the FastMCP class."""
    with patch("chroma_mcp.server.FastMCP", autospec=True) as mock:
        yield mock

# Patch logging.getLogger for tests needing to check log calls
@pytest.fixture
def mock_get_logger():
    with patch("chroma_mcp.server.logging.getLogger") as mock_get:
        mock_logger = MagicMock()
        mock_get.return_value = mock_logger
        yield mock_logger # Yield the instance returned by getLogger

# --- Test Functions ---

def test_create_parser():
    """Test argument parser creation."""
    parser = create_parser()
    assert isinstance(parser, argparse.ArgumentParser)
    # Check a few arguments
    args = parser.parse_args([]) # Get defaults
    assert args.client_type == 'ephemeral'
    assert args.ssl is True # Default SSL for HTTP client if relevant
    assert args.cpu_execution_provider == 'auto'

def test_server_config_defaults(mock_get_logger): # Use new fixture
    """Test server configuration with default arguments."""
    parser = create_parser()
    args = parser.parse_args([])

    with patch("os.path.exists", return_value=False):
        config_server(args)

    # Check logger initialization (using the mock instance)
    mock_get_logger.info.assert_any_call("Server configured (CPU provider: auto-detected)")

def test_server_config_persistent(mock_get_logger): # Use new fixture
    """Test server configuration with persistent client."""
    parser = create_parser()
    test_data_dir = "/tmp/chroma_test_data"
    test_log_dir = "/tmp/chroma_test_logs"
    args = parser.parse_args([
        "--client-type", "persistent",
        "--data-dir", test_data_dir,
        "--log-dir", test_log_dir
    ])

    with patch("os.path.exists", return_value=False), \
         patch("os.makedirs"), \
         patch("logging.handlers.RotatingFileHandler"): # Patch file handler creation
        config_server(args)

    # Use the mock logger instance for assertions
    mock_get_logger.info.assert_any_call(f"Logs will be saved to: {test_log_dir}")
    mock_get_logger.info.assert_any_call(f"Data directory: {test_data_dir}")

@patch('chroma_mcp.server.load_dotenv')
@patch('builtins.print') # Patch print instead
def test_server_config_error(mock_print, mock_load_dotenv):
    """Test error handling during server configuration (early failure)."""
    with patch("os.path.exists", return_value=True):
        mock_load_dotenv.side_effect = OSError("Failed to load .env")
        parser = create_parser()
        args = parser.parse_args([])

        with pytest.raises(McpError) as exc_info:
            config_server(args)

        assert "Failed to configure server" in str(exc_info.value)
        # Remove the assertion for logger.error
        # mock_logger_instance.error.assert_called_once_with("Failed to configure server: Failed to load .env")
        # Assert that print was called with the correct error message
        mock_print.assert_called_once_with("ERROR: Failed to configure server: Failed to load .env")

def test_server_config_cpu_provider_options(mock_get_logger): # Use new fixture
    """Test server configuration with different CPU provider settings."""
    parser = create_parser()

    # Test auto (default)
    args_auto = parser.parse_args([])
    with patch("os.path.exists", return_value=False), \
         patch("logging.handlers.RotatingFileHandler"): # Patch file handler
        config_server(args_auto)
    mock_get_logger.info.assert_any_call("Server configured (CPU provider: auto-detected)")
    mock_get_logger.reset_mock() # Reset mock for next call

    # Test force true
    args_true = parser.parse_args(["--cpu-execution-provider", "true"])
    with patch("os.path.exists", return_value=False), \
         patch("logging.handlers.RotatingFileHandler"): # Patch file handler
        config_server(args_true)
    mock_get_logger.info.assert_any_call("Server configured (CPU provider: enabled)")
    mock_get_logger.reset_mock() # Reset mock for next call

    # Test force false
    args_false = parser.parse_args(["--cpu-execution-provider", "false"])
    with patch("os.path.exists", return_value=False), \
         patch("logging.handlers.RotatingFileHandler"): # Patch file handler
        config_server(args_false)
    mock_get_logger.info.assert_any_call("Server configured (CPU provider: disabled)")

def test_get_mcp_initialization(
    mock_mcp, mock_register_collection, mock_register_document, mock_register_thinking, monkeypatch
):
    """Test successful MCP initialization and tool registration."""
    monkeypatch.setattr(server, "_mcp_instance", None)

    mcp_instance = get_mcp()

    assert mcp_instance is mock_mcp.return_value

    mock_mcp.assert_called_once_with("chroma")

    mock_register_collection.assert_called_once_with(mock_mcp.return_value)
    mock_register_document.assert_called_once_with(mock_mcp.return_value)
    mock_register_thinking.assert_called_once_with(mock_mcp.return_value)

    # Check that the .tool() method was called with the correct name
    # for the get_version_tool
    found_tool_call = False
    for method_call in mock_mcp.return_value.method_calls:
        # method_call looks like call.tool(name=..., ...)
        if method_call[0] == 'tool' and method_call.kwargs.get('name') == 'chroma_get_server_version':
            found_tool_call = True
            break
    assert found_tool_call, "call to .tool(name='chroma_get_server_version') not found on mock MCP"

def test_get_mcp_initialization_error(mock_mcp, monkeypatch):
    """Test MCP initialization error handling."""
    monkeypatch.setattr(server, "_mcp_instance", None)

    mock_mcp.side_effect = Exception("Failed to initialize")

    with pytest.raises(McpError) as exc_info:
        get_mcp()

    assert "Failed to initialize MCP" in str(exc_info.value)
    mock_mcp.assert_called_once_with("chroma")
