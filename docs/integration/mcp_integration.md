# MCP Integration Guide into your IDE of choice

This guide explains how to integrate Chroma MCP Server with your IDE of choice (e.g. Cursor AI) to enable vector database capabilities in your AI applications.

## Prerequisites

- IDE (e.g. Cursor AI) installed
- Python 3.10 or higher
- `uv` and `uvx` for optimal integration
  
## Installation

1. Install the Chroma MCP Server package:

   ```bash
   # Standard installation
   pip install chroma-mcp-server
   
   # Or with UV for better dependency management
   uv pip install chroma-mcp-server
   ```

2. Install UVX for seamless integration with Cursor:

   ```bash
   pip install uv uvx
   ```

## MCP Configuration in Workspace

Create or update the MCP config file in your project directory, depending on the actual IDE:

|IDE|MCP Workspace Config|
|---|---|
|Cursor|`.cursor/mcp.json`|
|VS Code|`.vscode/mcp.json`|
|Windsurf|`~/.codeium/windsurf/mcp_config.json`|

### Example Configuration

Here is an example `.cursor/mcp.json` configuration demonstrating how to set up development, test, and production servers:

```json
{
  "mcpServers": {
    "chroma_dev": {
      "command": "/path/to/project/scripts/run_chroma_mcp_server_dev.sh",
      "args": [],
      "env": {
        "CHROMA_CLIENT_TYPE": "persistent",
        "CHROMA_DATA_DIR": "/path/to/your/dev_data", // Separate data for dev
        "CHROMA_LOG_DIR": "/path/to/your/dev_logs",  // Separate logs for dev
        "LOG_LEVEL": "DEBUG",
        "MCP_LOG_LEVEL": "DEBUG"
        // Other env vars as needed (e.g., API keys, embedding function)
      }
    },
    "chroma_test": {
      "command": "uvx",
      "args": [
        "--refresh", // Ensure uvx checks for the latest version
        "--default-index", "https://test.pypi.org/simple/", // Prioritize TestPyPI
        "--index", "https://pypi.org/simple/", // Fallback to PyPI
        "--index-strategy", "unsafe-best-match", // Allows resolving dependencies across indexes
        "chroma-mcp-server@latest" // Fetch the latest version from TestPyPI
        // Add server arguments here if needed, e.g., "--embedding-function=accurate"
      ],
      "env": {
        "CHROMA_CLIENT_TYPE": "persistent",
        "CHROMA_DATA_DIR": "/path/to/your/test_data", // Separate data for testing
        "CHROMA_LOG_DIR": "/path/to/your/test_logs",  // Separate logs for testing
        "LOG_LEVEL": "INFO",
        "MCP_LOG_LEVEL": "INFO"
        // Other env vars as needed
      }
    },
    "chroma_prod": {
      "command": "uvx", // Use uvx to run the globally installed version
      "args": [
        "chroma-mcp-server"
        // Add server arguments here, e.g., "--embedding-function=accurate", "--client-type=cloud"
      ],
      "env": {
        "CHROMA_CLIENT_TYPE": "persistent", // Or 'cloud', 'http' as needed
        "CHROMA_DATA_DIR": "/path/to/your/prod_data", // Production data directory
        "CHROMA_LOG_DIR": "/path/to/your/prod_logs",  // Production log directory
        "LOG_LEVEL": "INFO",
        "MCP_LOG_LEVEL": "INFO"
        // Required env vars for your chosen client type (e.g., API keys for cloud)
      }
    }
  }
}
```

**Key Points:**

- **`chroma_dev`**: Uses the `run_chroma_mcp_server_dev.sh` script (replace the path with your absolute path) to run the server directly from your local source code via Hatch. Ideal for development.
- **`chroma_test`**: Uses `uvx` to automatically fetch and run the latest version from TestPyPI.
- **`chroma_prod`**: Uses `uvx` to run the version installed globally (usually the latest stable from PyPI).
- **Paths**: Use absolute paths for `command` and ensure data/log directories are unique for each environment.

## Available Environment Variables

