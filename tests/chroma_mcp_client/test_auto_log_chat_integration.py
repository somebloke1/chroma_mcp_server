"""
Integration tests for the auto_log_chat implementation with context module.
"""

import unittest
from unittest.mock import MagicMock, patch
import json
import logging
from typing import Dict, Any, List
import uuid

# Import from the correct location
from src.chroma_mcp_client.auto_log_chat_impl import log_chat_to_chroma, process_chat_for_logging


class TestAutoLogChatIntegration(unittest.TestCase):
    """Integration tests for auto_log_chat implementation with context module."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the UUID generation to always return the same ID for tests
        self.patcher = patch("uuid.uuid4")
        self.mock_uuid = self.patcher.start()
        self.mock_uuid.return_value = uuid.UUID("00000000-0000-0000-0000-000000000001")

        self.mock_client = MagicMock()

        # Mock collection for chat_history_v1
        self.mock_chat_collection = MagicMock()
        self.mock_chat_collection.get.return_value = {
            "ids": ["00000000-0000-0000-0000-000000000001"],
            "documents": ["Test document"],
            "metadatas": [{"session_id": "test-session-123"}],
        }

        # Mock collection for codebase_v1 (for bidirectional linking)
        self.mock_code_collection = MagicMock()
        self.mock_code_collection.query.return_value = {
            "ids": [["code-chunk-1", "code-chunk-2"]],
            "documents": [["Content 1", "Content 2"]],
            "metadatas": [[{"file_path": "src/auth.py"}, {"file_path": "src/auth.py"}]],
            "distances": [[0.1, 0.2]],
        }
        self.mock_code_collection.get.return_value = {
            "ids": ["code-chunk-1"],
            "documents": ["Content 1"],
            "metadatas": [{"file_path": "src/auth.py", "related_chat_ids": ""}],
        }

        # Configure get_collection to return appropriate mocks
        def get_collection_side_effect(name):
            if name == "chat_history_v1":
                return self.mock_chat_collection
            elif name == "codebase_v1":
                return self.mock_code_collection
            return None

        self.mock_client.get_collection.side_effect = get_collection_side_effect

        # Add mock for create_collection
        self.mock_client.create_collection.return_value = self.mock_chat_collection

        # Sample test data
        self.prompt_summary = "Update the authentication logic"
        self.response_summary = "Fixed authentication by refactoring the token validation"
        self.raw_prompt = "Please update the authentication logic in auth.py to fix the expired token issue."
        self.raw_response = "I've updated the authentication logic in auth.py. The issue was in the token validation function where it wasn't properly checking the expiration date. I've refactored it to use the new utility function we created earlier. This should fix the expired token issue."
        self.tool_usage = [
            {"name": "codebase_search", "args": {"query": "token validation auth.py"}},
            {"name": "read_file", "args": {"target_file": "src/auth.py"}},
            {"name": "edit_file", "args": {"target_file": "src/auth.py"}},
        ]
        self.file_changes = [
            {
                "file_path": "src/auth.py",
                "before_content": "def validate_token(token):\n    # Check if token is valid\n    if not token:\n        return False\n    # TODO: Check expiration\n    return True",
                "after_content": "def validate_token(token):\n    # Check if token is valid\n    if not token:\n        return False\n    # Check expiration\n    return not is_token_expired(token)",
            }
        ]
        self.involved_entities = "src/auth.py,validate_token,token validation"
        self.session_id = "test-session-123"

    def tearDown(self):
        """Clean up after tests."""
        self.patcher.stop()

    def test_process_chat_for_logging_with_file_changes(self):
        """Test processing chat with file changes."""
        result = process_chat_for_logging(
            prompt_summary=self.prompt_summary,
            response_summary=self.response_summary,
            raw_prompt=self.raw_prompt,
            raw_response=self.raw_response,
            tool_usage=self.tool_usage,
            file_changes=self.file_changes,
            involved_entities=self.involved_entities,
            session_id=self.session_id,
        )

        # Verify document format
        document = result["document"]
        self.assertIn(self.prompt_summary, document)
        self.assertIn(self.response_summary, document)
        self.assertIn("Code Changes:", document)
        self.assertIn("src/auth.py", document)

        # Verify metadata
        metadata = result["metadata"]
        self.assertEqual(metadata["session_id"], self.session_id)
        self.assertEqual(metadata["prompt_summary"], self.prompt_summary)
        self.assertEqual(metadata["response_summary"], self.response_summary)
        self.assertEqual(metadata["involved_entities"], self.involved_entities)
        self.assertEqual(metadata["status"], "captured")

        # Verify enhanced context fields
        self.assertIn("code_context", metadata)
        self.assertIn("diff_summary", metadata)
        self.assertEqual(metadata["tool_sequence"], "codebase_search→read_file→edit_file")
        self.assertEqual(metadata["modification_type"], "bugfix")
        self.assertGreaterEqual(metadata["confidence_score"], 0.0)
        self.assertLessEqual(metadata["confidence_score"], 1.0)

    def test_process_chat_for_logging_without_file_changes(self):
        """Test processing chat without file changes."""
        result = process_chat_for_logging(
            prompt_summary="How does authentication work?",
            response_summary="Explained the authentication flow",
            raw_prompt="Can you explain how the authentication flow works in this application?",
            raw_response="The authentication flow in this application starts with the login endpoint...",
            tool_usage=[
                {"name": "codebase_search", "args": {"query": "authentication flow"}},
                {"name": "read_file", "args": {"target_file": "src/auth.py"}},
            ],
            file_changes=[],
            involved_entities="authentication,login,auth.py",
            session_id=self.session_id,
        )

        # Verify document format
        document = result["document"]
        self.assertIn("How does authentication work?", document)
        self.assertIn("Explained the authentication flow", document)
        self.assertNotIn("Code Changes:", document)

        # Verify metadata
        metadata = result["metadata"]
        self.assertEqual(metadata["tool_sequence"], "codebase_search→read_file")
        self.assertNotIn("code_context", metadata)
        self.assertNotIn("diff_summary", metadata)

    def test_log_chat_to_chroma_success(self):
        """Test successful logging to ChromaDB."""
        result_id = log_chat_to_chroma(
            chroma_client=self.mock_client,
            prompt_summary=self.prompt_summary,
            response_summary=self.response_summary,
            raw_prompt=self.raw_prompt,
            raw_response=self.raw_response,
            tool_usage=self.tool_usage,
            file_changes=self.file_changes,
            involved_entities=self.involved_entities,
            session_id=self.session_id,
        )

        # Verify collection.add was called correctly
        self.mock_chat_collection.add.assert_called_once()
        call_args = self.mock_chat_collection.add.call_args[1]
        self.assertTrue(isinstance(call_args["documents"], list))
        self.assertTrue(isinstance(call_args["metadatas"], list))
        self.assertEqual(call_args["ids"], ["00000000-0000-0000-0000-000000000001"])
        self.assertEqual(result_id, "00000000-0000-0000-0000-000000000001")

    def test_log_chat_to_chroma_error_handling(self):
        """Test error handling when logging fails."""
        # Make the add method raise an exception
        self.mock_chat_collection.add.side_effect = Exception("Test error")

        with self.assertRaises(Exception):
            log_chat_to_chroma(
                chroma_client=self.mock_client,
                prompt_summary=self.prompt_summary,
                response_summary=self.response_summary,
                raw_prompt=self.raw_prompt,
                raw_response=self.raw_response,
                tool_usage=self.tool_usage,
                file_changes=self.file_changes,
                involved_entities=self.involved_entities,
                session_id=self.session_id,
            )

    @patch("src.chroma_mcp_client.auto_log_chat_impl.manage_bidirectional_links")
    def test_log_chat_to_chroma_with_bidirectional_links(self, mock_manage_links):
        """Test logging to ChromaDB with bidirectional links."""
        # Set up the mock for bidirectional links
        mock_manage_links.return_value = {"src/auth.py": ["code-chunk-1", "code-chunk-2"]}

        # Call the function
        result_id = log_chat_to_chroma(
            chroma_client=self.mock_client,
            prompt_summary=self.prompt_summary,
            response_summary=self.response_summary,
            raw_prompt=self.raw_prompt,
            raw_response=self.raw_response,
            tool_usage=self.tool_usage,
            file_changes=self.file_changes,
            involved_entities=self.involved_entities,
            session_id=self.session_id,
        )

        # Verify collection.add was called correctly
        self.mock_chat_collection.add.assert_called_once()

        # Verify bidirectional linking was attempted
        mock_manage_links.assert_called_once_with(
            chat_id="00000000-0000-0000-0000-000000000001",
            file_changes=self.file_changes,
            chroma_client=self.mock_client,
        )

        # Verify chat history was updated with related chunks
        self.mock_chat_collection.update.assert_called_once()
        update_call = self.mock_chat_collection.update.call_args
        _, kwargs = update_call
        metadata = kwargs.get("metadatas")[0]
        self.assertEqual(metadata["related_code_chunks"], "code-chunk-1,code-chunk-2")

        # Verify correct ID was returned
        self.assertEqual(result_id, "00000000-0000-0000-0000-000000000001")

    @patch("src.chroma_mcp_client.auto_log_chat_impl.manage_bidirectional_links")
    def test_log_chat_to_chroma_empty_bidirectional_links(self, mock_manage_links):
        """Test handling when no bidirectional links are found."""
        # Set up the mock for bidirectional links to return empty dict
        mock_manage_links.return_value = {}

        # Call the function
        result_id = log_chat_to_chroma(
            chroma_client=self.mock_client,
            prompt_summary=self.prompt_summary,
            response_summary=self.response_summary,
            raw_prompt=self.raw_prompt,
            raw_response=self.raw_response,
            tool_usage=self.tool_usage,
            file_changes=self.file_changes,
            involved_entities=self.involved_entities,
            session_id=self.session_id,
        )

        # Verify bidirectional linking was attempted
        mock_manage_links.assert_called_once_with(
            chat_id="00000000-0000-0000-0000-000000000001",
            file_changes=self.file_changes,
            chroma_client=self.mock_client,
        )

        # Verify chat history was NOT updated with related chunks (since there weren't any)
        self.mock_chat_collection.update.assert_not_called()

        # Verify correct ID was returned
        self.assertEqual(result_id, "00000000-0000-0000-0000-000000000001")


if __name__ == "__main__":
    unittest.main()
