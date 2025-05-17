# Console Script: `chroma-mcp-client`

This document describes the usage of the `chroma-mcp-client` console script, which provides a command-line interface for interacting directly with a ChromaDB instance for automation tasks, primarily codebase indexing and querying.

## Installation

To use this script, you need to install the `chroma-mcp-server` package with the `client` extra dependencies:

```bash
pip install "chroma-mcp-server[client]"
```

Alternatively, if managing the project with `hatch`, ensure the `client` feature or necessary dependencies are included in your environment.

## Configuration

The `chroma-mcp-client` script relies on a `.env` file located in the root of your project directory (or the directory where you run the command) to configure the connection to ChromaDB. Key variables include:

- `CHROMA_CLIENT_TYPE`: (`persistent`, `http`, `cloud`)
- `CHROMA_DATA_DIR`: (Required for `persistent`)
- `CHROMA_HOST`, `CHROMA_PORT`, `CHROMA_SSL`, `CHROMA_HEADERS`: (Used for `http`)
- `CHROMA_TENANT`, `CHROMA_DATABASE`, `CHROMA_API_KEY`: (Used for `cloud`)
- `CHROMA_EMBEDDING_FUNCTION`: (Optional, defaults to `default`)

Refer to the main project documentation for detailed `.env` configuration options.

## Usage

```bash
chroma-mcp-client [OPTIONS] COMMAND [ARGS]...
```

### Global Options

- `-h`, `--help`: Show the help message and exit.
- `-v, --verbose`: Increase output verbosity. Use `-v` for INFO level, `-vv` for DEBUG level. Defaults to INFO.

### Commands

#### `index`

Index specific files, directories (recursively), or all git-tracked files into ChromaDB.

```bash
chroma-mcp-client index [OPTIONS] [PATHS...]
```

**Arguments:**

- `PATHS...`: Optional specific file or directory paths to index. If directories are provided, they will be indexed recursively.

**Options:**

- `--repo-root PATH`: Path to the Git repository root (default: current directory). Used to determine relative file paths for document IDs.
- `--all`: Index all files tracked by Git in the specified repository.
- `--collection-name NAME`: Specify the ChromaDB collection name (default: `codebase_v1`).

**Examples:**

```bash
# Index a specific file
chroma-mcp-client index ./src/my_module.py --repo-root .

# Index all files tracked by git in the current repo
chroma-mcp-client index --all

# Index files in a specific directory recursively, using a custom collection
chroma-mcp-client index ./docs --collection-name project_docs --repo-root .
```

#### `count`

Count documents in a ChromaDB collection.

```bash
chroma-mcp-client count [OPTIONS]
```

**Options:**

- `--collection-name NAME`: Name of the ChromaDB collection to count. Default: `codebase_v1`.

**Example:**

```bash
chroma-mcp-client count --collection-name codebase_v1
```

#### `query`

Query a ChromaDB collection using semantic search.

```bash
chroma-mcp-client query [OPTIONS] QUERY_TEXT
```

**Arguments:**

- `QUERY_TEXT`: The natural language text to query for.

**Options:**

- `--collection-name NAME`: Name of the ChromaDB collection to query. Default: `codebase_v1`.
- `-n, --n-results N`: Number of results to return. Default: `5`.

**Example:**

```bash
chroma-mcp-client query "how to handle database connection errors" -n 3
```

#### `analyze-chat-history`

Analyzes recent chat history entries (from a specified collection, typically `chat_history_v1`) to correlate recorded AI suggestions/responses with actual Git changes made to mentioned files within a specified repository.

```bash
chroma-mcp-client analyze-chat-history [OPTIONS]
```

**Options:**

- `--collection-name NAME`: Name of the ChromaDB chat history collection. Default: `chat_history_v1`.
- `--repo-path PATH`: Path to the Git repository to analyze for code changes. Default: Current working directory.
- `--status-filter STATUS`: Metadata status value to filter entries for analysis. Default: `captured`.
- `--new-status STATUS`: Metadata status value to set for entries after successful analysis. Default: `analyzed`.
- `--days-limit N`: How many days back to look for entries to analyze (0 for no limit). Default: `7`.

**Example:**

```bash
# Analyze entries from the last 30 days in the current repo
chroma-mcp-client analyze-chat-history --days-limit 30

# Analyze entries in a different repo using a custom status
chroma-mcp-client analyze-chat-history --repo-path /path/to/other/repo --status-filter pending --new-status correlated
```

