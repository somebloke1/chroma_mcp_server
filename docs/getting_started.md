# Getting Started with Chroma MCP Server

This guide will help you set up and start using the Chroma MCP Server.

## Prerequisites

- Python 3.12 or higher
- Pip package manager
- Git (optional, for cloning the repository)

## Installation

### Option 1: Using the setup script (recommended)

```bash
# Clone the repository (if not already done)
git clone https://github.com/yourusername/chroma-mcp-server.git
cd chroma-mcp-server

# Run the setup script
./setup.sh  # On Unix/macOS
```

The setup script will:

- Create a virtual environment
- Install all dependencies
- Set up the package in development mode
- Verify the installation

### Option 2: Manual setup

```bash
# Clone the repository (if not already done)
git clone https://github.com/yourusername/chroma-mcp-server.git
cd chroma-mcp-server

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Unix/macOS
.venv\Scripts\activate    # On Windows

# Install the package in development mode
pip install -e ".[dev]"
```

## Configuration

### Setting Up Environment Variables

Create a `.env` file in the project root with the following options:

```ini
# Client Configuration
CHROMA_CLIENT_TYPE=persistent  # Options: http, cloud, persistent, ephemeral
CHROMA_DATA_DIR=./data         # Required for persistent client
CHROMA_HOST=localhost          # Required for http client
CHROMA_PORT=8000              # Optional for http client

# Server Settings
LOG_LEVEL=INFO                # Optional, default: INFO
MCP_LOG_LEVEL=INFO           # Optional, controls MCP framework logging
```

### Configure Cursor MCP Integration

If you want to use the server with Cursor AI, add this to your `.cursor/mcp.json` file:

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

## Running the Server

### Standalone Mode

For development and testing, you can run the server directly:

```bash
# Activate the virtual environment if not already active
source .venv/bin/activate  # On Unix/macOS
.venv\Scripts\activate    # On Windows

# Run the server
python run_chroma_mcp.py
```

### Verifying the Server

To verify the server is working:

```bash
# Run the verification script
./tests/run_chroma_mcp_test.sh  # On Unix/macOS
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
        command="python",
        args=["path/to/run_chroma_mcp.py"],
        env={"PYTHONUNBUFFERED": "1"}
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

## Next Steps

- Explore the [full documentation](../README.md)
- Check out the [example scripts](../examples)
- Review the [API reference](./api_reference.md)
