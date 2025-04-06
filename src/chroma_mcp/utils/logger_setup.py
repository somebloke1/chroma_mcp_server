"""
Logging utility for standardized log setup across all agents
"""
import os
import logging
import re
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional, List, Dict, Any


def get_logs_dir(custom_log_dir: Optional[str] = None) -> str:
    """
    Get the path to the centralized logs directory.
    
    Args:
        custom_log_dir: Optional custom directory to use for logs
        
    Returns:
        str: Path to the logs directory
    """
    # If a custom log directory is provided, use it
    if custom_log_dir:
        logs_dir = custom_log_dir
        # Create the logs directory if it doesn't exist
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir, exist_ok=True)
        return logs_dir
    
    # First check if we're running in a Docker container by checking PYTHONPATH or /.dockerenv
    if os.environ.get('PYTHONPATH') == '/app' or os.path.exists('/.dockerenv'):
        logs_dir = '/app/logs'
        # Create the logs directory if it doesn't exist
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir, exist_ok=True)
        return logs_dir
    
    # When running locally, use the path relative to this file
    current_dir = os.path.dirname(os.path.abspath(__file__))  # utils directory
    chroma_mcp_dir = os.path.dirname(current_dir)  # chroma_mcp directory
    src_dir = os.path.dirname(chroma_mcp_dir)  # src directory
    chroma_mcp_server_dir = os.path.dirname(src_dir)  # chroma_mcp_server directory
    logs_dir = os.path.join(chroma_mcp_server_dir, "logs")
    
    # Create the logs directory if it doesn't exist
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir, exist_ok=True)
        
    return logs_dir


