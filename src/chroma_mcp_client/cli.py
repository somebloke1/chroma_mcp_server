"""
Command Line Interface for the Direct ChromaDB Client.

Provides commands for indexing, querying, and managing the ChromaDB instance
used for automation tasks like RAG context building.
"""

import argparse
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Removed sys.path manipulation logic
# Imports should work directly when the package is installed
from .connection import get_client_and_ef
from .indexing import index_file, index_git_files
from .analysis import analyze_chat_history  # Import the new function

# Basic logging configuration (can be enhanced)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# --- Constants ---
DEFAULT_COLLECTION_NAME = "codebase_v1"
DEFAULT_QUERY_RESULTS = 5

# Load environment variables from .env file
load_dotenv()

# Determine default log level from environment or fallback
default_log_level_env = os.getenv("LOG_LEVEL", "INFO").upper()
if default_log_level_env not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    default_log_level_env = "INFO"  # Fallback if invalid value in env


def main():
    """Main entry point for the chroma-client CLI."""
    parser = argparse.ArgumentParser(
        description="ChromaDB Client CLI for indexing and querying.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--log-level",
        default=default_log_level_env,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level. Overrides LOG_LEVEL env var.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # --- Index Subparser ---
    index_parser = subparsers.add_parser(
        "index",
        help="Index specific files or all git-tracked files into ChromaDB.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    index_parser.add_argument(
        "paths",
        nargs="*",
        help="Optional specific file or directory paths to index.",
        type=Path,
        default=[],
    )
    index_parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(os.getcwd()),
        help="Repository root path (used for determining relative paths for IDs).",
    )
    index_parser.add_argument(
        "--all", action="store_true", help="Index all files currently tracked by git in the repo."
    )
    index_parser.add_argument(
        "--collection-name",
        default=DEFAULT_COLLECTION_NAME,
        help="Name of the ChromaDB collection to use.",
    )

    # --- Count Subparser ---
    count_parser = subparsers.add_parser("count", help="Count documents in a ChromaDB collection.")
    count_parser.add_argument(
        "--collection-name",
        default=DEFAULT_COLLECTION_NAME,
        help="Name of the ChromaDB collection to count.",
    )

    # --- Query Subparser ---
    query_parser = subparsers.add_parser("query", help="Query a ChromaDB collection.")
    query_parser.add_argument("query_text", help="The text to query for.")
    query_parser.add_argument(
        "--collection-name",
        default=DEFAULT_COLLECTION_NAME,
        help="Name of the ChromaDB collection to query.",
    )
    query_parser.add_argument(
        "-n",
        "--n-results",
        type=int,
        default=DEFAULT_QUERY_RESULTS,
        help="Number of results to return.",
    )

    # --- Analyze Chat History Subparser ---
    analyze_parser = subparsers.add_parser(
        "analyze-chat-history",
        help="Analyze recent chat history to correlate with Git changes.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    analyze_parser.add_argument(
        "--collection-name",
        default="chat_history_v1",
        help="Name of the ChromaDB chat history collection.",
    )
    analyze_parser.add_argument(
        "--repo-path",
        type=Path,
        default=Path(os.getcwd()),
        help="Path to the Git repository to analyze.",
    )
    analyze_parser.add_argument(
        "--status-filter",
        default="captured",
        help="Metadata status value to filter entries for analysis.",
    )
    analyze_parser.add_argument(
        "--new-status",
        default="analyzed",
        help="Metadata status value to set after analysis.",
    )
    analyze_parser.add_argument(
        "--days-limit",
        type=int,
        default=7,
        help="How many days back to look for entries to analyze.",
    )

    # --- Update Collection EF Subparser ---
    update_ef_parser = subparsers.add_parser(
        "update-collection-ef",
        help="Update the embedding function name stored in a collection's metadata.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    update_ef_parser.add_argument(
        "--collection-name",
        required=True,
        help="Name of the ChromaDB collection to update.",
    )
    update_ef_parser.add_argument(
        "--ef-name",
        required=True,
        help="The new embedding function name string to store (e.g., 'sentence_transformer').",
    )

    args = parser.parse_args()

    # Set logging level based on the final value in args (priority: CLI arg > env var > INFO)
    log_level_name = args.log_level  # Already incorporates the default logic
    log_level = getattr(logging, log_level_name, logging.INFO)
    logging.getLogger().setLevel(log_level)  # Set root logger level
    # Use log_level_name in the message for clarity
    logger.info(f"Log level set to {log_level_name}")

    # Initialize client/EF early to catch connection errors
    try:
        logger.info("Initializing ChromaDB connection...")
        client, ef = get_client_and_ef()  # Loads config from .env via connection module
        logger.info(
            f"ChromaDB connection successful (Client type: {client.__class__.__name__}, EF: {ef.__class__.__name__ if ef else 'Default'})"
        )
    except Exception as e:
        logger.critical(f"Failed to initialize ChromaDB client: {e}", exc_info=True)
        sys.exit(1)

    # --- Command Handling ---
    if args.command == "index":
        collection_name = args.collection_name
        logger.info(f"Executing 'index' command for collection '{collection_name}'...")
        # Resolve repo root path - specific to index command
        repo_root_path = args.repo_root.resolve()
        # REMOVED: Premature get_or_create_collection call
        # collection = client.get_or_create_collection(
        #     name=collection_name,
        #     embedding_function=ef,  # Pass embedding function here
        #     # Add metadata if needed: metadata=get_collection_settings(...)
        # )

        if args.all:
            logger.info(f"Indexing all tracked git files in {repo_root_path}...")
            # Pass the collection_name string
            count = index_git_files(repo_root_path, collection_name)
            logger.info(f"Git index command finished. Indexed {count} files.")
        elif args.paths:
            logger.info(f"Processing {len(args.paths)} specified file/directory paths...")
            indexed_count = 0
            for path_item in args.paths:
                if path_item.is_file():
                    # Pass the collection_name string
                    if index_file(path_item, repo_root_path, collection_name):
                        indexed_count += 1
                elif path_item.is_dir():
                    logger.warning(
                        f"Skipping directory: {path_item}. Indexing directories directly is not yet supported."
                    )
                    # TODO: Implement recursive directory indexing if needed
                else:
                    logger.warning(f"Skipping non-existent path: {path_item}")
            logger.info(f"File/directory index command finished. Indexed {indexed_count} files.")
        else:
            logger.warning("Index command called without --all flag or specific paths. Nothing to index.")

    elif args.command == "count":
        collection_name = args.collection_name
        logger.info(f"Executing 'count' command for collection '{collection_name}'...")
        try:
            collection = client.get_collection(name=collection_name)
            count = collection.count()
            print(f"Collection '{collection_name}' contains {count} documents.")
        except Exception as e:
            logger.error(f"Failed to get count for collection '{collection_name}': {e}", exc_info=True)
            print(f"Error: Could not retrieve collection '{collection_name}'. Does it exist?", file=sys.stderr)
            sys.exit(1)

    elif args.command == "query":
        collection_name = args.collection_name
        logger.info(f"Executing 'query' command for collection '{collection_name}'...")
        logger.info(f"Query text: '{args.query_text}'")
        logger.info(f"Number of results: {args.n_results}")
        try:
            collection = client.get_collection(name=collection_name, embedding_function=ef)
            results = collection.query(
                query_texts=[args.query_text], n_results=args.n_results, include=["metadatas", "documents", "distances"]
            )

            print(f"\n--- Query Results for '{args.query_text}' ({args.n_results} requested) ---")
            if not results or not results.get("ids") or not results["ids"][0]:
                print("No results found.")
            else:
                # Results is a dict with lists for each query_text (we only have one)
                ids = results["ids"][0]
                distances = results["distances"][0]
                metadatas = results["metadatas"][0]
                documents = results["documents"][0]

                for i, doc_id in enumerate(ids):
                    print(f"\nResult {i+1}:")
                    print(f"  ID: {doc_id}")
                    print(f"  Distance: {distances[i]:.4f}")
                    if metadatas and metadatas[i]:
                        print(f"  Metadata: {metadatas[i]}")
                    if documents and documents[i]:
                        # Show first N characters as snippet
                        snippet = documents[i].replace("\n", " ").strip()
                        max_snippet_len = 150
                        print(
                            f"  Snippet: {snippet[:max_snippet_len]}{'...' if len(snippet) > max_snippet_len else ''}"
                        )
                print("---------------------------------------------")

        except Exception as e:
            logger.error(f"Failed to query collection '{collection_name}': {e}", exc_info=True)
            print(f"Error: Could not query collection '{collection_name}'. Does it exist?", file=sys.stderr)
            sys.exit(1)

    elif args.command == "analyze-chat-history":
        logger.info(f"Executing 'analyze-chat-history' command...")
        # Note: The analysis function uses the client and ef initialized earlier
        try:
            processed, correlated = analyze_chat_history(
                client=client,  # Pass the initialized client
                embedding_function=ef,  # Pass the initialized EF
                repo_path=str(args.repo_path.resolve()),  # Pass resolved absolute path
                collection_name=args.collection_name,
                days_limit=args.days_limit,
                # Pass limit from args if needed, or keep default from analysis function
                # limit=args.limit, # Assuming limit arg exists or is added
                status_filter=args.status_filter,
                new_status=args.new_status,
            )
            logger.info("'analyze-chat-history' command finished. Processed=%d, Correlated=%d", processed, correlated)
            print("Chat history analysis finished.")  # Keep simple user output
        except Exception as e:
            logger.error(f"An error occurred during chat history analysis: {e}", exc_info=True)
            print(f"Error during analysis: {e}")  # Inform user
            sys.exit(1)  # Exit with non-zero code on error

    elif args.command == "update-collection-ef":
        collection_name = args.collection_name
        new_ef_name = args.ef_name
        logger.info(
            f"Executing 'update-collection-ef' for collection '{collection_name}' with EF name '{new_ef_name}'..."
        )
        try:
            # Get collection (requires client initialized earlier)
            # We don't pass EF here, just getting the object
            collection = client.get_collection(name=collection_name)

            # Prepare metadata update payload
            # IMPORTANT: Ensure this key 'hnsw:embedding_function' is correct for your Chroma version
            metadata_update = {"hnsw:embedding_function": new_ef_name}

            # Modify the collection's metadata
            collection.modify(metadata=metadata_update)

            logger.info(
                f"Successfully updated metadata for collection '{collection_name}' to set embedding function name to '{new_ef_name}'."
            )
            print(f"Collection '{collection_name}' metadata updated successfully.")

        except Exception as e:
            logger.error(f"Failed to update collection '{collection_name}': {e}", exc_info=True)
            print(f"Error: Could not update collection '{collection_name}'. Details: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
