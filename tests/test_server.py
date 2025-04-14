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
import json

# Import McpError and INTERNAL_ERROR from exceptions
from mcp import types  # Add this import
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS

# Local application imports
# Import main and config_server from server
# Change alias for main to avoid potential conflicts
from src.chroma_mcp.server import (
    config_server,
    call_tool,
    TOOL_NAMES,
    INPUT_MODELS,
    IMPL_FUNCTIONS,
    main as run_server_main_func,
)

# Keep ValidationError import
from src.chroma_mcp.utils.errors import ValidationError

# Import the client module itself to reset its globals
from src.chroma_mcp.utils import (
    chroma_client as client_utils,
    get_logger,
    set_main_logger,
    set_server_config,
    BASE_LOGGER_NAME,
)

# Import server instance
from src.chroma_mcp.app import server

# Import types needed for tests
from src.chroma_mcp.types import ChromaClientConfig


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
    run_server_main_func()  # Call the real server.main

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
        run_server_main_func()
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
        run_server_main_func()

    # Check the raised McpError message
    assert f"Critical error running MCP server: {error_message}" in str(exc_info.value)

    # Check logs (server.main logs the critical error)
    assert "Critical error running MCP server:" in caplog.text
    assert error_message in caplog.text


# --- Helper: Create Dummy Args --- #
def create_dummy_args(**kwargs):
    """Creates a dummy argparse.Namespace with defaults."""
    defaults = {
        "dotenv_path": None,
        "log_dir": None,
        "log_level": "INFO",
        "client_type": "ephemeral",
        "data_dir": None,
        "host": None,
        "port": None,
        "ssl": True,
        "tenant": None,
        "database": None,
        "api_key": None,
        "cpu_execution_provider": "auto",
        "embedding_function_name": "default",
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# --- Tests for config_server --- #


@patch("os.path.exists", return_value=False)
@patch("src.chroma_mcp.server.set_main_logger")
@patch("src.chroma_mcp.server.set_server_config")
@patch("logging.getLogger")  # Mock getLogger to control logger behavior
@patch("os.getenv")  # Mock os.getenv
def test_config_server_basic(mock_getenv, mock_get_logger, mock_set_config, mock_set_logger, mock_exists):
    """Test basic server configuration."""
    mock_logger = MagicMock(spec=logging.Logger)
    mock_get_logger.return_value = mock_logger
    # Configure getenv mock to return the desired level for LOG_LEVEL
    mock_getenv.side_effect = lambda key, default=None: "DEBUG" if key == "LOG_LEVEL" else default
    args = create_dummy_args(log_level="DEBUG")  # Args value is actually ignored by config_server for log_level

    # Explicitly reset level on the mock before test
    mock_logger.level = logging.NOTSET  # Or another value != DEBUG/INFO

    config_server(args)

    mock_set_logger.assert_called_once_with(mock_logger)
    mock_logger.setLevel.assert_called_once_with(logging.DEBUG)
    mock_set_config.assert_called_once()
    # Check the created config object
    call_args, _ = mock_set_config.call_args
    config_obj = call_args[0]
    assert isinstance(config_obj, ChromaClientConfig)
    assert config_obj.client_type == "ephemeral"
    assert config_obj.use_cpu_provider is None  # auto
    mock_logger.info.assert_any_call("Server configured (CPU provider: auto-detected)")


@patch("os.makedirs")
@patch("logging.handlers.RotatingFileHandler")
@patch("src.chroma_mcp.server.set_main_logger")
@patch("src.chroma_mcp.server.set_server_config")
@patch("logging.getLogger")
def test_config_server_with_log_file(
    mock_get_logger, mock_set_config, mock_set_logger, mock_file_handler, mock_makedirs
):
    """Test server configuration with log file creation."""
    mock_logger = MagicMock(spec=logging.Logger)
    # Simulate logger not having handlers initially
    mock_logger.hasHandlers.return_value = False
    mock_get_logger.return_value = mock_logger
    log_dir = "/fake/log/dir"
    args = create_dummy_args(log_dir=log_dir)

    config_server(args)

    mock_makedirs.assert_called_once_with(log_dir, exist_ok=True)
    mock_file_handler.assert_called_once_with(
        f"{log_dir}/chroma_mcp_server.log", maxBytes=10 * 1024 * 1024, backupCount=5
    )
    # Check if file handler was added
    mock_logger.addHandler.assert_any_call(mock_file_handler.return_value)
    mock_logger.info.assert_any_call(f"Logs will be saved to: {log_dir}")


@patch("src.chroma_mcp.server.set_server_config")
@patch("logging.getLogger")
def test_config_server_cpu_provider_false(mock_get_logger, mock_set_config):
    """Test server config forces CPU provider off."""
    mock_logger = MagicMock(spec=logging.Logger)
    mock_get_logger.return_value = mock_logger
    args = create_dummy_args(cpu_execution_provider="false")

    config_server(args)

    mock_set_config.assert_called_once()
    call_args, _ = mock_set_config.call_args
    config_obj = call_args[0]
    assert config_obj.use_cpu_provider is False
    mock_logger.info.assert_any_call("Server configured (CPU provider: disabled)")


@patch("src.chroma_mcp.server.load_dotenv", side_effect=Exception("dotenv fail"))
@patch("logging.getLogger")
def test_config_server_dotenv_error(mock_get_logger, mock_load_dotenv, capsys):
    """Test exception during dotenv load is caught and raised as McpError."""
    # NOTE: Removed mock_logger as it won't be configured when error happens early
    # mock_logger = MagicMock(spec=logging.Logger)
    # mock_get_logger.return_value = mock_logger
    args = create_dummy_args(dotenv_path="/path/to/.env")  # Assume exists for this test

    # Need to mock os.path.exists if dotenv_path is set
    with patch("os.path.exists", return_value=True):
        with pytest.raises(McpError) as excinfo:
            config_server(args)

    assert "Failed to configure server: dotenv fail" in str(excinfo.value)
    # Check stderr for the critical error message
    captured = capsys.readouterr()
    assert "CRITICAL CONFIG ERROR: Failed to configure server: dotenv fail" in captured.err
    # mock_logger.critical.assert_called_once_with("Failed to configure server: dotenv fail") # Logger not configured yet


@patch("src.chroma_mcp.server.set_main_logger", side_effect=Exception("logger fail"))
@patch("logging.getLogger")
def test_config_server_logger_error(mock_get_logger, mock_set_main_logger):
    """Test exception during logger setup is caught and raised."""
    # Test case where logger setup itself fails
    args = create_dummy_args()
    with pytest.raises(McpError) as excinfo:
        config_server(args)
    assert "Failed to configure server: logger fail" in str(excinfo.value)
    # print might be called if logger setup fails early


# --- Tests for call_tool --- #


@pytest.mark.asyncio
@patch("importlib.metadata.version", return_value="1.2.3")
async def test_call_tool_get_version_success(mock_version):
    """Test successful call to get_version tool."""
    tool_name = TOOL_NAMES["GET_VERSION"]
    arguments = {}

    result = await call_tool(tool_name, arguments)

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], types.TextContent)
    assert result[0].type == "text"
    expected_data = {"package": "chroma-mcp-server", "version": "1.2.3"}
    assert json.loads(result[0].text) == expected_data
    mock_version.assert_called_once_with("chroma-mcp-server")


