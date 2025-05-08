"""
Module for managing derived learnings, including promoting chat entries or manual insights
into the derived_learnings_v1 collection.
"""

import sys
import logging
import uuid
import time
import chromadb
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def promote_to_learnings_collection(
    client: chromadb.ClientAPI,
    embedding_function: Optional[chromadb.EmbeddingFunction],
    description: str,
    pattern: str,
    code_ref: str,
    tags: str,
    confidence: float,
    learnings_collection_name: str = "derived_learnings_v1",
    source_chat_id: Optional[str] = None,
    chat_history_collection_name: str = "chat_history_v1",
) -> Optional[str]:
    """
    Promotes a piece of information (e.g., from chat or manual input) to the derived learnings collection
    and optionally updates the status of the source chat entry.

    Args:
        client: Initialized ChromaDB client.
        embedding_function: Embedding function for the learnings collection.
        description: Natural language description of the learning (will be embedded).
        pattern: Core pattern identified (e.g., code snippet, regex, textual description).
        code_ref: Code reference illustrating the learning (e.g., chunk_id 'path:sha:index').
        tags: Comma-separated tags for categorization.
        confidence: Confidence score for this learning (0.0 to 1.0).
        learnings_collection_name: Name of the collection to add the derived learning to.
        source_chat_id: Optional ID of the source entry in the chat history collection.
        chat_history_collection_name: Name of the chat history collection for status updates.

    Returns:
        The ID of the newly created learning entry if successful, None otherwise.
    """
    logger.info(f"Attempting to promote learning to '{learnings_collection_name}'...")
    try:
        learning_id = str(uuid.uuid4())
        logger.debug(f"Generated learning_id: {learning_id}")

        metadata = {
            "learning_id": learning_id,
            "source_chat_id": source_chat_id if source_chat_id else "manual",
            "pattern": pattern,
            "example_code_reference": code_ref,
            "tags": tags,
            "confidence": confidence,
            "promotion_timestamp_utc": time.time(),
        }

        if not 0.0 <= confidence <= 1.0:
            logger.warning(f"Confidence score {confidence} is outside the suggested 0.0-1.0 range.")

        logger.debug(f"Prepared metadata for learning: {metadata}")

        try:
            learning_collection = client.get_collection(
                name=learnings_collection_name,
                embedding_function=embedding_function,
            )
            logger.debug(f"Accessed learning collection: {learnings_collection_name}")
        except Exception as e:
            logger.error(f"Failed to get learning collection '{learnings_collection_name}': {e}", exc_info=True)
            # Consider if creating the collection here is desired if it doesn't exist
            # For now, assume it should exist.
            print(f"Error: Could not access collection '{learnings_collection_name}'. Does it exist?", file=sys.stderr)
            return None

        learning_collection.add(ids=[learning_id], documents=[description], metadatas=[metadata])
        logger.info(f"Successfully added learning {learning_id} to '{learnings_collection_name}'.")
        print(f"Learning promoted with ID: {learning_id}")  # Keep some console feedback

        if source_chat_id:
            logger.info(
                f"Attempting to update status for source chat ID: {source_chat_id} in '{chat_history_collection_name}'"
            )
            try:
                chat_collection = client.get_collection(name=chat_history_collection_name)
                results = chat_collection.get(ids=[source_chat_id], include=["metadatas"])

                if results and results["ids"] and results["ids"][0] == source_chat_id:
                    existing_metadata = results["metadatas"][0] if results["metadatas"] else {}
                    if existing_metadata is None:  # Should not happen if ID exists, but good practice
                        existing_metadata = {}

                    existing_metadata["status"] = "promoted_to_learning"
                    existing_metadata["promoted_learning_id"] = learning_id

                    chat_collection.update(ids=[source_chat_id], metadatas=[existing_metadata])
                    logger.info(f"Successfully updated status for chat ID {source_chat_id} to 'promoted_to_learning'.")
                    print(f"Updated status for source chat ID: {source_chat_id}")
                else:
                    logger.warning(
                        f"Source chat ID {source_chat_id} not found in '{chat_history_collection_name}'. Cannot update status."
                    )
                    print(f"Warning: Source chat ID {source_chat_id} not found. Status not updated.")
            except Exception as e:
                logger.error(
                    f"Failed to update status for chat ID {source_chat_id} in '{chat_history_collection_name}': {e}",
                    exc_info=True,
                )
                print(f"Warning: Failed to update status for source chat ID {source_chat_id}. See logs.")

        return learning_id

    except Exception as e:
        logger.error(f"Failed to promote learning: {e}", exc_info=True)
        print(f"Error: Could not promote learning. See logs for details.", file=sys.stderr)
        return None
