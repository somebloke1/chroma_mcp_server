#!/usr/bin/env python
"""
Example demonstrating usage of Chroma MCP Thinking Utilities.

This script shows how to:
1. Create a thinking session
2. Record thoughts sequentially
3. Create a thought branch
4. Search for similar thoughts
5. Get session summaries

To run this example, make sure Chroma MCP Server is running,
and the chroma-mcp-server package is installed.
"""

import time
import uuid
import sys
import os

from chroma_mcp_client import ChromaMcpClient
from chroma_mcp_thinking.thinking_session import ThinkingSession
from chroma_mcp_thinking.utils import (
    record_thought_chain,
    create_thought_branch,
    find_thoughts_across_sessions,
)


def demonstrate_basic_recording():
    """Demonstrate basic thought recording with ThinkingSession."""
    print("\n=== Basic Recording ===")
    client = ChromaMcpClient()

    # Create a session with automatic ID generation
    session = ThinkingSession(client=client)
    session_id = session.session_id
    print(f"Created session with ID: {session_id}")

    # Record three thoughts sequentially
    for i in range(1, 4):
        thought = f"This is thought number {i} in the basic recording demo."
        session.record_thought(
            thought=thought,
            thought_number=i,
            total_thoughts=3,
            next_thought_needed=(i < 3),  # True for the first two thoughts
        )
        print(f"Recorded thought #{i}")
        time.sleep(0.5)  # Small pause for demonstration purposes

    # Get and display the recorded thoughts
    summary = session.get_session_summary()
    print("\nSession summary:")
    for thought in summary.get("thoughts", []):
        print(f"  Thought #{thought['metadata']['thought_number']}: {thought['document']}")

    return session_id


def demonstrate_thought_chain():
    """Demonstrate recording a chain of thoughts using the utility function."""
    print("\n=== Thought Chain Recording ===")
    client = ChromaMcpClient()

    # Prepare a list of thoughts
    thoughts = [
        "I need to solve this mathematical problem step by step.",
        "First, I'll identify the variables and constants in the equation.",
        "Then, I'll apply the appropriate formula to solve for the unknown.",
        "Finally, I'll verify my solution by substituting back into the original equation.",
    ]

    # Metadata for the session
    metadata = {"domain": "mathematics", "problem_type": "algebra", "difficulty": "medium"}

    # Record the chain and get back the session_id
    result = record_thought_chain(thoughts=thoughts, metadata=metadata, client=client)

    session_id = result["session_id"]
    print(f"Recorded thought chain with {len(thoughts)} thoughts in session: {session_id}")
    print(f"Metadata: {metadata}")

    return session_id


def demonstrate_branching(parent_session_id):
    """Demonstrate creating a thought branch from an existing session."""
    print("\n=== Thought Branching ===")
    client = ChromaMcpClient()

    # Branch thoughts representing an alternative approach
    branch_thoughts = [
        "Let me try a different approach to solve this problem.",
        "Instead of using algebraic methods, I'll use a geometric interpretation.",
        "This provides a more intuitive understanding of the solution.",
    ]

    # Create a custom branch ID
    branch_id = f"branch-{uuid.uuid4().hex[:6]}"

    # Create the branch (from thought #2 of the parent session)
    result = create_thought_branch(
        parent_session_id=parent_session_id,
        parent_thought_number=2,  # Branch from the second thought
        branch_thoughts=branch_thoughts,
        branch_id=branch_id,
        client=client,
    )

    print(f"Created branch '{branch_id}' from session {parent_session_id}")
    print(f"The branch contains {len(branch_thoughts)} thoughts")

    # Get the updated session with branches
    session = ThinkingSession(client=client, session_id=parent_session_id)
    summary = session.get_session_summary(include_branches=True)

    print("\nUpdated session with branches:")
    for thought in summary.get("thoughts", []):
        branch_info = ""
        if "branch_id" in thought["metadata"] and thought["metadata"]["branch_id"]:
            branch_info = f" [Branch: {thought['metadata']['branch_id']}]"

        print(f"  Thought #{thought['metadata']['thought_number']}{branch_info}: {thought['document'][:60]}...")

    return branch_id


def demonstrate_searching():
    """Demonstrate searching for thoughts and sessions."""
    print("\n=== Searching for Thoughts and Sessions ===")
    client = ChromaMcpClient()

    # Search for thoughts about mathematical problem-solving
    search_query = "mathematical problem solving approach"

    # Search for thoughts
    print(f"\nSearching for thoughts similar to: '{search_query}'")
    thought_results = find_thoughts_across_sessions(query=search_query, n_results=3, client=client)

    print(f"Found {len(thought_results)} similar thoughts:")
    for i, result in enumerate(thought_results, 1):
        session_id = result["metadata"]["session_id"]
        thought_num = result["metadata"]["thought_number"]
        branch_info = ""
        if "branch_id" in result["metadata"] and result["metadata"]["branch_id"]:
            branch_info = f" (branch: {result['metadata']['branch_id']})"

        print(f"{i}. Session: {session_id}{branch_info}, Thought #{thought_num}")
        print(f"   Score: {result['distance']:.4f}")
        print(f"   Content: {result['document'][:100]}...")
        print()

    # Search for sessions
    print(f"Searching for sessions similar to: '{search_query}'")
    session_results = ThinkingSession.find_similar_sessions(query=search_query, n_results=2, client=client)

    print(f"Found {len(session_results)} similar sessions:")
    for i, result in enumerate(session_results, 1):
        session_id = result["metadata"]["session_id"]
        print(f"{i}. Session: {session_id}")
        print(f"   Score: {result['distance']:.4f}")
        print()


def main():
    """Run the complete thinking utilities demonstration."""
    print("=== Chroma MCP Thinking Utilities Demonstration ===")

    # Demonstrate basic recording with ThinkingSession
    basic_session_id = demonstrate_basic_recording()

    # Demonstrate thought chain recording
    chain_session_id = demonstrate_thought_chain()

    # Demonstrate branching (using the thought chain session)
    demonstrate_branching(chain_session_id)

    # Allow time for indexing to complete
    print("\nWaiting for indexing to complete...")
    time.sleep(1)

    # Demonstrate searching
    demonstrate_searching()

    print("\n=== Demonstration Complete ===")
    print(f"Created sessions: {basic_session_id}, {chain_session_id}")
    print("You can further explore these sessions using the API or CLI tools.")


if __name__ == "__main__":
    main()
