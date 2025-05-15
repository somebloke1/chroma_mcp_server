# Tool Usage Format Specification

This document provides a comprehensive specification for the `tool_usage` parameter used in various parts of the Chroma MCP Server, particularly in the `chroma_log_chat` tool and related functionality.

**Document Purpose:** This is the canonical reference for the tool_usage format across the entire codebase. While individual tool documentation (like [`log-chat.md`](../scripts/log-chat.md)) may include basic usage examples, this specification covers all details, edge cases, and technical implementation aspects.

## Standard Format

The `tool_usage` parameter is an array of objects, where each object MUST follow this structure:

```json
{
  "name": "tool_name",
  "args": {
    "param1": "value1",
    "param2": "value2",
    ...
  }
}
```

### Required Fields

- `name` (string): The name of the tool that was used (e.g., "read_file", "edit_file", "codebase_search").
  
### Optional Fields

- `args` (object): A JSON object containing the arguments passed to the tool. This field is optional but recommended for comprehensive logging.

## Examples

### Basic Example

```json
[
  {"name": "read_file", "args": {"target_file": "src/config.js"}},
  {"name": "edit_file", "args": {"target_file": "src/config.js"}}
]
```

### Complex Example

```json
[
  {"name": "codebase_search", "args": {"query": "JWT authentication", "target_directories": ["src/auth"]}},
  {"name": "read_file", "args": {"target_file": "src/auth/jwt.js", "offset": 10, "limit": 50}},
  {"name": "edit_file", "args": {"target_file": "src/auth/jwt.js", "instructions": "Update token expiration"}}
]
```

## Programmatic Usage

When constructing the `tool_usage` list in code:

```python
tool_usage = [
    {"name": "read_file", "args": {"target_file": "file.txt"}},
    {"name": "edit_file", "args": {"target_file": "file.txt", "instructions": "Update content"}}
]
```

## Command Line Usage

When using with the `chroma-client log-chat` command:

```bash
--tool-usage '[{"name": "read_file", "args": {"target_file": "file.txt"}}, {"name": "edit_file", "args": {"target_file": "file.txt"}}]'
```

## Legacy/Deprecated Format

> **Note:** This format is deprecated and will be removed in a future version.

For backward compatibility, the system currently also accepts an alternative format:

```json
{
  "tool": "tool_name",
  "params": {
    "param1": "value1",
    "param2": "value2",
    ...
  }
}
```

However, using this format will generate warnings, and it's recommended to migrate to the standard format with `name` and `args` keys.

## Technical Details

The `tool_usage` parameter is used in multiple places:

1. **Auto Log Chat Rule**: The rule instructs AI assistants to log their tool usage during interactions.
2. **ChromaDB Storage**: The tool usage is processed and stored in the `chat_history_v1` collection.
3. **Analysis**: Tool sequences are derived from this data for pattern analysis and learning extraction.

### Processing

During processing:

1. The tool names are extracted to form a `tool_sequence` string (e.g., "read_file→edit_file→run_terminal_cmd").
2. This sequence helps identify problem-solving patterns and aids in confidence scoring.
3. The sequence may be used for reinforcement learning in later phases.

## Troubleshooting

If you encounter errors related to the `tool_usage` parameter:

1. **Validation Error**: Ensure each item in the array has a `name` key.
2. **Missing Required Fields**: Check that every object includes at least the `name` field.
3. **Format Issues**: Verify the JSON structure is valid with properly formatted arrays and objects.

## Related Documentation

- [API Reference - chroma_log_chat](../api_reference.md#chroma_log_chat)
- [Enhanced Context Capture](./enhanced_context_capture.md)
- [Log Chat Script](../scripts/log-chat.md)
