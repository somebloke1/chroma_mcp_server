#!/usr/bin/env python3
"""
Command-line interface entry point for the Chroma MCP Server.

This module provides a command-line interface (CLI) to configure and run the
Chroma MCP server, which facilitates interaction with ChromaDB via the
Model Context Protocol (MCP).
"""

import os
import sys
import argparse
from typing import List, Optional


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parses command line arguments for the server configuration.

    Sets up the argument parser with options for client type, data/log directories,
    logging level, connection details (HTTP/Cloud), embedding function behavior,
    and dotenv file path. Defaults are sourced from environment variables where
    applicable.

    Args:
        args: A list of strings representing the command line arguments.
              If None, arguments are taken from sys.argv.

    Returns:
        An argparse.Namespace object containing the parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Chroma MCP Server")

    # Client configuration
    parser.add_argument(
        "--client-type",
        choices=["http", "cloud", "persistent", "ephemeral"],
        default=os.getenv("CHROMA_CLIENT_TYPE", "ephemeral"),
        help="Type of Chroma client to use",
    )

    parser.add_argument("--data-dir", default=os.getenv("CHROMA_DATA_DIR"), help="Directory for persistent client data")

    parser.add_argument(
        "--log-dir", default=os.getenv("CHROMA_LOG_DIR"), help="Directory for log files (default: current directory)"
    )

    # Logging level
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=os.getenv("LOG_LEVEL", "INFO").upper(),
        help="Set the logging level (overrides LOG_LEVEL env var)",
    )

    # HTTP client options
    parser.add_argument("--host", default=os.getenv("CHROMA_HOST"), help="Chroma host for HTTP client")

    parser.add_argument("--port", default=os.getenv("CHROMA_PORT"), help="Chroma port for HTTP client")

    parser.add_argument(
        "--ssl",
        type=lambda x: x.lower() in ["true", "yes", "1", "t", "y"],
        default=os.getenv("CHROMA_SSL", "true").lower() in ["true", "yes", "1", "t", "y"],
        help="Use SSL for HTTP client",
    )

    # Cloud client options
    parser.add_argument("--tenant", default=os.getenv("CHROMA_TENANT"), help="Chroma tenant for cloud client")

    parser.add_argument("--database", default=os.getenv("CHROMA_DATABASE"), help="Chroma database for cloud client")

    parser.add_argument("--api-key", default=os.getenv("CHROMA_API_KEY"), help="Chroma API key for cloud client")

    # General options
    parser.add_argument(
        "--dotenv-path", default=os.getenv("CHROMA_DOTENV_PATH", ".env"), help="Path to .env file (optional)"
    )

    # Embedding function options
    parser.add_argument(
        "--cpu-execution-provider",
        choices=["auto", "true", "false"],
        default=os.getenv("CHROMA_CPU_EXECUTION_PROVIDER", "auto"),
        help="Force CPU execution provider for embedding functions",
    )

    # Add argument for the chosen embedding function
    parser.add_argument(
        "--embedding-function",
        default=os.getenv("CHROMA_EMBEDDING_FUNCTION", "default"),
        help=(
            "Name of the embedding function to use. Choices: "
            "'default'/'fast' (Local CPU/ONNX, balanced), "
            "'accurate' (Local CPU/GPU via sentence-transformers, higher accuracy), "
            "'openai' (API, requires OPENAI_API_KEY), "
            "'cohere' (API, requires COHERE_API_KEY), "
            "'google' (API, requires GOOGLE_API_KEY, covers Gemini models), "
            "'huggingface' (API, requires HUGGINGFACE_API_KEY), "
            "'voyageai' (API, requires VOYAGEAI_API_KEY), "
            "'bedrock' (AWS API, uses AWS credentials, e.g., env vars), "
            "'ollama' (Local/Remote API, uses OLLAMA_BASE_URL, defaults to http://localhost:11434). "
            "Ensure required API keys/credentials/URLs are set in environment variables."
        ),
        dest="embedding_function_name",
    )

    return parser.parse_args(args)


def main() -> int:
    """Main entry point for the Chroma MCP server CLI.

    Parses command-line arguments, loads the server configuration based on them,
    and runs the main server loop. Handles graceful shutdown on KeyboardInterrupt
    and logs other exceptions.

    Returns:
        0 on successful execution or graceful shutdown, 1 on error.
    """
    # Parse arguments
    args = parse_args()

    # Import server module here to avoid circular imports
    from chroma_mcp.server import config_server, main as server_main

    try:
        # Configure server
        config_server(args)

        # Run the server
        return server_main()
    except KeyboardInterrupt:
        print("Server stopped by user", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Error running server: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
