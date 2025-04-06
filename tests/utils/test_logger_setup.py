"""Tests for the logging setup utility."""

import pytest
import os
import logging
import re
from unittest.mock import patch, mock_open, MagicMock, PropertyMock
from logging.handlers import RotatingFileHandler # Ensure this is imported

# Import the components to test
from src.chroma_mcp.utils.logger_setup import get_logs_dir, LoggerSetup, MessageFlowFormatter

# --- Tests for get_logs_dir --- 

@patch('os.makedirs')
@patch('os.path.exists')
def test_get_logs_dir_custom_dir(mock_exists, mock_makedirs):
    """Test get_logs_dir with a custom directory path."""
    custom_dir = "/tmp/my_custom_logs"
    mock_exists.return_value = False # Simulate dir doesn't exist initially
    
    logs_path = get_logs_dir(custom_log_dir=custom_dir)
    
    assert logs_path == custom_dir
    mock_exists.assert_called_once_with(custom_dir)
    mock_makedirs.assert_called_once_with(custom_dir, exist_ok=True)

@patch('os.makedirs')
@patch('os.path.exists')
def test_get_logs_dir_docker_env_path(mock_exists, mock_makedirs):
    """Test get_logs_dir when running in 'Docker' (via PYTHONPATH)."""
    expected_docker_logs = '/app/logs'
    mock_exists.return_value = True # Simulate /.dockerenv doesn't exist, but /app/logs does
    # Patch environment variable
    with patch.dict(os.environ, {'PYTHONPATH': '/app'}, clear=True):
        logs_path = get_logs_dir()
        assert logs_path == expected_docker_logs
    # Check os.path.exists was called for /.dockerenv and then /app/logs
    # assert mock_exists.call_count == 2 # This check might be fragile
    # mock_makedirs should not be called if dir exists
    mock_makedirs.assert_not_called()

@patch('os.makedirs')
@patch('os.path.exists', return_value=True) # Mock /.dockerenv exists
def test_get_logs_dir_docker_env_file(mock_exists, mock_makedirs):
    """Test get_logs_dir when running in 'Docker' (via /.dockerenv)."""
    expected_docker_logs = '/app/logs'
    # Patch environment variable to be empty
    with patch.dict(os.environ, {}, clear=True):
        logs_path = get_logs_dir()
        assert logs_path == expected_docker_logs
    mock_exists.assert_any_call('/.dockerenv')
    # mock_makedirs should be called if /.dockerenv exists but /app/logs doesn't
    # To test this, we might need more complex mocking of os.path.exists side_effect
    # For now, assuming /app/logs exists based on return_value=True
    mock_makedirs.assert_not_called()

@patch('os.makedirs')
@patch('os.path.exists')
def test_get_logs_dir_local_fallback(mock_exists, mock_makedirs):
    """Test get_logs_dir falling back to local relative path."""
    # Simulate not being in Docker
    mock_exists.side_effect = lambda p: p == '/.dockerenv' and False # Only /.dockerenv doesn't exist
    
    with patch.dict(os.environ, {}, clear=True):
        logs_path = get_logs_dir()
        # Expect path relative to project root (assuming standard structure)
        assert logs_path.endswith('/logs') 
        assert os.path.isabs(logs_path)
        # Check makedirs was called for the final path
        mock_makedirs.assert_called_with(logs_path, exist_ok=True)

# --- Tests for MessageFlowFormatter ---

@pytest.fixture
def formatter_no_session():
    return MessageFlowFormatter(agent_name="TestAgent")

@pytest.fixture
def formatter_with_session():
    return MessageFlowFormatter(agent_name="TestAgent", session_id="sess123")

@pytest.fixture
def log_record_flow():
    record = logging.LogRecord(
        name='test', level=logging.INFO, pathname='', lineno=0,
        msg="Sender => Receiver | Flow message content", args=(), exc_info=None
    )
    record.created = 1678886400 # Fixed time for consistent timestamp
    record.msecs = 123
    return record

