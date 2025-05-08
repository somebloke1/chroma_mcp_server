# Script: `review-and-promote.sh`

This script provides a convenient way to launch the interactive chat history review and promotion workflow.

## Purpose

Initiates the `chroma-client review-and-promote` command within the correct Hatch environment. This command fetches chat entries marked as 'analyzed', displays them to the user, allows searching the codebase for relevant code references, and prompts the user to promote, ignore, or skip each entry.

See the main [`chroma-client` documentation](chroma-client.md#review-and-promote) for full details on the underlying command and its options.

## Usage

```bash
# Run with default settings (7 day limit, 50 fetch limit)
./scripts/review_and_promote.sh

# Run with custom day limit
./scripts/review_and_promote.sh --days-limit 3

# Run with custom fetch limit and collection names
./scripts/review_and_promote.sh --fetch-limit 20 --chat-collection-name my_chats_v2 --learnings-collection-name my_learnings_v2
```

## Hatch Alias

A convenient alias `review-promote` is typically defined in `pyproject.toml`:

```bash
# Run via hatch alias with defaults
hatch run review-promote

# Run via hatch alias with arguments
hatch run review-promote --days-limit 3
```

This script simplifies running the interactive promotion process from the command line.
