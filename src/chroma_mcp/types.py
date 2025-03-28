"""Type definitions for the ChromaMCP server."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from pydantic import BaseModel

# Error codes
INTERNAL_ERROR = "INTERNAL_ERROR"
INVALID_PARAMS = "INVALID_PARAMS"

class ErrorData(BaseModel):
    """Standard error data structure."""
    code: str
    message: str
    data: Optional[Dict[str, Any]] = None

@dataclass
class ChromaClientConfig:
    """Configuration for ChromaDB client."""
    client_type: str  # "ephemeral" or "persistent"
    data_dir: Optional[str] = None  # Directory for persistent storage
    host: Optional[str] = None  # Host for remote ChromaDB
    port: Optional[int] = None  # Port for remote ChromaDB
    ssl: bool = True  # Use SSL for remote connections
    tenant: Optional[str] = None  # Tenant ID for multi-tenant setups
    database: Optional[str] = None  # Database name
    api_key: Optional[str] = None  # API key for authentication
    use_cpu_provider: bool = False  # Use CPU provider instead of GPU

@dataclass
class ThoughtMetadata:
    """Metadata structure for thoughts."""
    session_id: str  # Unique identifier for the thinking session
    thought_number: int  # Position of the thought in the sequence
    total_thoughts: int  # Total number of thoughts expected in the sequence
    timestamp: int  # Unix timestamp when the thought was recorded
    branch_from_thought: Optional[int] = None  # Thought number this branches from
    branch_id: Optional[str] = None  # Identifier for the branch
    next_thought_needed: bool = False  # Whether another thought is needed
    custom_data: Optional[Dict[str, Any]] = None  # Additional metadata 