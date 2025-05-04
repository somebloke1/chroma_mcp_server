# Getting Started with Chroma MCP Server

This guide will help you set up and start using the Chroma MCP Server.

## Prerequisites

- Python 3.10 or higher
- Pip package manager
- Git (optional, for development)

## Installation

Choose your preferred installation method:

### Option 1: Simple Installation (pip/uvx)

```bash
# Install the base package from PyPI using pip
pip install chroma-mcp-server

# Or using uv
uv pip install chroma-mcp-server

# For full functionality including optional embedding models
pip install "chroma-mcp-server[full]"
# Or using uv
uv pip install "chroma-mcp-server[full]"
```

### Option 2: Via Smithery (for Local Execution)

[Smithery](https://smithery.ai/) provides a registry and CLI tool for managing MCP servers, often used by AI clients like Claude Desktop. This method still runs the server locally.

**Prerequisites:**

- Node.js and `npx` must be installed.
- The `chroma-mcp-server` package must be published on PyPI and registered on the Smithery website ([https://smithery.ai/](https://smithery.ai/)).

**Installation:**

```bash
# Install the package into a Smithery-managed environment
npx -y @smithery/cli install chroma-mcp-server

# If prompted or required by Smithery configuration, provide a key:
# npx -y @smithery/cli install chroma-mcp-server --key YOUR_API_KEY
```

### Option 3: Development Setup

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

Copy the example `.env.template` to `.env` and adjust values as needed:

```bash
cp .env.template .env
```

The server primarily uses environment variables for configuration. A `.env` file in the project root is loaded automatically. Key variables include:

- `CHROMA_CLIENT_TYPE`: Specifies how the MCP server connects to or manages ChromaDB. Available options:
  - `ephemeral` (Default): Runs an in-memory ChromaDB instance. Data is lost when the server stops. Good for quick tests or stateless operations.
  - `persistent`: Creates or uses a local, disk-based ChromaDB instance. Requires `CHROMA_DATA_DIR` to be set to a valid path. Data persists between server restarts.
  - `http`: Connects to an **external, already running** ChromaDB server via HTTP/HTTPS. Requires `CHROMA_HOST` and `CHROMA_PORT` (and optionally `CHROMA_SSL`, `CHROMA_HEADERS`) to be set. The MCP server acts only as a client.
  - `cloud`: Connects to a ChromaDB Cloud instance. Requires `CHROMA_TENANT`, `CHROMA_DATABASE`, and `CHROMA_API_KEY` to be set. The MCP server acts only as a client.
- `CHROMA_DATA_DIR`: Path for persistent storage (required and only used if `CHROMA_CLIENT_TYPE=persistent`).
- `CHROMA_LOG_DIR`: Path for log files (defaults to a temporary directory).
- `LOG_LEVEL`: Logging verbosity (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). Defaults to `INFO`.
- `MCP_LOG_LEVEL`: Specific logging verbosity for the MCP server components.
- `CHROMA_EMBEDDING_FUNCTION`: Specifies the embedding function to use (e.g., `default`, `accurate`, `openai`). See README or API reference for all options. Requires API keys for non-local models.
- API Keys: If using API-based embedding functions (like `openai`, `gemini`), ensure the relevant environment variables (e.g., `OPENAI_API_KEY`, `GOOGLE_API_KEY`) are set.
- Connection Details (`http`/`cloud` modes):
  - `CHROMA_HOST`, `CHROMA_PORT`, `CHROMA_SSL`: Required for `http` mode.
  - `CHROMA_HEADERS`: Optional HTTP headers (JSON string) for `http` mode.
  - `CHROMA_TENANT`, `CHROMA_DATABASE`, `CHROMA_API_KEY`: Required for `cloud` mode.

Cursor uses `.cursor/mcp.json` to configure server launch commands:

```json
{
  "mcpServers": {
    "chroma": { // Runs the version last installed via uvx (typically Prod)
      "command": "uvx",
      "args": [
        "chroma-mcp-server",
        "--client-type=persistent",
        "--embedding-function=default" // Example: Choose your embedding function
      ],
      "env": {
        "CHROMA_DATA_DIR": "/path/to/data/dir", // Replace with your actual path
        "CHROMA_LOG_DIR": "./logs",
        "LOG_LEVEL": "INFO",
        "MCP_LOG_LEVEL": "INFO"
      }
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

### Automated Chat History Logging

Leveraging the MCP integration, the server supports automatically logging summaries of AI chat interactions into a dedicated ChromaDB collection. This provides a persistent record for analysis and context retrieval.

See the **[Automated Chat History Logging Guide](integration/automated_chat_logging.md)** for configuration details.

## Development

### Development Prerequisites

- Python 3.10+
- `hatch` (Install with `pip install hatch`)
- `just` (optional, for `justfile`)
- `curl`, `jq` (for `release.sh`)

### Setup

```bash
hatch shell # Activate the Hatch environment (installs deps if needed)
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

### Standalone Mode (pip/uvx install)

If you installed via `pip` or `uvx`, you can run the server directly. Ensure required environment variables (like `CHROMA_DATA_DIR` for persistent mode, or API keys for specific embedding functions) are set.

```bash
# Run using the installed script
chroma-mcp-server --client-type ephemeral --embedding-function default

# Example with persistent mode (env var set)
# export CHROMA_DATA_DIR=/path/to/data
# chroma-mcp-server --client-type persistent
```

### Via Smithery CLI (Smithery install)

If you installed via Smithery, use the Smithery CLI to run the server. It reads the package's `smithery.yaml` to configure and launch the server locally.

```bash
# Run with default config from smithery.yaml
npx -y @smithery/cli run chroma-mcp-server

# Run with custom configuration override
npx -y @smithery/cli run chroma-mcp-server --config '{ "clientType": "persistent", "dataDir": "./my_smithery_data" }'

# If prompted or required by Smithery configuration, provide a key:
# npx -y @smithery/cli run chroma-mcp-server --key YOUR_API_KEY --config '{...}'
```

### Inspecting via Smithery (Optional)

You can use the Smithery CLI to inspect the server's registered configuration (requires installation via Smithery first):

```bash
npx -y @smithery/cli inspect chroma-mcp-server
```

### Development Mode (Using Hatch)

If you are running from a cloned repository within the development environment, use the provided wrapper script:

```bash
# From the project root directory
./scripts/run_chroma_mcp_server_dev.sh --client-type persistent --data-dir ./dev_data --log-dir ./dev_logs
```

See the [Developer Guide](developer_guide.md#running-the-server-locally) for more details on development setup and running locally.

### Choosing an Embedding Function

The server uses an embedding function to generate vector representations of text for semantic search and other tasks. You can specify which function to use via the `--embedding-function` command-line argument or the `CHROMA_EMBEDDING_FUNCTION` environment variable.

**Available Embedding Functions:**

- `default` / `fast`: Uses `ONNX MiniLM-L6-v2`. Fast and runs locally, good for general use without needing extra setup or API keys. Requires `onnxruntime` (installed by default).
- `accurate`: Uses `all-mpnet-base-v2` via `sentence-transformers`. More accurate but potentially slower than `default`. Requires `sentence-transformers` and `torch`.
- `openai`: Uses OpenAI's embedding models (e.g., `text-embedding-ada-002`). Requires the `openai` package and the `OPENAI_API_KEY` environment variable.
- `cohere`: Uses Cohere's embedding models. Requires the `cohere` package and the `COHERE_API_KEY` environment variable.
- `huggingface`: Uses models from the Hugging Face Hub via the `sentence-transformers` library. Requires `sentence-transformers`, `torch`, and potentially `transformers`. Requires `HUGGINGFACE_API_KEY` if using gated models.
- `voyageai`: Uses Voyage AI's embedding models. Requires the `voyageai` package and the `VOYAGEAI_API_KEY` environment variable.
- `google`: Uses Google's Generative AI embedding models (e.g., Gemini). Requires the `google-generativeai` package and the `GOOGLE_API_KEY` environment variable.
- `bedrock`: Uses embedding models available through AWS Bedrock (e.g., Cohere, Titan). Requires the `boto3` package and configured AWS credentials (via environment variables, shared credential file, or IAM role).
- `ollama`: Uses embedding models served by a local Ollama instance. Requires the `ollama` package and a running Ollama server. The server address can be configured via the `OLLAMA_HOST` environment variable (defaults to `http://localhost:11434`).

**Installation:**

To ensure all dependencies for optional embedding functions like `accurate`, `google`, `bedrock`, `ollama`, `openai`, `cohere`, `voyageai`, and `huggingface` are installed, use the `full` extra:

```bash
pip install "chroma-mcp-server[full]"
```

If you only need the default functions, a simple `pip install chroma-mcp-server` is sufficient.

## Running the Server from terminal

Once installed, you can run the server from your terminal:

```bash
chroma-mcp-server --client-type ephemeral --embedding-function default
```

- `--embedding-function TEXT`: Specifies the embedding function to use. Defaults to `default`. See [Choosing an Embedding Function](#choosing-an-embedding-function) for options.
- `--cpu-execution-provider [auto|true|false]`: Configures ONNX execution provider usage (primarily for `default`/`fast` embedding functions). Defaults to `auto`.
- `--version`: Show the server version and exit.
- `--help`: Show help message and exit.

**Environment Variables:**

Certain arguments can also be set via environment variables:

- `CHROMA_CLIENT_TYPE`: Overrides `--client-type`.
- `CHROMA_DATA_DIR`: Overrides `--data-dir`.
- `CHROMA_HOST`: Overrides `--host`.
- `CHROMA_PORT`: Overrides `--port`.
- `CHROMA_TENANT`: Overrides `--tenant`.
- `CHROMA_DATABASE`: Overrides `--database`.
- `CHROMA_API_KEY`: Overrides `--api-key` (for persistent HTTP/HTTPS clients).
- `CHROMA_EMBEDDING_FUNCTION`: Overrides `--embedding-function`.
- `CHROMA_LOG_DIR`: Overrides `--log-dir`.
- `CHROMA_LOG_LEVEL`: Overrides `--log-level`.
- `ONNX_CPU_PROVIDER`: Overrides `--cpu-execution-provider` (true/false).
- `OPENAI_API_KEY`: Required if using `--embedding-function openai`.
- `COHERE_API_KEY`: Required if using `--embedding-function cohere`.
- `HUGGINGFACE_API_KEY`: Required if using `--embedding-function huggingface` with private/gated models.
- `VOYAGEAI_API_KEY`: Required if using `--embedding-function voyageai`.
- `GOOGLE_API_KEY`: Required if using `--embedding-function google`.
- `OLLAMA_HOST`: Specifies the Ollama server address (e.g., `http://host.docker.internal:11434`) if using `--embedding-function ollama`. Defaults to `http://localhost:11434`.
- AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `AWS_REGION`, etc.): Required if using `--embedding-function bedrock` and not configured via other means (e.g., IAM role, shared credential file).

## Docker

Build and run via Docker:

```bash
docker build -t chroma-mcp-server .
docker run -p 8000:8000 \
  -e CHROMA_CLIENT_TYPE=persistent \
  -e CHROMA_DATA_DIR=/data \
  -e CHROMA_LOG_DIR=/logs \
  -e CHROMA_EMBEDDING_FUNCTION=default \
  chroma-mcp-server
```

Or with Compose:

```bash
docker-compose up --build
```
