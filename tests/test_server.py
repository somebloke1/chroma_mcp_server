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
from chroma_mcp.handlers import (
    CollectionHandler, DocumentHandler, ThinkingHandler
)
from chroma_mcp.server import (
    _initialize_mcp_instance, config_server, create_parser,
    get_collection_handler, get_document_handler, get_mcp, get_thinking_handler
)
from chroma_mcp.utils.errors import (
    CollectionNotFoundError, ValidationError
)
from chroma_mcp.server import LoggerSetup # Import LoggerSetup

# Mock dependencies globally for simplicity in these tests
@pytest.fixture(autouse=True)
def mock_logger_setup(): # Renamed fixture
    """Mocks the LoggerSetup to control logger creation."""
    mock_logger_instance = MagicMock()
    # Patch the create_logger method within the server module context
    with patch("chroma_mcp.server.LoggerSetup.create_logger", return_value=mock_logger_instance) as mock_create:
        yield mock_logger_instance # Yield the mock logger instance

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
    server._collection_handler = None
    server._document_handler = None
    server._thinking_handler = None
    yield
    server._mcp_instance = None
    server._collection_handler = None
    server._document_handler = None
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

def test_server_config_defaults(mock_logger_setup): # Use updated fixture
    """Test server configuration with default arguments."""
    parser = create_parser()
    args = parser.parse_args([])

    with patch("os.path.exists", return_value=False):
        config_server(args)

    # Check logger initialization (using the mock instance)
    mock_logger_setup.info.assert_any_call("Server configured (CPU provider: auto-detected)")

def test_server_config_persistent(mock_logger_setup): # Use updated fixture
    """Test server configuration with persistent client."""
    parser = create_parser()
    test_data_dir = "/tmp/chroma_test_data"
    test_log_dir = "/tmp/chroma_test_logs"
    args = parser.parse_args([
        "--client-type", "persistent",
        "--data-dir", test_data_dir,
        "--log-dir", test_log_dir
    ])

    with patch("os.path.exists", return_value=False):
        config_server(args)

    # Use the mock logger instance for assertions
    mock_logger_setup.info.assert_any_call(f"Logs will be saved to: {test_log_dir}")
    mock_logger_setup.info.assert_any_call(f"Data directory: {test_data_dir}")

@patch('chroma_mcp.server.load_dotenv')
def test_server_config_error(mock_load_dotenv, mock_logger_setup): # Use updated fixture
    """Test error handling during server configuration."""
    with patch("os.path.exists", return_value=True):
        mock_load_dotenv.side_effect = OSError("Failed to load .env")
        parser = create_parser()
        args = parser.parse_args([])

        with pytest.raises(McpError) as exc_info:
            config_server(args)

        assert "Failed to configure server" in str(exc_info.value)

def test_server_config_cpu_provider_options(mock_logger_setup): # Use updated fixture
    """Test server configuration with different CPU provider settings."""
    parser = create_parser()

    # Test auto (default)
    args_auto = parser.parse_args([])
    with patch("os.path.exists", return_value=False):
        config_server(args_auto)
    mock_logger_setup.info.assert_any_call("Server configured (CPU provider: auto-detected)")

    # Test force true
    args_true = parser.parse_args(["--cpu-execution-provider", "true"])
    with patch("os.path.exists", return_value=False):
        config_server(args_true)
    mock_logger_setup.info.assert_any_call("Server configured (CPU provider: enabled)")

    # Test force false
    args_false = parser.parse_args(["--cpu-execution-provider", "false"])
    with patch("os.path.exists", return_value=False):
        config_server(args_false)
    mock_logger_setup.info.assert_any_call("Server configured (CPU provider: disabled)")

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

@pytest.fixture
def mock_chroma_client_for_handlers():
    """Mock the Chroma client where it is looked up by handlers."""
    # Patch get_chroma_client in each handler module where it's likely imported/used
    with patch("chroma_mcp.handlers.collection_handler.get_chroma_client") as mock_ch, \
         patch("chroma_mcp.handlers.document_handler.get_chroma_client") as mock_dh, \
         patch("chroma_mcp.handlers.thinking_handler.get_chroma_client") as mock_th:
        
        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        mock_client.create_collection.return_value = mock_collection
        
        # Make all patched mocks return the same mock client instance
        mock_ch.return_value = mock_client
        mock_dh.return_value = mock_client
        mock_th.return_value = mock_client
        
        yield mock_client # Yield the single mock client instance

def test_get_handlers(mock_chroma_client_for_handlers):
    """Test handler initialization."""
    server._collection_handler = None
    server._document_handler = None
    server._thinking_handler = None
    
    collection_handler = get_collection_handler()
    assert isinstance(collection_handler, CollectionHandler)
    assert collection_handler is get_collection_handler()

    document_handler = get_document_handler()
    assert isinstance(document_handler, DocumentHandler)
    assert document_handler is get_document_handler()

    thinking_handler = get_thinking_handler()
    assert isinstance(thinking_handler, ThinkingHandler)
    assert thinking_handler is get_thinking_handler()
