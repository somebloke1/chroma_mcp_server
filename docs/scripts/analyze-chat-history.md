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

### Script Parameters

The script accepts several command-line arguments:

- `--collection-name NAME`: Specify the ChromaDB collection (default: `chat_history_v1`).
- `--repo-path PATH`: Path to the Git repository (default: current directory).
- `--status-filter STATUS`: Filter entries by this metadata status (default: `captured`).
- `--new-status STATUS`: Set entries to this status after analysis (default: `analyzed`).
- `--days-limit DAYS`: How many days back to look for entries (default: 7).
- `-v, --verbose`: Increase logging verbosity (`-v` for INFO, `-vv` for DEBUG). Default: INFO.

### Example Usage

```bash
# Analyze entries from the last day with DEBUG logging
./scripts/analyze_chat_history.sh -vv --days-limit 1

# Analyze entries with default settings
./scripts/analyze_chat_history.sh
```
