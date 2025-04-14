"""
Chroma MCP Server - Main Implementation

This module provides the core server implementation for the Chroma MCP service,
integrating ChromaDB with the Model Context Protocol (MCP).
"""

import os
import argparse
import importlib.metadata
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
import logging
import logging.handlers  # Add this for FileHandler
import sys  # Import sys for stderr output as last resort
import json

from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS

# REMOVE: from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.server import stdio

# ADD: Import the shared mcp instance from app
from .app import server

# Import ThoughtMetadata from .types
# Import ChromaClientConfig now also from .types
from .types import ThoughtMetadata, ChromaClientConfig

# Import config loading and tool registration
from .utils.config import load_config

# Import errors and specific utils (setters/getters for globals)
from .utils import (
    get_logger,
    set_main_logger,
    get_server_config,  # Keep getter for potential internal use
    set_server_config,
    BASE_LOGGER_NAME,
    # raise_validation_error # Keep these if used directly in server?
)
from pydantic import ValidationError  # Import for validation handling
from mcp import types  # Import base MCP types

# Import all Pydantic input models
from .tools.collection_tools import (
    CreateCollectionInput,
    CreateCollectionWithMetadataInput,
    ListCollectionsInput,
    GetCollectionInput,
    RenameCollectionInput,
    DeleteCollectionInput,
    PeekCollectionInput,
)
from .tools.document_tools import (
    AddDocumentInput,
    AddDocumentWithIDInput,
    AddDocumentWithMetadataInput,
    AddDocumentWithIDAndMetadataInput,
    QueryDocumentsInput,
    QueryDocumentsWithWhereFilterInput,
    QueryDocumentsWithDocumentFilterInput,
    GetDocumentsByIdsInput,
    GetDocumentsWithWhereFilterInput,
    GetDocumentsWithDocumentFilterInput,
    GetAllDocumentsInput,
    UpdateDocumentContentInput,
    UpdateDocumentMetadataInput,
    DeleteDocumentByIdInput,
    GetDocumentsByIdsEmbeddingsInput,
    GetDocumentsByIdsAllInput,
)
from .tools.thinking_tools import (
    SequentialThinkingInput,
    SequentialThinkingWithCustomDataInput,
    FindSimilarThoughtsInput,
    GetSessionSummaryInput,
    FindSimilarSessionsInput,
)

# Import all _impl functions
from .tools.collection_tools import (
    _create_collection_impl,
    _create_collection_with_metadata_impl,
    _list_collections_impl,
    _get_collection_impl,
    _rename_collection_impl,
    _delete_collection_impl,
    _peek_collection_impl,
)
from .tools.document_tools import (
    _add_document_impl,
    _add_document_with_id_impl,
    _add_document_with_metadata_impl,
    _add_document_with_id_and_metadata_impl,
    _query_documents_impl,
    _query_documents_with_where_filter_impl,
    _query_documents_with_document_filter_impl,
    _get_documents_by_ids_impl,
    _get_documents_with_where_filter_impl,
    _get_documents_with_document_filter_impl,
    _get_all_documents_impl,
    _update_document_content_impl,
    _update_document_metadata_impl,
    _delete_document_by_id_impl,
    _get_documents_by_ids_embeddings_impl,
    _get_documents_by_ids_all_impl,
)
from .tools.thinking_tools import (
    _sequential_thinking_impl,
    _sequential_thinking_with_custom_data_impl,
    _find_similar_thoughts_impl,
    _get_session_summary_impl,
    _find_similar_sessions_impl,
)

# Add this near the top of the file, after imports but before any other code
CHROMA_AVAILABLE = False
try:
    import chromadb

    CHROMA_AVAILABLE = True
except ImportError:
    # Use logger if available later, print is too early here
    # We will log this warning properly within config_server
    pass

FASTMCP_AVAILABLE = False
try:
    import fastmcp

    FASTMCP_AVAILABLE = True
except ImportError:
    # Use logger if available later, print is too early here
    # We will log this warning properly within config_server
    pass


