# Chroma MCP Server

[![Tests](https://github.com/djm81/chroma_mcp_server/actions/workflows/tests.yml/badge.svg)](https://github.com/djm81/chroma_mcp_server/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/djm81/chroma_mcp_server/branch/main/graph/badge.svg)](https://codecov.io/gh/djm81/chroma_mcp_server)

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
CHROMA_LOG_DIR=/path/to/logs   # Custom directory for log files
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

### Command Line Arguments

The server can also be configured using command line arguments:

```bash
python run_chroma_mcp.py --client-type persistent --data-dir /path/to/data --log-dir /path/to/logs
```

Available arguments:

- `--client-type`: Type of ChromaDB client to use (http, cloud, persistent, ephemeral)
- `--data-dir`: Directory for persistent client data
- `--log-dir`: Directory for log files
- `--host`: Chroma host for HTTP client
- `--port`: Chroma port for HTTP client
- `--ssl`: Enable SSL for HTTP client (true/false)
- `--tenant`: Chroma tenant for cloud client
- `--database`: Chroma database for cloud client
- `--api-key`: Chroma API key for cloud client
- `--cpu-execution-provider`: Force CPU execution provider (auto/true/false)

### Cursor MCP Configuration

Configure the MCP server in your Cursor MCP configuration file (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "chroma_mcp_server": {
      "command": "/path/to/venv/bin/python",
      "args": [
        "/path/to/repo/mcp/chroma_mcp_server/run_chroma_mcp.py",
        "--data-dir", "/path/to/custom/data",
        "--log-dir", "/path/to/custom/logs"
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
     - `documents`

## Quick Start with uvx

The easiest way to use the Chroma MCP Server is with [uv](https://github.com/astral-sh/uv), a fast Python package installer and runner.

### Install uv

```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# With pip
pip install uv
```

### Run with uvx

To run the server directly without installation, use the `uvx` command (an alias for `uv tool run`):

```bash
uvx chroma-mcp-server --data-dir /path/to/data --log-dir /path/to/logs
```

> **Note:** The package is named `chroma_mcp_server` in Python, but when using with uvx, you need to use the hyphenated version `chroma-mcp-server`.

This will automatically:

1. Download the package
2. Create an isolated virtual environment
3. Install dependencies
4. Run the server

### Configure in MCP-compatible IDEs

Add this to your IDE's MCP configuration file:

#### Cursor (.cursor/mcp.json)

```json
{
  "mcpServers": {
    "chroma_mcp_server": {
      "command": "uvx",
      "args": [
        "chroma-mcp-server",
        "--data-dir", "/path/to/data",
        "--log-dir", "/path/to/logs"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8",
        "LOG_LEVEL": "WARNING",
        "MCP_LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

#### JetBrains IDEs

Configure in Settings > AI Assistant > MCP Server Configuration:

- Server ID: `chroma_mcp_server`
- Command: `uvx`
- Arguments: `chroma-mcp-server --data-dir /path/to/data --log-dir /path/to/logs`

#### Permanently Install

To install the server permanently:

```bash
uv tool install chroma-mcp-server
```

Then configure with:

```json
{
  "mcpServers": {
    "chroma_mcp_server": {
      "command": "chroma-mcp",
      "args": [
        "--data-dir", "/path/to/data",
        "--log-dir", "/path/to/logs"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8",
        "LOG_LEVEL": "WARNING",
        "MCP_LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

## Development Guide

This repository includes scripts to simplify development and testing:

### Development Scripts

1. **Local Development Environment**

   The easiest way to work with the Chroma MCP Server during development is using the `run_chromamcp_local.py` script:

   ```bash
   # Run with default settings
   ./run_chromamcp_local.py
   
   # Run with custom settings
   ./run_chromamcp_local.py --log-dir custom_logs --data-dir custom_data
   ```

   This script:
   - Creates a dedicated virtual environment (`.venv_chromamcp`)
   - Installs the package with development dependencies
   - Runs the server with the specified arguments

2. **UVX Integration**

   For experimenting with UVX integration, use the following scripts:

   ```bash
   # Install the package and make it findable by UVX
   ./setup_for_uvx.py
   
   # Run with UVX in a dedicated environment
   ./run_with_uvx.py
   ```

   See the `docs/uvx_integration_status.md` file for detailed information about UVX integration efforts.

3. **MCP Integration**

   For integration with Cursor MCP, add this to your `.cursor/mcp.json`:

   ```json
   {
     "mcpServers": {
       "chroma_mcp_server": {
         "command": "python",
         "args": [
           "-m",
           "chroma_mcp.server",
           "--data-dir", "data",
           "--log-dir", "logs"
         ],
         "env": {
           "PYTHONUNBUFFERED": "1",
           "PYTHONIOENCODING": "utf-8"
         }
       }
     }
   }
   ```

   This configuration assumes the package is installed in the environment where Cursor runs. For local development, use absolute paths:

   ```json
   {
     "mcpServers": {
       "chroma_mcp_server": {
         "command": "/path/to/your/.venv_chromamcp/bin/python",
         "args": [
           "-m",
           "chroma_mcp.server",
           "--data-dir", "/path/to/your/data",
           "--log-dir", "/path/to/your/logs"
         ],
         "env": {
           "PYTHONUNBUFFERED": "1",
           "PYTHONIOENCODING": "utf-8"
         }
       }
     }
   }
   ```

For detailed information about our tested approaches and current status, see `docs/uvx_integration_status.md`.
