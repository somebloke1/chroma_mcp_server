# Client and Developer Scripts Documentation

This section provides documentation for the various command-line interface (CLI) scripts available in the `chroma-mcp-server` project. These scripts are primarily Python modules exposed as console entry points, replacing older shell scripts for better maintainability and cross-platform compatibility.

They are broadly categorized into:

- **Client Scripts:** Tools for end-users to interact with the ChromaDB instance, manage learnings, log information, and automate parts of their workflow. These are typically accessed via the `chroma-mcp-client` executable.
- **Developer Scripts:** Tools for project maintainers, covering tasks like building, releasing, and publishing the package. These are accessed via specific executables like `build-mcp`, `release-mcp`, etc.
- **Thinking Tools Scripts:** Standalone scripts for interacting with the working memory features, like `record-thought`.

## Available Script Guides

- **[`chroma-mcp-client`](./chroma-mcp-client.md)**
  - Main entry point for most client operations. This document details all its subcommands:
    - `analyze-chat-history`: Analyzes chat history for insights.
    - `index`: Manages codebase indexing.
    - `log-chat`: Logs chat interactions to ChromaDB.
    - `log-error`: Logs runtime errors.
    - `log-quality`: Logs code quality check results.
    - `log-test-results`: Logs test execution results.
    - `promote-learning`: Promotes analyzed interactions to derived learnings.
    - `query`: Queries the codebase or other collections.
    - `review-and-promote`: Interactive workflow for reviewing and promoting learnings.
    - `setup-collections`: Ensures all necessary ChromaDB collections exist.
    - `setup-test-workflow`: Configures Git hooks for the automated test workflow.
    - `validate-evidence`: Calculates and displays validation scores for potential learnings.

- **[`record-thought`](./record-thought.md)**
  - Script for recording structured thoughts into the `thinking_sessions_v1` collection for working memory.

*For developer-specific scripts (`build-mcp`, `release-mcp`, `publish-mcp`), their usage is typically covered within the [Testing and Build Guide](../rules/testing-and-build-guide.md) and the general developer workflow rather than having separate detailed markdown files here.*
