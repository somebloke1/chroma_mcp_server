# Wrapper Script: `log_chat.sh`

This script provides a simple wrapper for running the `log-chat` command of the `chroma-mcp-client` tool within the correct Hatch environment.

## Purpose

The primary goal of this script is to simplify the execution of the chat logging functionality, ensuring it runs with the project's dependencies managed by Hatch. It captures and stores chat interactions with enhanced context in a ChromaDB collection.

It essentially runs the following command:

```bash
hatch run chroma-mcp-client log-chat [ARGUMENTS...]
```

## Prerequisites

- `hatch` installed and available in your PATH.
- The project environment configured via `hatch`.
- A configured `.env` file for the `chroma-mcp-client` (see `docs/scripts/chroma-mcp-client.md`).

## Usage

Navigate to the project root directory and run the script:

```bash
./scripts/log_chat.sh [OPTIONS]
```

### Script Parameters

The script passes all arguments directly to the underlying `log-chat` subcommand. Common parameters include:

- `--prompt-summary TEXT`: A brief summary of the user's prompt (required).
- `--response-summary TEXT`: A brief summary of the AI's response (required).
- `--raw-prompt TEXT`: The complete text of the user's prompt (required).
- `--raw-response TEXT`: The complete text of the AI's response (required).
- `--collection-name NAME`: Specify the ChromaDB collection (default: `chat_history_v1`).
- `--involved-entities TEXT`: Comma-separated list of entities involved in the interaction (optional).
- `--session-id UUID`: Session ID for the interaction (optional, generated if not provided).
- `--file-changes JSON`: List of files modified with before/after content as JSON (optional).
- `--tool-usage JSON`: List of tools used during the interaction as JSON (optional).

### Example Usage

```bash
# Log a basic chat interaction
./scripts/log_chat.sh \
  --prompt-summary "User asked about authentication implementation" \
  --response-summary "Provided JWT-based authentication solution" \
  --raw-prompt "How should I implement authentication in my app?" \
  --raw-response "I recommend using JWT tokens for authentication..."

# Log with enhanced context
./scripts/log_chat.sh \
  --prompt-summary "User asked about authentication implementation" \
  --response-summary "Added JWT authentication to user model" \
  --raw-prompt "How should I implement authentication in my app?" \
  --raw-response "I've added JWT authentication to your user model..." \
  --involved-entities "user.js,auth.js,JWT" \
  --file-changes '[{"file_path": "src/models/user.js", "diff_summary": "Added JWT methods"}]' \
  --tool-usage '[{"name": "edit_file", "args": {"target_file": "src/models/user.js"}}]'
```

### Tool Usage Format

The `--tool-usage` parameter expects a JSON array of objects, where each object MUST contain:

- `name`: The name of the tool that was used (e.g., "read_file", "edit_file")
- `args`: (Optional) An object containing the arguments passed to the tool

Example:

```json
[
  {"name": "read_file", "args": {"target_file": "src/config.js"}},
  {"name": "edit_file", "args": {"target_file": "src/config.js", "instructions": "Update JWT settings"}}
]
```

> **Note:** For a complete specification of the tool_usage format, including advanced usage, programmatic examples, and technical details, see the [Tool Usage Format Specification](../usage/tool_usage_format.md).

## Expected Output

Upon successful completion, the script will log:

```text
Running chat logging in /path/to/project...
[Various log messages from the operation]
Chat logging completed successfully.
```

If errors occur during processing, they will be logged to the console, and the script will exit with a non-zero status code.

The successfully logged chat will be stored in the specified ChromaDB collection (default: `chat_history_v1`) and can be retrieved later using the `analyze-chat-history.sh` script.
