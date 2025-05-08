"""
Module for interactively reviewing and promoting chat history entries to derived learnings.
"""

import logging
import sys
from typing import Optional, List, Dict, Any
from pathlib import Path

# Add project root for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Assuming connection and analysis functions are importable
from chroma_mcp_client.connection import (
    get_client_and_ef,
    get_chroma_client,
    get_embedding_function,
)
from chroma_mcp_client.analysis import fetch_recent_chat_entries, update_entry_status

# Import the refactored promotion function
from chroma_mcp_client.learnings import promote_to_learnings_collection

# Import the new query function
from chroma_mcp_client.query import query_codebase, DEFAULT_CODEBASE_COLLECTION

# Need promote_learning logic - maybe refactor it out of cli.py into a reusable function?
# For now, assume we might call the CLI command via subprocess or reimplement.
# Also need functions to query codebase_v1
# from chroma_mcp_client.query import query_collection # Example, might need more specific query

logger = logging.getLogger(__name__)


def display_code_results(results: Dict[str, Any]):
    """Helper function to display codebase query results."""
    if not results or not results.get("ids") or not results["ids"][0]:
        print("No relevant code snippets found.")
        return []

    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    print("\nSuggested Code References:")
    valid_choices = []
    for i, doc_id in enumerate(ids):
        metadata = metadatas[i] if metadatas else {}
        file_path = metadata.get("relative_file_path", "N/A")
        document = documents[i] if documents else ""
        distance = distances[i] if distances else float("inf")
        snippet = document.splitlines()[0] if document else "(No snippet)"  # Just first line
        print(f"  {i+1}. ID: {doc_id}")
        print(f"     File: {file_path}")
        print(f"     Dist: {distance:.4f}")
        print(f"     Snippet: {snippet[:100]}{'...' if len(snippet)>100 else ''}")
        valid_choices.append(doc_id)
    print("  N. None of the above / Not applicable")
    return valid_choices


