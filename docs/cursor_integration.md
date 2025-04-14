# Cursor Integration Guide

This guide explains how to integrate Chroma MCP Server with Cursor AI to enable vector database capabilities in your AI applications.

## Prerequisites

- Cursor AI installed (<https://cursor.sh>)
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

## Configuration

Create or update the `.cursor/mcp.json` file in your project directory:

### Basic Configuration

```json
{
  "mcpServers": {
    "chroma": {
      "command": "chroma-mcp-server",
      "args": [
        "--embedding-function=default"
      ],
      "env": {
        "CHROMA_CLIENT_TYPE": "persistent",
        "CHROMA_DATA_DIR": "./chroma_data",
        "CHROMA_LOG_DIR": "./chroma_logs",
        "LOG_LEVEL": "INFO",
        "MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Optimized Configuration (with UVX)

```json
{
  "mcpServers": {
    "chroma": {
      "command": "uvx",
      "args": [
        "chroma-mcp-server",
        "--embedding-function=default"
      ],
      "env": {
        "CHROMA_CLIENT_TYPE": "persistent",
        "CHROMA_DATA_DIR": "./chroma_data",
        "CHROMA_LOG_DIR": "./chroma_logs",
        "LOG_LEVEL": "INFO",
        "MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

## Available Environment Variables

| Variable | Description | Default | Examples |
|----------|-------------|---------|----------|
| `CHROMA_CLIENT_TYPE` | Type of client connection | `persistent` | `ephemeral`, `persistent`, `http`, `cloud` |
| `CHROMA_DATA_DIR` | Storage location for persistent client | `./chroma_data` | `./data`, `/opt/chroma/data` |
| `CHROMA_LOG_DIR` | Storage location for logs | `./chroma_logs` | `./logs`, `/var/log/chroma` |
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
results = mcp_chroma_query_documents(
    collection_name="my_docs",
    query_texts=["document"],
    n_results=2 # Optional, defaults to 10
)
```

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
