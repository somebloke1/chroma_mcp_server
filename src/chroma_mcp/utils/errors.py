"""
Error handling utility module for standardized error management.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass

from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS

from .logger_setup import LoggerSetup

# Initialize logger
logger = LoggerSetup.create_logger(
    "ChromaErrors",
    log_file="chroma_errors.log"
)

class ValidationError(Exception):
    """Raised when input validation fails."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class CollectionNotFoundError(Exception):
    """Raised when a collection is not found."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class DocumentNotFoundError(Exception):
    """Raised when a document is not found."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class EmbeddingError(Exception):
    """Raised when there is an error with embeddings."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class ClientError(Exception):
    """Raised when there is an error with the ChromaDB client."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class ConfigurationError(Exception):
    """Raised when there is an error with the configuration."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

@dataclass
class ChromaError:
    """Standardized error structure for Chroma operations."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

# Error codes
COLLECTION_NOT_FOUND = "COLLECTION_NOT_FOUND"
INVALID_COLLECTION_NAME = "INVALID_COLLECTION_NAME"
DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
INVALID_DOCUMENT_FORMAT = "INVALID_DOCUMENT_FORMAT"
EMBEDDING_ERROR = "EMBEDDING_ERROR"
CLIENT_ERROR = "CLIENT_ERROR"
CONFIGURATION_ERROR = "CONFIGURATION_ERROR"

def handle_chroma_error(error: Exception, operation: str) -> McpError:
    """
    Convert ChromaDB exceptions to standardized MCP errors.
    
    Args:
        error: The original exception
        operation: Description of the operation that failed
        
    Returns:
        McpError instance with standardized error information
    """
    # Map ChromaDB exceptions to our error codes
    if "Collection not found" in str(error):
        code = COLLECTION_NOT_FOUND
    elif "Invalid collection name" in str(error):
        code = INVALID_COLLECTION_NAME
    elif "Document not found" in str(error):
        code = DOCUMENT_NOT_FOUND
    elif "Invalid document format" in str(error):
        code = INVALID_DOCUMENT_FORMAT
    elif "Embedding failed" in str(error):
        code = EMBEDDING_ERROR
    elif any(x in str(error).lower() for x in ["connection", "timeout", "network"]):
        code = CLIENT_ERROR
    else:
        code = INTERNAL_ERROR
    
    # Log the error
    logger.error(f"ChromaDB error during {operation}: {str(error)}")
    logger.error(f"Error code: {code}")
    
    # Create standardized error
    chroma_error = ChromaError(
        code=code,
        message=f"ChromaDB operation failed: {str(error)}",
        details={
            "operation": operation,
            "original_error": str(error),
            "error_type": error.__class__.__name__
        }
    )
    
    # Convert to MCP error
    return McpError(ErrorData(
        code=INTERNAL_ERROR if code == INTERNAL_ERROR else INVALID_PARAMS,
        message=chroma_error.message,
        data=chroma_error.details
    ))

def validate_input(
    value: Any,
    name: str,
    required: bool = True,
    max_length: Optional[int] = None,
    min_length: Optional[int] = None,
    pattern: Optional[str] = None
) -> Optional[str]:
    """
    Validate input parameters.
    
    Args:
        value: Value to validate
        name: Name of the parameter
        required: Whether the parameter is required
        max_length: Maximum length for string values
        min_length: Minimum length for string values
        pattern: Regex pattern for string validation
        
    Returns:
        Error message if validation fails, None otherwise
    """
    # Check required
    if required and value is None:
        return f"{name} is required"
    
    # Skip further validation if value is None and not required
    if value is None:
        return None
    
    # String validations
    if isinstance(value, str):
        if max_length and len(value) > max_length:
            return f"{name} exceeds maximum length of {max_length}"
        
        if min_length and len(value) < min_length:
            return f"{name} is shorter than minimum length of {min_length}"
        
        if pattern:
            import re
            if not re.match(pattern, value):
                return f"{name} does not match required pattern"
    
    return None

def raise_validation_error(error_message: str) -> None:
    """
    Raise a standardized validation error.
    
    Args:
        error_message: Validation error message
        
    Raises:
        ValidationError with error message
    """
    logger.error(f"Validation error: {error_message}")
    raise ValidationError(error_message)
