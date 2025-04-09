import importlib.metadata
from typing import Dict

from mcp.server.fastmcp import FastMCP

# It's crucial that logging is configured *before* this runs
# if we want these initial logs. Assuming config_server runs first.
# from .utils.logging_utils import get_logger
# logger = get_logger("app") # Get a logger specific to app initialization

# logger.info("Creating shared FastMCP instance...")

# Create the single, shared FastMCP instance
mcp = FastMCP()

# logger.info("Shared FastMCP instance created.")

# Register server utility tools directly here if they are simple
@mcp.tool(name="chroma_get_server_version", description="Return the installed version of the chroma-mcp-server package.")
def get_version_tool() -> Dict[str, str]:
     """Return the installed version of the chroma-mcp-server package."""
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
# logger.info("Importing tool modules to trigger decorator registration...")
from .tools import collection_tools
from .tools import document_tools
from .tools import thinking_tools
# logger.info("Tool module import complete.")