@pytest.fixture
def log_record_standard():
    record = logging.LogRecord(
        name='test', level=logging.INFO, pathname='', lineno=0,
        msg="Standard log message", args=(), exc_info=None
    )
    record.created = 1678886400
    record.msecs = 123
    return record

@pytest.fixture
def log_record_multiline():
    record = logging.LogRecord(
        name='test', level=logging.WARNING, pathname='', lineno=0,
        msg="First line\nSecond line\nThird line", args=(), exc_info=None
    )
    record.created = 1678886400
    record.msecs = 123
    return record

def test_formatter_flow_message(formatter_no_session, log_record_flow):
    """Test formatting a message matching the flow pattern."""
    formatted = formatter_no_session.format(log_record_flow)
    # FIX: Update regex to match the fixed format
    assert re.match(r"Receiver \| \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} \| Sender => Receiver \| Flow message content", formatted)

def test_formatter_flow_message_with_session(formatter_with_session, log_record_flow):
    """Test formatting a flow message with a session ID."""
    formatted = formatter_with_session.format(log_record_flow)
    # FIX: Update regex to match the fixed format
    assert re.match(r"Receiver \| \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} \| sess123 \| Sender => Receiver \| Flow message content", formatted)

def test_formatter_standard_message(formatter_no_session, log_record_standard):
    """Test formatting a standard message."""
    formatted = formatter_no_session.format(log_record_standard)
    assert re.match(r"TestAgent \| \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} \| Standard log message", formatted)

def test_formatter_standard_message_with_session(formatter_with_session, log_record_standard):
    """Test formatting a standard message with a session ID."""
    formatted = formatter_with_session.format(log_record_standard)
    assert re.match(r"TestAgent \| \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} \| sess123 \| Standard log message", formatted)

def test_formatter_multiline_message(formatter_with_session, log_record_multiline):
    """Test formatting a multiline message."""
    formatted = formatter_with_session.format(log_record_multiline)
    lines = formatted.split('\n')
    assert len(lines) == 3
    assert re.match(r"TestAgent \| \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} \| sess123 \| First line", lines[0])
    assert lines[1] == "Second line"
    assert lines[2] == "Third line"

def test_formatter_preserves_test_summary(formatter_no_session):
    """Test that test summary messages are preserved."""
    # FIX: Create a formatter specifically for this test case
    formatter_preserve = MessageFlowFormatter(agent_name="TestAgent", preserve_test_format=True)
    record1 = logging.LogRecord(name='test', level=logging.INFO, msg="=== Test Summary: PASSED ===", args=(), pathname='', lineno=0, exc_info=None)
    record2 = logging.LogRecord(name='test', level=logging.INFO, msg="Some other === line", args=(), pathname='', lineno=0, exc_info=None)
    # Use the specific formatter instance
    assert formatter_preserve.format(record1) == "=== Test Summary: PASSED ==="
    # Ensure non-summary lines are still formatted by this formatter
    formatted_other = formatter_preserve.format(record2)
    assert re.match(r"TestAgent \| \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} \| Some other === line", formatted_other)

def test_formatter_avoids_recursive_formatting(formatter_no_session, log_record_standard):
    """Test that already formatted messages are not reformatted."""
    # Format once
    formatted_once = formatter_no_session.format(log_record_standard)
    # Create a new record with the already formatted message
    record_already_formatted = logging.LogRecord(
        name='test', level=logging.INFO, pathname='', lineno=0,
        msg=formatted_once, args=(), exc_info=None
    )
    record_already_formatted.created = 1678886401 # Different time to ensure format isn't just cached
    record_already_formatted.msecs = 456
    # Format again
    formatted_twice = formatter_no_session.format(record_already_formatted)
    # Should be identical to the first formatting
    assert formatted_twice == formatted_once

# --- Tests for LoggerSetup.create_logger ---

