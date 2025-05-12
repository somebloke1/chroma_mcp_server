# Context Module API Documentation

The `context.py` module provides functionality for extracting rich contextual information from code changes, tool usage patterns, and chat interactions. It supports the enhanced context capture features of the auto_log_chat rule and other components.

## Overview

This module enables AI assistants to capture, analyze, and store valuable contextual information about their interactions with users, particularly focusing on code changes and the development process. This contextual information enhances the usefulness of chat history for future reference and learning extraction.

## Key Components

### Enumerations

#### `ModificationType`

An enumeration of standardized modification types for chat interactions.

```python
class ModificationType(Enum):
    REFACTOR = "refactor"      # Improving existing functionality without changing behavior
    BUGFIX = "bugfix"          # Correcting errors or unexpected behavior
    FEATURE = "feature"        # Adding new capabilities or functionality 
    DOCUMENTATION = "documentation"  # Improving comments or documentation
    OPTIMIZATION = "optimization"    # Performance improvements
    TEST = "test"              # Adding or updating tests
    CONFIG = "config"          # Configuration changes
    STYLE = "style"            # Code style or formatting changes
    UNKNOWN = "unknown"        # Default when no clear indicators
```

### Classes

#### `ToolPatterns`

Identifies common patterns in tool usage sequences.

```python
class ToolPatterns:
    MULTIPLE_READS = "multiple_reads"  # Multiple read_file operations before an edit
    SEARCH_THEN_EDIT = "search_then_edit"  # Search operations followed by edits
    ITERATIVE_REFINEMENT = "iterative_refinement"  # Edit followed by reapply
    EXPLORATION = "exploration"  # Multiple search or read operations
    CODE_EXECUTION = "code_execution"  # Running terminal commands to test code
    
    @classmethod
    def identify_patterns(cls, tool_sequence: str) -> List[str]:
        """Identify common patterns in a tool sequence."""
        # Implementation details...
```

### Functions

#### Code Context Extraction

```python
def extract_code_snippets(before_content: str, after_content: str, 
                           max_context_lines: int = 50) -> str:
    """
    Extract relevant code snippets showing changes between before and after content.
    
    Args:
        before_content: Original content before changes
        after_content: Modified content after changes
        max_context_lines: Maximum number of lines to include in snippets
    
    Returns:
        Formatted string with before/after code snippets
    """
```

#### Diff Generation

```python
def generate_diff_summary(before_content: str, after_content: str, 
                          file_path: str) -> str:
    """
    Generate a concise summary of changes between two contents.
    
    Args:
        before_content: Original content before changes
        after_content: Modified content after changes
        file_path: Path to the file being modified
    
    Returns:
        Human-readable summary of the key changes
    """
```

#### Tool Sequence Tracking

```python
def track_tool_sequence(tools_used: List[str]) -> str:
    """
    Convert a list of used tools into a standardized sequence string.
    
    Args:
        tools_used: List of tool names in order of use
        
    Returns:
        Standardized tool sequence string (e.g., "read_file→edit_file→run_terminal_cmd")
    """
```

#### Confidence Scoring

```python
def calculate_confidence_score(
    tool_sequence: str,
    file_changes: List[Dict[str, Any]],
    response_length: int
) -> float:
    """
    Calculate a confidence score (0.0-1.0) for the value of an interaction.
    
    Args:
        tool_sequence: The sequence of tools used
        file_changes: List of files modified with change information
        response_length: Length of AI response in characters
        
    Returns:
        Confidence score between 0.0 and 1.0
    """
```

#### Modification Type Detection

```python
def determine_modification_type(
    file_changes: List[Dict[str, Any]],
    prompt_summary: str,
    response_summary: str
) -> ModificationType:
    """
    Determine the type of modification based on changes and summaries.
    
    Args:
        file_changes: List of files modified with change information
        prompt_summary: Summary of the user's prompt
        response_summary: Summary of the AI's response
        
    Returns:
        ModificationType enum value
    """
```

#### Bidirectional Link Management

```python
def manage_bidirectional_links(
    chat_id: str,
    file_changes: List[Dict[str, str]],
    chroma_client
) -> Dict[str, List[str]]:
    """
    Manage bidirectional links between chat history and code chunks.
    
    Args:
        chat_id: ID of the current chat history entry
        file_changes: List of files modified
        chroma_client: ChromaDB client instance for interacting with collections
        
    Returns:
        Dictionary mapping file paths to their chunk IDs in codebase_v1
    """
```

## Usage Examples

### Extracting Code Snippets

```python
# Example: Get formatted code snippets showing changes
before_code = """def hello():
    print("Hello, world!")
"""

after_code = """def hello():
    print("Hello, universe!")
"""

snippets = extract_code_snippets(before_code, after_code)
print(snippets)
# Output:
# CHANGED FILE:
# ```diff
# @@ -1,2 +1,2 @@
#  def hello():
# -    print("Hello, world!")
# +    print("Hello, universe!")
# ```
```

### Generating a Diff Summary

```python
# Example: Generate human-readable summary of changes
summary = generate_diff_summary(before_code, after_code, "greeting.py")
print(summary)
# Output:
# Modified greeting.py: 1 lines added, 1 lines removed
```

### Tracking Tool Sequences

```python
# Example: Create standardized tool sequence
tools = ["read_file", "read_file", "grep_search", "edit_file"]
sequence = track_tool_sequence(tools)
print(sequence)
# Output:
# read_file→grep_search→edit_file
```

### Calculating Confidence Score

```python
# Example: Calculate confidence score for an interaction
score = calculate_confidence_score(
    "read_file→edit_file→run_terminal_cmd",
    [{"file_path": "auth.py"}],
    500
)
print(f"Confidence score: {score:.2f}")
# Output:
# Confidence score: 0.85
```

### Determining Modification Type

```python
# Example: Determine type of modification
mod_type = determine_modification_type(
    [{"file_path": "auth.py"}],
    "Fix login error",
    "Fixed the authentication bug by correcting token validation"
)
print(f"Modification type: {mod_type.value}")
# Output:
# Modification type: bugfix
```

## Integration with auto_log_chat

The context module is designed to be used with the `auto_log_chat` rule to enhance the contextual information captured during AI interactions. The integration happens in the `src/chroma_mcp/tools/auto_log_chat_impl.py` file.

## Testing

The module is thoroughly tested with unit tests in `tests/utils/test_context.py` and integration tests in `tests/tools/test_auto_log_chat_integration.py`.
