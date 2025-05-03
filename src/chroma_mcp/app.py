"""
Application setup for the Chroma MCP Server.

This module initializes the shared FastMCP instance (`mcp`) used throughout the
application. It also registers a basic server utility tool (`chroma_get_server_version`)
directly via the decorator.

Crucially, it imports the tool modules (`.tools.collection_tools`, etc.) AFTER
the `mcp` instance is created. This allows the `@mcp.tool` decorators within
those modules to automatically register themselves with the shared `mcp` instance.
"""
import importlib.metadata
from typing import Dict
import sys

from mcp.server import Server
from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.stdio import stdio_server

# Create the single, shared standard Server instance
# Using 'server' instead of 'mcp' to avoid confusion with the protocol name
server = Server(name="chroma-mcp-server")

# logger.info("Shared standard MCP Server instance created.")

# Register server utility tools directly here if they are simple
# REMOVE: We will define this in list_tools and handle in call_tool now
# @mcp.tool(name="chroma_get_server_version", description="Return the installed version of the chroma-mcp-server package.")
# def get_version_tool() -> Dict[str, str]:
#      """Return the installed version of the chroma-mcp-server package.
#
#      This tool takes no arguments.
#
#      Returns:
#          A dictionary containing the package name ('chroma-mcp-server') and its
#          installed version string. Returns 'unknown (not installed)' or 'error (...)'
#          if the version cannot be determined.
#      """
#      try:
#          version = importlib.metadata.version('chroma-mcp-server')
#          return {"package": "chroma-mcp-server", "version": version}
#      except importlib.metadata.PackageNotFoundError:
#          return {"package": "chroma-mcp-server", "version": "unknown (not installed)"}
#      except Exception as e:
#         # TODO: Add logging here if possible/needed
#         # logger.error(f"Error getting server version: {str(e)}")
#          return {"package": "chroma-mcp-server", "version": f"error ({str(e)})"}

# Tool modules will be imported after server is defined to allow registration.


async def main_stdio():
    """Run the server using stdio transport."""
    # logger.info("Entering stdio_server context manager...")
    async with stdio_server() as (read_stream, write_stream):
        # logger.info("Stdio streams acquired. Triggering tool handler registration...")
        # Import tool modules HERE to trigger registration
        try:
            from chroma_mcp.tools import collection_tools
            from chroma_mcp.tools import document_tools
            from chroma_mcp.tools import thinking_tools

            # logger.info("Successfully imported tool modules inside main_stdio.")
            # Explicitly import server module AFTER tools to ensure decorators run
            import chroma_mcp.server

            # logger.info("Explicitly imported chroma_mcp.server.")
        except ImportError as e:
            # logger.error(f"Failed to import tool modules/server inside main_stdio: {e}", exc_info=True)
            print(f"Failed to import tool modules/server inside main_stdio: {e}", file=sys.stderr)
            raise

        # logger.info("Creating initialization options...")
        init_options = server.create_initialization_options(
            notification_options=NotificationOptions(
                # Configure notifications if needed
            )
        )
        # logger.info("Initialization options created. Calling server.run...")
        try:
            await server.run(
                read_stream,
                write_stream,
                init_options,
                raise_exceptions=True,
            )
            # logger.info("server.run completed successfully.")
        except Exception as e:
            # logger.error("Error during server.run: %s", e, exc_info=True)
            print(f"Error during server.run: {e}", file=sys.stderr)
            raise


# REMOVE the _register_tool_handlers function
# def _register_tool_handlers():
#    ...

# Note: We could also place the imports directly at the top level here,
# but putting them in a function called from main_stdio ensures they run
# only when the stdio server is starting and makes the dependency clearer.
