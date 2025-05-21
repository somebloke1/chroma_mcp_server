# IDE and Tool Integration Guides

This section provides guides on how to integrate `chroma-mcp-server` and its client utilities with various Integrated Development Environments (IDEs) and development tools. Effective integration can streamline your workflow, enabling automated context capture, enhanced learning from test cycles, and easier access to working memory tools.

## Available Integration Guides

- **[Automated Chat Logging](./automated_chat_logging.md)**
  - Explains how to configure and use the `auto_log_chat` rule for automatically capturing AI chat summaries into ChromaDB. Covers setup for Cursor and generic approaches for other clients.

- **[IDE Integration for Thinking Utilities](./ide_integration.md)**
  - Provides examples for integrating the `record-thought` console script into IDEs like VS Code, Cursor, Windsurf, and JetBrains products to easily capture thoughts.

- **[MCP Integration Guide](./mcp_integration.md)**
  - Details how to configure your IDE (e.g., Cursor, VS Code, Windsurf) to use `chroma-mcp-server` via the Model Context Protocol (MCP), including example `mcp.json` configurations.

- **[Pytest Plugin Usage](./pytest_plugin_usage.md)**
  - Guides developers on how to use the `auto-capture-workflow` Pytest plugin (included with `chroma-mcp-server[client]`) in their own Python projects to log test failures and transitions to ChromaDB.

These guides aim to help you make the most of `chroma-mcp-server`'s capabilities by embedding them directly into your development environment.
