"""
Module for managing derived learnings, including promoting chat entries or manual insights
into the derived_learnings_v1 collection.
"""

import sys
import logging
import uuid
import time
import chromadb
from typing import Optional, Dict, Any, List, Union

logger = logging.getLogger(__name__)


def fetch_source_chat_context(
    client: chromadb.ClientAPI,
    source_chat_id: str,
    chat_history_collection_name: str = "chat_history_v1",
) -> Dict[str, Any]:
    """
    Fetches rich context data from a source chat entry.

    Args:
        client: Initialized ChromaDB client.
        source_chat_id: ID of the source entry in the chat history collection.
        chat_history_collection_name: Name of the chat history collection.

    Returns:
        Dictionary containing rich context data from the source chat entry.
    """
    context_data = {
        "code_context": "",
        "diff_summary": "",
        "tool_sequence": "",
        "confidence_score": 0.0,
        "modification_type": "unknown",
        "related_code_chunks": "",
        "prompt_summary": "",
        "response_summary": "",
    }

    try:
        chat_collection = client.get_collection(name=chat_history_collection_name)
        results = chat_collection.get(ids=[source_chat_id], include=["metadatas", "documents"])

        if not results or not results["ids"] or results["ids"][0] != source_chat_id:
            logger.warning(f"Source chat ID {source_chat_id} not found when fetching context.")
            return context_data

        metadata = results["metadatas"][0] if results.get("metadatas") else {}
        if not metadata:
            logger.warning(f"No metadata found for source chat ID {source_chat_id}.")
            return context_data

        # Extract available context fields
        for field in context_data.keys():
            if field in metadata and metadata[field] is not None:
                context_data[field] = metadata[field]

        # Add prompt and response summaries
        context_data["prompt_summary"] = metadata.get("prompt_summary", "")
        context_data["response_summary"] = metadata.get("response_summary", "")

        logger.info(f"Successfully fetched context data for chat ID {source_chat_id}.")

    except Exception as e:
        logger.error(f"Error fetching context for source chat ID {source_chat_id}: {e}", exc_info=True)

    return context_data


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
    include_chat_context: bool = True,
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
        include_chat_context: Whether to include rich context from the source chat.

    Returns:
        The ID of the newly created learning entry if successful, None otherwise.
    """
    logger.info(f"Attempting to promote learning to '{learnings_collection_name}'...")
    try:
        learning_id = str(uuid.uuid4())
        logger.debug(f"Generated learning_id: {learning_id}")

        # Initialize metadata with base fields
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

        # If we have a source chat ID and include_chat_context is True, fetch and include rich context
        source_context = {}
        if source_chat_id and include_chat_context:
            logger.info(f"Fetching rich context from source chat ID {source_chat_id}...")
            source_context = fetch_source_chat_context(client, source_chat_id, chat_history_collection_name)

            # Only override confidence if it's not explicitly provided
            if confidence == 0.0 and source_context.get("confidence_score"):
                try:
                    metadata["confidence"] = float(source_context["confidence_score"])
                    logger.info(f"Using confidence score {metadata['confidence']} from source chat.")
                except (ValueError, TypeError):
                    logger.warning(
                        f"Could not convert source confidence '{source_context.get('confidence_score')}' to float."
                    )

            # Add rich context fields if available
            for field_name, context_value in [
                ("code_context", source_context.get("code_context")),
                ("diff_summary", source_context.get("diff_summary")),
                ("tool_sequence", source_context.get("tool_sequence")),
                ("modification_type", source_context.get("modification_type")),
                ("related_code_chunks", source_context.get("related_code_chunks")),
            ]:
                if context_value:
                    metadata[field_name] = context_value
                    logger.debug(f"Included {field_name} from source chat.")

            # Enhance description with context if it's minimal
            if len(description) < 100 and source_context.get("diff_summary"):
                original_description = description
                description = f"{description}\n\nContext from source chat:\n{source_context.get('prompt_summary', '')}\n{source_context.get('response_summary', '')}\n\nCode changes:\n{source_context.get('diff_summary', '')}"
                logger.info("Enhanced description with context from source chat.")

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
        print(f"Learning promoted with ID: {learning_id}")

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