def config_server(args: argparse.Namespace) -> None:
    """
    Configures the Chroma MCP server based on parsed command-line arguments.

    This involves:
    - Loading environment variables from a specified .env file (if it exists).
    - Setting up logging (console and optional file handlers) with the specified level.
    - Creating a ChromaClientConfig object based on client type, connection details,
      and other settings provided in `args`.
    - Storing the logger and client configuration globally for access by other modules.
    - Logging configuration details and warnings about missing optional dependencies
      (chromadb, fastmcp).

    Args:
        args: An argparse.Namespace object containing the parsed command-line
              arguments from `cli.py`.

    Raises:
        McpError: Wraps any exception that occurs during configuration, ensuring
                  a consistent error format is propagated upwards. Logs critical
                  errors before raising.
    """
    logger = None  # Initialize logger to None before try block
    try:
        # Load environment variables if dotenv file exists
        if args.dotenv_path and os.path.exists(args.dotenv_path):
            load_dotenv(dotenv_path=args.dotenv_path)

        # --- Start: Logger Configuration ---
        log_dir = args.log_dir
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        log_level = getattr(logging, log_level_str, logging.INFO)

        # Get the root logger for our application
        logger = logging.getLogger(BASE_LOGGER_NAME)
        logger.setLevel(log_level)

        # Prevent adding handlers multiple times if config_server is called again (e.g., in tests)
        if not logger.hasHandlers():
            # Create formatter
            formatter = logging.Formatter(
                f"%(asctime)s | %(name)-{len(BASE_LOGGER_NAME)+15}s | %(levelname)-8s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

            # Create console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

            # Create file handler if log_dir is specified
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
                log_file = os.path.join(log_dir, "chroma_mcp_server.log")
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10 MB
                )
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)

        # Store the configured logger instance globally via setter
        set_main_logger(logger)
        # --- End: Logger Configuration ---

        # Handle CPU provider setting
        use_cpu_provider = None  # Auto-detect
        if args.cpu_execution_provider != "auto":
            use_cpu_provider = args.cpu_execution_provider == "true"

        # Create client configuration
        client_config = ChromaClientConfig(
            client_type=args.client_type,
            data_dir=args.data_dir,
            host=args.host,
            port=args.port,
            ssl=args.ssl,
            tenant=args.tenant,
            database=args.database,
            api_key=args.api_key,
            use_cpu_provider=use_cpu_provider,
            embedding_function_name=args.embedding_function_name,
        )

        # Store the config globally via setter
        set_server_config(client_config)

        # This will initialize our configurations for later use
        provider_status = (
            "auto-detected" if use_cpu_provider is None else ("enabled" if use_cpu_provider else "disabled")
        )
        logger.info(f"Server configured (CPU provider: {provider_status})")

        # Log the configuration details
        if log_dir:
            logger.info(f"Logs will be saved to: {log_dir}")
        if args.data_dir:
            logger.info(f"Data directory: {args.data_dir}")

        # Check for required dependencies
        if not CHROMA_AVAILABLE:
            logger.warning("ChromaDB is not installed. Vector database operations will not be available.")
            logger.warning("To enable full functionality, install the optional dependencies:")
            logger.warning("pip install chroma-mcp-server[full]")

        if not FASTMCP_AVAILABLE:
            logger.warning("FastMCP is not installed. MCP tools will not be available.")
            logger.warning("To enable full functionality, install the optional dependencies:")
            logger.warning("pip install chroma-mcp-server[full]")

    except Exception as e:
        # If logger isn't initialized yet, use print for critical errors
        error_msg = f"Failed to configure server: {str(e)}"
        if logger:
            # Use critical level for configuration failures
            logger.critical(error_msg)
        else:
            # Last resort if logger setup failed completely
            print(f"CRITICAL CONFIG ERROR: {error_msg}", file=sys.stderr)

        # Wrap the exception in McpError
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=error_msg))


# --- Tool Registration (list_tools) ---

