# Chroma MCP Server

[![CI](https://github.com/djm81/chroma_mcp_server/actions/workflows/tests.yml/badge.svg)](https://github.com/djm81/chroma_mcp_server/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/djm81/chroma_mcp_server/branch/main/graph/badge.svg)](https://codecov.io/gh/djm81/chroma_mcp_server)
![PyPI - Version](https://img.shields.io/pypi/v/chroma-mcp-server?color=blue)

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

This project uses [Hatch](https://hatch.pypa.io/) for development and package management. See the **Development** section below for setup instructions.

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

### Checking the Version

To check the installed version of the package, use:

```bash
chroma-mcp-server --version
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

### Smithery Integration

This MCP server is compatible with [Smithery](https://smithery.ai/). See the `smithery.yaml` file for configuration details.

## Development

This project uses [Hatch](https://hatch.pypa.io/) for development and package management.

### Development Scripts

The project includes several utility scripts in the `scripts/` directory to streamline development tasks:

```bash
# Start development environment (activates Hatch shell)
./scripts/develop.sh

# Run tests with coverage
./scripts/test.sh [--coverage] [--clean]

# Build the package
./scripts/build.sh

# Publish to TestPyPI/PyPI
./scripts/publish.sh [-t|-p] [-v VERSION]

# Test UVX installation from local wheel
./scripts/test_uvx_install.sh

# Update MCP version in Cursor config (optionally installing from PyPI/TestPyPI)
./scripts/update_mcp_version.sh [-i] [-t] [VERSION]

# Run the full release process (TestPyPI -> Prod PyPI -> Update Config)
./scripts/release.sh [--update-target <prod|test>] <VERSION>
```

### Setting Up Development Environment

1. **Install Hatch:** If you don't have it, install Hatch globally:

    ```bash
    pip install hatch
    ```

2. **Activate Environment:** Use the `develop.sh` script or run `hatch shell` directly in the project root directory:

    ```bash
    # Using the script
    ./scripts/develop.sh 
    
    # Or directly with Hatch
    hatch shell
    ```

    This creates (if needed) and activates a virtual environment managed by Hatch with all development dependencies installed.

### Running Tests

Once inside the Hatch environment (activated via `hatch shell` or `./scripts/develop.sh`):

```bash
# Run all tests using pytest directly
pytest

# Or use the test script (which runs pytest via hatch)
# Exit the hatch shell first if you are inside one
./scripts/test.sh

# Run with coverage report
./scripts/test.sh --coverage

# Run specific tests
pytest tests/path/to/test_file.py::test_function
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

### Releasing a New Version (Recommended)

For a streamlined release process that includes publishing to TestPyPI, testing the local install, publishing to production PyPI, and installing the final version locally for the `chroma` server entry, use the `release.sh` script:

```bash
# Example: Release version 0.2.0, install Prod version locally
./scripts/release.sh 0.2.0

# Example: Release version 0.2.1, install Test version locally
./scripts/release.sh --update-target test 0.2.1

# See script help for more options (--skip-testpypi, --test-only, -y)
./scripts/release.sh --help
```

This script automates the steps previously done manually using `publish.sh` and handles the installation for the main `uvx chroma-mcp-server` command.

**Note:** The `release.sh` script requires `curl` and `jq` to be installed to check if a version already exists on PyPI/TestPyPI before attempting to publish.

## Scripts Overview

- **build.sh**: Cleans and builds the package wheel.
- **publish.sh**: Publishes the package to PyPI or TestPyPI.
- **test.sh**: Runs tests using pytest.
- **test_uvx_install.sh**: Builds locally and tests installation via `uvx`.
- **release.sh**: Automates the full release process (TestPyPI -> Prod PyPI -> Install Prod/Test version locally).

## Development Setup

1. **Prerequisites:** Python 3.10+, Poetry, `just` (optional, for `justfile` commands), `curl`, `jq`.
2. **Install Dependencies:** `poetry install --with dev`
3. **Configure MCP Server:** Copy `.cursor/mcp.example.json` to `.cursor/mcp.json` and adjust environment variables (e.g., `CHROMA_DATA_DIR`).

## Running the MCP Server

You can run the server directly using Poetry or via `uvx` (recommended for Cursor integration):

```bash
# Using Poetry (for direct testing)
poetry run python src/chroma_mcp/server.py

# Using uvx (installs/runs isolated version)
# This implicitly uses the latest version from PyPI unless 
# a specific version was installed via "uvx <flags> chroma-mcp-server@<version>"
# (The release.sh script handles this installation)
 uvx chroma-mcp-server
```

Cursor uses the configurations in `.cursor/mcp.json` to launch servers:

- **`chroma`**: Runs `uvx chroma-mcp-server`, typically using the version last installed from PyPI (e.g., by `release.sh --update-target prod`).
- **`chroma_test`**: Runs `uvx <test-index-flags> chroma-mcp-server@latest`, actively fetching the latest version from TestPyPI on startup.

## Workflow & Scripts

### Local Development

1. Make code changes.
2. Run tests: `./scripts/test.sh` or `just test`
3. Optionally build and test local install: `just test-install` (uses `./scripts/test_uvx_install.sh`)

### Releasing a New Version after local tests (Recommended)

For a streamlined release process that includes publishing to TestPyPI, testing the local install, publishing to production PyPI, and installing the final version locally for the `chroma` server entry, use the `release.sh` script:

```bash
# Example: Release version 0.2.0, install Prod version locally
./scripts/release.sh 0.2.0

# Example: Release version 0.2.1, install Test version locally
./scripts/release.sh --update-target test 0.2.1

# See script help for more options (--skip-testpypi, --test-only, -y)
./scripts/release.sh --help
```

This script automates the steps previously done manually using `publish.sh` and handles the installation for the main `uvx chroma-mcp-server` command.

**Note:** The `release.sh` script requires `curl` and `jq` to be installed to check if a version already exists on PyPI/TestPyPI before attempting to publish.

## Dependencies

- **Core:** `fastapi`, `uvicorn`, `chromadb`, `fastmcp`, `python-dotenv`, `pydantic`
- **Development:** `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`

See `pyproject.toml` for specific version constraints.

## Troubleshooting

- **UVX Cache Issues:** If `uvx` seems stuck on an old version, try refreshing its cache: `uvx --refresh chroma-mcp-server --version`
- **Dependency Conflicts:** Ensure your environment matches the required Python version and dependencies in `pyproject.toml`.

## License

MIT License (see [LICENSE](LICENSE))
