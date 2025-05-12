# Enhanced Context Capture System

The Enhanced Context Capture system provides rich contextual information about code changes and AI interactions. It enables bidirectional linking between chat history and code chunks, allowing developers to understand the relationship between discussions and code modifications.

## Key Features

### 1. Code Context Extraction

The system automatically extracts relevant code snippets from before and after edits, showing the changes in a clear, diff-like format. This provides immediate visibility into what was modified without having to manually compare versions.

```diff
CHANGED FILE:
@@ -1,5 +1,5 @@
 def validate_token(token):
     # Check if token is valid
     if not token:
         return False
-    # TODO: Check expiration
+    # Check expiration
+    return not is_token_expired(token)
```

### 2. Diff Summarization

For each modified file, the system generates a human-readable summary of the changes, including:

- Number of lines added and removed
- Functions or classes added or removed
- Overall modification type

```bash
Modified src/auth.py: 2 lines added, 1 lines removed. Added: is_token_expired function
```

### 3. Tool Sequence Tracking

The system tracks the sequence of tools used during an interaction, revealing the problem-solving approach:

```bash
codebase_search→read_file→edit_file→run_terminal_cmd
```

Common patterns identified include:

- `MULTIPLE_READS`: Deep research into the codebase before making changes
- `SEARCH_THEN_EDIT`: Finding and then modifying relevant code
- `ITERATIVE_REFINEMENT`: Multiple edit-reapply cycles to perfect a change
- `EXPLORATION`: Extensive searching without edits (information gathering)
- `CODE_EXECUTION`: Running terminal commands to test or validate changes

### 4. Modification Type Classification

Changes are automatically categorized into standardized types:

- `REFACTOR`: Improving existing functionality without changing behavior
- `BUGFIX`: Correcting errors or unexpected behavior
- `FEATURE`: Adding new capabilities or functionality
- `DOCUMENTATION`: Improving comments or documentation
- `OPTIMIZATION`: Performance improvements
- `TEST`: Adding or updating tests
- `CONFIG`: Configuration changes
- `STYLE`: Code style or formatting changes

### 5. Confidence Scoring

Each interaction receives a confidence score (0.0-1.0) based on:

- Complexity of the interaction (tool usage)
- Number of files changed
- Response length and detail
- Tool patterns detected

Scores help identify high-value interactions:

- 0.9-1.0: High-value, comprehensive solution with clear impact
- 0.7-0.9: Solid solution with good explanation and implementation
- 0.5-0.7: Adequate solution that addresses the core problem
- 0.3-0.5: Partial solution with some uncertainty
- 0.0-0.3: Exploratory discussion or uncertain solution

### 6. Bidirectional Linking

The most powerful feature is bidirectional linking between chat history and code chunks:

- Each chat entry that modifies code stores references to the affected code chunks
- Each code chunk stores references to the chat entries that modified it

This creates a navigable history of changes and discussions:

- See which discussions led to specific code changes
- Find all code affected by a particular discussion
- Trace the evolution of a feature or bug fix across multiple conversations

## Semantic Code Chunking

To improve bidirectional linking, the system uses semantic boundaries (functions, classes) when chunking code files. This results in more meaningful code chunks that align with logical code structures, making it easier to understand the connection between discussions and specific code components.

## Usage

### Manually Logging Chat Interactions

For manually logging chat interactions with enhanced context, use the `log-chat` command:

```bash
# Log a chat interaction with basic information
chroma-client log-chat --prompt-summary "User's question about API design" --response-summary "Explanation of REST principles"

# Log with full context including raw text and tool usage
chroma-client log-chat --prompt-summary "Debug request" --response-summary "Fixed null pointer" \
  --raw-prompt "Why is my function returning null?" --raw-response "You need to initialize the variable" \
  --tool-usage-file ./tool_usage.json --modification-type bugfix --confidence-score 0.85
```

The command supports various parameters to capture rich context:

- `--prompt-summary`: Brief summary of the user's question (required)
- `--response-summary`: Brief summary of the AI's response (required)
- `--raw-prompt`: Full text of the user's prompt
- `--raw-response`: Full text of the AI's response
- `--tool-usage-file`: JSON file containing tool usage information
- `--modification-type`: Type of change (refactor, bugfix, feature, etc.)
- `--confidence-score`: Confidence in the value of the interaction (0.0-1.0)
- `--involved-entities`: Comma-separated list of files, functions, or concepts discussed
- `--code-context`: JSON file containing before/after code snippets
- `--diff-summary`: Summary of code changes made

### Viewing Enhanced Context in Chat History

Enhanced context is automatically captured by the `auto_log_chat` rule and stored in the `chat_history_v1` collection. To view it:

```bash
# Query the chat history collection
chroma-client query --collection chat_history_v1 --query "your search term"
```

### Finding Related Chat Discussions for Code

To find chat discussions related to a specific file:

```bash
# Query the codebase collection with a file path
chroma-client query --collection codebase_v1 --query "file:path/to/file.py"

# Extract chat IDs from the related_chat_ids field
# Then query chat history using those IDs
```

### Finding Code Changes from Chat History

To find code chunks modified by a specific chat:

```bash
# First get the chat entry ID
chroma-client query --collection chat_history_v1 --query "your discussion topic"

# Then look at the related_code_chunks field in the metadata
# Use those chunk IDs to query the codebase collection
```

## Analyzing High-Value Interactions

The enhanced context system helps identify particularly valuable interactions:

```bash
# Find high-confidence interactions
chroma-client query --collection chat_history_v1 --where '{"confidence_score": {"$gt": 0.8}}'

# Find specific modification types
chroma-client query --collection chat_history_v1 --where '{"modification_type": "feature"}'
```

## Implementation Details

The enhanced context capture functionality is implemented in several modules:

1. `src/chroma_mcp_client/context.py`: Core context extraction and analysis functions
2. `src/chroma_mcp_client/auto_log_chat_impl.py`: Integration with the chat logging system
3. `src/chroma_mcp_client/indexing.py`: Semantic chunking and bidirectional linking support

For detailed API documentation, see [context_module.md](./context_module.md).

## Best Practices

1. **Use clear commit messages and PR descriptions**: These improve the quality of context extraction
2. **Make focused changes**: Smaller, more targeted edits result in better context capture
3. **Include rationales in chat**: Explaining your reasoning helps build a better knowledge base
4. **Review high-confidence interactions**: These are prime candidates for promoting to derived learnings
5. **Leverage bidirectional links**: When fixing bugs or adding features, check for related discussions first