class MessageFlowFormatter(logging.Formatter):
    """
    Custom formatter that recognizes message flow patterns and formats them accordingly
    """
    
    # Regex to detect "Sender => Receiver | Message" pattern
    flow_pattern = re.compile(r"^([^=\s>]+)\s*=>\s*([^|\s]+)\s*\|\s*(.*)", re.DOTALL)
    # Regex to detect test summary lines
    test_summary_pattern = re.compile(r"^===.*===$") # Matches lines starting and ending with ===
    
    # Add pattern to detect already formatted messages (approximated)
    # Looks for a timestamp pattern preceded by a pipe
    already_formatted_pattern = re.compile(r"\| \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} \|")
    
    def __init__(self, agent_name: str, session_id: Optional[str] = None, 
                 preserve_newlines: bool = True, preserve_test_format: bool = False):
        """
        Initialize the formatter with the agent name
        
        Args:
            agent_name: Name of the agent (used when no flow information is in the message)
            session_id: Optional unique session ID to include in log messages
            preserve_newlines: Whether to preserve newlines in the original message
            preserve_test_format: Whether to skip formatting for test summary lines
        """
        self.agent_name = agent_name
        self.session_id = session_id
        self.preserve_newlines = preserve_newlines
        self.preserve_test_format = preserve_test_format
        # Basic format string used for timestamping
        super().__init__(fmt='%(asctime)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record according to message flow patterns
        
        Args:
            record: The log record to format
            
        Returns:
            Formatted log string
        """
        message = record.getMessage()

        # FIX: Check for already formatted messages FIRST
        if self.already_formatted_pattern.search(message):
            return message # Return as-is if it looks formatted

        # FIX: Now check for test summary preservation
        if self.preserve_test_format and self.test_summary_pattern.match(message):
            return message
        
        # Use default Formatter logic to handle timestamp AFTER checks
        s = super().format(record)

        match = self.flow_pattern.match(message)
        if match:
            sender, receiver, content = match.groups()
            log_prefix = f"{receiver} | {s},{int(record.msecs):03d}"
            if self.session_id:
                log_prefix += f" | {self.session_id}"
            log_prefix += f" | {sender} => {receiver}"
        else:
            content = message
            log_prefix = f"{self.agent_name} | {s},{int(record.msecs):03d}"
            if self.session_id:
                log_prefix += f" | {self.session_id}"

        lines = content.strip().split('\n')
        first_line = lines[0]
        formatted_message = f"{log_prefix} | {first_line}"

        if len(lines) > 1 and self.preserve_newlines:
            formatted_message += '\n' + '\n'.join(lines[1:])

        return formatted_message


class LoggerSetup:
    """
    Utility class for standardized logging setup across all agents
    """
    
    # Keep the old format for backward compatibility
    LEGACY_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DEFAULT_LOG_LEVEL = "INFO"
    
    # Store active loggers for management
    _active_loggers: Dict[str, logging.Logger] = {}
    
    @classmethod
    def create_logger(cls, name: str, log_file: Optional[str] = None, agent_name: Optional[str] = None, 
                     log_level: Optional[str] = None, session_id: Optional[str] = None,
                     use_rotating_file: bool = True, append_mode: bool = True,
                     preserve_test_format: bool = False, log_dir: Optional[str] = None) -> logging.Logger:
        """
        Creates and configures a logger with the given name
        
        Args:
            name: Name of the logger
            log_file: Optional file path for file logging. If just a filename is provided, it will be created in the centralized logs directory
            agent_name: Optional agent name for message flow formatting (defaults to name)
            log_level: Optional log level (defaults to environment variable or INFO)
            session_id: Optional unique session ID to include in all log messages
            use_rotating_file: Whether to use RotatingFileHandler (True) or simple FileHandler (False)
            append_mode: Whether to append to existing log file (True) or overwrite (False)
            preserve_test_format: Whether to preserve exact format of test-related messages
            log_dir: Optional custom directory to use for logs (overrides default)
            
        Returns:
            Configured logger instance
        """
        # Get log level from parameter, environment, or use default
        log_level_str = log_level or os.getenv("LOG_LEVEL", cls.DEFAULT_LOG_LEVEL)
        log_level_str = log_level_str.upper()
        log_level_num = getattr(logging, log_level_str, logging.INFO)
        
        # Use agent_name if provided, otherwise use the logger name
        actual_agent_name = agent_name or name.lower().replace("agent", "_agent")
        
        # Create or get existing logger
        logger = logging.getLogger(name)
        logger.setLevel(log_level_num)
        
        # Disable propagation to root logger to prevent duplicate logs
        logger.propagate = False
        
        # Clear existing handlers to avoid duplicates
        if logger.handlers:
            # Properly close file handlers before clearing
            for handler in logger.handlers:
                # Force flush before closing
                handler.flush()
                # Close the handler, which will close any files
                handler.close()
            logger.handlers.clear()
        
        # Create custom formatter
        message_flow_formatter = MessageFlowFormatter(
            actual_agent_name,
            session_id=session_id,
            preserve_test_format=preserve_test_format
        )
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level_num)
        console_handler.setFormatter(message_flow_formatter)
        logger.addHandler(console_handler)
        
        # Create file handler if log_file is provided
        if log_file:
            is_absolute = os.path.isabs(log_file)
            if is_absolute:
                log_file_path = log_file
                log_dir_path = os.path.dirname(log_file_path)
            elif not os.path.dirname(log_file):
                logs_dir = get_logs_dir(custom_log_dir=log_dir)
                log_file_path = os.path.join(logs_dir, log_file)
                log_dir_path = logs_dir
            else:
                logs_dir = get_logs_dir(custom_log_dir=log_dir)
                log_file_path = os.path.join(logs_dir, log_file)
                log_dir_path = os.path.dirname(log_file_path)

            # Ensure the target directory exists
            if log_dir_path and not os.path.exists(log_dir_path):
                os.makedirs(log_dir_path, exist_ok=True)
            
            logger.debug(f"Logging to file: {log_file_path}")
            
            file_mode = 'a' if append_mode else 'w'
            if use_rotating_file:
                file_handler = RotatingFileHandler(
                    log_file_path,
                    maxBytes=10*1024*1024, 
                    backupCount=5,
                    mode=file_mode
                )
            else:
                file_handler = logging.FileHandler(
                    log_file_path,
                    mode=file_mode
                )
                
            file_handler.setLevel(log_level_num)
            file_handler.setFormatter(message_flow_formatter)
            logger.addHandler(file_handler)
        
        # Store the logger in active loggers dictionary
        cls._active_loggers[name] = logger
        
        return logger
    
    @classmethod
    def flush_all_loggers(cls) -> None:
        """
        Flush all active loggers to ensure their output is written
        """
        for logger_name, logger in cls._active_loggers.items():
            for handler in logger.handlers:
                handler.flush()
    
    @classmethod
    def flush_logger(cls, name: str) -> bool:
        """
        Flush a specific logger by name
        
        Args:
            name: Name of the logger to flush
            
        Returns:
            True if logger was found and flushed, False otherwise
        """
        if name in cls._active_loggers:
            logger = cls._active_loggers[name]
            for handler in logger.handlers:
                handler.flush()
            return True
        return False
    
    @classmethod
    def write_test_summary(cls, logger: logging.Logger, summary: Dict[str, Any]) -> None:
        """
        Write test summary in a format that log_analyzer.py can understand
        
        Args:
            logger: The logger to use
            summary: Dictionary with test summary information
        """
        # Flush any pending logs
        for handler in logger.handlers:
            handler.flush()
        
        # Log summary in a format compatible with log_analyzer.py
        logger.info("=" * 15 + " test session starts " + "=" * 15)
        
        # Log test result counts
        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        skipped = summary.get('skipped', 0)
        duration = summary.get('duration', 0)
        
        logger.info(f"{passed} passed, {failed} failed, {skipped} skipped in {duration:.2f}s")
        logger.info(f"Test Summary: {passed} passed, {failed} failed, {skipped} skipped")
        logger.info(f"Status: {'PASSED' if failed == 0 else 'FAILED'}")
        logger.info(f"Duration: {duration:.2f} seconds")
        
        # Log failed tests if any
        if 'failed_tests' in summary and summary['failed_tests']:
            logger.info("Failed tests by module:")
            for module, tests in summary.get('failed_modules', {}).items():
                logger.info(f"Module: {module} - {len(tests)} failed tests")
                for test in tests:
                    logger.info(f"- {test}")
        
        logger.info("=" * 50)
        
        # Ensure everything is written
        for handler in logger.handlers:
            handler.flush()


def setup_logger(agent_name: str, log_level: str = "INFO", session_id: Optional[str] = None, 
                log_file: Optional[str] = None, use_rotating_file: bool = True) -> logging.Logger:
    """
    Set up a logger with the given name and log level
    
    Args:
        agent_name: Name of the agent
        log_level: Log level (default: INFO)
        session_id: Optional unique session ID to include in all log messages
        log_file: Optional file path for logging
        use_rotating_file: Whether to use rotating file handler (default: True)
        
    Returns:
        Configured logger
    """
    # Use the LoggerSetup class for consistent logging setup
    return LoggerSetup.create_logger(
        agent_name, 
        log_file=log_file,
        agent_name=agent_name, 
        log_level=log_level, 
        session_id=session_id,
        use_rotating_file=use_rotating_file
    ) 