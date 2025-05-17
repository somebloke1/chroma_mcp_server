# Chroma MCP Server Documentation

Welcome to the Chroma MCP Server documentation. This guide provides comprehensive information about installation, configuration, usage, and development of the server.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Cursor Integration](#cursor-integration)
- [Running in Development](#running-in-development)
- [Docker](#docker)
- [Logging](#logging)
- [Working Memory](#working-memory)
- [Enhanced Context Capture](usage/enhanced_context_capture.md)
- [Semantic Code Chunking](usage/semantic_chunking.md)
- [Tool Usage Format Specification](usage/tool_usage_format.md)
- [Automated Chat Logging](integration/automated_chat_logging.md)
- [Memory Integration](rules/memory-integration-rules.md)
- [Error-Driven Learning](usage/enhanced_context_capture.md#error-driven-learning)
- [Learning Validation Workflow](refactoring/learning_validation_workflow.md)
- [ROI Measurement Framework](usage/roi_measurement.md)
- [Automated Test Workflow](usage/automated_test_workflow.md)

## Overview

The Chroma MCP Server allows you to connect AI applications with Chroma through the Model Context Protocol. Beyond standard MCP interactions, this implementation emphasizes creating a persistent, automatically updated "Second Brain" for development by integrating:

- **Automated Codebase Indexing:** Tools and configurations (like Git hooks calling a dedicated `chroma-mcp-client`) enable automatic indexing of code changes into a designated Chroma collection.
- **Semantic Code Chunking:** The system preserves logical code structures (functions, classes) when creating chunks, ensuring more meaningful context retrieval.
- **Enhanced Context Capture:** Automatically extracts rich contextual information from code changes including diffs, tool sequences, and modification types.
- **Bidirectional Linking:** Creates navigable connections between chat discussions and code changes, allowing tracing of feature evolution.
- **Automated Chat Logging:** IDE rules (like `auto_log_chat` for Cursor) facilitate automatic summarization and logging of AI chat interactions into a separate Chroma collection.
- **Working Memory Tools:** Specialized MCP commands for capturing and retrieving structured thoughts and development context.
- **Automated Test-Driven Learning:** Captures test failures and successes, links them to code changes and discussions, and automatically promotes validated learning.

This enables AI models to:

- Store and retrieve embeddings
- Perform semantic search on vector data
- Manage collections of embeddings
- Support RAG (Retrieval Augmented Generation) workflows
- Track the evolution of code through discussions and modifications
- Maintain context across multiple development sessions
- Learn from test-driven development processes

**Current Implementation Status:** The foundational features of the "Second Brain" concept (Phase 1 in `docs/refactoring/local_rag_pipeline_plan_v4.md`) have been largely implemented, including automated indexing with semantic chunking, enhanced chat logging with rich context capture, bidirectional linking, working memory, and derived learnings promotion. The CLI tools for analysis and promotion are being enhanced to fully leverage this rich metadata. More advanced features (Phases 2 and 3) involving LoRA fine-tuning and automated reinforcement learning are under active development.

## Key Benefits

The "Second Brain" concept offers compelling benefits:

1. **Automated Context Capture**: All code changes and AI discussions are automatically indexed, with rich contextual information.
2. **Bidirectional Linking**: Create navigable connections between chat discussions and code changes.  
3. **Validated Learning Collection**: Store only code changes with proven learning value based on evidence like test transitions and error resolution.
4. **Measurable ROI**: Track concrete metrics showing the impact of your RAG system on development efficiency and code quality.
5. **Continuous Improvement**: The system naturally adapts to focus on high-value solutions.
6. **Automated Test-Driven Learning**: Captures the complete lifecycle from test failure to fix, creating evidence-based validation for promoted learnings.

## Key Enhanced Features

### Automated Test-Driven Learning

The system includes a fully automated test-driven learning workflow that:

- Automatically captures test failures and their context
- Monitors for subsequent test successes after code changes
- Creates validation evidence with bidirectional links to code and chat history
- Promotes high-quality fixes to derived learnings
- Integrates with Git hooks for seamless operation

See the [Automated Test Workflow Guide](usage/automated_test_workflow.md) for implementation details.

### Error-Driven Learning

The system now incorporates an error-driven learning approach that focuses on capturing and validating true learning moments:

- Only promotes code changes that solved actual problems (failing tests, runtime errors)
- Uses a validation scoring system to identify high-value learnings
- Tracks the complete lifecycle from initial implementation through error detection to resolution
- Creates a much higher signal-to-noise ratio in derived learnings

See the [Error-Driven Learning Guide](usage/enhanced_context_capture.md#error-driven-learning) for implementation details.

### Learning Validation Workflow

A comprehensive workflow ensures only validated learnings get promoted:

- Evidence-based validation scoring system
- Multiple validation types (test transitions, runtime errors, quality improvements)
- Enhanced review interface showing validation evidence
- Clear thresholds for promotion eligibility

See the [Learning Validation Workflow](refactoring/learning_validation_workflow.md) for the complete process.

### ROI Measurement Framework

A concrete measurement system quantifies the value of the RAG implementation:

- Error resolution metrics (time-to-fix, prevention rate)
- Quality impact metrics (before/after comparisons)
- Productivity measurements (time saved, knowledge reuse)
- Learning effectiveness evaluation

See the [ROI Measurement Framework](usage/roi_measurement.md) for detailed metrics and implementation.

### Enhanced Context Capture

The system automatically extracts rich contextual information when AI interactions modify code, including:

- Code snippets before and after changes (preserving context)
- Detailed diff summaries highlighting what was actually modified
- Tool sequences used during the interaction (e.g., read_file→edit_file→run_terminal_cmd)
- Confidence scores to help identify high-value interactions
- Classification of modification types (refactor/bugfix/feature/documentation)

See the [Enhanced Context Capture Guide](usage/enhanced_context_capture.md) for details.

### Bidirectional Linking

The system creates and maintains navigable connections between:

- Chat interactions that modify code and the affected code chunks
- Code chunks and the discussions that created or modified them

This allows tracing feature evolution across both domains, providing deeper context for AI and developers. See the [Automated Chat Logging Guide](integration/automated_chat_logging.md) for implementation details.

### Enhanced Interactive Promotion

The interactive promoter workflow (`review-and-promote`) now includes several productivity enhancements:

- **Auto-Promote Mode:** Automatically promote high-confidence entries (≥0.8) without manual review
- **Smart Defaults:** Intelligent defaults for all fields based on entry context
- **Low Confidence Warnings:** Visual indicators for entries that may need more careful review
- **Enhanced Code Selection:** Better bidirectional link support for more accurate code references

These improvements streamline the curation of derived learnings by allowing users to often just press Enter to accept sensible defaults. See the [Review and Promote Guide](scripts/review-and-promote.md) for details.

### Semantic Code Chunking

Rather than using fixed-size chunks, the system preserves logical code structures (functions, classes, methods) when indexing code, ensuring more meaningful context retrieval. See the [Semantic Chunking Guide](usage/semantic_chunking.md) for more information.

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

### Via Smithery (for Local Execution)

[Smithery](https://smithery.ai/) acts as a registry and local launcher for MCP servers. AI clients like Claude Desktop can use Smithery to find, install, and run your server locally.

```bash
# Requires Node.js/npx
# Installs the package (usually via pip) into a Smithery-managed environment
npx -y @smithery/cli install chroma-mcp-server

# If the server requires an API key for installation via Smithery:
# npx -y @smithery/cli install chroma-mcp-server --key YOUR_API_KEY
```

*(Note: This method requires the package to be published on PyPI and registered with Smithery. The `--key` option usage depends on the specific server's registration settings on Smithery).*

## Configuration

The server can be configured with command-line options or environment variables:

### Command-line Options

```bash
# Example setting mode to stdio
chroma-mcp-server --mode stdio --client-type persistent --data-dir ./my_data
# Example using default http mode
chroma-mcp-server --client-type persistent --data-dir ./my_data --log-dir ./logs --embedding-function accurate
```

### Environment Variables

```bash
export CHROMA_SERVER_MODE=stdio # Optional, defaults to http
export CHROMA_CLIENT_TYPE=persistent
export CHROMA_DATA_DIR=./my_data
export CHROMA_LOG_DIR=./logs
export LOG_RETENTION_DAYS=7 # Number of days to keep log files before cleanup
export CHROMA_EMBEDDING_FUNCTION=accurate
chroma-mcp-server
```

### Available Configuration Options

- `--mode`: Server mode (`stdio` or `http`, default: `http`). Also configurable via `CHROMA_SERVER_MODE`.
- `--client-type`: Type of Chroma client (`ephemeral`, `persistent`, `http`, `cloud`). Also configurable via `CHROMA_CLIENT_TYPE`.
- `--data-dir`: Path to data directory for persistent client. Also configurable via `CHROMA_DATA_DIR`.
- `--log-dir`: Path to log directory. Also configurable via `CHROMA_LOG_DIR`.
- Log retention: Configure with `LOG_RETENTION_DAYS` environment variable (default: 7 days).
- `--host`: Host address for HTTP client. Also configurable via `CHROMA_HOST`.
- `--port`: Port for HTTP client. Also configurable via `CHROMA_PORT`.
- `--ssl`: Whether to use SSL for HTTP client. Also configurable via `CHROMA_SSL`.
- `--tenant`: Tenant ID for Cloud client. Also configurable via `CHROMA_TENANT`.
- `--database`: Database name for Cloud client. Also configurable via `CHROMA_DATABASE`.
- `--api-key`: API key for Cloud client. Also configurable via `CHROMA_API_KEY`.
- `--cpu-execution-provider`: Force CPU execution provider for local embedding functions (`auto`, `true`, `false`). Also configurable via `CHROMA_CPU_EXECUTION_PROVIDER`.
- `--embedding-function`: Name of the embedding function to use. Choices: 'default'/'fast' (Local CPU, balanced), 'accurate' (Local CPU/GPU via sentence-transformers, higher accuracy), 'openai' (API, general purpose), 'cohere' (API, retrieval/multilingual focus), 'huggingface' (API, flexible model choice), 'jina' (API, long context focus), 'voyageai' (API, retrieval focus), 'gemini' (API, general purpose). API-based functions require corresponding API keys set as environment variables (e.g., OPENAI_API_KEY). Also configurable via `CHROMA_EMBEDDING_FUNCTION`.

### .env File Support

The server automatically loads environment variables from a `.env` file in the project root. You can copy the example file as a starting point:

```bash
cp .env.template .env
```

Edit the file to adjust values as needed for your setup.

## Usage

### Starting the server

```bash
# Using the command-line executable (after pip/uvx install)
chroma-mcp-server [OPTIONS]

# Or using the Python module (in an environment where it's installed)
python -m chroma_mcp.cli [OPTIONS]

# Or via Smithery CLI (after npx ... install)
# Example with config:
npx -y @smithery/cli run chroma-mcp-server --config '{ "clientType": "persistent", "dataDir": "./my_chroma_data" }'

# Example if the server requires an API key for running via Smithery:
# npx -y @smithery/cli run chroma-mcp-server --key YOUR_API_KEY --config '{...}'
```

### Checking the Version

```bash
chroma-mcp-server --version
```

## Cursor Integration

To use with Cursor, add or modify the `.cursor/mcp.json` file in your project root. Here's an example configuration defining development (`chroma_dev`), testing (`chroma_test`), and production (`chroma_prod`) server setups:

```json
{
  "mcpServers": {
    "chroma_dev": {
      "command": "/path/to/project/scripts/run_chroma_mcp_server_dev.sh",
      "args": [],
      "env": {
        "CHROMA_CLIENT_TYPE": "persistent",
        "CHROMA_DATA_DIR": "/path/to/your/dev_data",
        "CHROMA_LOG_DIR": "/path/to/your/dev_logs",
        "LOG_LEVEL": "DEBUG",
        "MCP_LOG_LEVEL": "DEBUG"
      }
    },
    "chroma_test": {
      "command": "uvx",
      "args": [
        "--refresh",
        "--default-index", "https://test.pypi.org/simple/",
        "--index", "https://pypi.org/simple/",
        "--index-strategy", "unsafe-best-match",
        "chroma-mcp-server@latest"
      ],
      "env": {
        "CHROMA_CLIENT_TYPE": "persistent",
        "CHROMA_DATA_DIR": "/path/to/your/test_data",
        "CHROMA_LOG_DIR": "/path/to/your/test_logs",
        "LOG_LEVEL": "INFO",
        "MCP_LOG_LEVEL": "INFO"
      }
    },
    "chroma_prod": {
      "command": "uvx",
      "args": [
        "chroma-mcp-server"
      ],
      "env": {
        "CHROMA_CLIENT_TYPE": "persistent",
        "CHROMA_DATA_DIR": "/path/to/your/prod_data",
        "CHROMA_LOG_DIR": "/path/to/your/prod_logs",
        "LOG_LEVEL": "INFO",
        "MCP_LOG_LEVEL": "INFO",
        "MCP_SERVER_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Notes:**

- Replace `/path/to/project/scripts/run_chroma_mcp_server_dev.sh` with the actual absolute path to the script in your development environment.
- Replace `/path/to/your/...` placeholders with actual paths for your data and log directories. It's recommended to use separate directories for dev, test, and prod to avoid data conflicts.
- The `chroma_dev` configuration uses the `run_chroma_mcp_server_dev.sh` script, which runs the server directly from your local source code using Hatch. This is ideal for rapid development and testing changes without reinstalling.
- The `chroma_test` configuration uses `uvx` to fetch and run the *latest* version available on TestPyPI. This is useful for testing release candidates.
- The `chroma_prod` configuration uses `uvx` to run the version of `chroma-mcp-server` that is currently installed globally via `uvx` (typically the latest stable release from PyPI).

## Running in Development

For development purposes, the recommended approach is to use the wrapper script that runs the server within the Hatch environment:

```bash
# Ensure you are in the project root directory
./scripts/run_chroma_mcp_server_dev.sh [OPTIONS]
```

**Important:** After modifying the code (server, client, etc.), you must rebuild and reinstall the package within the Hatch environment for changes to take effect:

```bash
# Replace <version> with the actual version built
hatch build && hatch run pip uninstall chroma-mcp-server -y && hatch run pip install 'dist/chroma_mcp_server-<version>-py3-none-any.whl[full,dev]'
```

For more detailed development information, see the **[Developer Guide](developer_guide.md)**.

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

## Logging

The server logs output in several ways depending on the mode of operation:

- **Stdio Mode** (default for MCP servers like Cursor integration): All Python logging is redirected to dedicated per-execution log files (e.g., `logs/chroma_mcp_stdio_<timestamp>.log`) to prevent contamination of the JSON communication stream.
- **HTTP Mode**: Standard Python logging to console and optionally to log files.

Log levels and directories are configurable through environment variables. See the [Server Logging Guide](logging/server_logging.md) for comprehensive details about the logging system improvements.

## Working Memory

This server includes specialized tools for creating a persistent, searchable "working memory" to aid AI development workflows. Learn more about how these tools leverage embeddings to manage context across sessions in the **[Embeddings and Thinking Tools Guide](thinking_tools/embeddings_and_thinking.md)**.

## Additional Resources

- [API Reference](api_reference.md) - Detailed documentation of available tools and their parameters
- [Getting Started](getting_started.md) - A more detailed guide for setting up and using the server
- [Getting Started with Second Brain](getting_started_second_brain.md) - Learn about the Second Brain concept
- [Developer Guide](developer_guide.md) - Instructions for developers working on the codebase
- [MCP Test Flow](mcp_test_flow.md) - A simulated workflow using the MCP tools

## License

Chroma MCP Server is licensed under the MIT License with Commons Clause. This means you can:

✅ **Allowed**:

- Use Chroma MCP Server for any purpose (personal, commercial, academic)
- Modify the code
- Distribute copies
- Create and sell products built using Chroma MCP Server

❌ **Not Allowed**:

- Sell Chroma MCP Server itself
- Offer Chroma MCP Server as a hosted service
- Create competing products based on Chroma MCP Server

See the [LICENSE.md](LICENSE.md) file for the complete license text.
