"""Tests for the ChromaMCP server implementation."""

# Standard library imports
import argparse
import importlib.metadata
import os
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, call, patch

# Third-party imports
import pytest
import trio
import sys
import logging # Import logging
# Import McpError and INTERNAL_ERROR from exceptions
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS

# Local application imports
# Import main and config_server from server
from src.chroma_mcp.server import main, config_server
# Keep ValidationError import
from chroma_mcp.utils.errors import ValidationError
# Import the client module itself to reset its globals
from chroma_mcp.utils import client as client_utils
# Import get_logger
from chroma_mcp.utils import get_logger

# Mock dependencies globally
@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock external dependencies like ChromaDB and FastMCP availability."""
    # Patch within server where they are checked
    with patch("src.chroma_mcp.server.CHROMA_AVAILABLE", True), \
         patch("src.chroma_mcp.server.FASTMCP_AVAILABLE", True):
        yield

# Fixture to reset globals
@pytest.fixture(autouse=True)
def reset_globals():
    setattr(client_utils, '_client', None)
    setattr(client_utils, '_embedding_function', None)
    yield
    setattr(client_utils, '_client', None)
    setattr(client_utils, '_embedding_function', None)

@pytest.fixture
def mock_mcp():
    # Mock the instance used in server.py (imported from app.py)
    with patch("src.chroma_mcp.server.mcp", autospec=True) as mock:
        yield mock

@pytest.fixture
def mock_get_logger():
    # Patch logger used within server module
    with patch("src.chroma_mcp.server.logging.getLogger") as mock_get:
        mock_logger = MagicMock()
        mock_get.return_value = mock_logger
        yield mock_logger

# --- Test server.main function --- #

@patch("src.chroma_mcp.server.mcp.run") # Patch mcp.run within server
@patch("sys.stdin") # Patch stdin
def test_main_calls_mcp_run(mock_stdin, mock_mcp_run):
    """Test that main attempts to call mcp.run with stdio."""
    mock_stdin.buffer = BytesIO(b'')
    mock_mcp_run.return_value = None

    main() # Call directly

    mock_mcp_run.assert_called_once_with(transport='stdio')

@patch("src.chroma_mcp.server.mcp.run") # Patch mcp.run within server
@patch("sys.stdin") # Patch stdin
def test_main_catches_mcp_run_mcp_error(mock_stdin, mock_mcp_run):
    """Test main catches McpError raised by the mcp.run call."""
    mock_stdin.buffer = BytesIO(b'')
    error_code = INVALID_PARAMS
    error_message = "Test MCP error message from mcp.run"
    test_error_data = ErrorData(code=error_code, message=error_message)
    mock_mcp_run.side_effect = McpError(test_error_data)

    # main should re-raise the original McpError
    with pytest.raises(McpError) as exc_info:
        main() # Call directly

    mock_mcp_run.assert_called_once_with(transport='stdio')
    assert exc_info.type is McpError
    assert str(error_message) in str(exc_info.value)

@patch("src.chroma_mcp.server.mcp.run") # Patch mcp.run within server
@patch("sys.stdin") # Patch stdin
@patch("sys.exit") # Patch sys.exit
def test_main_catches_mcp_run_unexpected_error(mock_exit, mock_stdin, mock_mcp_run):
    """Test main catches generic Exception raised by the mcp.run call."""
    mock_stdin.buffer = BytesIO(b'')
    unexpected_error_message = "Something unexpected went wrong in mcp.run"
    mock_mcp_run.side_effect = Exception(unexpected_error_message)

    # main should catch Exception, log, and raise a new McpError
    with pytest.raises(McpError) as exc_info:
         main() # Call directly

    mock_mcp_run.assert_called_once_with(transport='stdio')
    assert exc_info.type is McpError
    # Check the wrapped error code and message
    assert f"Critical error running MCP server: {unexpected_error_message}" in str(exc_info.value)
    # Check that main did NOT call sys.exit because it raised McpError instead
    mock_exit.assert_not_called()