# Tool names dictionary for consistency
TOOL_NAMES = {
    "CREATE_COLLECTION": "chroma_create_collection",
    "CREATE_COLLECTION_WITH_META": "chroma_create_collection_with_metadata",
    "LIST_COLLECTIONS": "chroma_list_collections",
    "GET_COLLECTION": "chroma_get_collection",
    "RENAME_COLLECTION": "chroma_rename_collection",
    "DELETE_COLLECTION": "chroma_delete_collection",
    "PEEK_COLLECTION": "chroma_peek_collection",
    "ADD_DOCS": "chroma_add_document",
    "ADD_DOCS_IDS": "chroma_add_document_with_id",
    "ADD_DOCS_META": "chroma_add_document_with_metadata",
    "ADD_DOCS_IDS_META": "chroma_add_document_with_id_and_metadata",
    "QUERY_DOCS": "chroma_query_documents",
    "QUERY_DOCS_WHERE": "chroma_query_documents_with_where_filter",
    "QUERY_DOCS_DOC": "chroma_query_documents_with_document_filter",
    "GET_DOCS_IDS": "chroma_get_documents_by_ids",
    "GET_DOCS_WHERE": "chroma_get_documents_with_where_filter",
    "GET_DOCS_DOC": "chroma_get_documents_with_document_filter",
    "GET_DOCS_ALL": "chroma_get_all_documents",
    "GET_DOCS_IDS_EMBEDDINGS": "chroma_get_documents_by_ids_embeddings",
    "GET_DOCS_IDS_ALL": "chroma_get_documents_by_ids_all",
    "DELETE_DOCS": "chroma_delete_document_by_id",
    "SEQ_THINKING": "chroma_sequential_thinking",
    "SEQ_THINKING_CUSTOM": "chroma_sequential_thinking_with_custom_data",
    "FIND_THOUGHTS": "chroma_find_similar_thoughts",
    "GET_SUMMARY": "chroma_get_session_summary",
    "FIND_SESSIONS": "chroma_find_similar_sessions",
    "GET_VERSION": "chroma_get_server_version",
    "UPDATE_DOC_CONTENT": "chroma_update_document_content",
    "UPDATE_DOC_META": "chroma_update_document_metadata",
}

# Pydantic models mapping
INPUT_MODELS = {
    TOOL_NAMES["CREATE_COLLECTION"]: CreateCollectionInput,
    TOOL_NAMES["CREATE_COLLECTION_WITH_META"]: CreateCollectionWithMetadataInput,
    TOOL_NAMES["LIST_COLLECTIONS"]: ListCollectionsInput,
    TOOL_NAMES["GET_COLLECTION"]: GetCollectionInput,
    TOOL_NAMES["RENAME_COLLECTION"]: RenameCollectionInput,
    TOOL_NAMES["DELETE_COLLECTION"]: DeleteCollectionInput,
    TOOL_NAMES["PEEK_COLLECTION"]: PeekCollectionInput,
    TOOL_NAMES["ADD_DOCS"]: AddDocumentInput,
    TOOL_NAMES["ADD_DOCS_IDS"]: AddDocumentWithIDInput,
    TOOL_NAMES["ADD_DOCS_META"]: AddDocumentWithMetadataInput,
    TOOL_NAMES["ADD_DOCS_IDS_META"]: AddDocumentWithIDAndMetadataInput,
    TOOL_NAMES["QUERY_DOCS"]: QueryDocumentsInput,
    TOOL_NAMES["QUERY_DOCS_WHERE"]: QueryDocumentsWithWhereFilterInput,
    TOOL_NAMES["QUERY_DOCS_DOC"]: QueryDocumentsWithDocumentFilterInput,
    TOOL_NAMES["GET_DOCS_IDS"]: GetDocumentsByIdsInput,
    TOOL_NAMES["GET_DOCS_WHERE"]: GetDocumentsWithWhereFilterInput,
    TOOL_NAMES["GET_DOCS_DOC"]: GetDocumentsWithDocumentFilterInput,
    TOOL_NAMES["GET_DOCS_ALL"]: GetAllDocumentsInput,
    TOOL_NAMES["GET_DOCS_IDS_EMBEDDINGS"]: GetDocumentsByIdsEmbeddingsInput,
    TOOL_NAMES["GET_DOCS_IDS_ALL"]: GetDocumentsByIdsAllInput,
    TOOL_NAMES["DELETE_DOCS"]: DeleteDocumentByIdInput,
    TOOL_NAMES["SEQ_THINKING"]: SequentialThinkingInput,
    TOOL_NAMES["SEQ_THINKING_CUSTOM"]: SequentialThinkingWithCustomDataInput,
    TOOL_NAMES["FIND_THOUGHTS"]: FindSimilarThoughtsInput,
    TOOL_NAMES["GET_SUMMARY"]: GetSessionSummaryInput,
    TOOL_NAMES["FIND_SESSIONS"]: FindSimilarSessionsInput,
    TOOL_NAMES["UPDATE_DOC_CONTENT"]: UpdateDocumentContentInput,
    TOOL_NAMES["UPDATE_DOC_META"]: UpdateDocumentMetadataInput,
    TOOL_NAMES["GET_VERSION"]: None,  # GET_VERSION has no input model
}

