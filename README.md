# Chroma MCP Server

[![CI](https://github.com/djm81/chroma_mcp_server/actions/workflows/tests.yml/badge.svg)](https://github.com/djm81/chroma_mcp_server/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/djm81/chroma_mcp_server/branch/main/graph/badge.svg)](https://codecov.io/gh/djm81/chroma_mcp_server)
[![PyPI - Version](https://img.shields.io/pypi/v/chroma-mcp-server?color=blue)](https://pypi.org/project/chroma-mcp-server)

A Model Context Protocol (MCP) server integration for [Chroma](https://www.trychroma.com/), the open-source embedding database.

## Overview

Chroma MCP Server creates a persistent, searchable "working memory" for AI-assisted development:

- **Automated Context Recall:** AI assistants can query relevant information from past sessions
- **Developer-Managed Persistence:** Store key decisions and insights in ChromaDB via MCP
- **Second Brain Integration:** Integrates with IDE workflows to create a unified knowledge hub

Key features:

- **Automated Codebase Indexing:** Track and index code changes
- **Automated Chat Logging:** Log AI interactions with enhanced context capture (code diffs, tool sequences)
- **Bidirectional Linking:** Connect discussions to code changes for tracing feature evolution
- **Semantic Code Chunking:** Preserve logical code structures for more meaningful context retrieval
- **Working Memory Tools:** MCP commands for capturing and retrieving development context

See the [Getting Started with your Second Brain guide](docs/getting_started_second_brain.md) for more details.

## Quick Start

### Installation

```bash
# Basic installation
pip install chroma-mcp-server

# Full installation with all embedding models
pip install "chroma-mcp-server[full]"
```

### Running

```bash
# With in-memory storage (data lost on restart)
chroma-mcp-server --client-type ephemeral

# With persistent storage
chroma-mcp-server --client-type persistent --data-dir ./my_data
```

### Cursor Integration

Add or modify `.cursor/mcp.json` in your project root:

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
        "CHROMA_DATA_DIR": "/path/to/your/data",
        "CHROMA_LOG_DIR": "/path/to/your/logs",
        "LOG_LEVEL": "INFO",
        "MCP_LOG_LEVEL": "INFO",
        "MCP_SERVER_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

## Recent Improvements

- **Enhanced Context Capture:** Automatically extracts code diffs, tool sequences, and assigns confidence scores
- **Bidirectional Linking:** Creates navigable connections between chat discussions and code changes
- **Semantic Code Chunking:** Uses logical boundaries (functions, classes) instead of fixed-size chunks
- **Server-Side Timestamp Enforcement:** Ensures consistent timestamps across all collections
- **Enhanced Logging System:** Per-execution log files prevent contamination of JSON communication in stdio mode
- **Embedding Function Management:** Tools to update collection metadata when changing embedding functions
- **Collection Setup Command:** Simplifies creation of multiple collections with consistent configuration
- **Auto-Promote Workflow:** Streamlined derived learning promotion with automatic handling of high-confidence entries
- **Smart Defaults:** Interactive promotion with intelligent defaults for all fields based on context
- **Low Confidence Warnings:** Visual indicators for entries that may need more careful review

## Documentation

Comprehensive documentation is available in the [docs directory](docs/):

- [Main Documentation](docs/README.md) - Complete guide to installation, configuration, and usage
- [Getting Started](docs/getting_started.md) - Detailed setup instructions
- [Developer Guide](docs/developer_guide.md) - For contributors and developers
- [Server Logging](docs/logging/server_logging.md) - Details on the improved logging system
- [Enhanced Context Capture](docs/usage/enhanced_context_capture.md) - Details on code diff extraction and tool sequencing
- [Semantic Code Chunking](docs/usage/semantic_chunking.md) - Logic-preserving code chunking for meaningful retrieval
- [Automated Chat Logging](docs/integration/automated_chat_logging.md) - Enriched chat history with bidirectional linking
- [API Reference](docs/api_reference.md) - Available MCP tools and parameters

## License

MIT License (see [LICENSE](LICENSE))
