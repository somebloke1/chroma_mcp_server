# Console Script: `chroma-client`

This document describes the usage of the `chroma-client` console script, which provides a command-line interface for interacting directly with a ChromaDB instance for automation tasks, primarily codebase indexing and querying.

## Installation

To use this script, you need to install the `chroma-mcp-server` package with the `client` extra dependencies:

```bash
pip install "chroma-mcp-server[client]"
```

Alternatively, if managing the project with `hatch`, ensure the `client` feature or necessary dependencies are included in your environment.

## Configuration

The `chroma-client` script relies on a `.env` file located in the root of your project directory (or the directory where you run the command) to configure the connection to ChromaDB. Key variables include:

- `CHROMA_CLIENT_TYPE`: (`persistent`, `http`, `cloud`)
- `CHROMA_DATA_DIR`: (Required for `persistent`)
- `CHROMA_HOST`, `CHROMA_PORT`, `CHROMA_SSL`, `CHROMA_HEADERS`: (Used for `http`)
- `CHROMA_TENANT`, `CHROMA_DATABASE`, `CHROMA_API_KEY`: (Used for `cloud`)
- `CHROMA_EMBEDDING_FUNCTION`: (Optional, defaults to `default`)

Refer to the main project documentation for detailed `.env` configuration options.

## Usage

```bash
chroma-client [OPTIONS] COMMAND [ARGS]...
```

### Global Options

- `-h`, `--help`: Show the help message and exit.
- `-v, --verbose`: Increase output verbosity. Use `-v` for INFO level, `-vv` for DEBUG level. Defaults to INFO.

### Commands

#### `index`

Index specific files, directories (recursively), or all git-tracked files into ChromaDB.

```bash
chroma-client index [OPTIONS] [PATHS...]
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
chroma-client index ./src/my_module.py --repo-root .

# Index all files tracked by git in the current repo
chroma-client index --all

# Index files in a specific directory recursively, using a custom collection
chroma-client index ./docs --collection-name project_docs --repo-root .
```

#### `count`

Count documents in a ChromaDB collection.

```bash
chroma-client count [OPTIONS]
```

**Options:**

- `--collection-name NAME`: Name of the ChromaDB collection to count. Default: `codebase_v1`.

**Example:**

```bash
chroma-client count --collection-name codebase_v1
```

#### `query`

Query a ChromaDB collection using semantic search.

```bash
chroma-client query [OPTIONS] QUERY_TEXT
```

**Arguments:**

- `QUERY_TEXT`: The natural language text to query for.

**Options:**

- `--collection-name NAME`: Name of the ChromaDB collection to query. Default: `codebase_v1`.
- `-n, --n-results N`: Number of results to return. Default: `5`.

**Example:**

```bash
chroma-client query "how to handle database connection errors" -n 3
```

#### `analyze-chat-history`

Analyzes recent chat history entries (from a specified collection, typically `chat_history_v1`) to correlate recorded AI suggestions/responses with actual Git changes made to mentioned files within a specified repository.

```bash
chroma-client analyze-chat-history [OPTIONS]
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
chroma-client analyze-chat-history --days-limit 30

# Analyze entries in a different repo using a custom status
chroma-client analyze-chat-history --repo-path /path/to/other/repo --status-filter pending --new-status correlated
```

#### `update-collection-ef`

Updates the embedding function name stored in a specific collection's metadata.

**When to Use:**

This command is necessary when you change the embedding function your client uses (e.g., by modifying the `CHROMA_EMBEDDING_FUNCTION` setting in your `.env` file or the equivalent configuration in `.cursor/mcp.json`) for a project with an **existing** ChromaDB collection.

If the new client embedding function doesn't match the function name stored in the collection's metadata (from when it was created or last updated), ChromaDB will raise an `Embedding function name mismatch` error when you try to access the collection (e.g., via `query` or `analyze-chat-history`). Running this command syncs the collection's metadata record with your new client-side setting.

```bash
chroma-client update-collection-ef --collection-name NAME --ef-name EF_NAME
```

**Options:**

- `--collection-name NAME`: (Required) Name of the ChromaDB collection to update.
- `--ef-name EF_NAME`: (Required) The new embedding function name string to store in the collection's metadata (e.g., `sentence_transformer`, `onnx_mini_lm_l6_v2`). This name should typically match the class name or identifier used by ChromaDB for the embedding function specified in your *current* client configuration (`.env` or `mcp.json`).

**Example:**

```bash
# You changed CHROMA_EMBEDDING_FUNCTION in .env to 'accurate' (which maps to sentence_transformer internally)
# Now update the existing 'chat_history_v1' collection metadata to match:
chroma-client update-collection-ef --collection-name chat_history_v1 --ef-name sentence_transformer
```

### Note on Usage with Hatch

When running these commands within the `hatch` environment (e.g., `hatch run ...`), you might encounter issues where the `chroma-client` alias defined in `pyproject.toml` is not correctly resolved for subcommands like `analyze-chat-history`.

If commands like `hatch run chroma-client analyze-chat-history ...` fail with "command not found" or similar errors, use the direct module execution syntax instead:

```bash
hatch run python -m chroma_mcp_client.cli <command> [OPTIONS] [ARGS]...

# Example:
hatch run python -m chroma_mcp_client.cli analyze-chat-history --days-limit 30
```
