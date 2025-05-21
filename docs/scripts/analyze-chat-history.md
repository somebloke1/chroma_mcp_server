# Wrapper Script: `analyze_chat_history.sh`

**DEPRECATION NOTICE:** The `analyze_chat_history.sh` shell script is deprecated and will be removed in version 0.3.0. Please use the `analyze-chat-history` console script installed via the Python package (`chroma-mcp-client analyze-chat-history`).

## Purpose

The primary goal of this script is to simplify the execution of the chat history analysis logic, ensuring it runs with the project's dependencies managed by Hatch.

It essentially runs the following command:

```bash
hatch run python -m chroma_mcp_client.cli analyze-chat-history [ARGUMENTS...]
```

## Prerequisites

- `hatch` installed and available in your PATH.
- The project environment configured via `hatch`.
- A configured `.env` file for the `chroma-mcp-client` (see `docs/scripts/chroma-mcp-client.md`).

## Usage

**Recommended**: Use the console script directly:

```bash
chroma-mcp-client analyze-chat-history [OPTIONS]
```

**Legacy wrapper script (deprecated)**:

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
- `--prioritize-by-confidence`: Prioritize entries with higher confidence scores (flag, default: false).
- `-v, --verbose`: Increase logging verbosity (`-v` for INFO, `-vv` for DEBUG). Default: INFO.

### Example Usage

```bash
# Analyze entries from the last day with DEBUG logging
./scripts/analyze_chat_history.sh -vv --days-limit 1

# Analyze entries with default settings
./scripts/analyze_chat_history.sh

# Analyze entries and prioritize by confidence score
./scripts/analyze_chat_history.sh --prioritize-by-confidence
```

## Enhanced Context Features

The analyze-chat-history command now supports enhanced context capture features:

1. **Confidence Score Prioritization**: When using `--prioritize-by-confidence`, entries with higher confidence scores are analyzed first, focusing attention on potentially more valuable interactions.

2. **Existing Code Context**: The command uses code context and diff summaries already captured during the interaction, avoiding the need to regenerate git diffs when possible.

3. **Tool Sequence Analysis**: Tool usage patterns are analyzed to identify code modification activities, even without explicit diffs.

4. **Bidirectional Links**: Related code chunks from bidirectional links are used to establish correlations between chat interactions and code changes.

## Expected Output

Upon successful completion, the script (via the underlying `chroma-mcp-client` command) will log:

1. Information about the entries being processed, including confidence scores and modification types.
2. Tool sequences used during the interactions.
3. Whether existing code context or git diffs were used for analysis.
4. The final count of processed and correlated entries.
5. A summary of entries updated to `analyzed` status, sorted by confidence score.

The command prioritizes entries with rich context metadata, making it more effective at identifying valuable interactions that should be considered for promotion to derived learnings.
