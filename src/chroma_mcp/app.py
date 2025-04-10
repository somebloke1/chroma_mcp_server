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

from mcp.server import Server

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


# Tool modules are now imported directly by server.py where needed.
# Removing imports from here to break potential circular dependencies.
