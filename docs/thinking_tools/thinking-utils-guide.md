# Chroma MCP Thinking Utilities Guide

## Overview

The Chroma MCP Thinking Utilities provide a set of high-level functions for working with thinking sessions in Chroma MCP. These utilities make it easier to:

- Record complete thought chains in a single operation
- Create branching thought sequences from existing sessions
- Find similar thoughts across multiple sessions
- Manage and organize your thinking sessions
- Connect thinking sessions with chat history and code changes via bidirectional linking

## Installation

The thinking utilities are included in the Chroma MCP Server package. Make sure you have the package installed:

```bash
pip install chroma-mcp-server
```

## Core Concepts

### Thinking Sessions

A thinking session represents a sequence of related thoughts, typically forming a coherent line of reasoning or exploration. Each session has:

- A unique session ID
- A sequence of numbered thoughts
- Optional metadata such as timestamps and tags
- Optional links to code chunks and chat history entries

### Branches

Branches allow you to create alternative thought sequences that diverge from a specific point in a parent session. This is useful for exploring different approaches or solutions to a problem.

## Basic Usage

### ThinkingSession Class

The `ThinkingSession` class provides direct interaction with thinking sessions:

```python
from chroma_mcp_thinking.thinking_session import ThinkingSession
from mcp import ClientSession # Assuming ClientSession is available via mcp package

# Initialize the MCP client (adjust based on your connection)
mcp_client = ClientSession() 

# Create a new session
session = ThinkingSession(client=mcp_client)

# Record thoughts sequentially
session.record_thought(
    thought="This is my first thought.",
    thought_number=1,
    total_thoughts=3,
    next_thought_needed=True
)

# Get session summary
summary = session.get_session_summary()
```

### Utility Functions

#### Recording Complete Thought Chains

```python
from chroma_mcp_thinking.utils import record_thought_chain
from mcp import ClientSession # Assuming ClientSession is available via mcp package

# Initialize the MCP client
mcp_client = ClientSession()

thoughts = [
    "Initiate analysis of user query logs.",
    "Identify common error patterns.",
    "Hypothesize root causes for frequent failures.",
    "Plan remediation steps."
]

# Record multiple thoughts in one call
result = record_thought_chain(
    thoughts=thoughts,
    session_id="log-analysis-session-123", # Optional: Provide a specific session ID
    client=mcp_client # Pass the initialized client
)

# Get the session ID from the result
session_id = result["session_id"]
```

#### Creating Thought Branches

```python
from chroma_mcp_thinking.utils import create_thought_branch
from mcp import ClientSession # Assuming ClientSession is available via mcp package

# Initialize the MCP client
mcp_client = ClientSession()

parent_session = "log-analysis-session-123"
parent_thought = 3 # Branch off after the third thought
branch_id = "remediation-options"

branch_thoughts = [
    "Implement a new error handling mechanism",
    "Update the database connection string",
    "Reconfigure the application to use a different database"
]

# Create a branch from an existing thought
branch_result = create_thought_branch(
    parent_session_id=parent_session,
    parent_thought_number=parent_thought,
    branch_thoughts=branch_thoughts,
    branch_id=branch_id,
    client=mcp_client # Pass the initialized client
)
```

#### Finding Similar Thoughts

```python
from chroma_mcp_thinking.utils import find_thoughts_across_sessions
from mcp import ClientSession # Assuming ClientSession is available via mcp package

# Initialize the MCP client
mcp_client = ClientSession()

query = "solutions for database connection errors"

# Search for thoughts similar to a query
similar_thoughts = find_thoughts_across_sessions(
    query=query,
    n_results=5,
    client=mcp_client # Pass the initialized client
)

# Process results
for thought in similar_thoughts:
    print(thought["document"])  # The thought text
    print(thought["metadata"]["session_id"])  # Session ID
    print(thought["distance"])  # Similarity score (lower is better)
```

## Command-Line Interface (CLI)

The package includes a command-line interface for working with thinking sessions without writing Python code:

```bash
# To use the CLI after installing the package:
python -m chroma_mcp_thinking.thinking_cli <command> [options]
```

### Recording Thoughts

```bash
# Record a single thought
python -m chroma_mcp_thinking.thinking_cli record --thought "This is a new thought" --thought-number 1 --total-thoughts 3

# Record a thought chain from a file (one thought per line)
python -m chroma_mcp_thinking.thinking_cli record --file thoughts.txt

# Continue an existing session
python -m chroma_mcp_thinking.thinking_cli record --thought "Next thought in sequence" --session-id abc123 --thought-number 2
```

### Creating Branches

```bash
# Create a branch from an existing session
python -m chroma_mcp_thinking.thinking_cli branch --parent-session-id abc123 --parent-thought-number 2 \
  --thoughts "First branch thought" "Second branch thought" "Third branch thought"

# Create a branch with thoughts from a file
python -m chroma_mcp_thinking.thinking_cli branch --parent-session-id abc123 --parent-thought-number 2 \
  --file branch_thoughts.txt --branch-id "alternative-approach"
```

### Searching Thoughts

```bash
# Search for thoughts similar to a query
python -m chroma_mcp_thinking.thinking_cli search "problem solving methodology"

# Search with filters and limits
python -m chroma_mcp_thinking.thinking_cli search "system architecture" --limit 10 --threshold 0.75 --session-id abc123

# Search for similar sessions instead of thoughts
python -m chroma_mcp_thinking.thinking_cli search "machine learning techniques" --sessions
```

### Getting Session Summaries

