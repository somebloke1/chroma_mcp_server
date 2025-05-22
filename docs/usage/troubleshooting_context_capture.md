# Troubleshooting Enhanced Context Capture

## Introduction

The enhanced context capture system in Chroma MCP Server is designed to automatically log rich information about your interactions with an AI assistant, including code changes, tool usage, and AI confidence. This data, primarily stored in the `chat_history_v1` collection, is vital for implicit learning and later analysis.

This guide helps you diagnose and resolve common issues you might encounter with this system.

## Common Issues and Solutions

### 1. `auto_log_chat` Rule Not Triggering or Logging to ChromaDB

- **Symptom:** No new entries appear in `chat_history_v1` after AI interactions.
- **Troubleshooting Steps:**
    1. **MCP Server Status:** Ensure the `chroma-mcp-server` is running in your IDE and the IDE indicates a successful connection.
    2. **IDE Rule Configuration:** Verify that your IDE's MCP rule file (e.g., `.cursorrules`, `.windsurfrules`) contains the `auto_log_chat` rule and that it's correctly formatted and enabled.
    3. **ChromaDB Connection (MCP Server):**
        - Check the MCP server logs (usually in `logs/chroma_mcp_stdio_*.log` or a similar path configured by `CHROMA_LOG_DIR`). Look for errors related to ChromaDB connection or the `#chroma_log_chat` tool call.
        - Verify your project's `.env` file has the correct settings for `CHROMA_DB_IMPL`, `CHROMA_DB_PATH` (for persistent local DB), or `CHROMA_HTTP_URL` (for a remote DB).
    4. **`chat_history_v1` Collection:** Confirm the `chat_history_v1` collection exists in your ChromaDB instance. You can use `chroma-mcp-client setup-collections` to create it if missing.
    5. **Tool Call Errors:** Examine MCP server logs for any errors specifically during the execution of the `#chroma_log_chat` tool.

### 2. Logged Chat Entries Missing Code Context (Diffs, Before/After Snippets)

- **Symptom:** Entries in `chat_history_v1` lack `code_context` or `diff_summary` even when you believe code was changed.
- **Troubleshooting Steps:**
    1. **Actual File Modifications:** Confirm that the AI assistant *actually made and applied changes to files* during the interaction. Context is typically captured only when file modifications occur.
    2. **IDE Tool Chain:** The `auto_log_chat` rule relies on the IDE correctly reporting file changes made by the AI. Ensure your IDE and its MCP integration are functioning correctly in this regard.
    3. **Internal Logic (Advanced):** If issues persist, it might point to the internal logic within `auto_log_chat` or `src/chroma_mcp_client/context.py` not correctly identifying or processing the file changes. This would typically require deeper debugging of the server code.

### 3. Tool Sequence Not Captured or Incorrect

- **Symptom:** The `tool_sequence` metadata in `chat_history_v1` is empty or doesn't accurately reflect the tools used by the AI.
- **Troubleshooting Steps:**
    1. **Tool Usage:** Ensure the AI assistant is actually using MCP tools that are intended to be tracked (e.g., `edit_file`, `run_terminal_cmd`, `read_file`).
    2. **IDE Reporting:** The `auto_log_chat` rule depends on the IDE providing information about the tools invoked by the AI.

### 4. Confidence Scores Consistently Off or Missing

- **Symptom:** The `confidence_score` is always very low, very high, or not being recorded.
- **Troubleshooting Steps:**
    1. **Heuristic Nature:** The confidence score calculation (within `src/chroma_mcp_client/context.py`) is heuristic-based. If it's consistently misaligned with perceived interaction quality, the underlying heuristics might need adjustment in the source code.
    2. **Data for Calculation:** Ensure that the necessary inputs for the heuristic (tool sequence, nature of file changes, response length) are being captured correctly.

### 5. Modification Type Miscategorized or 'Unknown'

- **Symptom:** The `modification_type` (e.g., `bugfix`, `refactor`) is often `unknown` or doesn't match the nature of the AI's task.
- **Troubleshooting Steps:**
    1. **Heuristic Nature:** Similar to confidence scores, modification type determination (in `src/chroma_mcp_client/context.py`) uses heuristics based on prompt/response summaries and file changes. Persistent miscategorization might require refining these heuristics in the code.

### 6. Bi-Directional Links Not Being Created

- **Symptom:** `related_chat_ids` in `codebase_v1` entries are not populated, or `code_context` in `chat_history_v1` doesn't correctly link back to code, despite relevant interactions.
- **Troubleshooting Steps:**
    1. **Git Hooks & Indexing:** Ensure `chroma-mcp-client index --changed` is running successfully via your `post-commit` Git hook after code changes that were part of an AI-assisted interaction. This updates `codebase_v1`.
    2. **Chat Logging Logic:** Verify that the `manage_bidirectional_links` function within `src/chroma_mcp_client/context.py` (called during `auto_log_chat`) is functioning correctly to establish links when chat entries are logged.

## General Debugging Steps

1. **Check MCP Server Logs:** The most important first step. Look for errors or warnings in `logs/chroma_mcp_stdio_*.log` (or your configured `CHROMA_LOG_DIR`).
2. **Check `chroma-mcp-client` Output:** If using CLI tools related to context (e.g., `analyze-chat-history`), pay attention to any error messages.
3. **Inspect ChromaDB Directly:** Use `chroma-mcp-client query` or other database tools to look at the raw entries in `chat_history_v1` and `codebase_v1` to see what is (or isn't) being stored.
4. **Verify `.env` Configuration:** Double-check that all necessary environment variables (for ChromaDB connection, API keys if used by embedding models, `LOG_LEVEL`, etc.) are correctly set in your project's `.env` file.
5. **Rebuild & Reinstall:** After any changes to the `chroma-mcp-server` codebase (including client or context modules), always rebuild and reinstall the package to ensure your IDE and CLI are using the latest version:

    ```bash
    hatch build && hatch run pip uninstall chroma-mcp-server -y && hatch run pip install 'dist/chroma_mcp_server-<version>-py3-none-any.whl[client,dev]'
    ```

    Then, **manually reload the MCP server in your IDE.**

## When to Seek Further Help

- If server logs indicate unrecoverable internal errors within the `chroma-mcp-server` or `chroma-mcp-client` Python code.
- If ChromaDB itself is reporting persistent errors not related to client configuration.
- If issues persist after trying the above steps, consider raising an issue on the project's issue tracker with detailed logs and reproduction steps.
