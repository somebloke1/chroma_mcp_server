#!/usr/bin/env python
"""
Simple example demonstrating basic usage of Chroma MCP Thinking Utilities.

This example shows:
1. Creating a thinking session
2. Recording individual thoughts
3. Recording a thought chain using a utility function
4. Finding similar thoughts by semantic search

Prerequisites:
- Chroma MCP Server must be running
- chroma-mcp-server package must be installed
"""

import sys
import os

from chroma_mcp_client import ChromaMcpClient
from chroma_mcp_thinking.thinking_session import ThinkingSession
from chroma_mcp_thinking.utils import record_thought_chain, find_thoughts_across_sessions

import time


def example_individual_thoughts():
    """Demonstrate recording individual thoughts manually."""
    print("\n1. Recording individual thoughts")

    # Create a client to connect to the MCP server
    client = ChromaMcpClient()

    # Create a new thinking session
    session = ThinkingSession(client=client)
    print(f"Created session with ID: {session.session_id}")

    # Record three thoughts one by one
    session.record_thought(
        thought="I need to solve this problem step by step.",
        thought_number=1,
        total_thoughts=3,
        next_thought_needed=True,
    )
    print("Recorded thought #1")

    session.record_thought(
        thought="First, I'll identify the key variables.", thought_number=2, total_thoughts=3, next_thought_needed=True
    )
    print("Recorded thought #2")

    session.record_thought(
        thought="Finally, I'll apply the formula to find the solution.",
        thought_number=3,
        total_thoughts=3,
        next_thought_needed=False,
    )
    print("Recorded thought #3")

    # Retrieve the session summary to see all thoughts
    summary = session.get_session_summary()

    print("\nThoughts recorded in the session:")
    for thought in summary.get("thoughts", []):
        print(f"  Thought #{thought['metadata']['thought_number']}: {thought['document']}")

    return session.session_id


def example_thought_chain():
    """Demonstrate recording a complete thought chain at once."""
    print("\n2. Recording a thought chain")

    # Prepare a list of thoughts
    thoughts = [
        "Let's approach this problem differently.",
        "We can break it down into smaller parts.",
        "By solving each part, we arrive at the complete solution.",
        "This method is more efficient for complex problems.",
    ]

    # Optional metadata for the session
    metadata = {"subject": "problem-solving", "technique": "decomposition", "difficulty": "medium"}

    # Record the entire chain at once using the utility function
    result = record_thought_chain(thoughts=thoughts, metadata=metadata)

    print(f"Recorded a thought chain with {len(thoughts)} thoughts")
    print(f"Session ID: {result['session_id']}")
    print(f"Metadata: {metadata}")

    return result["session_id"]


def example_finding_similar_thoughts(wait_time=1):
    """Demonstrate finding similar thoughts using semantic search."""
    print("\n3. Finding similar thoughts")

    # Wait a moment for indexing to complete
    print(f"Waiting {wait_time} seconds for indexing to complete...")
    time.sleep(wait_time)

    # Search for thoughts about problem-solving
    query = "efficient problem-solving methods"
    print(f"Searching for thoughts similar to: '{query}'")

    # Use the utility function to search across all sessions
    similar_thoughts = find_thoughts_across_sessions(query=query, n_results=3)  # Return top 3 matches

    # Display the results
    print(f"\nFound {len(similar_thoughts)} similar thoughts:")
    for i, thought in enumerate(similar_thoughts, 1):
        session_id = thought["metadata"]["session_id"]
        thought_num = thought["metadata"]["thought_number"]
        similarity = thought["distance"]  # Lower distance means more similar

        print(f"\nMatch #{i}:")
        print(f"  Session: {session_id}")
        print(f"  Thought #{thought_num}")
        print(f"  Similarity score: {similarity:.4f}")
        print(f"  Content: \"{thought['document']}\"")


def main():
    """Run the complete example demonstrating thinking utilities."""
    print("=== Chroma MCP Thinking Utilities: Simple Example ===")

    # Example 1: Recording individual thoughts
    example_individual_thoughts()

    # Example 2: Recording a thought chain
    example_thought_chain()

    # Example 3: Finding similar thoughts (wait for indexing)
    example_finding_similar_thoughts(wait_time=1)

    print("\n=== Example Complete ===")
    print("These examples demonstrate basic functionality of the Thinking Utilities.")
    print("For more advanced features, see the comprehensive example at examples/thinking_example.py")


if __name__ == "__main__":
    main()
