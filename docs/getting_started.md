# Getting Started with Chroma MCP Server

This guide will help you set up and start using the Chroma MCP Server.

## Prerequisites

- Python 3.10 or higher
- Pip package manager
- Git (optional, for development)

## Installation

### Option 1: Simple Installation (Recommended)

```bash
# Install the package from PyPI
pip install chroma-mcp-server

# For full functionality with embedding models
pip install chroma-mcp-server[full]
```

### Option 2: Development Setup

```bash
# Clone the repository (if not already done)
git clone https://github.com/yourusername/chroma-mcp-server.git
cd chroma-mcp-server

# Install Hatch if not already installed
pip install hatch

# Create a development environment
hatch shell

# Or run the helper script
./develop.sh
```

## Configuration

### Environment Variables

You can configure the server using environment variables:

```bash
# Client Configuration
export CHROMA_CLIENT_TYPE=persistent  # Options: http, cloud, persistent, ephemeral
export CHROMA_DATA_DIR=./data         # Required for persistent client
export CHROMA_LOG_DIR=./logs          # Directory for log files
export CHROMA_HOST=localhost          # Required for http client
export CHROMA_PORT=8000               # Optional for http client

# Server Settings
export LOG_LEVEL=INFO                 # Optional, default: INFO
export MCP_LOG_LEVEL=INFO             # Optional, controls MCP framework logging
```

### Command-line Options

Alternatively, you can use command-line options:

```bash
chroma-mcp-server --client-type persistent --data-dir ./data --log-dir ./logs
```

### Configure Cursor MCP Integration

If you want to use the server with Cursor AI, add this to your `.cursor/mcp.json` file:

```json
{
  "mcpServers": {
    "chroma": {
      "command": "chroma-mcp-server",
      "args": [],
      "env": {
        "CHROMA_CLIENT_TYPE": "persistent",
        "CHROMA_DATA_DIR": "/path/to/data/dir",
        "CHROMA_LOG_DIR": "/path/to/logs/dir",
        "LOG_LEVEL": "INFO",
        "MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

## Running the Server

### Standalone Mode

For development and testing, you can run the server directly:

```bash
# If installed from PyPI
chroma-mcp-server

# If in a development environment
hatch run python -m chroma_mcp.server
```

### Verifying the Server

To verify the server is working, you can run the tests:

```bash
# Run all tests
hatch run python -m pytest

# Or use the test script
./test.sh
```

## Basic Usage Example

This example shows how to use the server from a Python client:

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # Set up server parameters
    server_params = StdioServerParameters(
        command="chroma-mcp-server",  # Use the installed command
        args=[],
        env={
            "PYTHONUNBUFFERED": "1", 
            "CHROMA_CLIENT_TYPE": "ephemeral"  # In-memory database for testing
        }
    )
    
    # Connect to the server
    async with stdio_client(server_params) as (stdio, write):
        async with ClientSession(stdio, write) as session:
            # Initialize the session
            await session.initialize()
            
            # List available tools
            response = await session.list_tools()
            print(f"Available tools: {[tool.name for tool in response.tools]}")
            
            # Create a collection
            create_result = await session.call_tool("chroma_create_collection", {
                "collection_name": "my_collection",
                "description": "A test collection"
            })
            print(f"Created collection: {create_result.content[0].text}")
            
            # Add documents
            add_result = await session.call_tool("chroma_add_documents", {
                "collection_name": "my_collection",
                "documents": ["This is a test document", "Another test document"]
            })
            print(f"Added documents: {add_result.content[0].text}")
            
            # Query documents
            query_result = await session.call_tool("chroma_query_documents", {
                "collection_name": "my_collection",
                "query_texts": ["test document"],
                "n_results": 2
            })
            print(f"Query results: {query_result.content[0].text}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Optimized Dependencies

The package has been optimized with three dependency groups:

1. **Core Dependencies** (installed by default):
   - `chromadb` - Vector database
   - `fastmcp` - MCP framework
   - `python-dotenv` - Environment variable management
   - `pydantic` - Data validation
   - `fastapi` - API framework
   - `uvicorn` - ASGI server
   - `numpy` - Numerical operations

2. **Full Dependencies** (optional):
   - `onnxruntime` - Optimized ML runtime
   - `sentence-transformers` - Text embedding models
   - `httpx` - HTTP client for remote connections

3. **Development Dependencies** (for contributors):
   - Testing tools (pytest, pytest-cov)
   - Code quality tools (black, isort, mypy)

## Next Steps

- Explore the [full documentation](../README.md)
- Check out the [API reference](./api_reference.md)
- Learn about [advanced configuration options](./api_reference.md)
