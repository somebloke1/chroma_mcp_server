"""Tests for the ChromaMCP server implementation."""

import os
import pytest
import argparse

from pydantic import BaseModel
from fastapi import FastAPI

from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from mcp.types import ErrorData, INVALID_PARAMS

from src.chroma_mcp.server import app, create_parser, config_server
from src.chroma_mcp.types import ChromaClientConfig, ThoughtMetadata
from src.chroma_mcp.handlers import CollectionHandler, DocumentHandler, ThinkingHandler
from src.chroma_mcp.utils.errors import ValidationError, CollectionNotFoundError, McpError

# Initialize test client
client = TestClient(app)

@pytest.fixture
def mock_chroma_client():
    """Mock the Chroma client."""
    with patch("src.chroma_mcp.server.get_chroma_client") as mock:
        yield mock

@pytest.fixture
def mock_collection_handler():
    """Mock the collection handler."""
    handler = AsyncMock()
    with patch("src.chroma_mcp.server.get_collection_handler", return_value=handler):
        yield handler

@pytest.fixture
def mock_document_handler():
    """Mock the document handler."""
    handler = AsyncMock()
    with patch("src.chroma_mcp.server.get_document_handler", return_value=handler):
        yield handler

@pytest.fixture
def mock_thinking_handler():
    """Mock the thinking handler."""
    handler = AsyncMock()
    with patch("src.chroma_mcp.server.get_thinking_handler", return_value=handler):
        yield handler

@pytest.fixture
def test_client():
    """Create a test client."""
    return TestClient(app)

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

@pytest.mark.asyncio
async def test_server_config(mock_chroma_client):
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
        dotenv_path='.env'
    )

    # No need to mock the Chroma client as config_server doesn't initialize it
    config_server(args)
    # If no exception is raised, the test passes

@pytest.mark.asyncio
async def test_server_config_error():
    """Test server configuration with error."""
    # Mock load_dotenv to raise an exception
    with patch("src.chroma_mcp.server.load_dotenv") as mock_load_dotenv:
        mock_load_dotenv.side_effect = Exception("Failed to load environment")

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
            dotenv_path='.env'
        )

        with pytest.raises(McpError) as exc_info:
            config_server(args)
        assert "Failed to configure server: Failed to load environment" in str(exc_info.value)
        mock_load_dotenv.assert_called_once()

@pytest.mark.asyncio
async def test_server_config_auto_cpu_provider():
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
        dotenv_path='.env'
    )

    with patch("src.chroma_mcp.server.load_dotenv"):
        config_server(args)
        # If no exception is raised, the test passes

@pytest.mark.asyncio
async def test_server_config_force_cpu_provider():
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
        dotenv_path='.env'
    )

    with patch("src.chroma_mcp.server.load_dotenv"):
        config_server(args)
        # If no exception is raised, the test passes

@pytest.mark.asyncio
async def test_server_config_disable_cpu_provider():
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
        dotenv_path='.env'
    )

    with patch("src.chroma_mcp.server.load_dotenv"):
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

def test_root_endpoint(test_client):
    """Test root endpoint."""
    response = test_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "ChromaMCP Server is running"}

@pytest.mark.asyncio
async def test_create_collection_error(test_client, mock_collection_handler):
    """Test collection creation with error."""
    error = McpError(ErrorData(code=INVALID_PARAMS, message="Collection exists"))
    mock_collection_handler.create_collection.side_effect = error
    response = test_client.post("/collections?name=test_collection")
    assert response.status_code == 400
    assert response.json()["detail"] == "Collection exists"

@pytest.mark.asyncio
async def test_list_collections_success(test_client, mock_collection_handler):
    """Test successful collections listing."""
    mock_response = {"collections": [{"name": "col1", "id": "1"}, {"name": "col2", "id": "2"}]}
    mock_collection_handler.list_collections.return_value = mock_response
    response = test_client.get("/collections")
    assert response.status_code == 200
    assert response.json() == mock_response

@pytest.mark.asyncio
async def test_get_collection_success(test_client, mock_collection_handler):
    """Test successful collection retrieval."""
    mock_response = {
        "name": "test_collection",
        "id": "123",
        "metadata": {"key": "value"},
        "count": 10
    }
    mock_collection_handler.get_collection.return_value = mock_response
    response = test_client.get("/collections/test_collection")
    assert response.status_code == 200
    assert response.json() == mock_response

@pytest.mark.asyncio
async def test_get_collection_not_found(test_client, mock_collection_handler):
    """Test collection retrieval when not found."""
    mock_collection_handler.get_collection.side_effect = CollectionNotFoundError("Collection not found")
    response = test_client.get("/collections/test_collection")
    assert response.status_code == 404
    assert response.json()["detail"] == "Collection not found"

@pytest.mark.asyncio
async def test_query_documents_success(test_client, mock_document_handler):
    """Test successful document query."""
    mock_response = {
        "documents": ["test doc"],
        "metadatas": [{"key": "value"}],
        "distances": [0.5],
        "ids": ["1"]
    }
    mock_document_handler.query_collection.return_value = mock_response
    response = test_client.post(
        "/collections/test_collection/query",
        json={
            "query_texts": ["test query"],
            "n_results": 1
        }
    )
    assert response.status_code == 200
    assert response.json() == mock_response

@pytest.mark.asyncio
async def test_record_thought_success(test_client, mock_thinking_handler):
    """Test successful thought recording."""
    mock_response = {"thought_id": "123"}
    mock_thinking_handler.add_thought.return_value = mock_response
    response = test_client.post(
        "/thoughts",
        json={
            "thought": "test thought",
            "thought_number": 1,
            "session_id": "test_session",
            "branch_id": "main",
            "metadata": {
                "session_id": "test_session",
                "thought_number": 1,
                "total_thoughts": 1,
                "timestamp": 1234567890,
                "branch_id": "main"
            }
        }
    )
    assert response.status_code == 200
    assert response.json() == mock_response

@pytest.mark.asyncio
async def test_get_session_summary_success(test_client, mock_thinking_handler):
    """Test successful session summary retrieval."""
    mock_response = {
        "session_id": "test_session",
        "thoughts": [
            {"thought": "thought1", "thought_number": 1},
            {"thought": "thought2", "thought_number": 2}
        ]
    }
    mock_thinking_handler.get_thoughts.return_value = mock_response
    response = test_client.get("/thoughts/sessions/test_session")
    assert response.status_code == 200
    assert response.json() == mock_response

def test_internal_server_error(test_client, mock_collection_handler):
    """Test internal server error handling."""
    mock_collection_handler.create_collection.side_effect = Exception("Unexpected error")
    response = test_client.post("/collections?name=test_collection")
    assert response.status_code == 500
    assert response.json()["detail"] == "Unexpected error"

def test_validation_error(test_client, mock_document_handler):
    """Test validation error handling."""
    mock_document_handler.add_documents.side_effect = ValidationError("Invalid input")
    response = test_client.post(
        "/collections/test_collection/documents",
        json={
            "documents": ["doc1"],
            "metadatas": [{"key": "value1"}, {"key": "value2"}]
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid input"
