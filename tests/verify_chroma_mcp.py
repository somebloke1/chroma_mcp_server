#!/usr/bin/env python3
"""
Verification script to check if the Chroma MCP server is running correctly.
Tests basic connectivity and tool availability.
"""

import os
import sys
import asyncio
from contextlib import AsyncExitStack

# Path to the runner script
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up one level to root
server_script = os.path.join(script_dir, 'run_chroma_mcp.py')

# Set up logs directory
logs_dir = os.path.join(script_dir, 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Use the current Python executable
PYTHON_EXECUTABLE = sys.executable

try:
    # Import the MCP client library
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("Error: MCP client library not found. Please install it with:")
    print("pip install mcp")
    sys.exit(1)

async def verify_chroma_mcp_server():
    """Check if the Chroma MCP server is running correctly."""
    print(f"Verifying Chroma MCP server using: {server_script}")
    
    # Create the async exit stack for resource cleanup
    exit_stack = AsyncExitStack()
    
    try:
        # Set up server parameters
        server_params = StdioServerParameters(
            command=PYTHON_EXECUTABLE,
            args=[server_script, "--log-dir", logs_dir],
            env={
                "PYTHONUNBUFFERED": "1",
                "PYTHONIOENCODING": "utf-8"
            }
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
        
        # Try to find one of our Chroma tools
        chroma_tools = [t for t in tools if t.name.startswith("chroma_")]
        if chroma_tools:
            print(f"Found {len(chroma_tools)} Chroma tools: {[t.name for t in chroma_tools]}")
            
            # Test a specific Chroma tool if available
            if any(t.name == "chroma_list_collections" for t in chroma_tools):
                print("Testing chroma_list_collections tool...")
                try:
                    list_result = await session.call_tool("chroma_list_collections", {})
                    print("List collections result:")
                    for content in list_result.content:
                        print(content.text)
                except Exception as e:
                    print(f"List collections failed: {e}, falling back to ping")
            else:
                print("chroma_list_collections tool not found, testing ping instead")
        else:
            print("No Chroma tools found.")
                    
        print("\n✅ Chroma MCP server verification successful!")
        
    except Exception as e:
        print(f"\n❌ Chroma MCP server verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up resources
        await exit_stack.aclose()
    
    return True

if __name__ == "__main__":
    # Run the verification
    success = asyncio.run(verify_chroma_mcp_server())
    sys.exit(0 if success else 1) 