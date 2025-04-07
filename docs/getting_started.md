# Getting Started with Chroma MCP Server

This guide will help you set up and start using the Chroma MCP Server.

## Prerequisites

- Python 3.10 or higher
- Pip package manager
- Git (optional, for development)

## Installation

### Option 1: Simple Installation (Recommended)

```bash
# Install the package from PyPI
pip install chroma-mcp-server

# For full functionality with embedding models
pip install chroma-mcp-server[full]
```

### Option 2: Development Setup

1. **Clone the Repository:**

    ```bash
    git clone https://github.com/djm81/chroma_mcp_server.git # Use your repo URL
    cd chroma_mcp_server
    ```

2. **Install Hatch:** If you don't have it, install Hatch globally:

    ```bash
    pip install hatch
    ```

3. **Activate Environment:** Use the `develop.sh` script or `hatch shell`:

    ```bash
    # Using the script
    ./scripts/develop.sh 
    
    # Or directly with Hatch
    hatch shell
    ```

    This sets up the environment with all necessary development dependencies.

## Development Scripts

The project includes several utility scripts in the `scripts/` directory:

```bash
# Start development environment
./scripts/develop.sh

# Build the package
./scripts/build.sh

# Run tests with coverage
./scripts/test.sh

# Publish to PyPI/TestPyPI
./scripts/publish.sh [-t|-p] [-v VERSION]

# Test UVX installation from local wheel
./scripts/test_uvx_install.sh

# Automate the full release process (includes installing Prod/Test version locally)
./scripts/release.sh [--update-target <prod|test>] <VERSION>
```

## Configuration

The server primarily uses environment variables for configuration. A `.env` file in the project root is loaded automatically. Key variables include:

- `CHROMA_CLIENT_TYPE`: `persistent` or `ephemeral` (default)
- `CHROMA_DATA_DIR`: Path for persistent storage (required if `persistent`)
- `CHROMA_LOG_DIR`: Directory where the `chroma_mcp_server.log` file will be created. If not set, logs only go to the console.
- `LOG_LEVEL`: Standard Python log level (e.g., `DEBUG`, `INFO`).

Cursor uses `.cursor/mcp.json` to configure server launch commands:

```json
{
  "mcpServers": {
    "chroma": { // Runs the version last installed via uvx (typically Prod)
      "command": "uvx",
      "args": ["chroma-mcp-server"],
      "env": { ... }
    },
    "chroma_test": { // Runs the latest version from TestPyPI
      "command": "uvx",
      "args": [
        "--default-index", "https://test.pypi.org/simple/",
        "--index", "https://pypi.org/simple/",
        "--index-strategy", "unsafe-best-match",
        "chroma-mcp-server@latest"
      ],
      "env": { ... }
    }
  }
}
```

### Running Specific Versions

- The `chroma_test` entry automatically runs the latest from TestPyPI.
- The `chroma` entry runs the version last installed by `uvx`. The `release.sh` script handles installing the released version (from PyPI or TestPyPI via `--update-target`) for this entry.
- To manually run a specific version with the `chroma` entry, install it directly:

  ```bash
  # Install prod version 0.1.11
  uvx --default-index https://pypi.org/simple/ chroma-mcp-server@0.1.11
  
  # Install test version 0.1.11
  uvx --default-index https://test.pypi.org/simple/ --index https://pypi.org/simple/ --index-strategy unsafe-best-match chroma-mcp-server@0.1.11
  ```

After installing, restart the `chroma` server in Cursor.

## Development

### Development Prerequisites

- Python 3.10+
- Poetry
- `just` (optional, for `justfile`)
- `curl`, `jq` (for `release.sh`)

### Setup

```bash
poetry install --with dev
cp .cursor/mcp.example.json .cursor/mcp.json
# Edit .cursor/mcp.json and/or .env as needed
```

### Testing

```bash
./scripts/test.sh # Run unit/integration tests
./scripts/test.sh --coverage # Run with coverage

# Build and test local install via uvx
./scripts/test_uvx_install.sh
```

### Releasing

Use the `release.sh` script:

```bash
# Release 0.2.0, install Prod version for local 'uvx chroma-mcp-server' command
./scripts/release.sh 0.2.0

# Release 0.2.1, install Test version for local 'uvx chroma-mcp-server' command
./scripts/release.sh --update-target test 0.2.1
```

## Troubleshooting

- **UVX Cache Issues:** If `uvx` seems stuck on an old version, try refreshing its cache: `uvx --refresh chroma-mcp-server --version`
- **Dependency Conflicts:** Ensure your environment matches the required Python version and dependencies in `pyproject.toml`.

## Running the Server

### Standalone Mode

```bash
# If installed globally or via standard pip/uvx
# Ensure CHROMA_... env vars are set or use command-line args
chroma-mcp-server --client-type persistent --data-dir ./data --log-dir ./logs

# If running from within the development environment (Poetry shell)
poetry run python src/chroma_mcp/server.py --client-type persistent --data-dir ./data --log-dir ./logs
```
