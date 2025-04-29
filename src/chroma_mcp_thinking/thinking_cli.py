#!/usr/bin/env python
"""
CLI interface for working with Chroma MCP Thinking Sessions.
Provides commands for recording thoughts, creating branches, and searching thoughts.
"""

import argparse
import json
import sys
import uuid
from typing import List, Optional, Dict, Any

from chroma_mcp_client import ChromaMcpClient
from chroma_mcp_thinking.thinking_session import ThinkingSession
from chroma_mcp_thinking.utils import (
    record_thought_chain,
    create_thought_branch,
    find_thoughts_across_sessions,
)


def setup_client() -> ChromaMcpClient:
    """Initialize and return a ChromaMcpClient."""
    try:
        return ChromaMcpClient()
    except Exception as e:
        print(f"Error connecting to Chroma MCP Server: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_record(args: argparse.Namespace) -> None:
    """Record a single thought or a thought chain."""
    client = setup_client()

    # Handle direct thought input vs file input
    thoughts = []
    if args.thought:
        thoughts = [args.thought]
    elif args.file:
        try:
            with open(args.file, "r") as f:
                # Split file by lines, filter empty lines
                thoughts = [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            print(f"Error reading thoughts from file: {e}", file=sys.stderr)
            sys.exit(1)

    if not thoughts:
        print("No thoughts provided. Use --thought or --file.", file=sys.stderr)
        sys.exit(1)

    # Parse metadata if provided
    metadata = {}
    if args.metadata:
        try:
            metadata = json.loads(args.metadata)
        except json.JSONDecodeError:
            print("Invalid metadata JSON format.", file=sys.stderr)
            sys.exit(1)

    # Record the thought(s)
    try:
        if len(thoughts) == 1 and args.thought_number:
            # Record a single thought with specific number
            session = ThinkingSession(client=client, session_id=args.session_id)
            result = session.record_thought(
                thought=thoughts[0],
                thought_number=args.thought_number,
                total_thoughts=args.total_thoughts or args.thought_number,
                next_thought_needed=args.next_thought_needed,
            )
            session_id = session.session_id
        else:
            # Record a chain of thoughts
            result = record_thought_chain(
                thoughts=thoughts,
                session_id=args.session_id,
                metadata=metadata if metadata else None,
                client=client,
            )
            session_id = result["session_id"]

        print(f"Recorded {len(thoughts)} thought(s) in session: {session_id}")
        if args.verbose:
            for i, thought in enumerate(thoughts, 1):
                print(f"  {i}. {thought[:50]}{'...' if len(thought) > 50 else ''}")

    except Exception as e:
        print(f"Error recording thought(s): {e}", file=sys.stderr)
        sys.exit(1)


def cmd_branch(args: argparse.Namespace) -> None:
    """Create a thought branch from an existing session."""
    client = setup_client()

    # Get branch thoughts
    branch_thoughts = []
    if args.thoughts:
        branch_thoughts = args.thoughts
    elif args.file:
        try:
            with open(args.file, "r") as f:
                branch_thoughts = [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            print(f"Error reading branch thoughts from file: {e}", file=sys.stderr)
            sys.exit(1)

    if not branch_thoughts:
        print("No branch thoughts provided. Use --thoughts or --file.", file=sys.stderr)
        sys.exit(1)

    # Generate branch ID if not provided
    branch_id = args.branch_id or str(uuid.uuid4())[:8]

    try:
        result = create_thought_branch(
            parent_session_id=args.parent_session_id,
            parent_thought_number=args.parent_thought_number,
            branch_thoughts=branch_thoughts,
            branch_id=branch_id,
            client=client,
        )

        print(
            f"Created branch '{branch_id}' from session {args.parent_session_id} thought #{args.parent_thought_number}"
        )
        print(f"Branch contains {len(branch_thoughts)} thought(s)")
        if args.verbose:
            for i, thought in enumerate(branch_thoughts, 1):
                print(f"  {i}. {thought[:50]}{'...' if len(thought) > 50 else ''}")

    except Exception as e:
        print(f"Error creating thought branch: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_search(args: argparse.Namespace) -> None:
    """Search for thoughts similar to a query."""
    client = setup_client()

    try:
        if args.sessions:
            # Search for similar sessions
            results = ThinkingSession.find_similar_sessions(
                query=args.query,
                n_results=args.limit,
                threshold=args.threshold,
                client=client,
            )

            print(f"Found {len(results)} similar sessions:")
            for i, session in enumerate(results, 1):
                session_id = session["metadata"]["session_id"]
                distance = session["distance"]
                first_thought = session["document"]
                print(f"{i}. Session: {session_id} (score: {distance:.4f})")
                if args.verbose:
                    print(f"   First thought: {first_thought[:100]}{'...' if len(first_thought) > 100 else ''}")
                    print()

        else:
            # Search for similar thoughts
            results = find_thoughts_across_sessions(
                query=args.query,
                n_results=args.limit,
                threshold=args.threshold,
                include_branches=not args.exclude_branches,
                session_id=args.session_id,  # Optional filtering to specific session
                client=client,
            )

            print(f"Found {len(results)} similar thoughts:")
            for i, thought in enumerate(results, 1):
                session_id = thought["metadata"]["session_id"]
                thought_num = thought["metadata"]["thought_number"]
                distance = thought["distance"]
                content = thought["document"]

                branch_info = ""
                if "branch_id" in thought["metadata"] and thought["metadata"]["branch_id"]:
                    branch_info = f" (branch: {thought['metadata']['branch_id']})"

                print(f"{i}. Session: {session_id}{branch_info}, Thought #{thought_num} (score: {distance:.4f})")
                print(f"   {content[:100]}{'...' if len(content) > 100 else ''}")
                print()

    except Exception as e:
        print(f"Error searching thoughts: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_summary(args: argparse.Namespace) -> None:
    """Get a summary of a thinking session."""
    client = setup_client()

    try:
        session = ThinkingSession(client=client, session_id=args.session_id)
        summary = session.get_session_summary(include_branches=not args.exclude_branches)

        # Determine total thoughts and branches
        thoughts = summary.get("thoughts", [])
        branches = set()
        for thought in thoughts:
            if "branch_id" in thought["metadata"] and thought["metadata"]["branch_id"]:
                branches.add(thought["metadata"]["branch_id"])

        # Print summary info
        print(f"Session: {args.session_id}")
        print(f"Total thoughts: {len(thoughts)}")
        if branches:
            print(f"Branches: {len(branches)} ({', '.join(branches)})")
        print()

        # Print thoughts
        for thought in thoughts:
            thought_num = thought["metadata"]["thought_number"]
            content = thought["document"]

            branch_info = ""
            if "branch_id" in thought["metadata"] and thought["metadata"]["branch_id"]:
                branch_info = f" [{thought['metadata']['branch_id']}]"

            print(f"Thought #{thought_num}{branch_info}:")
            print(f"{content}")
            print()

    except Exception as e:
        print(f"Error getting session summary: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Chroma MCP Thinking Session CLI",
        epilog="For more information, see the documentation at: "
        "https://github.com/your-org/chroma-mcp-server/docs/thinking-utils-guide.md",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Record command
    record_parser = subparsers.add_parser("record", help="Record a thought or thought chain")
    record_parser.add_argument("--thought", type=str, help="Single thought to record")
    record_parser.add_argument("--file", type=str, help="File containing thoughts (one per line)")
    record_parser.add_argument("--session-id", type=str, help="Session ID (creates new if not provided)")
    record_parser.add_argument("--metadata", type=str, help="JSON metadata string for the session/thoughts")
    record_parser.add_argument("--thought-number", type=int, help="Thought number (for single thought recording)")
    record_parser.add_argument("--total-thoughts", type=int, help="Total expected thoughts in session")
    record_parser.add_argument("--next-thought-needed", action="store_true", help="Indicate more thoughts coming")
    record_parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")

    # Branch command
    branch_parser = subparsers.add_parser("branch", help="Create a thought branch")
    branch_parser.add_argument("--parent-session-id", type=str, required=True, help="Parent session ID")
    branch_parser.add_argument("--parent-thought-number", type=int, required=True, help="Thought number to branch from")
    branch_parser.add_argument("--thoughts", type=str, nargs="+", help="Branch thoughts (space separated)")
    branch_parser.add_argument("--file", type=str, help="File containing branch thoughts (one per line)")
    branch_parser.add_argument("--branch-id", type=str, help="Custom branch ID (generates UUID if not provided)")
    branch_parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for thoughts or sessions")
    search_parser.add_argument("query", type=str, help="Search query")
    search_parser.add_argument("--sessions", action="store_true", help="Search for sessions instead of thoughts")
    search_parser.add_argument("--session-id", type=str, help="Filter to specific session ID")
    search_parser.add_argument("--limit", type=int, default=5, help="Maximum results to return")
    search_parser.add_argument("--threshold", type=float, default=-1, help="Similarity threshold (0-1, -1 for default)")
    search_parser.add_argument("--exclude-branches", action="store_true", help="Exclude thoughts in branches")
    search_parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")

    # Summary command
    summary_parser = subparsers.add_parser("summary", help="Get a summary of a thinking session")
    summary_parser.add_argument("session_id", type=str, help="Session ID")
    summary_parser.add_argument("--exclude-branches", action="store_true", help="Exclude thoughts in branches")

    # Parse arguments and execute appropriate command
    args = parser.parse_args()

    if args.command == "record":
        cmd_record(args)
    elif args.command == "branch":
        cmd_branch(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "summary":
        cmd_summary(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