# Use pytest.mark.usefixtures("clean_loggers") to ensure clean state 
# Needs a fixture defined in conftest.py or this file:
@pytest.fixture(autouse=True)
def clean_loggers():
    """Fixture to reset logging state before/after tests."""
    # Before test: Clear handlers from any previously configured loggers
    for name, logger in logging.Logger.manager.loggerDict.items():
        if isinstance(logger, logging.Logger):
             logger.handlers.clear()
             logger.propagate = True # Reset propagate
    # Reset root logger handlers as well
    logging.getLogger().handlers.clear()
    LoggerSetup._active_loggers.clear()
    yield # Run the test
    # After test: Cleanup (optional, depends on desired isolation)
    for name, logger in logging.Logger.manager.loggerDict.items():
        if isinstance(logger, logging.Logger):
             logger.handlers.clear()
             logger.propagate = True
    logging.getLogger().handlers.clear()
    LoggerSetup._active_loggers.clear()

@patch('src.chroma_mcp.utils.logger_setup.get_logs_dir')
# FIX: Remove handler mocks, keep only _open mock implicitly via later tests or add here if needed
def test_create_logger_console_only(mock_get_dir):
    """Test creating a logger with only console output."""
    logger = LoggerSetup.create_logger("TestConsole", log_level="DEBUG")
    
    assert logger.name == "TestConsole"
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert isinstance(logger.handlers[0].formatter, MessageFlowFormatter)
    assert logger.handlers[0].formatter.agent_name == "testconsole"
    mock_get_dir.assert_not_called()

@patch('src.chroma_mcp.utils.logger_setup.get_logs_dir')
@patch('logging.FileHandler._open') # Keep _open patch
def test_create_logger_rotating_file(mock_open_method, mock_get_dir):
    """Test creating a logger with a rotating file handler."""
    log_filename = "rotate.log"
    logs_path = "/tmp/testlogs"
    mock_get_dir.return_value = logs_path
    expected_path = os.path.join(logs_path, log_filename)
    
    logger = LoggerSetup.create_logger("TestRotate", log_file=log_filename, log_level="INFO", session_id="sess_rot")
    
    assert len(logger.handlers) == 2 # Console + File
    mock_get_dir.assert_called_once_with(custom_log_dir=None)
    mock_open_method.assert_called() # Ensure _open was called (by the handler init)

    # FIX: Find the actual file handler and check its properties
    file_handler = next((h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)), None)
    assert file_handler is not None 
    assert file_handler.baseFilename == expected_path
    assert file_handler.maxBytes == 10485760
    assert file_handler.backupCount == 5 # Default changed to 5
    assert file_handler.mode == 'a'
    assert isinstance(file_handler.formatter, MessageFlowFormatter)
    assert file_handler.formatter.session_id == "sess_rot"
    assert file_handler.level == logging.INFO

@patch('src.chroma_mcp.utils.logger_setup.get_logs_dir')
# FIX: Reinstate _open patch
@patch('logging.FileHandler._open') 
def test_create_logger_simple_file_overwrite(mock_open_method, mock_get_dir):
    """Test creating a logger with a simple file handler in overwrite mode."""
    log_filename = "simple.log"
    logs_path = "/tmp/testlogs2"
    mock_get_dir.return_value = logs_path
    expected_path = os.path.join(logs_path, log_filename)
    
    with patch('os.makedirs') as mock_make_simple:
        logger = LoggerSetup.create_logger(
            "TestSimple", 
            log_file=log_filename, 
            log_level="WARNING", 
            use_rotating_file=False, # Use simple FileHandler
            append_mode=False # Overwrite mode
        )
    
    assert len(logger.handlers) == 2
    mock_get_dir.assert_called_once_with(custom_log_dir=None)
    # Assert _open was called by the handler init
    mock_open_method.assert_called()

    # FIX: Access handler directly and assert type/properties
    assert len(logger.handlers) == 2
    file_handler = logger.handlers[1] # Assume file handler is the second one
    assert isinstance(file_handler, logging.FileHandler)
    assert not isinstance(file_handler, logging.handlers.RotatingFileHandler)
    assert file_handler.baseFilename == expected_path
    assert file_handler.mode == 'w' # Check mode 'w'
    assert isinstance(file_handler.formatter, MessageFlowFormatter)
    assert file_handler.level == logging.WARNING

