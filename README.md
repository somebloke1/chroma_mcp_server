# Chroma MCP Server

[![Tests](https://github.com/nold-ai/nold-ai-automation/actions/workflows/test.yml/badge.svg)](https://github.com/nold-ai/nold-ai-automation/actions/workflows/test.yml)

A Model-Context-Protocol (MCP) server implementation for ChromaDB vector database operations.

## Overview

The Chroma MCP Server provides a standardized interface for interacting with ChromaDB through the Model Context Protocol. It supports:

- Collection management (create, list, modify, delete)
- Document operations (add, query, update, delete)
- Sequential thinking tools for AI applications
- Multiple client types (HTTP, Cloud, Persistent, Ephemeral)
- Comprehensive error handling and logging

## Installation

```bash
# Option 1: Using the setup script (recommended)
./setup.sh  # On Unix/macOS
# This will:
# - Create a virtual environment
# - Install all dependencies
# - Set up the package in development mode
# - Verify the installation

# Option 2: Manual setup
python -m venv .venv
source .venv/bin/activate  # On Unix/macOS
.venv\Scripts\activate    # On Windows

# Install package in development mode
pip install -e ".[dev]"
```

## Configuration

### Environment Variables

The server can be configured using environment variables or a `.env` file:

```shell
# Client Configuration
CHROMA_CLIENT_TYPE=persistent  # Options: http, cloud, persistent, ephemeral
CHROMA_DATA_DIR=/path/to/data  # Required for persistent client
CHROMA_HOST=localhost          # Required for http client
CHROMA_PORT=8000              # Optional for http client

# Cloud Configuration
CHROMA_TENANT=your-tenant     # Required for cloud client
CHROMA_DATABASE=your-db       # Required for cloud client
CHROMA_API_KEY=your-key       # Required for cloud client

# Server Settings
LOG_LEVEL=INFO               # Optional, default: INFO
MCP_LOG_LEVEL=INFO          # Optional, controls MCP framework logging
```

### Cursor MCP Configuration

Configure the MCP server in your Cursor MCP configuration file (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "chroma_mcp_server": {
      "command": "/path/to/venv/bin/python",
      "args": [
        "/path/to/repo/mcp/chroma_mcp_server/run_chroma_mcp.py"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": "/path/to/repo/mcp/chroma_mcp_server",
        "LOG_LEVEL": "WARNING",
        "MCP_LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

## Verifying the Server

You can verify that the server is working correctly using the included verification script:

```bash
# First, activate the virtual environment
source .venv/bin/activate  # On Unix/macOS
.venv\Scripts\activate    # On Windows

# Run the verification script
./tests/run_chroma_mcp_test.sh  # On Unix/macOS
```

The verification script will:

1. Start the Chroma MCP server
2. Connect to it using the MCP protocol
3. List available tools
4. Test the collection listing functionality
5. Verify that everything is working correctly

## Available Tools

The server provides 15 tools across three categories:

### Collection Management

1. `chroma_create_collection` - Create a new ChromaDB collection
   - Parameters:
     - `collection_name` (str): Name of the collection
     - `description` (str, optional): Collection description
     - `metadata` (dict, optional): Additional metadata
     - `hnsw_space` (str, optional): HNSW space type
     - `hnsw_construction_ef` (int, optional): HNSW construction factor
     - `hnsw_search_ef` (int, optional): HNSW search factor
     - `hnsw_M` (int, optional): HNSW M parameter

2. `chroma_list_collections` - List all collections
   - Parameters:
     - `limit` (int, optional): Maximum number of collections to return
     - `offset` (int, optional): Number of collections to skip
     - `name_contains` (str, optional): Filter collections by name substring

3. `chroma_get_collection` - Get information about a specific collection
   - Parameters:
     - `collection_name` (str): Name of the collection

4. `chroma_modify_collection` - Modify a collection's name or metadata
   - Parameters:
     - `collection_name` (str): Current collection name
     - `new_name` (str, optional): New name for the collection
     - `new_metadata` (dict, optional): Updated metadata

5. `chroma_delete_collection` - Delete a collection
   - Parameters:
     - `collection_name` (str): Name of the collection

6. `chroma_peek_collection` - Get a sample of documents from a collection
   - Parameters:
     - `collection_name` (str): Name of the collection
     - `limit` (int, optional): Maximum number of documents to return

### Document Operations

1. `chroma_add_documents` - Add documents to a collection
   - Parameters:
     - `collection_name` (str): Target collection
     - `documents` (List[str]): Document contents
     - `ids` (List[str], optional): Document IDs
     - `metadatas` (List[dict], optional): Document metadata
     - `increment_index` (bool, optional): Whether to increment index for auto-generated IDs

2. `chroma_query_documents` - Query documents by similarity
   - Parameters:
     - `collection_name` (str): Target collection
     - `query_texts` (List[str]): Query strings
     - `n_results` (int, optional): Number of results per query
     - `where` (dict, optional): Metadata filter
     - `where_document` (dict, optional): Document content filter
     - `include` (List[str], optional): What to include in response

3. `chroma_get_documents` - Get documents from a collection
   - Parameters:
     - `collection_name` (str): Target collection
     - `ids` (List[str], optional): Document IDs to retrieve
     - `where` (dict, optional): Metadata filter
     - `where_document` (dict, optional): Document content filter
     - `limit` (int, optional): Maximum number of documents to return
     - `offset` (int, optional): Number of documents to skip
     - `include` (List[str], optional): What to include in response

4. `chroma_update_documents` - Update existing documents
   - Parameters:
     - `collection_name` (str): Target collection
     - `ids` (List[str]): Document IDs to update
     - `documents` (List[str], optional): New document contents
     - `metadatas` (List[dict], optional): New metadata

5. `chroma_delete_documents` - Delete documents from a collection
   - Parameters:
     - `collection_name` (str): Target collection
     - `ids` (List[str]): Document IDs to delete
     - `where` (dict, optional): Metadata filter
     - `where_document` (dict, optional): Document content filter

### Thinking Tools

1. `chroma_sequential_thinking` - Record a thought in a sequential thinking process
   - Parameters:
     - `thought` (str): The current thought content
     - `thought_number` (int): Position in the thought sequence (1-based)
     - `total_thoughts` (int): Total expected thoughts in the sequence
     - `session_id` (str, optional): Session identifier
     - `branch_from_thought` (int, optional): Thought number this branches from
     - `branch_id` (str, optional): Branch identifier for parallel thought paths
     - `next_thought_needed` (bool, optional): Whether another thought is needed
     - `custom_data` (dict, optional): Additional metadata

2. `chroma_find_similar_thoughts` - Find similar thoughts across thinking sessions
   - Parameters:
     - `query` (str): The thought or concept to search for
     - `n_results` (int, optional): Number of similar thoughts to return
     - `threshold` (float, optional): Similarity threshold (0-1)
     - `session_id` (str, optional): Limit search to specific session
     - `include_branches` (bool, optional): Whether to include branch paths

3. `chroma_get_session_summary` - Get a summary of all thoughts in a session
   - Parameters:
     - `session_id` (str): The session identifier
     - `include_branches` (bool, optional): Whether to include branch paths

4. `chroma_find_similar_sessions` - Find thinking sessions with similar content
   - Parameters:
     - `query` (str): The concept or pattern to search for
     - `n_results` (int, optional): Number of similar sessions to return
     - `threshold` (float, optional): Similarity threshold (0-1)

## Error Handling

The server provides standardized error handling with detailed error messages:

- `ValidationError`: Input validation failures
- `CollectionNotFoundError`: Requested collection doesn't exist
- `DocumentNotFoundError`: Requested document doesn't exist
- `ChromaDBError`: Errors from the underlying ChromaDB
- `McpError`: General MCP-related errors

All errors include:

- Error code
- Descriptive message
- Additional details when available

## Development

### Test Suite Structure

The test suite is organized into several components:

```shell
tests/
├── conftest.py                    # Shared test fixtures and configuration
├── handlers/                      # Handler-specific tests
│   ├── test_collection_handler.py
│   ├── test_document_handler.py
│   └── test_thinking_handler.py
├── tools/                         # Tool implementation tests
│   ├── test_collection_tools.py
│   ├── test_document_tools.py
│   └── test_thinking_tools.py
├── test_server.py                 # Server endpoints and configuration tests
└── test_chroma_ops.py            # ChromaDB operations tests
```

### Running Tests

The project uses pytest for testing. You can run tests using the `run_tests.py` script.

```bash
# Run all tests
python run_tests.py

# Run only unit tests
python run_tests.py -t unit

# Run with verbose output
python run_tests.py -v

# Run tests with coverage reporting
python run_tests.py -c

# Run tests with coverage and HTML report
python run_tests.py -c --html

# Combine options
python run_tests.py -t unit -c -v
```

### Code Style

The project follows standard Python code style guidelines:

- PEP 8 for general code style
- Type annotations for improved code clarity and safety
- Docstrings for all classes and functions

## Logging

The server uses structured logging with different log files for each component:

- `chroma_mcp_server.log`: Main server logs
- `chroma_collections.log`: Collection operations
- `chroma_documents.log`: Document operations
- `chroma_thinking.log`: Thinking operations
- `chroma_errors.log`: Error tracking
- `chroma_client.log`: ChromaDB client operations
- `chroma_config.log`: Configuration information

Configure log levels using the `LOG_LEVEL` environment variable.

## Documentation

Comprehensive documentation is available in the `docs` directory:

- [Getting Started Guide](docs/getting_started.md): Setup and basic usage instructions
- [API Reference](docs/api_reference.md): Detailed information about available tools and parameters

## Examples

Check out the `examples` directory for sample code demonstrating how to use the Chroma MCP Server:

- [Simple Client](examples/simple_client.py): Basic example of connecting to the server and using key tools

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Security

For information about reporting security vulnerabilities, please see our [Security Policy](SECURITY.md).

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a history of changes to this project.

## License

MIT License - see [LICENSE.md](LICENSE.md) for details
