"""Tests for src/chroma_mcp/utils/__init__.py"""

import logging
import pytest
import numpy as np
import json
from unittest.mock import patch, MagicMock
import sys

# Import functions and classes to test from the __init__ module
from src.chroma_mcp.utils import (
    set_main_logger,
    set_server_config,
    get_logger,
    get_server_config,
    NumpyEncoder,
    BASE_LOGGER_NAME,
)
from src.chroma_mcp.types import ChromaClientConfig
from mcp.shared.exceptions import McpError

# Import the module containing the globals
import src.chroma_mcp.utils as utils_target_module

# Keep track of original state to restore after tests
original_logger = None
original_config = None


def setup_module(module):
    """Save original global state before tests run."""
    global original_logger, original_config
    # Use internal access for testing setup/teardown on the TARGET module
    original_logger = utils_target_module._main_logger_instance
    original_config = utils_target_module._global_client_config
    # Reset before running tests in this module
    reset_globals()


def teardown_module(module):
    """Restore original global state after tests run."""
    # Use internal access for testing setup/teardown on the TARGET module
    utils_target_module._main_logger_instance = original_logger
    utils_target_module._global_client_config = original_config


def reset_globals():
    """Helper to reset globals before each test needing isolation."""
    # Use internal access for testing setup/teardown
    utils_target_module._main_logger_instance = None
    utils_target_module._global_client_config = None


# --- Tests for Logger ---


def test_set_and_get_main_logger():
    """Test setting and getting the main logger instance."""
    reset_globals()
    mock_logger = MagicMock(spec=logging.Logger)
    set_main_logger(mock_logger)
    retrieved_logger = get_logger()
    assert retrieved_logger is mock_logger


def test_get_child_logger():
    """Test getting a child logger after main logger is set."""
    reset_globals()
    mock_logger = logging.getLogger(f"{BASE_LOGGER_NAME}_test_parent")
    set_main_logger(mock_logger)
    child_name = "child_test"
    child_logger = get_logger(child_name)
    assert child_logger.name == f"{BASE_LOGGER_NAME}.{child_name}"
    # Check it's a child of the base logger, not necessarily the exact instance set
    assert child_logger.parent.name == BASE_LOGGER_NAME


# @patch("logging.StreamHandler") # Remove this patch
def test_get_logger_before_config():  # Already removed mock_stream_handler arg
    """Test getting logger before set_main_logger is called."""
    reset_globals()
    # Ensure the target logger really has no handlers before the test
    fallback_logger_name = f"{BASE_LOGGER_NAME}.unconfigured"
    logging.getLogger(fallback_logger_name).handlers.clear()
    # Also reset propagation if necessary, although unlikely needed here
    # logging.getLogger(fallback_logger_name).propagate = True

    logger = get_logger()  # This should now add the handler

    assert logger.name == fallback_logger_name

    # Check that the logger has exactly one StreamHandler targeting stderr
    assert len(logger.handlers) == 1, f"Expected 1 handler, found {len(logger.handlers)}"
    handler = logger.handlers[0]
    assert isinstance(handler, logging.StreamHandler), f"Expected StreamHandler, got {type(handler)}"
    assert handler.stream == sys.stderr, "Handler stream is not sys.stderr"

    # Clean up handler added by this test to avoid affecting others
    logger.removeHandler(handler)


# --- Tests for Server Config ---


def test_set_and_get_server_config():
    """Test setting and getting the server config."""
    reset_globals()
    mock_config = ChromaClientConfig(client_type="ephemeral")
    set_server_config(mock_config)
    retrieved_config = get_server_config()
    assert retrieved_config is mock_config


def test_get_server_config_before_set():
    """Test getting server config before it's set raises McpError."""
    reset_globals()
    with pytest.raises(McpError) as excinfo:
        get_server_config()
    assert "Server configuration not initialized" in str(excinfo.value)


# --- Tests for NumpyEncoder ---


def test_numpy_encoder_ints():
    """Test NumpyEncoder with various numpy integer types."""
    data = {
        "np_int8": np.int8(1),
        "np_int16": np.int16(2),
        "np_int32": np.int32(3),
        "np_int64": np.int64(4),
        "np_uint8": np.uint8(5),
        "py_int": 6,
    }
    expected_json = '{"np_int8": 1, "np_int16": 2, "np_int32": 3, "np_int64": 4, "np_uint8": 5, "py_int": 6}'
    assert json.dumps(data, cls=NumpyEncoder) == expected_json


def test_numpy_encoder_floats():
    """Test NumpyEncoder with various numpy float types."""
    data = {
        "np_float16": np.float16(1.5),
        "np_float32": np.float32(2.5),
        "np_float64": np.float64(3.5),
        "py_float": 4.5,
    }
    expected_json = '{"np_float16": 1.5, "np_float32": 2.5, "np_float64": 3.5, "py_float": 4.5}'
    assert json.dumps(data, cls=NumpyEncoder) == expected_json


def test_numpy_encoder_ndarray():
    """Test NumpyEncoder with a numpy ndarray."""
    data = {"array": np.array([[1, 2], [3, 4]])}
    expected_json = '{"array": [[1, 2], [3, 4]]}'
    assert json.dumps(data, cls=NumpyEncoder) == expected_json


def test_numpy_encoder_unhandled_type():
    """Test NumpyEncoder falls back to superclass for unhandled types."""

    class Unhandled:
        pass

    data = {"unhandled": Unhandled()}
    with pytest.raises(TypeError):
        json.dumps(data, cls=NumpyEncoder)
