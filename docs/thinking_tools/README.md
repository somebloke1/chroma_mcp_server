# Chroma MCP Thinking Utilities

A powerful toolset for recording, organizing, and retrieving thought chains using semantic search capabilities powered by ChromaDB.

## Overview

Chroma MCP Thinking Utilities provides a structured way to:

- Record sequential chains of thoughts
- Create branching thought sequences
- Find semantically similar thoughts across sessions
- Manage and retrieve complete thinking sessions
- Integrate with enhanced context from chat history and code changes
- Leverage bidirectional linking for comprehensive context

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
- **Related Context**: Optional links to chat history entries and code chunks through bidirectional linking

### Branches

A **Branch** represents an alternative thought path that diverges from an existing thought:

- **Branch ID**: Identifier for the specific branch
- **Parent Thought**: The thought number this branch originated from
- **Branch Thoughts**: Sequence of thoughts in the branch

### Integration with Enhanced Context Capture

Thinking Utilities work seamlessly with the enhanced context capture system:

- **Bidirectional Linking**: Connect thoughts to related chat history entries and code chunks
- **Contextual Reasoning**: Leverage rich metadata from chat history (code diffs, tool sequences, confidence scores)
- **Cross-Collection Queries**: Retrieve relevant context from multiple collections (thoughts, chat history, code)

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

## Connecting Thoughts to Enhanced Context

### Linking to Chat History and Code Changes

Record thoughts with references to related conversations and code:

```python
from chroma_mcp_thinking.thinking_session import ThinkingSession

session = ThinkingSession()

# Record a thought that references a specific chat and code
session.record_thought(
    thought="Decision: We will implement the authentication flow using JWT tokens based on our discussion",
    thought_number=1,
    total_thoughts=3,
    metadata={
        "related_chat_ids": ["chat-uuid-1"],  # Reference to chat_history_v1 entry
        "related_code_chunks": ["src/auth/auth.py"],  # Reference to codebase_v1
        "confidence": 0.95,  # Confidence score (like in enhanced chat logging)
        "modification_type": "feature"  # Type of change being considered
    }
)
```

### Retrieving Comprehensive Context

Query across multiple collections for a complete understanding:

```python
from chroma_mcp_thinking.utils import find_thoughts_across_sessions
from chroma_mcp_client import ChromaMcpClient

client = ChromaMcpClient()

# Find thoughts about authentication
auth_thoughts = find_thoughts_across_sessions(
    query="JWT authentication implementation",
    n_results=3,
    client=client
)

# For each thought, retrieve related context
for thought in auth_thoughts:
    # Find related code
    if "related_code_chunks" in thought["metadata"]:
        for code_path in thought["metadata"]["related_code_chunks"]:
            code_chunks = client.query_documents(
                collection_name="codebase_v1",
                query_texts=[""],
                where={"file_path": code_path}
            )
            
    # Find related discussions
    if "related_chat_ids" in thought["metadata"]:
        for chat_id in thought["metadata"]["related_chat_ids"]:
            chat_entries = client.query_documents(
                collection_name="chat_history_v1",
                query_texts=[""],
                where={"chat_id": chat_id}
            )
            
            # Access rich context from chat history
            for entry in chat_entries:
                print(f"Code Diff: {entry['metadata'].get('diff_summary', 'N/A')}")
                print(f"Tool Sequence: {entry['metadata'].get('tool_sequence', 'N/A')}")
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
        "tags": ["brainstorming", "innovation"],
        "confidence": 0.85,  # Confidence in this reasoning chain
        "related_chat_ids": ["chat-uuid-2"]  # Link to relevant discussions
    }
)
```

## Example Application

A complete example showcasing various features is available at `examples/thinking_example.py`. It demonstrates:

1. Basic thought recording
2. Creating thought chains
3. Branching from existing thoughts
4. Searching for similar thoughts and sessions
5. Integrating with enhanced context from chat history and code changes

## Best Practices

1. **Atomic Thoughts**: Keep individual thoughts focused on a single idea or step
2. **Clear Branches**: Use descriptive branch IDs to distinguish alternative approaches
3. **Descriptive Queries**: When searching for thoughts, use semantically rich queries
4. **Consistent Metadata**: Establish a schema for metadata to ensure consistency
5. **Contextual Linking**: Reference related chat history entries and code chunks to create a comprehensive knowledge graph
6. **Confidence Annotation**: Mark thoughts with confidence scores to help prioritize reasoning paths
7. **Cross-Collection Context**: Combine search results from thoughts, chat history, and code for a complete picture

## Troubleshooting

### Cannot Connect to ChromaDB MCP Server

Ensure the MCP server is running and the connection details are correctly configured in the ChromaMcpClient.

### Invalid Session ID

If you encounter errors about invalid session IDs, ensure you're using the session ID returned by the server and not modifying it.

### Thoughts Not Found in Search Results

- Check if enough time has passed for indexing to complete
- Try refining your query to be more semantically aligned with content
- Verify the thoughts were successfully recorded by retrieving the session summary

### Missing Related Context

- Ensure bidirectional links are correctly set up in metadata
- Verify that referenced chat IDs and code paths exist in their respective collections
- Check that you're using the correct metadata field names for references

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
