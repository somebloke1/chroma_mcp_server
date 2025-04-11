#!/usr/bin/env python3
"""
A simple example client for the Chroma MCP Server that demonstrates:
1. Connecting to the server
2. Creating a collection
3. Adding documents
4. Querying documents
"""

import os
import sys
import asyncio
from contextlib import AsyncExitStack
from pathlib import Path
import json

# Add the parent directory to sys.path to allow importing the server module
parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))

try:
    # Import the MCP client library
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("Error: MCP client library not found. Please install it with:")
    print("pip install mcp")
    sys.exit(1)

# Path to the runner script
server_script = os.path.join(parent_dir, "run_chroma_mcp.py")

# Use the current Python executable
PYTHON_EXECUTABLE = sys.executable


async def main():
    """Run a simple demo of Chroma MCP server capabilities."""
    print("Starting Chroma MCP Client Demo")
    print(f"Using server script at: {server_script}")

    # Create the async exit stack for resource cleanup
    exit_stack = AsyncExitStack()

    try:
        # Set up server parameters
        server_params = StdioServerParameters(
            command=PYTHON_EXECUTABLE, args=[server_script], env={"PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
        )

        print("Connecting to server...")

        # Connect to the server
        stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport

        # Create a client session
        session = await exit_stack.enter_async_context(ClientSession(stdio, write))

        # Initialize the session
        print("Initializing session...")
        await session.initialize()

        # List available tools
        print("Listing available tools...")
        response = await session.list_tools()
        tools = response.tools
        print(f"Found {len(tools)} available tools: {[tool.name for tool in tools]}")

        # Create a test collection
        collection_name = "demo_collection"
        print(f"\nCreating collection: {collection_name}")
        try:
            create_result = await session.call_tool(
                "chroma_create_collection",
                {"collection_name": collection_name, "description": "A demo collection for testing"},
            )
            for content in create_result.content:
                print(f"Collection created: {content.text}")
                collection_info = json.loads(content.text)
                print(f"Collection ID: {collection_info.get('id')}")
        except Exception as e:
            print(f"Error creating collection: {e}")
            print("Continuing with existing collection...")

        # Add documents to the collection
        test_documents = [
            "The Chroma MCP Server provides a standardized interface for vector databases.",
            "ChromaDB is an open-source embedding database for AI applications.",
            "Vector databases are optimized for storing and searching high-dimensional vectors.",
            "Semantic search allows finding documents based on meaning rather than keywords.",
        ]

        print(f"\nAdding {len(test_documents)} documents to collection...")
        add_result = await session.call_tool(
            "chroma_add_documents", {"collection_name": collection_name, "documents": test_documents}
        )
        for content in add_result.content:
            print(f"Documents added: {content.text}")

        # Query the collection
        query = "vector database for AI"
        print(f"\nQuerying collection with: '{query}'")
        query_result = await session.call_tool(
            "chroma_query_documents",
            {
                "collection_name": collection_name,
                "query_texts": [query],
                "n_results": 2,
                "include": ["documents", "distances"],
            },
        )
        for content in query_result.content:
            results = json.loads(content.text)
            print("\nQuery results:")
            for i, (doc, dist) in enumerate(zip(results["documents"][0], results["distances"][0])):
                print(f"{i+1}. [{dist:.4f}] {doc}")

        # Clean up (optional)
        print("\nDemo completed. Delete the test collection? (y/n)")
        if input().lower() == "y":
            delete_result = await session.call_tool("chroma_delete_collection", {"collection_name": collection_name})
            for content in delete_result.content:
                print(f"Collection deleted: {content.text}")

    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Clean up resources
        await exit_stack.aclose()
        print("\nDemo finished.")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())