# Add patch for os.makedirs
@patch('os.makedirs') 
# Add patch for os.path.exists
@patch('os.path.exists') 
@patch('src.chroma_mcp.utils.logger_setup.get_logs_dir')
# FIX: Reinstate _open patch
@patch('logging.FileHandler._open') 
def test_create_logger_absolute_path(mock_open_method, mock_get_dir, mock_path_exists, mock_makedirs):
    """Test creating logger with an absolute log file path."""
    abs_path = "/var/log/myapp.log"
    abs_dir = os.path.dirname(abs_path)
    mock_path_exists.side_effect = lambda p: p != abs_dir
    
    logger = LoggerSetup.create_logger("TestAbsPath", log_file=abs_path, use_rotating_file=False)
    
    mock_open_method.assert_called()
    mock_makedirs.assert_called_with(abs_dir, exist_ok=True)
    mock_path_exists.assert_called_with(abs_dir)

    # FIX: Access handler directly and assert type/properties
    assert len(logger.handlers) == 2
    file_handler = logger.handlers[1] # Assume file handler is the second one
    assert isinstance(file_handler, logging.FileHandler)
    assert not isinstance(file_handler, logging.handlers.RotatingFileHandler)
    assert file_handler.baseFilename == abs_path
    assert file_handler.mode == 'a'

# Add patch for os.makedirs
@patch('os.makedirs') 
@patch('src.chroma_mcp.utils.logger_setup.get_logs_dir')
# FIX: Reinstate _open patch
@patch('logging.FileHandler._open') 
def test_create_logger_custom_log_dir(mock_open_method, mock_get_dir, mock_makedirs):
    """Test providing a custom log directory."""
    custom_dir = "/data/applogs"
    log_filename = "app.log"
    mock_get_dir.return_value = custom_dir
    expected_path = os.path.join(custom_dir, log_filename)

    # Patch os.path.exists locally for this test to ensure makedirs is called
    with patch('os.path.exists') as mock_custom_exists:
        mock_custom_exists.side_effect = lambda p: p != custom_dir
        logger = LoggerSetup.create_logger(
            "TestCustomDir", 
            log_file=log_filename, 
            log_dir=custom_dir, 
            use_rotating_file=False
        )

    mock_get_dir.assert_called_once_with(custom_log_dir=custom_dir)
    mock_open_method.assert_called()
    mock_makedirs.assert_called_with(custom_dir, exist_ok=True)

    # FIX: Access handler directly and assert type/properties
    assert len(logger.handlers) == 2
    file_handler = logger.handlers[1] # Assume file handler is the second one
    assert isinstance(file_handler, logging.FileHandler)
    assert not isinstance(file_handler, logging.handlers.RotatingFileHandler)
    assert file_handler.baseFilename == expected_path
    assert file_handler.mode == 'a'

@patch('src.chroma_mcp.utils.logger_setup.get_logs_dir')
def test_create_logger_env_level(mock_get_dir):
    """Test setting log level via environment variable."""
    with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}, clear=True):
        logger = LoggerSetup.create_logger("TestEnvLevel")
        assert logger.level == logging.DEBUG
        # Check handlers also got the level
        for handler in logger.handlers:
            assert handler.level == logging.DEBUG

def test_create_logger_preserves_test_format():
    """Test that preserve_test_format uses the simple formatter."""
    logger = LoggerSetup.create_logger("TestFormat", preserve_test_format=True)
    # Check formatter on console handler (assuming it's the first handler)
    console_handler = logger.handlers[0]

    # Check that test summary lines are returned *exactly* as they are
    assert console_handler.formatter.format(
        logging.LogRecord(name='test', level=logging.INFO, msg="=== TEST MSG ===", args=(), pathname='', lineno=0, exc_info=None)
    ) == "=== TEST MSG ==="

    # Ensure non-test messages still get formatted by the MessageFlowFormatter
    record_standard = logging.LogRecord(name='test', level=logging.INFO, msg="Standard Message", args=(), pathname='', lineno=0, exc_info=None)
    # FIX: Expect standard message to be formatted now
    formatted_standard = console_handler.formatter.format(record_standard)
    assert re.match(r"testformat \| \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} \| Standard Message", formatted_standard) 