| Variable | Description | Default | Examples |
|----------|-------------|---------|----------|
| `CHROMA_CLIENT_TYPE` | Type of client connection | `persistent` | `ephemeral`, `persistent`, `http`, `cloud` |
| `CHROMA_DATA_DIR` | Storage location for persistent client | `./chroma_data` | `./data`, `/opt/chroma/data` |
| `CHROMA_LOG_DIR` | Storage location for logs | `./chroma_logs` | `./logs`, `/var/log/chroma` |
| `LOG_RETENTION_DAYS` | Number of days to keep log files before automatic cleanup | `7` | `14`, `30` |
| `CHROMA_HOST` | Host address for HTTP client | `localhost` | `127.0.0.1`, `chroma.example.com` |
| `CHROMA_PORT` | Port for HTTP client | `8000` | `8000`, `9000` |
| `CHROMA_SSL` | Whether to use SSL | `false` | `true`, `false` |
| `CHROMA_TENANT` | Tenant ID for Cloud client | None | `tenant1` |
| `CHROMA_DATABASE` | Database name for Cloud client | None | `db1` |
| `CHROMA_API_KEY` | API key for Cloud client | None | `sk_...` |
| `CPU_EXECUTION_PROVIDER` | Force CPU execution provider | `auto` | `true`, `false`, `auto` |
| `CHROMA_EMBEDDING_FUNCTION` | Name of the embedding function to use. API keys may be needed for some. | `default` | `default`, `fast`, `accurate`, `openai`, `cohere`, `huggingface`, `jina`, `voyageai`, `gemini` |
| `LOG_LEVEL` | Log level for server | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `MCP_LOG_LEVEL` | Log level for MCP interface | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## Usage in Cursor

Once configured, Cursor will automatically start the Chroma MCP Server when needed. You can then use the MCP functions to interact with the vector database:

```python
# Example usage in Cursor chat
mcp_chroma_create_collection(collection_name="my_docs")
# Add documents individually using the appropriate tool
mcp_chroma_add_document_with_id_and_metadata(
    collection_name="my_docs",
    document="This is document 1",
    id="doc1",
    metadata='{"source": "file1"}'
)
mcp_chroma_add_document_with_id_and_metadata(
    collection_name="my_docs",
    document="This is document 2",
    id="doc2",
    metadata='{"source": "file2"}'
)

# Step 1: Query to get relevant document IDs
results = mcp_chroma_query_documents(
    collection_name="my_docs",
    query_texts=["document"],
    n_results=2 # Optional, defaults to 10
)

# Assuming 'results' contains a structure like {"ids": [["id1", "id2"]], ...}
# Extract the IDs (adjust based on actual result structure)
retrieved_ids = results['ids'][0] 

# Step 2: Fetch the document details using the retrieved IDs
if retrieved_ids:
    document_details = mcp_chroma_get_documents_by_ids(
        collection_name="my_docs",
        ids=retrieved_ids
    )
    print(document_details) # Now contains documents, metadatas etc.

```

## Automated Chat History Logging

A key feature enabled by this MCP integration is the ability to automatically log summaries of chat interactions (prompts, AI responses, actions) directly into a ChromaDB collection (e.g., `chat_history_v1`). This is typically configured using IDE-specific rules that instruct the AI assistant to perform the logging after each response.

See the **[Automated Chat History Logging Guide](automated_chat_logging.md)** for details on setting up this feature in your IDE.

## Troubleshooting

### Common Issues

1. **"Command not found" error**:
   - Ensure `chroma-mcp-server` is installed and in your PATH
   - Check that you've activated the correct virtual environment

2. **"Unable to connect to MCP server" error**:
   - Check that the server is running properly
   - Verify your `.cursor/mcp.json` configuration

3. **Embedding errors**:
   - If using embedding functionality, install the full dependencies:

     ```bash
     pip install "chroma-mcp-server[full]"
     ```

   - Or specify your own embedding provider in queries

4. **UVX-related errors**:
   - Ensure UVX is properly installed: `pip install uvx`
   - Try using the non-UVX configuration if issues persist

5. **Storage errors**:
   - Check that `CHROMA_DATA_DIR` points to a writable directory
   - Ensure sufficient disk space is available

## Further Resources

- [Chroma MCP Server Documentation](https://github.com/djm81/chroma_mcp_server)
- [Cursor MCP Documentation](https://cursor.sh/docs/mcp)
- [Chroma Documentation](https://docs.trychroma.com/)