def run_interactive_promotion(
    days_limit: int = 7,
    fetch_limit: int = 50,
    chat_collection_name: str = "chat_history_v1",
    learnings_collection_name: str = "derived_learnings_v1",
    # repo_path: Optional[Path] = None # Needed for diff/code-ref later
):
    """
    Runs the interactive workflow to review and promote chat entries.
    """
    logger.info("Starting interactive promotion workflow...")
    # repo_path = repo_path or Path.cwd()

    try:
        # Initialize client and EF (or get from context if integrated differently)
        # client, ef = initialize_chroma()
        # For standalone execution, let's initialize here:
        logger.debug("Initializing Chroma connection for interactive promoter...")
        client, ef = get_client_and_ef()
        if not client or not ef:
            logger.error("Failed to initialize Chroma connection.")
            return

        chat_collection = client.get_collection(name=chat_collection_name)
        # learnings_collection = client.get_collection(name=learnings_collection_name)

        # 1. Fetch entries with status 'analyzed'
        logger.info(
            f"Fetching entries with status 'analyzed' from '{chat_collection_name}' (last {days_limit} days)..."
        )
        analyzed_entries: List[Dict[str, Any]] = fetch_recent_chat_entries(
            collection=chat_collection, status_filter="analyzed", days_limit=days_limit, fetch_limit=fetch_limit
        )

        if not analyzed_entries:
            print("No entries with status 'analyzed' found within the specified time limit.")
            logger.info("No analyzed entries found.")
            return

        print(f"Found {len(analyzed_entries)} entries to review.")

        # 2. Loop through entries
        promoted_count = 0
        ignored_count = 0
        skipped_count = 0

        for i, entry in enumerate(analyzed_entries):
            entry_id = entry.get("id")
            metadata = entry.get("metadata", {})
            timestamp = metadata.get("timestamp", "N/A")
            prompt_summary = metadata.get("prompt_summary", "N/A")
            response_summary = metadata.get("response_summary", "N/A")
            involved_entities = metadata.get("involved_entities", "N/A")

            print("\n" + "-" * 50)
            print(f"Reviewing Entry {i+1}/{len(analyzed_entries)}")
            print(f"  ID: {entry_id}")
            print(f"  Timestamp: {timestamp}")
            print(f"  Prompt Summary: {prompt_summary}")
            print(f"  Response Summary: {response_summary}")
            print(f"  Involved Entities: {involved_entities}")
            # TODO: Show correlated diff if possible
            print("-" * 50)

            while True:
                action = input("Action (p=promote, i=ignore, s=skip, q=quit): ").lower()
                if action in ["p", "i", "s", "q"]:
                    break
                print("Invalid action. Please enter p, i, s, or q.")

            if action == "q":
                print("Quitting review process.")
                break
            elif action == "s":
                print(f"Skipping entry {entry_id}.")
                skipped_count += 1
                continue
            elif action == "i":
                print(f"Marking entry {entry_id} as ignored...")
                # Update status to 'ignored' (or similar)
                if update_entry_status(client, chat_collection_name, entry_id, new_status="ignored"):
                    print("Status updated to 'ignored'.")
                    ignored_count += 1
                else:
                    print(f"Warning: Failed to update status for {entry_id}.")
                continue  # Move to next entry
            elif action == "p":
                print(f"Starting promotion process for entry {entry_id}...")

                # --- Suggest Code Refs ---
                print("\nSearching codebase for relevant snippets...")
                query_text = f"{prompt_summary}\n{response_summary}"
                code_results = query_codebase(
                    client=client,
                    embedding_function=ef,
                    query_texts=[query_text],
                    collection_name=DEFAULT_CODEBASE_COLLECTION,  # Use default codebase collection
                    n_results=5,  # Show top 5 suggestions
                )
                suggested_ids = display_code_results(code_results)

                # --- Gather Promotion Details ---
                print("\nPlease provide the following details for the new learning entry:")

                default_description = f"Prompt: {prompt_summary}\nResponse: {response_summary}"
                description = input(f"Description (default: '{default_description}'): ") or default_description

                pattern = input("Pattern (e.g., code snippet, regex, textual key insight): ")

                # Get code_ref from user selection or manual input
                code_ref = ""
                while not code_ref:
                    code_ref_input = input(
                        f"Code Reference (select 1-{len(suggested_ids)}, type manually, or 'n' for N/A): "
                    ).lower()
                    if code_ref_input == "n":
                        code_ref = "N/A"
                        break
                    try:
                        choice_index = int(code_ref_input) - 1
                        if 0 <= choice_index < len(suggested_ids):
                            code_ref = suggested_ids[choice_index]
                            print(f"Selected: {code_ref}")
                            break
                        else:
                            print(
                                f"Invalid selection. Please enter a number between 1 and {len(suggested_ids)} or 'n'."
                            )
                    except ValueError:
                        # Assume manual input if not 'n' and not a valid number
                        code_ref = code_ref_input
                        print(f"Using manual input: {code_ref}")
                        break  # Allow any manual string for now

                tags = input("Tags (comma-separated, e.g., python,refactor,logging): ")

                confidence_str = ""
                while True:
                    confidence_str = input("Confidence (0.0 to 1.0): ")
                    try:
                        confidence = float(confidence_str)
                        if 0.0 <= confidence <= 1.0:
                            break
                        else:
                            print("Confidence must be between 0.0 and 1.0.")
                    except ValueError:
                        print("Invalid input. Please enter a number for confidence.")

                # Call the refactored promotion function
                # client and ef are already available in this scope
                new_learning_id = promote_to_learnings_collection(
                    client=client,
                    embedding_function=ef,
                    description=description,
                    pattern=pattern,
                    code_ref=code_ref,
                    tags=tags,
                    confidence=confidence,
                    learnings_collection_name=learnings_collection_name,  # Passed as arg to run_interactive_promotion
                    source_chat_id=entry_id,  # Link to the current chat entry
                    chat_history_collection_name=chat_collection_name,  # Passed as arg
                )

                if new_learning_id:
                    print(f"Successfully promoted entry {entry_id} to learning {new_learning_id}.")
                    promoted_count += 1
                    # Status of chat entry is updated by promote_to_learnings_collection
                else:
                    print(f"Failed to promote entry {entry_id}. Please check logs.")
                    # Optionally, mark as skipped or allow retry?
                    skipped_count += 1  # For now, count as skipped if promotion fails

        # 3. Summary
        print("\n" + "=" * 50)
        print("Review Complete")
        print(f"  Entries Reviewed: {len(analyzed_entries)}")
        print(f"  Promoted: {promoted_count}")
        print(f"  Ignored: {ignored_count}")
        print(f"  Skipped: {skipped_count}")
        print("=" * 50)

    except Exception as e:
        logger.error(f"Interactive promotion workflow failed: {e}", exc_info=True)
        print(f"An error occurred: {e}")
    finally:
        logger.info("Interactive promotion workflow finished.")


# Example placeholder for how it might be called (not used directly by CLI)
# if __name__ == '__main__':
#     run_interactive_promotion()
