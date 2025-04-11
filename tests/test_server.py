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
import logging  # Import logging

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

# Import server instance
from chroma_mcp.app import server


# Mock dependencies globally
@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock external dependencies like ChromaDB and FastMCP availability."""
    # Patch within server where they are checked
    with patch("src.chroma_mcp.server.CHROMA_AVAILABLE", True), patch("src.chroma_mcp.server.FASTMCP_AVAILABLE", True):
        yield


# Fixture to reset globals
@pytest.fixture(autouse=True)
def reset_globals():
    setattr(client_utils, "_client", None)
    setattr(client_utils, "_embedding_function", None)
    yield
    setattr(client_utils, "_client", None)
    setattr(client_utils, "_embedding_function", None)


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


# Patch only the components directly used by server.main
@patch("src.chroma_mcp.server.stdio.stdio_server")  # Patch the context manager
@patch("src.chroma_mcp.server.server.run")  # Patch the server.run call
def test_main_calls_mcp_run(
    mock_server_run,  # Capture patched server.run
    mock_stdio_cm,  # Capture patched context manager
):
    # Mock the context manager to return mock streams
    mock_stdio_cm.return_value.__aenter__.return_value = (MagicMock(), MagicMock())
    # Mock server.run (async)
    mock_server_run.return_value = None

    # --- Act ---
    main()  # Call the real server.main

    # --- Assert ---
    # stdio_server context manager should be entered
    mock_stdio_cm.assert_called_once()
    # server.run (from app) should be called
    mock_server_run.assert_called_once()


# Patch only the components directly used by server.main
@patch("src.chroma_mcp.server.stdio.stdio_server")  # Patch the context manager
@patch("src.chroma_mcp.server.server.run")  # Patch the server.run call
def test_main_catches_mcp_run_mcp_error(
    mock_server_run,  # Capture patched server.run
    mock_stdio_cm,  # Capture patched context manager
    caplog,
):
    # Mock the context manager
    mock_stdio_cm.return_value.__aenter__.return_value = (MagicMock(), MagicMock())
    # Simulate server.run raising McpError
    error_message = "MCP specific error"
    mock_server_run.side_effect = McpError(ErrorData(code=INVALID_PARAMS, message=error_message))

    # --- Act & Assert ---
    # Expect server.main() to catch the McpError and re-raise it
    with pytest.raises(McpError) as exc_info:
        main()
    assert error_message in str(exc_info.value)

    # Check logs (server.main logs the error before re-raising)
    assert "MCP Error:" in caplog.text
    assert error_message in caplog.text


# Patch only the components directly used by server.main
@patch("src.chroma_mcp.server.stdio.stdio_server")  # Patch the context manager
@patch("src.chroma_mcp.server.server.run")  # Patch the server.run call
def test_main_catches_mcp_run_unexpected_error(
    mock_server_run,  # Capture patched server.run
    mock_stdio_cm,  # Capture patched context manager
    caplog,
):
    # Mock the context manager
    mock_stdio_cm.return_value.__aenter__.return_value = (MagicMock(), MagicMock())
    # Simulate server.run raising an unexpected error
    error_message = "Something else went wrong"
    mock_server_run.side_effect = Exception(error_message)

    # --- Act & Assert ---
    # Expect server.main() to catch the error, log, and raise McpError
    with pytest.raises(McpError) as exc_info:
        main()

    # Check the raised McpError message
    assert f"Critical error running MCP server: {error_message}" in str(exc_info.value)

    # Check logs (server.main logs the critical error)
    assert "Critical error running MCP server:" in caplog.text
    assert error_message in caplog.text
