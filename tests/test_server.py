"""Tests for the ChromaMCP server implementation."""

import os
import pytest
import argparse

from unittest.mock import AsyncMock, MagicMock, patch
from mcp.types import ErrorData, INVALID_PARAMS, INTERNAL_ERROR
from mcp.shared.exceptions import McpError

from chroma_mcp.server import (
    create_parser,
    config_server,
    get_mcp,
    get_collection_handler,
    get_document_handler,
    get_thinking_handler
)
from chroma_mcp.types import ChromaClientConfig, ThoughtMetadata
from chroma_mcp.handlers import CollectionHandler, DocumentHandler, ThinkingHandler
from chroma_mcp.utils.errors import ValidationError, CollectionNotFoundError

@pytest.fixture(autouse=True)
def reset_mcp():
    """Reset the MCP instance before each test."""
    import chroma_mcp.server
    chroma_mcp.server._mcp = None
    yield

@pytest.fixture
def mock_chroma_client():
    """Mock the Chroma client."""
    with patch("chroma_mcp.server.get_chroma_client") as mock:
        yield mock

@pytest.fixture
def mock_collection_handler():
    """Mock the collection handler."""
    handler = AsyncMock()
    with patch("chroma_mcp.server.get_collection_handler", return_value=handler):
        yield handler

@pytest.fixture
def mock_document_handler():
    """Mock the document handler."""
    handler = AsyncMock()
    with patch("chroma_mcp.server.get_document_handler", return_value=handler):
        yield handler

@pytest.fixture
def mock_thinking_handler():
    """Mock the thinking handler."""
    handler = AsyncMock()
    with patch("chroma_mcp.server.get_thinking_handler", return_value=handler):
        yield handler

@pytest.fixture
def mock_mcp():
    """Mock the MCP instance."""
    with patch("chroma_mcp.server.FastMCP") as mock:
        yield mock

def test_create_parser():
    """Test parser creation with various arguments."""
    parser = create_parser()
    
    # Test default values
    args = parser.parse_args([])
    assert args.client_type == 'ephemeral'
    assert args.ssl is True
    
    # Test custom values
    args = parser.parse_args([
        '--client-type', 'http',
        '--host', 'localhost',
        '--port', '8000',
        '--ssl', 'false',
        '--data-dir', '/tmp/data'
    ])
    assert args.client_type == 'http'
    assert args.host == 'localhost'
    assert args.port == '8000'
    assert args.ssl is False
    assert args.data_dir == '/tmp/data'

def test_server_config(mock_chroma_client):
    """Test server configuration."""
    args = argparse.Namespace(
        client_type='ephemeral',
        data_dir=None,
        host=None,
        port=None,
        ssl=True,
        tenant=None,
        database=None,
        api_key=None,
        cpu_execution_provider='false',
        dotenv_path='.env',
        log_dir=None
    )

    # No need to mock the Chroma client as config_server doesn't initialize it
    config_server(args)
    # If no exception is raised, the test passes

def test_server_config_error():
    """Test server configuration with error."""
    # Create a custom exception to be raised
    class DotenvError(Exception):
        pass
    
    # We need to ensure load_dotenv is actually called by making os.path.exists return True
    with patch("os.path.exists", return_value=True), \
         patch("chroma_mcp.server.load_dotenv", side_effect=DotenvError("Failed to load environment")):
        
        args = argparse.Namespace(
            client_type='ephemeral',
            data_dir=None,
            host=None,
            port=None,
            ssl=True,
            tenant=None,
            database=None,
            api_key=None,
            cpu_execution_provider='false',
            dotenv_path='.env',
            log_dir=None
        )

        # The server code converts exceptions to McpError
        with pytest.raises(McpError) as exc_info:
            config_server(args)
        
        # Check that the original exception message is included in the McpError
        assert "Failed to load environment" in str(exc_info.value)

