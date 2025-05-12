"""Test configuration and fixtures for ChromaDB MCP server tests."""

import pytest
import chromadb
import inspect
import uuid
import time
import logging
import logging.handlers
import os
import warnings
import argparse
import sys

# Import the server module to access its globals
from src.chroma_mcp import server

from typing import Dict, List, Optional, Any
from datetime import datetime

from unittest.mock import AsyncMock, MagicMock, patch
from chromadb.types import Collection

from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS

from src.chroma_mcp.types import ChromaClientConfig, ThoughtMetadata
from src.chroma_mcp.utils import (
    get_chroma_client,
    get_embedding_function,
    ValidationError,
    set_main_logger,
    set_server_config,
    BASE_LOGGER_NAME,
)

from unittest.mock import MagicMock, patch
from dotenv import load_dotenv

# Import necessary components for testing server configuration and setup
from src.chroma_mcp.server import config_server

# Import functions/classes needed for tool tests
from src.chroma_mcp.utils.chroma_client import get_chroma_client, get_embedding_function
from src.chroma_mcp.utils.errors import McpError, ValidationError
from src.chroma_mcp.types import (
    ChromaClientConfig,
    ThoughtMetadata,
    DocumentMetadata,  # Ensure DocumentMetadata is imported
)

# Import the function to initialize the client
from chroma_mcp.server import _initialize_chroma_client

# Import the reset function with its new name
from chroma_mcp.utils.chroma_client import reset_client as reset_chroma_client

# --- Start: Logger Configuration for Tests ---
TEST_LOG_DIR = "logs"
# Target the actual base logger name used by the application
# TEST_BASE_LOGGER_NAME = "chromamcp.test" # Use a sub-logger for tests
TEST_BASE_LOGGER_NAME = "chromamcp"  # Configure the app's root logger

logger = logging.getLogger(TEST_BASE_LOGGER_NAME)
logger.setLevel(logging.DEBUG)  # Default to DEBUG for tests

# Prevent adding handlers multiple times
if not logger.hasHandlers():
    formatter = logging.Formatter(
        f"%(asctime)s | %(name)-{len(TEST_BASE_LOGGER_NAME)+10}s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (useful for seeing test output)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    os.makedirs(TEST_LOG_DIR, exist_ok=True)
    log_file = os.path.join(TEST_LOG_DIR, "test_debug.log")
    file_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)  # 5 MB
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# --- Explicitly set the global instance for tests ---
server._main_logger_instance = logger
# --- End: Logger Configuration for Tests ---

THOUGHTS_COLLECTION = "thoughts"
DEFAULT_SIMILARITY_THRESHOLD = 0.7


# Define MockCollection at module level
class MockCollection:
    """Mock implementation of ChromaDB collection."""

    def __init__(self):
        self.name = "test_collection"
        self.metadata = {"description": "test collection"}

    def add(self, documents=None, metadatas=None, ids=None, embeddings=None):
        """Mock add method."""
        return None

    def get(self, ids=None, where=None, limit=None, offset=None, where_document=None):
        """Mock get method."""
        return {
            "ids": ["1", "2"],
            "documents": ["thought1", "thought2"],
            "metadatas": [
                {"session_id": "test_session", "thought_number": 1},
                {"session_id": "test_session", "thought_number": 2},
            ],
            "embeddings": None,
        }

    def query(self, query_texts=None, n_results=2, where=None, where_document=None):
        """Mock query method."""
        return {
            "ids": [["1", "2"]],
            "documents": [["thought1", "thought2"]],
            "metadatas": [
                [
                    {"session_id": "test_session", "thought_number": 1},
                    {"session_id": "test_session", "thought_number": 2},
                ]
            ],
            "distances": [[0.1, 0.2]],
        }

    def count(self):
        """Mock count method."""
        return 2

    def modify(self, *args, **kwargs):
        """Mock modify method."""
        return None

    def delete(self, *args, **kwargs):
        """Mock delete method."""
        return None

    def update(self, *args, **kwargs):
        """Mock update method."""
        return None

    def upsert(self, *args, **kwargs):
        """Mock upsert method."""
        return None

    def peek(self, limit=10):
        """Mock peek method."""
        return self.get(limit=limit)

    def __str__(self):
        return f"MockCollection(name={self.name})"


# Define MockClient at module level
class MockClient:
    """Mock implementation of ChromaDB client."""

    def get_collection(self, *args, **kwargs):
        return MockCollection()

    def list_collections(self):
        return []


@pytest.fixture
def mock_chroma_client():
    """Mock ChromaDB client."""
    return MockClient()


@pytest.fixture
def mock_collection():
    """Mock ChromaDB collection."""
    return MockCollection()


