"""Tests for the promotion module in the validation package."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import uuid
import json
import datetime
from pathlib import Path

from chroma_mcp_client.validation.promotion import LearningPromoter, promote_validated_learning
from chroma_mcp_client.validation.schemas import (
    ValidationEvidenceType,
    ValidationEvidence,
    TestTransitionEvidence,
    RuntimeErrorEvidence,
    CodeQualityEvidence,
)


class TestLearningPromoter:
    """Test cases for the LearningPromoter class."""

    def test_init(self):
        """Test initializing the LearningPromoter."""
        promoter = LearningPromoter()

        assert promoter.chroma_client is None

        # Test with custom parameters
        mock_client = MagicMock()
        promoter = LearningPromoter(chroma_client=mock_client)

        assert promoter.chroma_client == mock_client

    @patch("chroma_mcp.utils.chroma_client.get_chroma_client")
    def test_get_validation_evidence(self, mock_get_chroma_client):
        """Test retrieving validation evidence."""
        # Set up mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        mock_get_chroma_client.return_value = mock_client

        # Mock the collection get result
        mock_collection.get.return_value = {
            "ids": ["evidence-1"],
            "documents": [
                json.dumps(
                    {
                        "evidence_types": ["test_transition"],
                        "score": 0.8,
                        "test_transitions": [
                            {
                                "test_id": "test-123",
                                "test_file": "tests/test_module.py",
                                "test_name": "test_function",
                                "before_status": "fail",
                                "after_status": "pass",
                                "before_timestamp": "2023-04-15T14:30:00Z",
                                "after_timestamp": "2023-04-15T15:45:00Z",
                                "code_changes": {"file.py": {"before": "old", "after": "new"}},
                            }
                        ],
                    }
                )
            ],
            "metadatas": [{"evidence_id": "evidence-1", "score": 0.8}],
        }

        # Create promoter and get evidence
        promoter = LearningPromoter(chroma_client=mock_client)
        evidence = promoter.get_validation_evidence("evidence-1")

        # Check the evidence
        assert isinstance(evidence, ValidationEvidence)
        assert evidence.score == 0.8
        assert ValidationEvidenceType.TEST_TRANSITION in evidence.evidence_types
        assert len(evidence.test_transitions) == 1
        assert evidence.test_transitions[0].test_id == "test-123"

        # Check that collection was accessed correctly
        mock_client.get_collection.assert_called_once_with(name="validation_evidence_v1")
        mock_collection.get.assert_called_once_with(ids=["evidence-1"])

        # Test with error
        mock_client.reset_mock()
        mock_collection.get.side_effect = Exception("Error retrieving evidence")

        evidence = promoter.get_validation_evidence("evidence-1")
        assert evidence is None

    def test_format_learning(self):
        """Test formatting validation evidence into learning."""
        # Create validation evidence with a test transition
        test_transition = TestTransitionEvidence(
            test_id="test-123",
            test_file="tests/test_module.py",
            test_name="test_function",
            before_status="fail",
            after_status="pass",
            before_timestamp="2023-04-15T14:30:00Z",
            after_timestamp="2023-04-15T15:45:00Z",
            error_message_before="AssertionError: Expected 42, got None",
            code_changes={"file.py": {"before": "old", "after": "new"}},
        )

        evidence = ValidationEvidence(
            evidence_types=[ValidationEvidenceType.TEST_TRANSITION], score=0.8, test_transitions=[test_transition]
        )

        # Format the learning
        promoter = LearningPromoter()
        learning = promoter.format_learning(evidence, chat_id="chat-123")

        # Check the learning
        assert learning["title"].startswith("Fixed failing test")
        assert learning["validation_score"] == 0.8
        assert "chat_id" in learning
        assert learning["chat_id"] == "chat-123"
        assert len(learning["code_snippets"]) == 1
        assert learning["code_snippets"][0]["file"] == "file.py"
        assert learning["code_snippets"][0]["code_before"] == "old"
        assert learning["code_snippets"][0]["code_after"] == "new"

        # Check with additional metadata
        learning = promoter.format_learning(evidence, metadata={"key": "value"})
        assert "key" in learning
        assert learning["key"] == "value"

    @patch("uuid.uuid4")
    @patch("datetime.datetime")
    @patch("chroma_mcp.utils.chroma_client.get_chroma_client")
    @patch("chroma_mcp_client.validation.schemas.ValidationEvidence.meets_threshold")
    def test_promote_learning(self, mock_meets_threshold, mock_get_chroma_client, mock_datetime, mock_uuid):
        """Test promoting a validated learning."""
        # Set up mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        mock_get_chroma_client.return_value = mock_client

        mock_uuid.return_value = "learning-uuid"
        mock_now = MagicMock()
        mock_now.isoformat.return_value = "2023-04-15T12:00:00Z"
        mock_datetime.now.return_value = mock_now

        # Make ValidationEvidence.meets_threshold return True
        mock_meets_threshold.return_value = True

        # Create test transition evidence
        test_transition = TestTransitionEvidence(
            test_id="test-123",
            test_file="tests/test_module.py",
            test_name="test_function",
            before_status="fail",
            after_status="pass",
            before_timestamp="2023-04-15T14:30:00Z",
            after_timestamp="2023-04-15T15:45:00Z",
            error_message_before="AssertionError: Expected 42, got None",
            code_changes={"file.py": {"before": "old", "after": "new"}},
        )

        # Create validation evidence
        evidence = ValidationEvidence(
            evidence_types=[ValidationEvidenceType.TEST_TRANSITION], score=0.8, test_transitions=[test_transition]
        )

        # Test promoting a learning
        promoter = LearningPromoter(chroma_client=mock_client)
        result = promoter.promote_learning(evidence, chat_id="chat-123")

        # Check the result
        assert result == "learning-uuid"

        # Verify the collection was accessed
        mock_client.get_collection.assert_called_once_with(name="derived_learnings_v1")

        # Check with collection creation
        mock_client.reset_mock()
        mock_client.get_collection.side_effect = Exception("Collection not found")
        mock_client.create_collection.return_value = mock_collection

        result = promoter.promote_learning(evidence)

        mock_client.create_collection.assert_called_once_with(name="derived_learnings_v1")

        # Test with evidence below threshold
        mock_meets_threshold.return_value = False

        result = promoter.promote_learning(evidence)
        assert result is None

    @patch("chroma_mcp.utils.chroma_client.get_chroma_client")
    def test_promote_by_evidence_id(self, mock_get_chroma_client):
        """Test promoting by evidence ID."""
        # Set up mocks
        mock_client = MagicMock()
        mock_get_chroma_client.return_value = mock_client

        # Test the case with valid evidence
        with patch.object(LearningPromoter, "get_validation_evidence") as mock_get_evidence:
            with patch.object(LearningPromoter, "promote_learning") as mock_promote:
                # Set up mocks for successful promotion
                mock_evidence = MagicMock()
                mock_get_evidence.return_value = mock_evidence
                mock_promote.return_value = "learning-uuid"

                # Create promoter and call method
                promoter = LearningPromoter(chroma_client=mock_client)
                result = promoter.promote_by_evidence_id(
                    evidence_id="evidence-1", chat_id="chat-123", metadata={"key": "value"}
                )

                # Check result
                assert result == "learning-uuid"

                # Verify method calls with the exact same positional argument order as in the implementation
                mock_get_evidence.assert_called_with("evidence-1", "validation_evidence_v1")
                assert mock_get_evidence.call_count == 1

                mock_promote.assert_called_with(
                    mock_evidence,  # evidence (positional)
                    "chat-123",  # chat_id (positional)
                    "derived_learnings_v1",  # collection_name (positional)
                    {"key": "value"},  # metadata (positional)
                )
                assert mock_promote.call_count == 1

        # Test the case with no evidence found (use fresh mocks)
        with patch.object(LearningPromoter, "get_validation_evidence") as mock_get_evidence:
            with patch.object(LearningPromoter, "promote_learning") as mock_promote:
                # Set up mock to return None (no evidence found)
                mock_get_evidence.return_value = None

                # Create promoter and call method
                promoter = LearningPromoter(chroma_client=mock_client)
                result = promoter.promote_by_evidence_id("evidence-1")

                # Check result
                assert result is None

                # Verify get_validation_evidence was called
                mock_get_evidence.assert_called_with("evidence-1", "validation_evidence_v1")
                assert mock_get_evidence.call_count == 1

                # Verify promote_learning was not called
                mock_promote.assert_not_called()


@patch("chroma_mcp_client.validation.promotion.LearningPromoter")
def test_promote_validated_learning(mock_promoter_class):
    """Test the convenience function for promoting validated learning."""
    # Set up mocks
    mock_promoter = MagicMock()
    mock_promoter.promote_by_evidence_id.return_value = "learning-uuid"
    mock_promoter_class.return_value = mock_promoter

    # Call the function
    result = promote_validated_learning(
        evidence_id="evidence-1", chat_id="chat-123", metadata={"key": "value"}, chroma_client="mock-client"
    )

    # Check the result
    assert result == "learning-uuid"

    # Verify the promoter was initialized with positional args as used in the code
    mock_promoter_class.assert_called_with("mock-client")
    assert mock_promoter_class.call_count == 1

    # Verify promote_by_evidence_id was called with positional args as used in the code
    mock_promoter.promote_by_evidence_id.assert_called_with(
        "evidence-1",  # evidence_id (positional)
        "chat-123",  # chat_id (positional)
        "validation_evidence_v1",  # evidence_collection (positional)
        "derived_learnings_v1",  # learning_collection (positional)
        {"key": "value"},  # metadata (positional)
    )
    assert mock_promoter.promote_by_evidence_id.call_count == 1