@pytest.mark.asyncio
@patch("importlib.metadata.version", side_effect=importlib.metadata.PackageNotFoundError("not found"))
async def test_call_tool_get_version_package_not_found(mock_version):
    """Test get_version tool when package is not found."""
    tool_name = TOOL_NAMES["GET_VERSION"]
    arguments = {}

    with pytest.raises(McpError) as excinfo:
        await call_tool(tool_name, arguments)

    # Check the string representation of the exception
    assert "Tool Error: chroma-mcp-server package not found." in str(excinfo.value)


@pytest.mark.asyncio
async def test_call_tool_unknown_tool():
    """Test calling an unknown tool name."""
    tool_name = "non_existent_tool"
    arguments = {"arg1": "val1"}

    with pytest.raises(McpError) as excinfo:
        await call_tool(tool_name, arguments)

    # Check the string representation of the exception
    assert f"Tool Error: Unknown tool name '{tool_name}'" in str(excinfo.value)


@pytest.mark.asyncio
async def test_call_tool_validation_error():
    """Test call_tool raising McpError on Pydantic validation failure."""
    # Use a tool that has required arguments, like create_collection
    tool_name = TOOL_NAMES["CREATE_COLLECTION"]
    arguments = {}  # Missing required 'collection_name'

    with pytest.raises(McpError) as excinfo:
        await call_tool(tool_name, arguments)

    # Check the string representation of the exception
    assert "Input Error:" in str(excinfo.value)
    assert "Field required" in str(excinfo.value)  # Pydantic detail should be included


# --- Tests for server_main --- #


