# Wrapper Script: `promote_learning.sh`

This script provides a simple wrapper for running the `promote-learning` command of the `chroma-client` tool within the correct Hatch environment.

## Purpose

The primary goal of this script is to simplify the execution of the learning promotion logic, ensuring it runs with the project's dependencies managed by Hatch.

It essentially runs the following command:

```bash
hatch run chroma-client promote-learning [ARGUMENTS...]
```

Refer to the main [`chroma-client` documentation](chroma-client.md#promote-learning) for details on the underlying command's arguments (`--description`, `--pattern`, `--code-ref`, etc.).

## Prerequisites

- `hatch` installed and available in your PATH.
- The project environment configured via `hatch`.
- A configured `.env` file for the `chroma-client` (see `docs/scripts/chroma-client.md`).

## Usage

Navigate to the project root directory and run the script, passing the necessary arguments for the `promote-learning` command:

```bash
./scripts/promote_learning.sh [OPTIONS_FOR_PROMOTE_LEARNING]
```

### Script Parameters

This script passes all arguments directly to the `chroma-client promote-learning` command. See the [`chroma-client` documentation](chroma-client.md#promote-learning) for the required and optional arguments like `--description`, `--pattern`, `--code-ref`, `--tags`, `--confidence`, `--source-chat-id`, etc.

### Enhanced Context Features

The promote-learning command now supports rich context features:

1. **Automatic Context Inclusion**: When providing a source chat ID, the command automatically fetches and includes rich context data such as code snippets, diff summaries, tool sequences, and modification types in the derived learning.

2. **Confidence Score Inference**: If no explicit confidence score is provided (or set to 0.0) and the source chat has a confidence score, the source chat's score will be used.

3. **Description Enhancement**: For minimal descriptions (less than 100 characters), the command can automatically enhance them with context from the source chat, including prompt summary, response summary, and diff summary.

4. **Context Control**: Use `--include-chat-context` (default) to include rich context, or `--no-include-chat-context` to disable this feature if you prefer a completely manual approach.

### Example Usage

```bash
# Promote learning from chat entry 'xyz', linking to a code chunk
./scripts/promote_learning.sh \
    --source-chat-id "xyz" \
    --description "Use BackgroundTasks for non-blocking FastAPI tasks." \
    --pattern "Defer long operations in FastAPI via BackgroundTasks." \
    --code-ref "src/api/tasks.py:abc123def456:1" \
    --tags "fastapi,background,async,python" \
    --confidence 0.9

# Promote learning with manual confidence and no automatic context inclusion
./scripts/promote_learning.sh \
    --source-chat-id "xyz" \
    --description "Detailed manual description..." \
    --pattern "Manual pattern..." \
    --code-ref "src/file.py:sha:0" \
    --tags "manual,tags" \
    --confidence 0.75 \
    --no-include-chat-context

# Using the Hatch alias (if defined in pyproject.toml, e.g., 'promote-learn')
hatch run promote-learn --source-chat-id "xyz" --description "..." --pattern "..." --code-ref "..." --tags "..." --confidence 0.8
```

## Expected Output

Upon successful completion, the script will:

1. Display the ID of the newly created learning entry in the `derived_learnings_v1` collection.
2. Confirm the status update of the source chat entry to `promoted_to_learning`.
3. Let you know if rich context was included from the source chat.

Example output:

```bash
Running promote-learning in /path/to/project...
Learning promoted with ID: 12345678-1234-5678-1234-567812345678
Updated status for source chat ID: xyz
promote-learning finished successfully.
```

If errors occur (e.g., missing required arguments, database connection issues), they will be logged, and the script will exit with an error code.