@pytest.fixture
def mock_config() -> ChromaClientConfig:
    """Create a mock ChromaDB client configuration."""
    return ChromaClientConfig(client_type="ephemeral", host=None, port=None, data_dir=None)


@pytest.fixture
def sample_documents():
    """Create sample documents for testing."""
    return {
        "documents": ["doc1", "doc2"],
        "metadatas": [{"key": "value1"}, {"key": "value2"}],
        "ids": ["1", "2"],
        "embeddings": [[0.1, 0.2], [0.3, 0.4]],
    }


@pytest.fixture
def sample_thought() -> ThoughtMetadata:
    """Create a sample thought metadata."""
    return ThoughtMetadata(
        session_id="test_session",
        thought_number=1,
        total_thoughts=3,
        timestamp=1234567890,
        branch_from_thought=None,
        branch_id=None,
        next_thought_needed=False,
        custom_data={"key": "value"},
    )


@pytest.fixture
def sample_session():
    """Create a sample thinking session for testing."""
    return {
        "session_id": "test_session",
        "metadata": {"total_thoughts": 3, "start_time": 1234567890, "status": "in_progress"},
        "thoughts": [{"thought": "Initial thought", "metadata": {"thought_number": 1, "total_thoughts": 3}}],
    }


class MockMCP:
    """Mock MCP class with all required methods."""

    def __init__(self):
        """Initialize mock MCP."""
        self.name = "mock-mcp"

    async def chroma_add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Add documents to a collection."""
        # Validate inputs
        if not documents:
            raise McpError(ErrorData(code=INVALID_PARAMS, message="No documents provided"))

        return {"status": "success", "collection_name": collection_name, "count": len(documents)}

    async def chroma_query_documents(
        self,
        collection_name: str,
        query_texts: List[str],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Query documents from a collection."""
        # Generate mock results
        results = []
        for query in query_texts:
            matches = []
            for i in range(n_results):
                matches.append(
                    {
                        "id": f"{i+1}",
                        "document": f"doc{i+1}",
                        "metadata": {"key": f"value{i+1}"},
                        "distance": 0.1 * (i + 1),
                    }
                )
            results.append({"query": query, "matches": matches})

        return {"results": results}

    async def chroma_get_documents(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get documents from a collection."""
        # Generate mock results
        documents = []
        if ids:
            for id in ids:
                documents.append({"id": id, "document": f"doc-{id}", "metadata": {"key": f"value-{id}"}})
        else:
            for i in range(1, (limit or 10) + 1):
                documents.append({"id": f"{i}", "document": f"doc{i}", "metadata": {"key": f"value{i}"}})

        return {"documents": documents}

    async def chroma_update_documents(
        self,
        collection_name: str,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Update documents in a collection."""
        return {"status": "success", "collection_name": collection_name, "count": len(ids)}

    async def chroma_delete_documents(
        self, collection_name: str, ids: Optional[List[str]] = None, where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Delete documents from a collection."""
        count = len(ids) if ids else 1
        return {"status": "success", "collection_name": collection_name, "count": count}

    async def chroma_create_collection(
        self,
        collection_name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        hnsw_space: Optional[str] = None,
        hnsw_construction_ef: Optional[int] = None,
        hnsw_search_ef: Optional[int] = None,
        hnsw_M: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a new collection."""
        # Create collection metadata
        collection_metadata = {
            "description": description or f"Collection {collection_name}",
            "settings": {
                "hnsw:space": hnsw_space or "l2",
                "hnsw:construction_ef": hnsw_construction_ef or 100,
                "hnsw:search_ef": hnsw_search_ef or 100,
                "hnsw:M": hnsw_M or 16,
            },
        }

        if metadata:
            collection_metadata.update(metadata)

        return {"name": collection_name, "id": str(uuid.uuid4()), "metadata": collection_metadata}

    async def chroma_list_collections(
        self, limit: Optional[int] = None, offset: Optional[int] = None, name_contains: Optional[str] = None
    ) -> Dict[str, Any]:
        """List available collections."""
        # Generate mock collections
        collections = []
        for i in range(1, 4):
            name = f"collection{i}"
            if name_contains and name_contains not in name:
                continue
            collections.append({"name": name, "id": f"{i}", "metadata": {"description": f"Description for {name}"}})

        # Apply limit and offset
        if offset:
            collections = collections[offset:]
        if limit:
            collections = collections[:limit]

        return {"collections": collections, "total_count": len(collections)}

    async def chroma_get_collection(self, collection_name: str) -> Dict[str, Any]:
        """Get information about a collection."""
        return {
            "name": collection_name,
            "id": str(uuid.uuid4()),
            "metadata": {"description": f"Description for {collection_name}"},
            "count": 10,
            "sample_entries": [{"id": "1", "document": "Sample doc 1"}, {"id": "2", "document": "Sample doc 2"}],
        }

    async def chroma_modify_collection(
        self, collection_name: str, new_metadata: Optional[Dict[str, Any]] = None, new_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Modify an existing collection."""
        modified_name = new_name or collection_name
        modified_metadata = {"description": f"Description for {modified_name}"}
        if new_metadata:
            modified_metadata.update(new_metadata)

        return {"name": modified_name, "id": str(uuid.uuid4()), "metadata": modified_metadata}

    async def chroma_delete_collection(self, collection_name: str) -> Dict[str, Any]:
        """Delete a collection."""
        return {"status": "success", "collection_name": collection_name}

    async def chroma_peek_collection(self, collection_name: str, limit: int = 10) -> Dict[str, Any]:
        """Peek at documents in a collection."""
        # Generate mock entries
        entries = []
        for i in range(1, limit + 1):
            entries.append({"id": f"{i}", "document": f"Document {i}", "metadata": {"key": f"value{i}"}})

        return {"entries": entries}

    async def chroma_sequential_thinking(
        self,
        thought: str,
        session_id: str,
        thought_number: int,
        total_thoughts: int,
        branch_id: Optional[str] = None,
        branch_from_thought: Optional[int] = None,
        next_thought_needed: bool = False,
        custom_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process sequential thoughts."""
        # Validate inputs
        if not thought:
            raise McpError(ErrorData(code=INVALID_PARAMS, message="Thought content is required"))
        if thought_number < 1:
            raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Invalid thought number: {thought_number}"))

        response = {
            "status": "success",
            "thought": thought,
            "session_id": session_id,
            "thought_number": thought_number,
            "total_thoughts": total_thoughts,
        }

        # Add branch information if provided
        if branch_id:
            response["branch_id"] = branch_id
        if branch_from_thought:
            response["branch_from_thought"] = branch_from_thought

        # Add previous thought if it exists
        if thought_number > 1:
            response["previous_thought"] = "previous thought"

        return response

    async def chroma_find_similar_thoughts(
        self,
        query: str,
        n_results: int = 5,
        session_id: Optional[str] = None,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        include_branches: bool = True,
    ) -> Dict[str, Any]:
        """Find similar thoughts."""
        matches = [
            {"thought": "thought1", "metadata": {"session_id": "session1"}, "similarity": 0.9},
            {"thought": "thought2", "metadata": {"session_id": "session2"}, "similarity": 0.8},
        ]

        # Filter by session if specified
        if session_id:
            matches = [m for m in matches if m["metadata"]["session_id"] == session_id]

        return {"matches": matches[:n_results]}

    async def chroma_get_session_summary(self, session_id: str, include_branches: bool = True) -> Dict[str, Any]:
        """Get summary for a session."""
        return {
            "session_id": session_id,
            "thoughts": [{"thought": "thought1", "thought_number": 1}, {"thought": "thought2", "thought_number": 2}],
        }

    async def chroma_find_similar_sessions(
        self, query: str, n_results: int = 3, threshold: float = DEFAULT_SIMILARITY_THRESHOLD
    ) -> Dict[str, Any]:
        """Find similar sessions."""
        return {
            "matches": [
                {"session_id": "session1", "summary": "session1 summary", "similarity": 0.9},
                {"session_id": "session2", "summary": "session2 summary", "similarity": 0.8},
            ][:n_results]
        }

    async def ping(self) -> Dict[str, Any]:
        """Test if the MCP server is alive."""
        return {"status": "ok", "message": "Server is alive"}


@pytest.fixture(scope="session")
def patched_mcp():
    """Return a mock MCP instance with all required methods."""
    return MockMCP()


# Add this fixture to automatically shut down logging after tests
@pytest.fixture(autouse=True)
def shutdown_logging_after_tests():
    """Ensures logging is shut down after tests, closing handlers."""
    yield
    logging.shutdown()


@pytest.fixture(scope="function")
def initialized_chroma_client():
    """Fixture to ensure chroma client is initialized before a test runs.

    Uses ephemeral client by default. Resets after test.
    """
    # Create mock args for initialization (using ephemeral client)
    mock_args = argparse.Namespace(
        dotenv_path=None,  # Assume no .env for basic test
        cpu_execution_provider="auto",
        client_type="ephemeral",
        data_dir=None,
        host=None,
        port=8000,
        ssl=False,
        tenant=None,
        database=None,
        api_key=None,
        embedding_function_name="default",
        # Add other args _initialize_chroma_client might access, even via getattr
        # Though getattr should handle missing ones
    )

    # Patch get_logger to avoid side effects during init
    with patch("chroma_mcp.server.get_logger") as mock_get_logger:
        # Ensure chromadb is available or mocked if needed for specific tests
        # For basic initialization testing, assuming it's available
        # Call the actual initialization function
        _initialize_chroma_client(mock_args)

    yield  # Test runs here

    # Teardown: Reset the client instance after the test
    # This assumes you have a way to reset the global _chroma_client_instance
    # Option 1: If you have a reset function (best)
    reset_chroma_client()
    # Option 2: Manually reset the global (more brittle)
    # from chroma_mcp import server
    # server._chroma_client_instance = None
    # print("Chroma client reset after test.")


# --- Begin added logger fixture ---
@pytest.fixture(scope="session", autouse=True)
def configure_test_logger():
    """
    Configures a basic logger for the test session to prevent
    'Logger requested before main configuration' warnings and ensure
    logs are captured by pytest if needed. Runs automatically for the session.
    """
    logger = logging.getLogger(BASE_LOGGER_NAME)
    # Prevent adding handlers multiple times if fixture runs unexpectedly often
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)  # Set to DEBUG to capture all levels during tests
        handler = logging.StreamHandler(sys.stderr)  # Log to stderr like pytest does
        formatter = logging.Formatter("%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        # Set this basic logger as the 'main' logger for the utils.get_logger() function
        set_main_logger(logger)
        logger.debug("Test logger configured by session fixture.")
    # Yield control to the test session
    yield
    # Teardown (optional, e.g., remove handler if necessary)
    # logger.handlers.clear() # Might not be needed if process exits cleanly


# --- End added logger fixture ---


# Fixture to initialize Chroma client once per session for specific tests
# This avoids repeated initialization warnings if multiple tests need it.
# Note: This assumes a persistent client setup for testing to avoid state issues.
# If ephemeral is needed, adjust or use a function-scoped fixture.
@pytest.fixture(scope="session")
def initialized_chroma_client(tmp_path_factory):
    """Initializes a persistent Chroma client for the test session."""
    data_path = tmp_path_factory.mktemp("chroma_test_data")
    print(f"DEBUG: Using tmp Chroma data path: {data_path}")

    # Define a minimal config for testing
    test_config = ChromaClientConfig(
        client_type="persistent",
        data_dir=str(data_path),
        embedding_function_name="default",  # Use a known default EF
    )

    # Store the original config if it exists, to restore later
    # Note: get_server_config might raise if never set, handle this?
    # For simplicity, assume it's None initially or we don't need strict restore.
    # original_config = None
    # try:
    #     original_config = get_server_config()
    # except Exception:
    #     pass

    # Set the test configuration globally
    set_server_config(test_config)
    print(f"DEBUG: Set test server config: {test_config}")

    # Use patch only for the client instance, ensuring it starts as None
    with patch("src.chroma_mcp.utils.chroma_client._chroma_client", None):
        print("DEBUG: Attempting to get Chroma client within fixture...")
        try:
            # Call get_chroma_client which should initialize based on the *globally set* config
            client = get_chroma_client()
            print(f"DEBUG: Chroma client obtained: {client}")
            yield client  # Provide the client to tests

            # Teardown:
            # Reset the client instance via the utility function
            from src.chroma_mcp.utils.chroma_client import reset_client

            reset_client()
            print("DEBUG: Chroma client reset via reset_client().")

            # Restore original config if needed (optional)
            # if original_config:
            #    set_server_config(original_config)
            # else:
            #    # Or clear it? Depends on desired state after tests.
            #    # You might need a `clear_server_config()` function.
            #    pass
            print("DEBUG: Chroma client fixture teardown complete.")

        except Exception as e:
            print(f"ERROR: Failed to initialize/yield Chroma client in fixture: {e}")
            pytest.fail(f"Failed to initialize Chroma client for tests: {e}")


@pytest.fixture(autouse=True)
def setup_logging(caplog):
    """Configure logging to ensure caplog captures all logs properly."""
    # Set caplog level to DEBUG to capture all logs
    caplog.set_level(logging.DEBUG)

    # Ensure logs from all relevant modules are captured
    for logger_name in [
        "chroma_mcp_client",
        "chroma_mcp_client.cli",
        "chroma_mcp_client.indexing",
        "chroma_mcp_client.query",
        "chroma_mcp_client.interactive_promoter",
        "chroma_mcp",
        "chromamcp",
        "src.chroma_mcp.server",
        "src.chroma_mcp.utils",
        "root",  # For root logger
    ]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        # Reset handlers to avoid duplication
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    yield
