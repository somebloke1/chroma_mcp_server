# Testing Chroma MCP Server Installation

This guide provides steps to verify your Chroma MCP Server installation is working correctly.

## Prerequisites

- Chroma MCP Server installed
- Python 3.10 or higher
- A terminal or command prompt

## Basic Installation Verification

### 1. Check Command Availability

First, verify that the `chroma-mcp-server` command is available in your environment:

```bash
chroma-mcp-server --help
```

You should see the help message listing available options.

### 2. Check Package Version

Verify the installed version:

```bash
pip show chroma-mcp-server
```

This should display the package information including version, dependencies, and installation location.

## Functional Testing

### 1. Start the Server

Start the server with default settings:

```bash
chroma-mcp-server
```

The server should start without errors and display a message indicating it's waiting for connections.

### 2. Test Basic Functionality

In a separate terminal, create a simple Python script to test the server:

```python
# test_chroma_mcp.py
import os
import asyncio
from chromadb import Client
from chromadb.utils import embedding_functions

async def test_connection():
    # Create a client
    client = Client(
        client_type="persistent",
        path="./test_data"
    )
    
    # Create a collection
    collection = client.create_collection(
        name="test_collection",
        embedding_function=embedding_functions.DefaultEmbeddingFunction()
    )
    
    # Add documents
    collection.add(
        documents=["This is a test document", "This is another test document"],
        metadatas=[{"source": "test1"}, {"source": "test2"}],
        ids=["id1", "id2"]
    )
    
    # Query
    results = collection.query(
        query_texts=["test document"],
        n_results=2
    )
    
    print("Query results:", results)
    
    # Clean up
    client.delete_collection("test_collection")
    print("Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_connection())
```

Run the script:

```bash
python test_chroma_mcp.py
```

## Testing with Cursor

If you're using Cursor, you can test the integration with Cursor's chat:

1. Configure the MCP server in your `.cursor/mcp.json` as described in the Cursor integration guide.

2. Open Cursor and use the chat to execute MCP commands:

```bash
Please create a chroma collection called "test_collection" and add two documents
```

The Cursor AI should use the MCP functions to create the collection and add documents.

## Testing UVX Integration

If you're using UVX, verify the integration:

```bash
# Verify UVX is installed
uvx --version

# Test running the server with UVX
uvx chroma-mcp-server --help
```

## Common Issues and Solutions

### Missing Dependencies

If you encounter errors about missing dependencies, install the full package:

```bash
pip install "chroma-mcp-server[full]"
```

### Database Access Issues

For persistent storage errors:

```bash
# Check the data directory exists and is writable
mkdir -p ./chroma_data
touch ./chroma_data/test.txt
rm ./chroma_data/test.txt
```

### Port Already in Use

If port 8000 is already in use:

```bash
# Try using a different port
chroma-mcp-server --port 8001
```

## Next Steps

Once you've verified your installation is working, you can:

1. Configure the server for your specific needs
2. Integrate with your AI applications
3. Start building your RAG (Retrieval Augmented Generation) workflows
