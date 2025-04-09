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

from mcp.server.fastmcp import FastMCP

# Create the single, shared FastMCP instance
mcp = FastMCP()

# logger.info("Shared FastMCP instance created.")

# Register server utility tools directly here if they are simple
@mcp.tool(name="chroma_get_server_version", description="Return the installed version of the chroma-mcp-server package.")
def get_version_tool() -> Dict[str, str]:
     """Return the installed version of the chroma-mcp-server package.

     This tool takes no arguments.

     Returns:
         A dictionary containing the package name ('chroma-mcp-server') and its
         installed version string. Returns 'unknown (not installed)' or 'error (...)'
         if the version cannot be determined.
     """
     try:
         version = importlib.metadata.version('chroma-mcp-server')
         return {"package": "chroma-mcp-server", "version": version}
     except importlib.metadata.PackageNotFoundError:
         return {"package": "chroma-mcp-server", "version": "unknown (not installed)"}
     except Exception as e:
        # TODO: Add logging here if possible/needed
        # logger.error(f"Error getting server version: {str(e)}")
         return {"package": "chroma-mcp-server", "version": f"error ({str(e)})"}


# Import tool modules AFTER mcp instance is created.
# This allows the @mcp.tool decorators within these modules to
# find and register themselves with the 'mcp' instance above.
from .tools import collection_tools
from .tools import document_tools
from .tools import thinking_tools
