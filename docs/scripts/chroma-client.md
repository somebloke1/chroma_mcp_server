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
- `--log-level LEVEL`: Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Overrides the `LOG_LEVEL` environment variable if set. Defaults to the value of the `LOG_LEVEL` environment variable, or `INFO` if the environment variable is not set or invalid.

### Commands

#### `index`

Index specific files, directories (recursively), or all git-tracked files into ChromaDB.

```bash
chroma-client index [OPTIONS] [PATHS...]
```

**Arguments:**

- `PATHS...`: Optional specific file or directory paths to index. If directories are provided, they will be indexed recursively.

**Options:**

- `--repo-root PATH`: Repository root path. Used for determining relative paths for document IDs and metadata. Default: Current working directory.
- `--all`: Index all files currently tracked by git in the specified `--repo-root`.
- `--collection-name NAME`: Name of the ChromaDB collection to use. Default: `codebase_v1`.

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
