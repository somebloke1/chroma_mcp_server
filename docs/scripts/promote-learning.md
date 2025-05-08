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

# Using the Hatch alias (if defined in pyproject.toml, e.g., 'promote-learn')
hatch run promote-learn \
    --source-chat-id "xyz" \
    --description "Use BackgroundTasks for non-blocking FastAPI tasks." \
    --pattern "Defer long operations in FastAPI via BackgroundTasks." \
    --code-ref "src/api/tasks.py:abc123def456:1" \
    --tags "fastapi,background,async,python" \
    --confidence 0.9
```

## Expected Output

Upon successful completion, the script will log:

- Confirmation that the learning was added to `derived_learnings_v1` (including its new ID).
- Confirmation that the source chat entry (if provided via `--source-chat-id`) was updated in `chat_history_v1`.
- A final message: `promote-learning finished successfully.`

If errors occur (e.g., missing required arguments, database connection issues), they will be logged, and the script will exit with an error code.
