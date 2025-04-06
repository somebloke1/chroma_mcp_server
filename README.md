# Chroma MCP Server

[![CI](https://github.com/djm81/chroma_mcp_server/actions/workflows/tests.yml/badge.svg)](https://github.com/djm81/chroma_mcp_server/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/djm81/chroma_mcp_server/branch/main/graph/badge.svg)](https://codecov.io/gh/djm81/chroma_mcp_server)
[![PyPI - Version](https://img.shields.io/pypi/v/chroma-mcp-server?color=blue)](https://pypi.org/project/chroma-mcp-server)

A Model Context Protocol (MCP) server integration for [Chroma](https://www.trychroma.com/), the open-source embedding database.

## Motivation: AI Development Working Memory

In AI-assisted development workflows, particularly when using tools like Cursor or GitHub Copilot over multiple sessions, maintaining context from previous interactions is crucial but often manual. Developers frequently resort to creating temporary markdown files or other artifacts simply to capture and reload context into a new chat session.

The Chroma MCP Server aims to streamline this process by providing a persistent, searchable "working memory":

- **Automated Context Recall:** Instead of manual context loading, AI assistants (guided by specific rules or instructions) can query this MCP server to retrieve relevant information from past sessions based on the current development task.
- **Developer-Managed Persistence:** Developers can actively summarize key decisions, code snippets, or insights from the current session and store them in ChromaDB via the MCP interface. This allows building a rich, task-relevant knowledge base over time.
- **Separation of Concerns:** This "working memory" is distinct from final user-facing documentation or committed code artifacts, focusing specifically on capturing the transient but valuable context of the development process itself.

By integrating ChromaDB through MCP, this server facilitates more seamless and context-aware AI-assisted development, reducing manual overhead and improving the continuity of complex tasks across multiple sessions.

## Overview

The Chroma MCP Server allows you to connect AI applications with Chroma through the Model Context Protocol. This enables AI models to:

- Store and retrieve embeddings
- Perform semantic search on vector data
- Manage collections of embeddings
- Support RAG (Retrieval Augmented Generation) workflows

See the [API Reference](docs/api_reference.md) for a detailed list of available tools and their parameters.

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

## Usage

### Starting the server

```bash
# Using the command-line executable
chroma-mcp-server

# Or using the Python module
python -m chroma_mcp.server
```

### Checking the Version

```bash
chroma-mcp-server --version
```

### Configuration

The server can be configured with command-line options or environment variables:

#### Command-line Options

```bash
chroma-mcp-server --client-type persistent --data-dir ./my_data --log-dir ./logs
```

#### Environment Variables

```bash
export CHROMA_CLIENT_TYPE=persistent
export CHROMA_DATA_DIR=./my_data
export CHROMA_LOG_DIR=./logs
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

See [Getting Started](docs/getting_started.md) for more setup details.

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

See [Cursor Integration](docs/cursor_integration.md) for more details.

## Development

For instructions on how to set up the development environment, run tests, build the package, and contribute, please see the **[Developer Guide](docs/developer_guide.md)**.

## Testing the Tools

A simulated workflow using the MCP tools is available in the **[MCP Test Flow](docs/mcp_test_flow.md)** document.

## License

MIT License (see [LICENSE](LICENSE))
