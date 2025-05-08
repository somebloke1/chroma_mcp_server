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
import uuid
import time

# Get our specific logger
logger = logging.getLogger(__name__)

# Removed sys.path manipulation logic
# Imports should work directly when the package is installed
from .connection import get_client_and_ef
from .indexing import index_file, index_git_files
from .analysis import analyze_chat_history  # Import the new function

# Import from utils to set the main logger
from chroma_mcp.utils import set_main_logger, BASE_LOGGER_NAME as UTILS_BASE_LOGGER_NAME

# Import the function for the new subcommand
from .interactive_promoter import run_interactive_promotion

# Import the refactored promotion function
from .learnings import promote_to_learnings_collection

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
    # Configure logging EARLY inside main()
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    # Set a default level; will be adjusted based on verbosity later
    logging.basicConfig(level=logging.WARNING, format=log_format)

    # Get the logger for the current module (chroma_mcp_client.cli)
    # This specific logger is fine, but we also need to set the main one for utils.
    logger = logging.getLogger(__name__)

    # --- Setup Logging Level based on verbosity (occurs after arg parsing) ---
    # The actual setting of levels will happen after args are parsed.
    # For now, we ensure a basic config is up.

    parser = argparse.ArgumentParser(
        description="ChromaDB Client CLI for indexing and querying.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase output verbosity (e.g., -v for INFO, -vv for DEBUG)",
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

    # --- Setup Collections Subparser ---
    setup_collections_parser = subparsers.add_parser(
        "setup-collections",
        help="Check and create all required ChromaDB collections if they do not exist.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # No arguments needed for this command yet, but parser is set up for future extension

    # --- Review and Promote Subparser ---
    review_promote_parser = subparsers.add_parser(
        "review-and-promote",
        help="Interactively review 'analyzed' chat entries and promote them to learnings.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    review_promote_parser.add_argument(
        "--days-limit",
        type=int,
        default=7,
        help="How many days back to look for 'analyzed' entries.",
    )
    review_promote_parser.add_argument(
        "--fetch-limit",
        type=int,
        default=50,
        help="Maximum number of entries to fetch for review in one go.",
    )
    review_promote_parser.add_argument(
        "--chat-collection-name",
        default="chat_history_v1",
        help="Name of the ChromaDB chat history collection.",
    )
    review_promote_parser.add_argument(
        "--learnings-collection-name",
        default="derived_learnings_v1",
        help="Name of the collection to add derived learnings to.",
    )
    # Add --repo-path later if needed for diffs

    # --- Promote Learning Subparser ---
    promote_parser = subparsers.add_parser(
        "promote-learning",
        help="Promote an analyzed insight or manual finding into the derived learnings collection.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    promote_parser.add_argument(
        "--description",
        required=True,
        help="Natural language description of the learning (will be embedded).",
    )
    promote_parser.add_argument(
        "--pattern",
        required=True,
        help="Core pattern identified (e.g., code snippet, regex, textual description).",
    )
    promote_parser.add_argument(
        "--code-ref",
        required=True,
        help="Code reference illustrating the learning (e.g., chunk_id 'path:sha:index').",
    )
    promote_parser.add_argument(
        "--tags",
        required=True,
        help="Comma-separated tags for categorization (e.g., 'python,refactor,logging').",
    )
    promote_parser.add_argument(
        "--confidence",
        required=True,
        type=float,
        help="Confidence score for this learning (e.g., 0.0 to 1.0).",
    )
    promote_parser.add_argument(
        "--source-chat-id",
        help="Optional ID of the source entry in the chat history collection.",
    )
    promote_parser.add_argument(
        "--collection-name",
        default="derived_learnings_v1",
        help="Name of the collection to add the derived learning to.",
    )
    promote_parser.add_argument(
        "--chat-collection-name",
        default="chat_history_v1",
        help="Name of the chat history collection to update status if source ID is provided.",
    )

    args = parser.parse_args()

    # --- Setup Logging Level based on verbosity ---
    if args.verbose == 1:
        log_level = logging.INFO
    elif args.verbose >= 2:
        log_level = logging.DEBUG
    else:
        # Default to INFO if not specified or 0, to ensure our logs are seen
        # unless the user *really* wants less (which isn't an option here)
        log_level = logging.INFO

    # Set the level for the root logger AND the main 'chromamcp' base logger from utils
    # This affects all loggers unless they have their own level set
    logging.getLogger().setLevel(log_level)
    logging.getLogger(UTILS_BASE_LOGGER_NAME).setLevel(log_level)  # Configure the base 'chromamcp' logger

    # Set the main logger instance for chroma_mcp.utils
    # This uses the already configured 'chromamcp' base logger.
    set_main_logger(logging.getLogger(UTILS_BASE_LOGGER_NAME))

    # Set the level specifically for our client's own sub-loggers if desired
    # (e.g., chroma_mcp_client.cli, chroma_mcp_client.connection)
    # This ensures that even if the root/base is INFO, client can be DEBUG if -vv
    logging.getLogger("chroma_mcp_client").setLevel(log_level)

    # Optionally set levels for other loggers if needed (e.g., sentence_transformers)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

    # logger.info(f"Log level set to {logging.getLevelName(log_level)}")
    # Use the utils logger to announce this, as it's now configured.
    utils_logger = logging.getLogger(f"{UTILS_BASE_LOGGER_NAME}.cli_setup")  # Get a child of the main logger
    utils_logger.info(
        f"Client CLI log level set to {logging.getLevelName(log_level)} for base '{UTILS_BASE_LOGGER_NAME}' and 'chroma_mcp_client'"
    )

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
        ef_name = args.ef_name
        logger.info(
            f"Executing 'update-collection-ef' command for collection '{collection_name}' with new EF name '{ef_name}'..."
        )
        try:
            collection = client.get_collection(name=collection_name)  # Get it first to ensure it exists
            metadata = collection.metadata or {}
            metadata["embedding_function_name"] = ef_name
            collection.modify(metadata=metadata)
            logger.info(f"Successfully updated embedding function name for collection '{collection_name}'.")
            print(f"Embedding function name for '{collection_name}' updated to '{ef_name}'.")
        except Exception as e:
            logger.error(
                f"Failed to update embedding function name for collection '{collection_name}': {e}",
                exc_info=True,
            )
            print(
                f"Error: Could not update collection '{collection_name}'. Does it exist?",
                file=sys.stderr,
            )
            sys.exit(1)

    elif args.command == "setup-collections":
        logger.info("Executing 'setup-collections' command...")
        required_collections = [
            "codebase_v1",
            "chat_history_v1",
            "derived_learnings_v1",
            "thinking_sessions_v1",
        ]
        collections_created = 0
        collections_existing = 0

        for collection_name in required_collections:
            logger.info(f"Checking/Creating collection: '{collection_name}'")
            try:
                # Attempt to get the collection first to see if it exists
                # This is a bit more verbose but gives clearer logging
                try:
                    client.get_collection(name=collection_name)
                    logger.info(f"Collection '{collection_name}' already exists.")
                    collections_existing += 1
                except Exception:  # Should be a more specific exception if Chroma client provides one for not found
                    logger.info(f"Collection '{collection_name}' not found, creating...")
                    client.get_or_create_collection(
                        name=collection_name,
                        embedding_function=ef,
                        # metadata={"description": f"Default collection for {collection_name}"} # Example metadata
                    )
                    logger.info(f"Collection '{collection_name}' created successfully.")
                    collections_created += 1
            except Exception as e:
                logger.error(
                    f"Failed to check/create collection '{collection_name}': {e}",
                    exc_info=True,
                )
                print(
                    f"Error processing collection '{collection_name}'. See logs for details.",
                    file=sys.stderr,
                )
                # Optionally, decide if we should exit or continue with other collections
                # sys.exit(1) # Uncomment to exit on first error

        summary_message = (
            f"Collections setup finished. Created: {collections_created}, Already Existed: {collections_existing}."
        )
        logger.info(summary_message)
        print(summary_message)

    elif args.command == "review-and-promote":
        logger.info("Executing 'review-and-promote' command...")
        try:
            run_interactive_promotion(
                days_limit=args.days_limit,
                fetch_limit=args.fetch_limit,
                chat_collection_name=args.chat_collection_name,
                learnings_collection_name=args.learnings_collection_name,
                # repo_path=args.repo_path # Add if/when repo_path arg is added
            )
            logger.info("'review-and-promote' command finished.")
            print("Interactive review and promotion process complete.")
        except Exception as e:
            logger.error(f"An error occurred during interactive promotion: {e}", exc_info=True)
            print(f"Error during interactive promotion: {e}")
            sys.exit(1)

    elif args.command == "promote-learning":
        logger.info(f"Executing 'promote-learning' command...")

        # Call the refactored function
        # Note: client and ef are already initialized earlier in main()
        learning_id = promote_to_learnings_collection(
            client=client,
            embedding_function=ef,
            description=args.description,
            pattern=args.pattern,
            code_ref=args.code_ref,
            tags=args.tags,
            confidence=args.confidence,
            learnings_collection_name=args.collection_name,  # from --collection-name
            source_chat_id=args.source_chat_id,
            chat_history_collection_name=args.chat_collection_name,
        )

        if learning_id:
            # The function already prints messages, so we might not need more here
            # or we can have a simpler success message.
            logger.info(f"'promote-learning' command completed for learning ID: {learning_id}")
        else:
            logger.error("'promote-learning' command failed. See previous logs for details.")
            sys.exit(1)  # Exit if the promotion function indicated failure by returning None

    else:
        logger.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