# Tool implementation function mapping
IMPL_FUNCTIONS = {
    TOOL_NAMES["CREATE_COLLECTION"]: _create_collection_impl,
    TOOL_NAMES["CREATE_COLLECTION_WITH_META"]: _create_collection_with_metadata_impl,
    TOOL_NAMES["LIST_COLLECTIONS"]: _list_collections_impl,
    TOOL_NAMES["GET_COLLECTION"]: _get_collection_impl,
    TOOL_NAMES["RENAME_COLLECTION"]: _rename_collection_impl,
    TOOL_NAMES["DELETE_COLLECTION"]: _delete_collection_impl,
    TOOL_NAMES["PEEK_COLLECTION"]: _peek_collection_impl,
    TOOL_NAMES["ADD_DOCS"]: _add_document_impl,
    TOOL_NAMES["ADD_DOCS_IDS"]: _add_document_with_id_impl,
    TOOL_NAMES["ADD_DOCS_META"]: _add_document_with_metadata_impl,
    TOOL_NAMES["ADD_DOCS_IDS_META"]: _add_document_with_id_and_metadata_impl,
    TOOL_NAMES["QUERY_DOCS"]: _query_documents_impl,
    TOOL_NAMES["QUERY_DOCS_WHERE"]: _query_documents_with_where_filter_impl,
    TOOL_NAMES["QUERY_DOCS_DOC"]: _query_documents_with_document_filter_impl,
    TOOL_NAMES["GET_DOCS_IDS"]: _get_documents_by_ids_impl,
    TOOL_NAMES["GET_DOCS_WHERE"]: _get_documents_with_where_filter_impl,
    TOOL_NAMES["GET_DOCS_DOC"]: _get_documents_with_document_filter_impl,
    TOOL_NAMES["GET_DOCS_ALL"]: _get_all_documents_impl,
    TOOL_NAMES["GET_DOCS_IDS_EMBEDDINGS"]: _get_documents_by_ids_embeddings_impl,
    TOOL_NAMES["GET_DOCS_IDS_ALL"]: _get_documents_by_ids_all_impl,
    TOOL_NAMES["DELETE_DOCS"]: _delete_document_by_id_impl,
    TOOL_NAMES["SEQ_THINKING"]: _sequential_thinking_impl,
    TOOL_NAMES["SEQ_THINKING_CUSTOM"]: _sequential_thinking_with_custom_data_impl,
    TOOL_NAMES["FIND_THOUGHTS"]: _find_similar_thoughts_impl,
    TOOL_NAMES["GET_SUMMARY"]: _get_session_summary_impl,
    TOOL_NAMES["FIND_SESSIONS"]: _find_similar_sessions_impl,
    TOOL_NAMES["UPDATE_DOC_CONTENT"]: _update_document_content_impl,
    TOOL_NAMES["UPDATE_DOC_META"]: _update_document_metadata_impl,
    TOOL_NAMES["GET_VERSION"]: None,  # GET_VERSION needs a simple handler
}


