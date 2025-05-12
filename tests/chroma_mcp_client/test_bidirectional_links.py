"""
Unit tests for bidirectional linking functionality in the context module.
"""

import unittest
from unittest.mock import MagicMock, patch
import json
from src.chroma_mcp_client.context import manage_bidirectional_links


class TestBidirectionalLinks(unittest.TestCase):
    """Test case for bidirectional link management."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.mock_collection = MagicMock()
        self.mock_client.get_collection.return_value = self.mock_collection

        # Set up mock query response
        self.mock_collection.query.return_value = {
            "ids": [["chunk-1", "chunk-2"]],
            "documents": [["Content 1", "Content 2"]],
            "metadatas": [[{"file_path": "test.py"}, {"file_path": "test.py"}]],
            "distances": [[0.1, 0.2]],
        }

        # Set up mock get response
        self.mock_collection.get.return_value = {
            "ids": ["chunk-1"],
            "documents": ["Content 1"],
            "metadatas": [{"file_path": "test.py", "related_chat_ids": ""}],
        }

        # File changes sample data
        self.file_changes = [
            {"file_path": "test.py", "before_content": "def old():\n    pass", "after_content": "def new():\n    pass"}
        ]
        self.chat_id = "chat-123"

    def test_manage_bidirectional_links_success(self):
        """Test successful bidirectional link management."""
        result = manage_bidirectional_links(
            chat_id=self.chat_id, file_changes=self.file_changes, chroma_client=self.mock_client
        )

        # Verify client interactions
        self.mock_client.get_collection.assert_called_once_with(name="codebase_v1")
        self.mock_collection.query.assert_called_once()
        self.mock_collection.get.assert_called()
        self.mock_collection.update.assert_called()

        # Verify returned mapping
        self.assertEqual(result, {"test.py": ["chunk-1", "chunk-2"]})

        # Verify metadata update (related_chat_ids should include our chat_id)
        update_calls = self.mock_collection.update.call_args_list
        for call in update_calls:
            args, kwargs = call
            metadata = kwargs.get("metadatas")[0]
            self.assertIn(self.chat_id, metadata["related_chat_ids"])

    def test_manage_bidirectional_links_collection_not_found(self):
        """Test handling when codebase collection is not found."""
        self.mock_client.get_collection.return_value = None

        result = manage_bidirectional_links(
            chat_id=self.chat_id, file_changes=self.file_changes, chroma_client=self.mock_client
        )

        # Should return empty result
        self.assertEqual(result, {})
        self.mock_client.get_collection.assert_called_once_with(name="codebase_v1")
        self.mock_collection.query.assert_not_called()

    def test_manage_bidirectional_links_query_empty(self):
        """Test handling when query returns no results."""
        self.mock_collection.query.return_value = {"ids": [[]]}

        result = manage_bidirectional_links(
            chat_id=self.chat_id, file_changes=self.file_changes, chroma_client=self.mock_client
        )

        # Should return empty result
        self.assertEqual(result, {})
        self.mock_collection.get.assert_not_called()
        self.mock_collection.update.assert_not_called()

    def test_manage_bidirectional_links_append_to_existing(self):
        """Test appending chat_id to existing related_chat_ids."""
        existing_chat_id = "chat-456"
        self.mock_collection.get.return_value = {
            "ids": ["chunk-1"],
            "documents": ["Content 1"],
            "metadatas": [{"file_path": "test.py", "related_chat_ids": existing_chat_id}],
        }

        result = manage_bidirectional_links(
            chat_id=self.chat_id, file_changes=self.file_changes, chroma_client=self.mock_client
        )

        # Verify metadata update (should include both chat IDs)
        update_calls = self.mock_collection.update.call_args_list
        for call in update_calls:
            args, kwargs = call
            metadata = kwargs.get("metadatas")[0]
            self.assertIn(self.chat_id, metadata["related_chat_ids"])
            self.assertIn(existing_chat_id, metadata["related_chat_ids"])

    def test_manage_bidirectional_links_error_handling(self):
        """Test error handling during bidirectional link management."""
        self.mock_collection.query.side_effect = Exception("Query error")

        result = manage_bidirectional_links(
            chat_id=self.chat_id, file_changes=self.file_changes, chroma_client=self.mock_client
        )

        # Should return empty result on error
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