#### `log-chat`

Log a chat interaction with enhanced context to ChromaDB, capturing rich metadata about the interaction, file changes, and tool usage.

```bash
chroma-mcp-client log-chat [OPTIONS]
```

**Options:**

- `--prompt-summary TEXT`: (Required) Summary of the user's prompt/question.
- `--response-summary TEXT`: (Required) Summary of the AI's response/solution.
- `--raw-prompt TEXT`: Full text of the user's prompt. Falls back to prompt summary if not provided.
- `--raw-response TEXT`: Full text of the AI's response. Falls back to response summary if not provided.
- `--tool-usage-file PATH`: Path to JSON file containing tool usage information.
- `--file-changes-file PATH`: Path to JSON file containing information about file changes.
- `--involved-entities TEXT`: Comma-separated list of entities involved in the interaction (e.g., file paths, function names).
- `--session-id UUID`: Session ID for the interaction. Generated as a new UUID if not provided.
- `--collection-name NAME`: Name of the ChromaDB collection to log to. Default: `chat_history_v1`.

**Examples:**

```bash
# Basic usage with only required parameters
chroma-mcp-client log-chat --prompt-summary "How to fix the login bug" --response-summary "Fixed the login issue by updating authentication flow"

# Complete usage with all parameters
chroma-mcp-client log-chat \
  --prompt-summary "How to fix the login bug" \
  --response-summary "Fixed the login issue by updating authentication flow" \
  --raw-prompt "I'm having issues with users not being able to log in. Can you help fix it?" \
  --raw-response "The issue is in auth.js where the token validation is incorrect. I've updated the code to properly validate tokens." \
  --tool-usage-file tools.json \
  --file-changes-file changes.json \
  --involved-entities "auth.js,login.js,authentication,validation" \
  --session-id "3e4r5t6y-7u8i-9o0p-a1s2-d3f4g5h6j7k8" \
  --collection-name "custom_chat_history"
```

The captured information is stored in the specified ChromaDB collection with rich metadata to enable future retrieval, correlation with code changes, and learning from past interactions.

#### `update-collection-ef`

Updates the embedding function name stored in a specific collection's metadata.

**When to Use:**

This command is necessary when you change the embedding function your client uses (e.g., by modifying the `CHROMA_EMBEDDING_FUNCTION` setting in your `.env` file or the equivalent configuration in `.cursor/mcp.json`) for a project with an **existing** ChromaDB collection.

If the new client embedding function doesn't match the function name stored in the collection's metadata (from when it was created or last updated), ChromaDB will raise an `Embedding function name mismatch` error when you try to access the collection (e.g., via `query` or `analyze-chat-history`). Running this command syncs the collection's metadata record with your new client-side setting.

```bash
chroma-mcp-client update-collection-ef --collection-name NAME --ef-name EF_NAME
```

**Options:**

- `--collection-name NAME`: (Required) Name of the ChromaDB collection to update.
- `--ef-name EF_NAME`: (Required) The new embedding function name string to store in the collection's metadata (e.g., `sentence_transformer`, `onnx_mini_lm_l6_v2`). This name should typically match the class name or identifier used by ChromaDB for the embedding function specified in your *current* client configuration (`.env` or `mcp.json`).

**Example:**

```bash
# You changed CHROMA_EMBEDDING_FUNCTION in .env to 'accurate' (which maps to sentence_transformer internally)
# Now update the existing 'chat_history_v1' collection metadata to match:
chroma-mcp-client update-collection-ef --collection-name chat_history_v1 --ef-name sentence_transformer
```

#### `promote-learning`

Manually promotes an insight or finding into the `derived_learnings_v1` collection. This is useful for adding learnings that didn't originate directly from an automatically analyzed chat entry, or if the interactive `review-and-promote` workflow is bypassed.

```bash
chroma-mcp-client promote-learning [OPTIONS]
```

**Options:**

- `--description TEXT`: **(Required)** Concise description of the learning.
- `--pattern TEXT`: **(Required)** Generalized pattern or rule derived.
- `--code-ref TEXT`: **(Required)** Relevant code snippet reference (`chunk_id`: `file:sha:index`).
- `--tags TEXT`: **(Required)** Comma-separated tags.
- `--confidence FLOAT`: **(Required)** Confidence score (0.0-1.0).
- `--source-chat-id TEXT`: (Optional) ID of the source entry in `chat_history_v1` to link and update status to `promoted_to_learning`.
- `--collection-name NAME`: Target collection for the new learning (default: `derived_learnings_v1`).
- `--chat-collection-name NAME`: Source chat history collection (default: `chat_history_v1`).