@server.list_tools()
async def list_tools() -> List[types.Tool]:
    """Registers all available tools with the MCP server."""
    # Get logger instance
    logger = get_logger("list_tools")
    tool_definitions = [
        # Collection Tools
        types.Tool(
            name=TOOL_NAMES["CREATE_COLLECTION"],
            description="Create a new ChromaDB collection using server default settings. Requires: `collection_name`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["CREATE_COLLECTION"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["CREATE_COLLECTION_WITH_META"],
            description="Create a new ChromaDB collection with specific metadata/settings provided. Requires: `collection_name`, `metadata` (JSON string).",
            inputSchema=INPUT_MODELS[TOOL_NAMES["CREATE_COLLECTION_WITH_META"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["LIST_COLLECTIONS"],
            description="List all collections. Optional: `limit`, `offset`, `name_contains`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["LIST_COLLECTIONS"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["GET_COLLECTION"],
            description="Get information about a specific collection. Requires: `collection_name`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["GET_COLLECTION"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["RENAME_COLLECTION"],
            description="Renames an existing collection. Requires: `collection_name`, `new_name`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["RENAME_COLLECTION"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["DELETE_COLLECTION"],
            description="Delete a collection. Requires: `collection_name`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["DELETE_COLLECTION"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["PEEK_COLLECTION"],
            description="Get a sample of documents from a collection. Requires: `collection_name`. Optional: `limit`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["PEEK_COLLECTION"]].model_json_schema(),
        ),
        # Document Tools
        types.Tool(
            name=TOOL_NAMES["ADD_DOCS"],
            description="Add a document (auto-generates ID, no metadata). Requires: `collection_name`, `document`. Optional: `increment_index`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["ADD_DOCS"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["ADD_DOCS_IDS"],
            description="Add a document with a specified ID (no metadata). Requires: `collection_name`, `document`, `id`. Optional: `increment_index`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["ADD_DOCS_IDS"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["ADD_DOCS_META"],
            description="Add a document with specified metadata (auto-generates ID). Requires: `collection_name`, `document`, `metadata` (JSON string). Optional: `increment_index`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["ADD_DOCS_META"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["ADD_DOCS_IDS_META"],
            description="Add a document with specified ID and metadata. Requires: `collection_name`, `document`, `id`, `metadata` (JSON string). Optional: `increment_index`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["ADD_DOCS_IDS_META"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["QUERY_DOCS"],
            description="Query documents using semantic search (no filters). Requires: `collection_name`, `query_texts`. Optional: `n_results`, `include`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["QUERY_DOCS"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["QUERY_DOCS_WHERE"],
            description="Query documents using semantic search with a metadata filter. Requires: `collection_name`, `query_texts`, `where`. Optional: `n_results`, `include`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["QUERY_DOCS_WHERE"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["QUERY_DOCS_DOC"],
            description="Query documents using semantic search with a document content filter. Requires: `collection_name`, `query_texts`, `where_document`. Optional: `n_results`, `include`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["QUERY_DOCS_DOC"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["GET_DOCS_IDS"],
            description="Get documents from a collection by specific IDs. Requires: `collection_name`, `ids`. Optional: `include`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["GET_DOCS_IDS"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["GET_DOCS_WHERE"],
            description="Get documents from a collection using a metadata filter. Requires: `collection_name`, `where`. Optional: `limit`, `offset`, `include`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["GET_DOCS_WHERE"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["GET_DOCS_DOC"],
            description="Get documents from a collection using a document content filter. Requires: `collection_name`, `where_document`. Optional: `limit`, `offset`, `include`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["GET_DOCS_DOC"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["GET_DOCS_ALL"],
            description="Get all documents from a collection. Requires: `collection_name`. Optional: `limit`, `offset`, `include`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["GET_DOCS_ALL"]].model_json_schema(),
        ),
        # --- Start: Add New Include Variants ---
        types.Tool(
            name=TOOL_NAMES["GET_DOCS_IDS_EMBEDDINGS"],
            description="Get documents from a collection by specific IDs, including embeddings only. Requires: `collection_name`, `ids`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["GET_DOCS_IDS_EMBEDDINGS"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["GET_DOCS_IDS_ALL"],
            description="Get documents from a collection by specific IDs, including all available data. Requires: `collection_name`, `ids`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["GET_DOCS_IDS_ALL"]].model_json_schema(),
        ),
        # --- End: Add New Include Variants ---
        types.Tool(
            name=TOOL_NAMES["DELETE_DOCS"],
            description="Delete a document from a collection by its specific ID. Requires: `collection_name`, `id`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["DELETE_DOCS"]].model_json_schema(),
        ),
        # Update Document Variants
        types.Tool(
            name=TOOL_NAMES["UPDATE_DOC_CONTENT"],
            description="Update the content of an existing document by ID. Requires: `collection_name`, `id`, `document`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["UPDATE_DOC_CONTENT"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["UPDATE_DOC_META"],
            description="Update the metadata of an existing document by ID. Requires: `collection_name`, `id`, `metadata` (dict).",
            inputSchema=INPUT_MODELS[TOOL_NAMES["UPDATE_DOC_META"]].model_json_schema(),
        ),
        # Thinking Tools
        types.Tool(
            name=TOOL_NAMES["SEQ_THINKING"],
            description="Records a single thought. Requires: `thought`, `thought_number`, `total_thoughts`. Optional: `session_id`, `branch_id`, `branch_from_thought`, `next_thought_needed`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["SEQ_THINKING"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["FIND_THOUGHTS"],
            description="Finds thoughts semantically similar to a query. Requires: `query`. Optional: `session_id`, `n_results`, `threshold`, `include_branches`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["FIND_THOUGHTS"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["GET_SUMMARY"],
            description="Retrieves all thoughts recorded within a specific thinking session. Requires: `session_id`. Optional: `include_branches`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["GET_SUMMARY"]].model_json_schema(),
        ),
        types.Tool(
            name=TOOL_NAMES["FIND_SESSIONS"],
            description="Finds thinking sessions similar to a query. Requires: `query`. Optional: `n_results`, `threshold`.",
            inputSchema=INPUT_MODELS[TOOL_NAMES["FIND_SESSIONS"]].model_json_schema(),
        ),
        # Utility Tool
        types.Tool(
            name=TOOL_NAMES["GET_VERSION"],
            description="Return the installed version of the chroma-mcp-server package. Takes no parameters.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]
    # Add debug log
    logger.debug(f"Returning {len(tool_definitions)} tool definitions: {[t.name for t in tool_definitions]}")
    # Optionally log the full definitions if needed for deep debugging:
    logger.debug(f"Full tool definitions: {tool_definitions}")
    logger.debug("Finished listing tools.")
    return tool_definitions


# --- Tool Execution (call_tool) ---


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handles incoming tool calls, validates input, and dispatches to implementation functions."""
    logger = get_logger("call_tool")
    # Add this line to log raw arguments
    logger.debug(f"Raw arguments received for tool '{name}': {arguments}")
    # logger.debug(f"Received tool call: {name} with arguments: {arguments}")

    # REMOVE the outer try...except block. Let Server handle exceptions.
    # try:
    # --- Special case: Get Version (no Pydantic model) ---
    if name == TOOL_NAMES["GET_VERSION"]:
        try:
            version = importlib.metadata.version("chroma-mcp-server")
            result_text = json.dumps({"package": "chroma-mcp-server", "version": version})
            content_list = [types.TextContent(type="text", text=result_text)]
            logger.debug(f"Returning result for {name}: {content_list}")  # Log before return
            return content_list
        except importlib.metadata.PackageNotFoundError as e:
            logger.error(f"Error getting server version: {str(e)}", exc_info=True)
            # Raise exception for Server to handle
            error_data = ErrorData(code=INTERNAL_ERROR, message="Tool Error: chroma-mcp-server package not found.")
            raise McpError(error_data)
        except Exception as e:
            logger.error(f"Error getting server version: {str(e)}", exc_info=True)
            # Raise exception for Server to handle
            error_data = ErrorData(
                code=INTERNAL_ERROR, message=f"Tool Error: Could not get server version. Details: {str(e)}"
            )
            raise McpError(error_data)

    # --- Get Pydantic Model and Implementation Function --- >
    InputModel = INPUT_MODELS.get(name)
    impl_function = IMPL_FUNCTIONS.get(name)

    if not InputModel or not impl_function:
        logger.error(f"Unknown tool name received: {name}")
        # Raise exception for Server to handle, wrapping ErrorData
        error_data = ErrorData(code=INVALID_PARAMS, message=f"Tool Error: Unknown tool name '{name}'")
        raise McpError(error_data)

    # --- Pydantic Validation --- >
    try:
        logger.debug(f"Validating arguments for {name} using {InputModel.__name__}")
        validated_input = InputModel(**arguments)
        logger.debug(f"Validation successful for {name}")
    except ValidationError as e:
        logger.warning(f"Input validation failed for {name}: {e}")
        # Wrap Pydantic error message in McpError with ErrorData
        error_data = ErrorData(code=INVALID_PARAMS, message=f"Input Error: {str(e)}")
        raise McpError(error_data)

    # --- Call Core Logic --- >
    logger.debug(f"Calling implementation function for {name}")
    # Pass the validated Pydantic model instance to the implementation function
    # Assume impl_function now returns List[TextContent] or raises Exception
    content_list: List[types.TextContent] = await impl_function(validated_input)
    logger.debug(f"Implementation function for {name} returned content list.")

    # Add debug log before returning
    logger.debug("Debug log for call_tool result.")
    logger.debug(f"Returning call_tool result for {name}: {content_list}")  # Log before return
    logger.debug("Finished debug log for call_tool result.")
    return content_list


def main() -> None:
    """Main execution function for the Chroma MCP server.

    Assumes that `config_server` has already been called (typically by `cli.py`).
    Retrieves the globally configured logger.
    Logs the server start event, including the package version.
    Initiates the MCP server run loop using the configured stdio transport
    and the shared `server` instance from `app.py`.

    Catches and logs `McpError` exceptions specifically.
    Catches any other exceptions, logs them as critical errors, and wraps them
    in an `McpError` before raising to ensure a consistent exit status via the CLI.
    """
    logger = None  # Initialize logger variable for this scope
    try:
        # Configuration should have been done by cli.py calling config_server
        logger = get_logger()

        if logger:
            try:
                version = importlib.metadata.version("chroma-mcp-server")
            except importlib.metadata.PackageNotFoundError:
                version = "unknown"
            logger.info(f"Chroma MCP server v{version} started. Using stdio transport.")

        # Start server with stdio transport using the IMPORTED shared 'server' instance
        # The run method now needs the read/write streams and options
        # We need asyncio to run the server properly now
        import asyncio

        async def run_server():
            options = server.create_initialization_options()
            async with stdio.stdio_server() as (read_stream, write_stream):
                await server.run(read_stream, write_stream, options, raise_exceptions=True)

        # Run the async server function
        asyncio.run(run_server())

    except McpError as e:
        if logger:
            logger.error(f"MCP Error: {str(e)}")
        # Re-raise McpError to potentially be caught by CLI
        # Ensure ErrorData is propagated if available, otherwise use the message
        err_data = (
            e.args[0] if e.args and isinstance(e.args[0], ErrorData) else ErrorData(code=INTERNAL_ERROR, message=str(e))
        )
        raise McpError(err_data)
    except Exception as e:
        error_msg = f"Critical error running MCP server: {str(e)}"
        if logger:
            logger.error(error_msg)
        # Convert unexpected errors to McpError for consistent exit
        err_data = ErrorData(code=INTERNAL_ERROR, message=error_msg)
        raise McpError(err_data)


if __name__ == "__main__":
    # In a typical setup, cli.py would call config_server then main.
    # For direct execution (if needed for debugging), configuration might be missing.
    # Consider adding basic argument parsing and config call here if direct execution is intended.
    # For now, assume cli.py is the entry point.
    pass
