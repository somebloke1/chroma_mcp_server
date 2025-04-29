# Chroma MCP Thinking Utilities

A powerful toolset for recording, organizing, and retrieving thought chains using semantic search capabilities powered by ChromaDB.

## Overview

Chroma MCP Thinking Utilities provides a structured way to:

- Record sequential chains of thoughts
- Create branching thought sequences
- Find semantically similar thoughts across sessions
- Manage and retrieve complete thinking sessions

## Installation

```bash
pip install chroma-mcp-server
```

Ensure a ChromaDB MCP server is running and accessible.

## Core Concepts

### Thinking Sessions

A **Thinking Session** represents a sequence of related thoughts with the following attributes:

- **Session ID**: Unique identifier for the session (auto-generated UUID or custom)
- **Thoughts**: Ordered sequence of thought entries
- **Branches**: Optional divergent thought sequences that branch from main thoughts

### Branches

A **Branch** represents an alternative thought path that diverges from an existing thought:

- **Branch ID**: Identifier for the specific branch
- **Parent Thought**: The thought number this branch originated from
- **Branch Thoughts**: Sequence of thoughts in the branch

## Basic Usage

### Creating a Session and Recording Thoughts

```python
from chroma_mcp_client import ChromaMcpClient
from chroma_mcp_thinking.thinking_session import ThinkingSession

# Create a session with automatic ID generation
client = ChromaMcpClient()
session = ThinkingSession(client=client)
session_id = session.session_id

# Record thoughts sequentially
session.record_thought(
    thought="This is my first thought",
    thought_number=1,
    total_thoughts=3,
    next_thought_needed=True
)

session.record_thought(
    thought="This is my second thought",
    thought_number=2, 
    total_thoughts=3,
    next_thought_needed=True
)

session.record_thought(
    thought="This is my final thought",
    thought_number=3,
    total_thoughts=3,
    next_thought_needed=False
)

# Get the session summary
summary = session.get_session_summary()
```

### Using Utility Functions

#### Recording a Thought Chain

```python
from chroma_mcp_thinking.utils import record_thought_chain

thoughts = [
    "First step in solving the problem",
    "Second step with intermediate results",
    "Final step with solution"
]

metadata = {
    "domain": "mathematics",
    "problem_type": "algebra"
}

result = record_thought_chain(
    thoughts=thoughts,
    metadata=metadata
)

session_id = result["session_id"]
```

#### Creating a Branch

```python
from chroma_mcp_thinking.utils import create_thought_branch

branch_thoughts = [
    "Alternative approach to the problem",
    "Different method yielding similar results",
    "Conclusion from alternative approach"
]

branch_result = create_thought_branch(
    parent_session_id=session_id,
    parent_thought_number=2,  # Branch from the second thought
    branch_thoughts=branch_thoughts,
    branch_id="alternative-method"
)
```

#### Finding Similar Thoughts

```python
from chroma_mcp_thinking.utils import find_thoughts_across_sessions

similar_thoughts = find_thoughts_across_sessions(
    query="Problem-solving approach for mathematics",
    n_results=5
)

for thought in similar_thoughts:
    print(f"Session: {thought['metadata']['session_id']}")
    print(f"Thought #{thought['metadata']['thought_number']}")
    print(f"Content: {thought['document']}")
    print(f"Similarity Score: {thought['distance']}")
```

## Advanced Usage

### Finding Similar Sessions

```python
from chroma_mcp_thinking.thinking_session import ThinkingSession

similar_sessions = ThinkingSession.find_similar_sessions(
    query="Problem-solving steps for algebraic equations",
    n_results=3
)

for session in similar_sessions:
    print(f"Session ID: {session['metadata']['session_id']}")
    print(f"Similarity Score: {session['distance']}")
```

### Adding Metadata During Thought Recording

Metadata can be added when using the `record_thought_chain` utility:

```python
from chroma_mcp_thinking.utils import record_thought_chain

result = record_thought_chain(
    thoughts=["Thought 1", "Thought 2", "Thought 3"],
    metadata={
        "author": "User123",
        "topic": "Research",
        "priority": "High",
        "tags": ["brainstorming", "innovation"]
    }
)
```

## Example Application

A complete example showcasing various features is available at `examples/thinking_example.py`. It demonstrates:

1. Basic thought recording
2. Creating thought chains
3. Branching from existing thoughts
4. Searching for similar thoughts and sessions

## Best Practices

1. **Atomic Thoughts**: Keep individual thoughts focused on a single idea or step
2. **Clear Branches**: Use descriptive branch IDs to distinguish alternative approaches
3. **Descriptive Queries**: When searching for thoughts, use semantically rich queries
4. **Consistent Metadata**: Establish a schema for metadata to ensure consistency

## Troubleshooting

### Cannot Connect to ChromaDB MCP Server

Ensure the MCP server is running and the connection details are correctly configured in the ChromaMcpClient.

### Invalid Session ID

If you encounter errors about invalid session IDs, ensure you're using the session ID returned by the server and not modifying it.

### Thoughts Not Found in Search Results

- Check if enough time has passed for indexing to complete
- Try refining your query to be more semantically aligned with content
- Verify the thoughts were successfully recorded by retrieving the session summary

## API Reference

### ThinkingSession Class

- `__init__(client=None, session_id=None)`: Initialize a new session
- `record_thought(thought, thought_number, total_thoughts, ...)`: Record a single thought
- `find_similar_thoughts(query, n_results=5, ...)`: Find similar thoughts within the session
- `get_session_summary(include_branches=True)`: Get all thoughts in the session
- `find_similar_sessions(query, n_results=5, ...)`: Find similar sessions (class method)

### Utility Functions

- `record_thought_chain(thoughts, session_id=None, metadata=None, ...)`: Record multiple thoughts at once
- `find_thoughts_across_sessions(query, n_results=10, ...)`: Find thoughts across all sessions
- `create_thought_branch(parent_session_id, parent_thought_number, branch_thoughts, ...)`: Create a branch