@patch("src.chroma_mcp.server.get_logger")
@patch("importlib.metadata.version", return_value="1.2.3")
@patch("src.chroma_mcp.server.stdio.stdio_server")
@patch("src.chroma_mcp.server.server.run")  # Mock the server run loop
@patch("asyncio.run")  # Mock asyncio.run
def test_server_main_success(mock_async_run, mock_mcp_run, mock_stdio, mock_version, mock_get_logger):
    """Test successful run of server_main."""
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    # Mock the async context manager
    mock_stdio.return_value.__aenter__.return_value = (MagicMock(), MagicMock())

    run_server_main_func()

    mock_logger.info.assert_any_call("Chroma MCP server v1.2.3 started. Using stdio transport.")
    mock_async_run.assert_called_once()  # Check that asyncio.run was called
    # Further checks could involve asserting calls within the nested async def run_server
    # For simplicity, we check the top-level asyncio.run call


@patch("src.chroma_mcp.server.get_logger")
@patch("src.chroma_mcp.server.server.run", side_effect=McpError(ErrorData(code=INTERNAL_ERROR, message="Run failed")))
@patch("asyncio.run")
def test_server_main_mcp_error(mock_async_run, mock_mcp_run, mock_get_logger):
    """Test server_main catches and logs McpError."""
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger

    # Mock asyncio.run to simulate the inner function raising the error AFTER run_server_main_func calls asyncio.run
    mock_async_run.side_effect = mock_mcp_run.side_effect  # Make asyncio.run raise the error

    # Need to mock stdio_server as well if server.run is called within its context
    with patch("src.chroma_mcp.server.stdio.stdio_server") as mock_stdio:
        mock_stdio.return_value.__aenter__.return_value = (MagicMock(), MagicMock())
        with pytest.raises(McpError) as excinfo:  # server_main should re-raise
            run_server_main_func()

    # Check the string representation of the exception
    assert "Run failed" in str(excinfo.value)
    mock_logger.error.assert_any_call("MCP Error: Run failed")


@patch("src.chroma_mcp.server.get_logger")
@patch("src.chroma_mcp.server.server.run", side_effect=Exception("Unexpected crash"))
@patch("asyncio.run")
def test_server_main_unexpected_exception(mock_async_run, mock_mcp_run, mock_get_logger):
    """Test server_main catches and wraps unexpected exceptions."""
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger

    # Mock asyncio.run to simulate the inner function raising the error
    mock_async_run.side_effect = mock_mcp_run.side_effect  # Make asyncio.run raise the error

    with patch("src.chroma_mcp.server.stdio.stdio_server") as mock_stdio:
        mock_stdio.return_value.__aenter__.return_value = (MagicMock(), MagicMock())
        with pytest.raises(McpError) as excinfo:
            run_server_main_func()

    # Check the string representation of the exception
    assert "Critical error running MCP server: Unexpected crash" in str(excinfo.value)
    mock_logger.error.assert_called_once_with("Critical error running MCP server: Unexpected crash")


# --- Tests for config_server --- #


@patch("os.path.exists", return_value=False)
@patch("src.chroma_mcp.server.set_main_logger")
@patch("src.chroma_mcp.server.set_server_config")
@patch("logging.getLogger")  # Mock getLogger to control logger behavior
@patch("os.getenv")  # Mock os.getenv
def test_config_server_success(mock_getenv, mock_get_logger, mock_set_config, mock_set_logger, mock_exists):
    """Test successful server configuration."""
    mock_logger = MagicMock(spec=logging.Logger)
    mock_get_logger.return_value = mock_logger
    # Configure getenv mock to return the desired level for LOG_LEVEL
    mock_getenv.side_effect = lambda key, default=None: "DEBUG" if key == "LOG_LEVEL" else default
    mock_args = create_dummy_args(
        log_level="DEBUG",
        client_type="persistent",
        data_dir="/test/data",
        cpu_execution_provider="false",
        embedding_function_name="test-ef",
    )

    # Explicitly reset level on the mock before test
    mock_logger.level = logging.NOTSET  # Or another value != DEBUG/INFO

    # Call config_server with mocked args
    config_server(mock_args)

    # Assert set_main_logger was called
    mock_set_logger.assert_called_once()
    # Assert set_server_config was called with a ChromaClientConfig instance
    mock_set_config.assert_called_once()
    call_args, call_kwargs = mock_set_config.call_args
    assert isinstance(call_args[0], ChromaClientConfig)
    # Assert specific values passed to ChromaClientConfig
    config_instance = call_args[0]
    assert config_instance.client_type == "persistent"
    assert config_instance.data_dir == "/test/data"
    assert config_instance.use_cpu_provider is False  # Based on mock_args
    assert config_instance.embedding_function_name == "test-ef"  # Check new arg

    # Assert logger configuration messages
    mock_logger.info.assert_any_call("Server configured (CPU provider: disabled)")
