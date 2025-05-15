# Automated Chat History Logging

This document explains how to configure and utilize the `auto_log_chat` rule to automatically capture summaries of AI assistant interactions into the `chat_history_v1` ChromaDB collection.

## Purpose

The goal is to create a persistent log of chat interactions (prompts, responses, actions taken) within ChromaDB. This history can then be analyzed to derive learnings, understand development patterns, or provide richer context for future AI interactions, fulfilling Phase 4 of the [Local RAG Pipeline Plan](../refactoring/local_rag_pipeline_plan_v4.md).

## Rule Overview

The core mechanism is an AI instruction rule named `auto_log_chat`. Two versions are maintained:

- `.cursor/rules/auto_log_chat.mdc`: The primary rule file used by the Cursor IDE.
- `docs/rules/auto_log_chat.md`: A generic Markdown copy for reference and potential use by other clients.

## Cursor Setup

Cursor has built-in support for applying rules located in the `.cursor/rules/` directory.

1. **Ensure the Rule File Exists:** Verify that `.cursor/rules/auto_log_chat.mdc` exists.
2. **Add Required Header:** The rule file **must** begin with a YAML front matter block like this to ensure Cursor applies it automatically to all interactions:

    ```yaml
    ---
    description: This rule helps to log chat history to the `chat_history_v1` collection
    globs:
    alwaysApply: true
    ---
    ```

3. **Rule Content:** Following the header, the file contains the Markdown instructions defining the `auto_log_chat` rule (summarize prompt/response, identify entities, call MCP tool).
4. **Automatic Application:** Because `alwaysApply` is set to `true`, Cursor will automatically load and instruct the AI assistant to follow this rule for every prompt/response cycle without needing manual intervention.

## Generic Rule for Other Clients

The file `docs/rules/auto_log_chat.md` serves as a standard Markdown version of the rule.

### Windsurf / VS Code + Copilot / Other Client Integration

Integration with non-Cursor clients depends heavily on the specific client's capabilities for incorporating custom instructions or rules:

- **Manual Inclusion:** If the client allows for custom system prompts, meta-prompts, or pre-prompt instructions, you can manually copy the content of `docs/rules/auto_log_chat.md` into that configuration.
- **Client-Specific Mechanisms:** Some clients might develop mechanisms to read rules from specific files or directories. If such features become available, `docs/rules/auto_log_chat.md` could be used as the source.
- **Limited Support:** If the client offers no way to inject persistent instructions automatically, you would need to manually remind the AI assistant to follow the logging procedure described in the rule file, which is less reliable.

Consult the documentation for your specific AI client/IDE integration to determine the best method for applying the rule instructions.

## Manual Logging via CLI Command

In cases where automatic logging is not available or for logging interactions from non-IDE environments, the project provides a CLI command for manual logging:

### `chroma-client log-chat`

This command allows you to manually log chat interactions with rich context:

```bash
chroma-client log-chat --prompt-summary "User question" --response-summary "AI response"
```

#### Required Parameters

- `--prompt-summary`: A concise summary of the user's question or request
- `--response-summary`: A concise summary of the AI's response or solution

#### Optional Parameters

- `--raw-prompt`: The full text of the user's prompt
- `--raw-response`: The full text of the AI's response
- `--tool-usage-file`: Path to a JSON file containing tool usage information
- `--file-changes-file`: Path to a JSON file containing file change information
- `--involved-entities`: Comma-separated list of entities involved (files, functions, concepts)
- `--session-id`: A session identifier (UUID) to group related interactions
- `--collection-name`: The collection to log to (default: `chat_history_v1`)

#### Example Usage

Basic usage with only required parameters:

```bash
chroma-client log-chat \
  --prompt-summary "How to fix the authentication bug" \
  --response-summary "Updated token validation in auth.js"
```

Advanced usage with optional parameters:

```bash
chroma-client log-chat \
  --prompt-summary "How to fix the authentication bug" \
  --response-summary "Updated token validation in auth.js" \
  --raw-prompt "Users are reporting they can't log in after session timeout" \
  --raw-response "The issue appears to be in the token validation logic. I've updated auth.js to properly check expiration times." \
  --tool-usage-file tools.json \
  --file-changes-file changes.json \
  --involved-entities "auth.js,login.js,token_validation,session_timeout" \
  --session-id "550e8400-e29b-41d4-a716-446655440000"
```

For further details on this command, see the [CLI Reference](../scripts/chroma-client.md#log-chat).

## Tool Usage Format

When logging chat interactions (either automatically or manually), the system expects tool usage information to follow a specific format:

```json
[
  {"name": "read_file", "args": {"target_file": "src/config.js"}},
  {"name": "edit_file", "args": {"target_file": "src/config.js", "instructions": "Update JWT settings"}}
]
```

Each tool usage item must contain:

- `name`: The name of the tool that was used
- `args`: (Optional) An object containing the arguments passed to the tool

For comprehensive details about the format, technical specifics, and examples, refer to the [Tool Usage Format Specification](../usage/tool_usage_format.md).

For further details on the logging command, see the [CLI Reference](../scripts/chroma-client.md#log-chat).