**Example:**

```bash
# Promote learning from chat entry 'xyz', linking to a code chunk
chroma-mcp-client promote-learning \
  --source-chat-id "xyz" \
  --description "Use BackgroundTasks for non-blocking FastAPI tasks." \
  --pattern "Defer long operations in FastAPI via BackgroundTasks." \
  --code-ref "src/api/tasks.py:abc123def456:1" \
  --tags "fastapi,background,async,python" \
  --confidence 0.9
```

**(Note:** For ease of use, a wrapper script `scripts/promote_learning.sh` and a corresponding hatch alias `promote-learn` are typically available. See [`docs/scripts/promote-learning.md`](promote-learning.md) for details.)**

#### `setup-collections`

Ensures that all standard ChromaDB collections required by the system (`codebase_v1`, `chat_history_v1`, `derived_learnings_v1`, `thinking_sessions_v1`) exist. It will create any missing collections using default settings.

```bash
hatch run chroma-mcp-client setup-collections
# or using alias:
hatch run setup-collections
```

#### `review-and-promote`

Starts an interactive workflow to review chat entries marked with the status 'analyzed' (typically by the `analyze-chat-history` command). It allows the user to:

- View the summary of each analyzed chat entry.
- Search the codebase (`codebase_v1`) for potentially relevant code snippets (chunks) based on the chat summary.
- Choose to:
  - **Promote (p):** Create a new entry in the `derived_learnings_v1` collection. The user provides details like pattern, tags, and confidence, and selects a suggested code reference or enters one manually.
  - **Ignore (i):** Mark the chat entry with status 'ignored'.
  - **Skip (s):** Skip the current entry and move to the next.
  - **Quit (q):** Exit the review process.

**Recent Enhancements:**

- **Auto-Promote:** Automatically promote high confidence entries (≥0.8 by default), with customizable threshold.
- **Smart Defaults:** Intelligent defaults for all fields based on context, allowing users to often just press Enter.
- **Low Confidence Warnings:** Visual warnings when promoting entries with confidence below 0.5.
- **Enhanced Code Selection:** Better bidirectional link support, auto-selecting the most relevant code reference.

**Arguments:**

- `--days-limit` (int, default: 7): How many days back to look for 'analyzed' entries.
- `--fetch-limit` (int, default: 50): Maximum number of entries to fetch for review in one go.
- `--chat-collection-name` (str, default: "chat_history_v1"): Name of the chat history collection.
- `--learnings-collection-name` (str, default: "derived_learnings_v1"): Name of the derived learnings collection.
- `--modification-type` (str, default: "all"): Filter by modification type (choices: all, refactor, bugfix, feature, documentation, optimization, test, config, style, unknown).
- `--min-confidence` (float, default: 0.0): Minimum confidence score threshold (0.0-1.0).
- `--sort-by-confidence/--no-sort-by-confidence` (bool, default: True): Sort entries by confidence score.
- `--auto-promote` (bool, default: False): Automatically promote high confidence entries without user review.
- `--auto-promote-threshold` (float, default: 0.8): Custom confidence threshold for auto-promotion (0.0-1.0).

**Example:**

```bash
# Start interactive review for entries from the last 3 days
hatch run chroma-mcp-client review-and-promote --days-limit 3

# or using alias:
hatch run review-promote --days-limit 3

# Enable auto-promote with a custom threshold
hatch run review-promote --auto-promote --auto-promote-threshold 0.75
```

For more details, see the [review-and-promote.md](review-and-promote.md) documentation.

### Note on Usage with Hatch

When running these commands within the `hatch` environment (e.g., `hatch run ...`), you might encounter issues where the `chroma-mcp-client` alias defined in `pyproject.toml` is not correctly resolved for subcommands like `analyze-chat-history`.

If commands like `hatch run chroma-mcp-client analyze-chat-history ...` fail with "command not found" or similar errors, use the direct module execution syntax instead:

```bash
hatch run python -m chroma_mcp_client.cli <command> [OPTIONS] [ARGS]...

# Example:
hatch run python -m chroma_mcp_client.cli analyze-chat-history --days-limit 30
```