```bash
# View all thoughts in a session
python -m chroma_mcp_thinking.thinking_cli summary abc123

# Exclude branches from the summary
python -m chroma_mcp_thinking.thinking_cli summary abc123 --exclude-branches
```

## Integration with Enhanced Context Capture

The thinking utilities can leverage the rich contextual information captured by the enhanced context capture system:

### Linking Thoughts to Chat History and Code Changes

When recording thoughts, you can reference related chat history entries and code chunks:

```python
from chroma_mcp_thinking.thinking_session import ThinkingSession
from mcp import ClientSession

# Initialize the MCP client
mcp_client = ClientSession()
session = ThinkingSession(client=mcp_client)

# Record a thought that references a chat history entry and code chunk
session.record_thought(
    thought="We should refactor the authentication module following the pattern discussed in our recent chat",
    thought_number=1,
    total_thoughts=3,
    metadata={
        "related_chat_ids": ["chat-uuid-1", "chat-uuid-2"],  # References to chat_history_v1 entries
        "related_code_chunks": ["src/auth/auth.py#15-42"]     # References to codebase_v1 chunks
    }
)
```

### Utilizing Enhanced Context in Reasoning

You can leverage the rich context metadata (code diffs, tool sequences, confidence scores) when analyzing related discussions:

```python
from chroma_mcp_thinking.utils import find_thoughts_across_sessions
from chroma_mcp_client import ChromaMcpClient

client = ChromaMcpClient()

# Find thoughts related to authentication
auth_thoughts = find_thoughts_across_sessions(
    query="authentication module refactoring",
    n_results=3,
    client=client
)

# For each thought, retrieve related chat history entries with rich context
for thought in auth_thoughts:
    if "related_chat_ids" in thought["metadata"]:
        for chat_id in thought["metadata"]["related_chat_ids"]:
            # Query chat_history_v1 for the related chat entry
            chat_entries = client.query_documents(
                collection_name="chat_history_v1",
                query_texts=[""],  # Empty query to match by ID
                where={"chat_id": chat_id}
            )
            
            # Access rich context from the chat entry
            for entry in chat_entries:
                print(f"Related Chat: {entry['metadata']['prompt_summary']}")
                print(f"Confidence Score: {entry['metadata']['confidence_score']}")
                print(f"Code Changes: {entry['metadata']['diff_summary']}")
                print(f"Tool Sequence: {entry['metadata']['tool_sequence']}")
```

## Advanced Usage

### Finding Similar Sessions

```python
from chroma_mcp_thinking.thinking_session import ThinkingSession
from mcp import ClientSession # Assuming ClientSession is available via mcp package

# Initialize the MCP client
mcp_client = ClientSession()

similar_sessions = ThinkingSession.find_similar_sessions(
    query="Refactoring authentication flow",
    n_results=3,
    client=mcp_client # Pass the initialized client
)
```

### Customizing Metadata

When recording thoughts or creating sessions, you can include additional metadata:

```python
# Assuming 'session' is an initialized ThinkingSession instance
# with an associated client
session.record_thought(
    thought="Final decision: Use JWT for authentication.",
    thought_number=5,
    total_thoughts=5,
    metadata={
        "decision": "final", 
        "component": "auth",
        "confidence": 0.95,  # Confidence score like in enhanced chat logging
        "modification_type": "refactor"  # Similar to enhanced chat logging
    }
)
```

### Cross-Collection Context Integration

For comprehensive context retrieval, you can query across multiple collections:

```python
# First search for relevant thoughts
similar_thoughts = find_thoughts_across_sessions(
    query="authentication module implementation",
    n_results=3,
    client=client
)

# Then search for relevant code chunks
code_chunks = client.query_documents(
    collection_name="codebase_v1",
    query_texts=["authentication module implementation"],
    n_results=3
)

# And relevant chat history entries
chat_entries = client.query_documents(
    collection_name="chat_history_v1",
    query_texts=["authentication module implementation"],
    n_results=3
)

# Combine results for a comprehensive view
for thought in similar_thoughts:
    print(f"Thought: {thought['document']}")
    
for chunk in code_chunks:
    print(f"Code: {chunk['document']}")
    
for entry in chat_entries:
    print(f"Chat: {entry['document']}")
```

## Example Application

See the complete example in `examples/thinking_example.py` that demonstrates:

1. Creating and using a ThinkingSession directly
2. Recording a complete thought chain in one operation
3. Creating a branch from an existing session
4. Finding similar thoughts across all sessions
5. Finding similar sessions

## Best Practices

1. **Atomic Thoughts**: Keep individual thoughts focused on a single idea or step in your reasoning.
2. **Clear Branches**: When creating branches, make sure the first thought clearly indicates how it diverges from the parent.
3. **Descriptive Queries**: When searching for similar thoughts, use specific and descriptive queries to get better results.
4. **Consistent Metadata**: Establish conventions for metadata fields like tags and project names.
5. **Rich Context Integration**: Utilize bidirectional linking to connect thoughts with related chat history entries and code chunks for more comprehensive context.
6. **Confidence Scoring**: Apply confidence scores to thoughts similar to enhanced chat logging to help identify high-value reasoning.
7. **Cross-Collection Queries**: When solving complex problems, leverage context from `sequential_thoughts_v1`, `chat_history_v1`, and `codebase_v1` collections.

## Troubleshooting

If you encounter issues:

- Ensure your ChromaMcpClient is properly configured and connected
- Check that your session IDs are valid and exist in the system
- Verify that thought numbers are sequential and start from 1
- For branches, ensure the parent thought exists in the parent session
