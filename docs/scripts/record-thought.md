# Console Script: `record-thought`

This document describes the usage of the `record-thought` console script, which provides a command-line interface for interacting with the Chroma MCP Thinking Utilities. It allows you to record thoughts, create branches, and search thinking sessions stored via an MCP server.

## Installation

To use this script, you need to install the `chroma-mcp-server` package. This script directly launches the Chroma MCP server as a subprocess using standard input/output (stdio) for communication.

```bash
# Installs server, thinking tools, and dependencies
pip install "chroma-mcp-server"
```

## Communication

This script communicates with the Chroma MCP Server using the **stdio** transport layer. It automatically starts the server (`python -m chroma_mcp.cli --mode stdio`) in the background when a command is executed and communicates with it via the MCP protocol over the subprocess's stdin and stdout streams. No separate server URL configuration is required.

## Usage

```bash
record-thought COMMAND [ARGS]...
```

### Commands

#### `record`

Record a single thought or a chain of thoughts into a thinking session.

```bash
record-thought record [OPTIONS] [THOUGHTS...]
```

**Arguments:**

- `THOUGHTS...`: One or more thought strings to record. If multiple are provided, they form a chain.

**Options:**

- `--thought TEXT`: Specify a single thought (alternative to positional arguments).
- `--file PATH`: Read thoughts from a file (one thought per line).
- `--session-id ID`: Specify an existing session ID to add thoughts to. If omitted, a new session is created.
- `--thought-number NUM`: (Use only with single thought) Explicitly set the thought number. Requires `--total-thoughts`.
- `--total-thoughts NUM`: (Use only with single thought) Explicitly set the total expected thoughts. Required if `--thought-number` is used.
- `--next-thought-needed`: (Use only with single thought) Flag indicating a subsequent thought is expected.
- `--metadata JSON`: Attach custom JSON metadata string to the session (only applies when creating a new chain via `record_thought_chain`).

**Examples:**

```bash
# Record a single thought into a new session
record-thought record "Initial idea for refactoring the API."

# Record a chain of thoughts
record-thought record "Step 1: Identify endpoints." "Step 2: Draft new schema." "Step 3: Implement changes."

# Record thoughts from a file into a specific session
record-thought record --session-id xyz789 --file ./my_thoughts.txt

# Add a single thought to an existing session, specifying numbers
record-thought record --session-id xyz789 --thought "Adding error handling." --thought-number 4 --total-thoughts 5 --next-thought-needed
```

#### `branch`

Create a new thought branch diverging from a specific thought in an existing session.

```bash
record-thought branch [OPTIONS] --parent-session-id ID --parent-thought-number NUM [THOUGHTS...]
```

**Arguments:**

- `THOUGHTS...`: One or more thought strings for the new branch.

**Required Options:**

- `--parent-session-id ID`: ID of the session to branch from.
- `--parent-thought-number NUM`: The thought number in the parent session to branch from.

**Options:**

- `--thoughts TEXT...`: Specify branch thoughts via options (alternative to positional arguments).
- `--file PATH`: Read branch thoughts from a file.
- `--branch-id ID`: Specify a custom ID for the new branch. If omitted, a short UUID is generated.

**Example:**

```bash
# Create a branch from thought #2 of session xyz789
record-thought branch --parent-session-id xyz789 --parent-thought-number 2 \
  "Alternative approach: Use caching." "Measure performance difference."
```

#### `search`

Search for semantically similar thoughts or sessions.

```bash
record-thought search [OPTIONS] QUERY
```

**Arguments:**

- `QUERY`: The text to search for.

**Options:**

- `--session-id ID`: Limit search to a specific session ID.
- `--limit N, -n N`: Maximum number of results to return. Default: `10`.
- `--threshold T`: Similarity score threshold (0.0 to 1.0, lower is more similar). Default: `-1.0` (uses server default).
- `--exclude-branches`: Exclude thoughts belonging to branches from the search.
- `--sessions`: Search for similar *sessions* based on overall content, instead of individual thoughts.

**Examples:**

```bash
# Search for thoughts related to "database optimization"
record-thought search "database optimization"

# Search within a specific session, excluding branches
record-thought search "API error handling" --session-id abc123 --exclude-branches -n 5

# Search for similar sessions
record-thought search "user authentication patterns" --sessions
```

#### `summary`

Retrieve and display all thoughts recorded within a specific thinking session.

```bash
record-thought summary [OPTIONS] SESSION_ID
```

**Arguments:**

- `SESSION_ID`: The ID of the session to summarize.

**Options:**

- `--exclude-branches`: Do not include thoughts from branches in the summary.

**Example:**

```bash
record-thought summary abc123
```
