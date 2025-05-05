# Wrapper Script: `analyze_chat_history.sh`

This script provides a simple wrapper for running the `analyze-chat-history` command of the `chroma-client` tool within the correct Hatch environment.

## Purpose

The primary goal of this script is to simplify the execution of the chat history analysis logic, ensuring it runs with the project's dependencies managed by Hatch.

It essentially runs the following command:

```bash
hatch run python -m chroma_mcp_client.cli analyze-chat-history [ARGUMENTS...]
```

## Prerequisites

- `hatch` installed and available in your PATH.
- The project environment configured via `hatch`.
- A configured `.env` file for the `chroma-client` (see `docs/scripts/chroma-client.md`).

## Usage

Navigate to the project root directory and run the script:

```bash
./scripts/analyze_chat_history.sh [OPTIONS]
```

### Options

The script passes any arguments directly to the underlying `chroma-client analyze-chat-history` command. Refer to the `chroma-client` documentation for available options:

- `--collection-name NAME`: Name of the chat history collection (Default: `chat_history_v1`).
- `--repo-path PATH`: Path to the Git repository (Default: Current directory).
- `--status-filter STATUS`: Status of entries to analyze (Default: `captured`).
- `--new-status STATUS`: Status to set after analysis (Default: `analyzed`).
- `--days-limit N`: Number of days back to analyze (Default: `7`, 0 for no limit).
- `--log-level LEVEL`: Logging level (DEBUG, INFO, etc.).

### Examples

```bash
# Analyze entries from the last 30 days using default settings
./scripts/analyze_chat_history.sh --days-limit 30

# Analyze entries in a specific repo path
./scripts/analyze_chat_history.sh --repo-path /path/to/your/repo

# Analyze with DEBUG logging
./scripts/analyze_chat_history.sh --log-level DEBUG --days-limit 1
```