def test_server_config_auto_cpu_provider():
    """Test server configuration with auto CPU provider detection."""
    args = argparse.Namespace(
        client_type='ephemeral',
        data_dir=None,
        host=None,
        port=None,
        ssl=True,
        tenant=None,
        database=None,
        api_key=None,
        cpu_execution_provider='auto',
        dotenv_path='.env',
        log_dir=None
    )

    with patch("chroma_mcp.server.load_dotenv"):
        config_server(args)
        # If no exception is raised, the test passes

def test_server_config_force_cpu_provider():
    """Test server configuration with forced CPU provider."""
    args = argparse.Namespace(
        client_type='ephemeral',
        data_dir=None,
        host=None,
        port=None,
        ssl=True,
        tenant=None,
        database=None,
        api_key=None,
        cpu_execution_provider='true',
        dotenv_path='.env',
        log_dir=None
    )

    with patch("chroma_mcp.server.load_dotenv"):
        config_server(args)
        # If no exception is raised, the test passes

def test_server_config_disable_cpu_provider():
    """Test server configuration with disabled CPU provider."""
    args = argparse.Namespace(
        client_type='ephemeral',
        data_dir=None,
        host=None,
        port=None,
        ssl=True,
        tenant=None,
        database=None,
        api_key=None,
        cpu_execution_provider='false',
        dotenv_path='.env',
        log_dir=None
    )

    with patch("chroma_mcp.server.load_dotenv"):
        config_server(args)
        # If no exception is raised, the test passes

def test_create_parser_cpu_provider_options():
    """Test parser creation with CPU provider options."""
    parser = create_parser()
    
    # Test auto detection (default)
    args = parser.parse_args([])
    assert args.cpu_execution_provider == 'auto'
    
    # Test force CPU provider
    args = parser.parse_args(['--cpu-execution-provider', 'true'])
    assert args.cpu_execution_provider == 'true'
    
    # Test disable CPU provider
    args = parser.parse_args(['--cpu-execution-provider', 'false'])
    assert args.cpu_execution_provider == 'false'

def test_get_mcp_initialization(mock_mcp, mock_collection_handler, mock_document_handler, mock_thinking_handler):
    """Test MCP initialization and tool registration."""
    with patch("chroma_mcp.server.register_collection_tools") as mock_register_collection, \
         patch("chroma_mcp.server.register_document_tools") as mock_register_document, \
         patch("chroma_mcp.server.register_thinking_tools") as mock_register_thinking:
        
        mcp = get_mcp()
        
        # Verify MCP was initialized
        mock_mcp.assert_called_once_with("chroma")
        
        # Verify tools were registered
        mock_register_collection.assert_called_once()
        mock_register_document.assert_called_once()
        mock_register_thinking.assert_called_once()

def test_get_mcp_initialization_error(mock_mcp):
    """Test MCP initialization error handling."""
    # Mock the FastMCP constructor to raise an exception
    mock_mcp.side_effect = Exception("Failed to initialize")
    
    with pytest.raises(McpError) as exc_info:
        get_mcp()
    
    assert "Failed to initialize MCP" in str(exc_info.value)

@pytest.fixture
def mock_chroma_client_for_handlers():
    """Mock the Chroma client for handler tests."""
    with patch("chroma_mcp.handlers.thinking_handler.get_chroma_client") as mock:
        # Create a mock client that returns a mock collection
        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        mock_client.create_collection.return_value = mock_collection
        mock.return_value = mock_client
        yield mock_client

def test_get_handlers(mock_chroma_client_for_handlers):
    """Test handler initialization."""
    # Test collection handler
    collection_handler = get_collection_handler()
    assert isinstance(collection_handler, CollectionHandler)
    assert collection_handler is get_collection_handler()  # Test singleton pattern
    
    # Test document handler
    document_handler = get_document_handler()
    assert isinstance(document_handler, DocumentHandler)
    assert document_handler is get_document_handler()  # Test singleton pattern
    
    # Test thinking handler
    thinking_handler = get_thinking_handler()
    assert isinstance(thinking_handler, ThinkingHandler)
    assert thinking_handler is get_thinking_handler()  # Test singleton pattern
