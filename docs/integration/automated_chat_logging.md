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
