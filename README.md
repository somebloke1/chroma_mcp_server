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
./scripts/develop.sh

# To build the package
./scripts/build.sh

# To publish to PyPI
./scripts/publish.sh
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
      "command": "uvx",
      "args": [
        "chroma-mcp-server"
      ],
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

#### Version Management

We provide a script to manage your server version:

```bash
# Install and configure a specific version
./scripts/update_mcp_version.sh -i 0.1.4

# Only update configuration (if already installed)
./scripts/update_mcp_version.sh 0.1.4

# Use version from pyproject.toml
./scripts/update_mcp_version.sh
```

The script provides:
- One-time installation with `-i` flag
- Clean server configuration
- Automatic version detection from pyproject.toml
- Clear post-update instructions

After updating:
1. Restart Cursor to apply the changes
2. The server will start using the configured version
3. No unnecessary reinstalls on server restart

### Smithery Integration

This MCP server is compatible with [Smithery](https://smithery.ai/). See the `smithery.yaml` file for configuration details.

## Development

This project uses [Hatch](https://hatch.pypa.io/) for development and package management.

### Development Scripts

The project includes several utility scripts in the `scripts/` directory to streamline development tasks:

```bash
# Start development environment
./scripts/develop.sh

# Run tests with coverage
./scripts/test.sh

# Build the package
./scripts/build.sh

# Publish to TestPyPI/PyPI
./scripts/publish.sh [-t|-p] -v VERSION

# Test UVX installation
./scripts/test_uvx_install.sh

# Update MCP version in Cursor config
./scripts/update_mcp_version.sh [VERSION]
```

### Setting Up Development Environment

```bash
# Install Hatch globally
pip install hatch

# Create and activate development environment using our script
./scripts/develop.sh
```

### Running Tests

```bash
# Run all tests
hatch run test:run

# Run with coverage (using our script)
./scripts/test.sh

# Run tests for specific file/directory
hatch run test:run tests/path/to/test.py
```

### Building the Package

```bash
# Build using our script (recommended)
./scripts/build.sh

# Or manually with Hatch
hatch build
```

### Publishing

```bash
# Publish to TestPyPI (for testing)
./scripts/publish.sh -t -v VERSION

# Publish to PyPI (production)
./scripts/publish.sh -p -v VERSION

# Additional options:
#  -y: Auto-confirm prompts
#  -u: PyPI username
#  -w: PyPI password/token
#  -f: Fix dependencies
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

MIT License (see [LICENSE](LICENSE))
