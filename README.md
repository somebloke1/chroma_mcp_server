# Chroma MCP Server

A Model Context Protocol (MCP) server integration for [Chroma](https://www.trychroma.com/), the open-source embedding database.

## Overview

The Chroma MCP Server allows you to connect AI applications with Chroma through the Model Context Protocol. This enables AI models to:

- Store and retrieve embeddings
- Perform semantic search on vector data
- Manage collections of embeddings
- Support RAG (Retrieval Augmented Generation) workflows

## Installation

Choose your preferred installation method:

### Standard Installation

```bash
# Using pip
pip install chroma-mcp-server

# Using UVX (recommended for Cursor)
uv pip install chroma-mcp-server
```

### Full Installation (with embedding models)

```bash
# Using pip
pip install chroma-mcp-server[full]

# Using UVX
uv pip install "chroma-mcp-server[full]"
```

### Development Installation

```bash
# Clone the repository
git clone https://github.com/djm81/chroma_mcp_server.git
cd chroma_mcp_server

# Install in development mode
pip install -e .
```

## Usage

### Starting the server

```bash
# Using the command-line executable
chroma-mcp-server

# Or using the Python module
python -m chroma_mcp.server
```

Or use the provided scripts during development:

```bash
# For development environment
./develop.sh

# To build the package
./build.sh

# To publish to PyPI
./publish.sh
```

### Configuration

The server can be configured with command-line options or environment variables:

#### Command-line Options

```bash
chroma-mcp-server --client-type persistent --data-dir ./my_data
```

#### Environment Variables

```bash
export CHROMA_CLIENT_TYPE=persistent
export CHROMA_DATA_DIR=./my_data
chroma-mcp-server
```

#### Available Configuration Options

- `--client-type`: Type of Chroma client (`ephemeral`, `persistent`, `http`, `cloud`)
- `--data-dir`: Path to data directory for persistent client
- `--log-dir`: Path to log directory
- `--host`: Host address for HTTP client
- `--port`: Port for HTTP client
- `--ssl`: Whether to use SSL for HTTP client
- `--tenant`: Tenant ID for Cloud client
- `--database`: Database name for Cloud client
- `--api-key`: API key for Cloud client
- `--cpu-execution-provider`: Force CPU execution provider for embedding functions (`auto`, `true`, `false`)

### Cursor Integration

To use with Cursor, add the following to your `.cursor/mcp.json`:

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

For UVX integration with Cursor, use:

```json
{
  "mcpServers": {
    "chroma": {
      "command": "uvx",
      "args": ["chroma-mcp-server"],
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

### Smithery Integration

This MCP server is compatible with [Smithery](https://smithery.ai/). See the `smithery.yaml` file for configuration details.

## Development

This project uses [Hatch](https://hatch.pypa.io/) for development and package management.

### Setting Up Development Environment

```bash
# Install Hatch globally
pip install hatch

# Create and activate a development environment
hatch shell
```

### Running Tests

```bash
# Run all tests
hatch run python -m pytest

# Run with coverage
hatch run python -m pytest --cov=chroma_mcp

# Using the test script (with coverage)
./test.sh
```

### Building the Package

```bash
# Build both wheel and sdist
hatch build

# Or use the script
./build.sh
```

### Publishing

```bash
# Publish to TestPyPI (for testing)
./publish.sh -t -v 0.1.x

# Publish to PyPI (production)
./publish.sh -p -v 0.1.x
```

## Dependencies

The package has optimized dependencies organized into groups:

- **Core**: Required for basic functionality (`python-dotenv`, `pydantic`, `fastapi`, `chromadb`, etc.)
- **Full**: Optional for extended functionality (`sentence-transformers`, `onnxruntime`, etc.)
- **Dev**: Only needed for development and testing

## Troubleshooting

### Common Issues

1. **Missing dependencies**: If you encounter module import errors, make sure to install all required dependencies:
   ```bash
   pip install "chroma-mcp-server[full]"
   ```

2. **Permission errors**: When using persistent storage, ensure the data directory is writable.

3. **UVX integration**: If using UVX with Cursor, make sure UVX is installed and in your PATH:
   ```bash
   pip install uv uvx
   ```

## License

Apache-2.0 (see [LICENSE](LICENSE))
