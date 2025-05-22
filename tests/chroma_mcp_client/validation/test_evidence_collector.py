"""Tests for the evidence collector module in the validation package."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import uuid
import datetime
import json
from pathlib import Path
from typing import Dict, List, Any

from chroma_mcp_client.validation.evidence_collector import EvidenceCollector, collect_and_score_evidence
from chroma_mcp_client.validation.schemas import (
    ValidationEvidenceType,
    ValidationEvidence,
    TestTransitionEvidence,
    RuntimeErrorEvidence,
    CodeQualityEvidence,
)


class TestEvidenceCollector:
    """Test cases for the EvidenceCollector class."""

    def test_init(self):
        """Test initializing the EvidenceCollector."""
        collector = EvidenceCollector()

        assert collector.chroma_client is None
        assert collector.evidence_types == []
        assert collector.test_transitions == []
        assert collector.runtime_errors == []
        assert collector.code_quality == []
        assert collector.knowledge_gap_resolutions == []
        assert collector.security_fixes == []
        assert collector.performance_improvements == []

        # With client
        mock_client = MagicMock()
        collector = EvidenceCollector(chroma_client=mock_client)
        assert collector.chroma_client == mock_client

    @patch("chroma_mcp_client.validation.evidence_collector.create_test_transition_evidence")
    def test_collect_test_evidence(self, mock_create_evidence):
        """Test collecting test transition evidence."""
        # Mock the test transition evidence creation
        mock_evidence = TestTransitionEvidence(
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
        mock_create_evidence.return_value = [mock_evidence]

        # Create collector and collect evidence
        collector = EvidenceCollector()
        collector.collect_test_evidence(
            before_xml="before.xml",
            after_xml="after.xml",
            code_before={"file.py": "old"},
            code_after={"file.py": "new"},
        )

        # Check the evidence was collected
        assert ValidationEvidenceType.TEST_TRANSITION in collector.evidence_types
        assert len(collector.test_transitions) == 1
        assert collector.test_transitions[0] == mock_evidence

        # Check the mock was called correctly
        mock_create_evidence.assert_called_once_with("before.xml", "after.xml", {"file.py": "old"}, {"file.py": "new"})

        # Test with no transitions found
        mock_create_evidence.reset_mock()
        mock_create_evidence.return_value = []

        collector = EvidenceCollector()
        collector.collect_test_evidence(before_xml="before.xml", after_xml="after.xml")

        # Check that no evidence was added
        assert ValidationEvidenceType.TEST_TRANSITION not in collector.evidence_types
        assert len(collector.test_transitions) == 0

    @patch("chroma_mcp_client.validation.evidence_collector.create_runtime_error_evidence")
    def test_collect_runtime_error_evidence(self, mock_create_evidence):
        """Test collecting runtime error evidence."""
        # Mock the runtime error evidence creation
        mock_evidence = RuntimeErrorEvidence(
            error_id="error-123",
            error_message="IndexError: list index out of range",
            error_type="IndexError",
            first_occurrence="2023-04-15T14:30:00Z",
            stacktrace="File 'app.py', line 42\n  result = items[10]\nIndexError: list index out of range",
            resolution_timestamp="2023-04-15T15:00:00Z",
            resolution_verified=True,
            code_changes={"app.py": {"before": "old", "after": "new"}},
        )
        mock_create_evidence.return_value = [mock_evidence]

        # Create collector and collect evidence
        collector = EvidenceCollector()
        collector.collect_runtime_error_evidence(
            before_log="before.log", after_log="after.log", code_before={"app.py": "old"}, code_after={"app.py": "new"}
        )

        # Check the evidence was collected
        assert ValidationEvidenceType.RUNTIME_ERROR_RESOLUTION in collector.evidence_types
        assert len(collector.runtime_errors) == 1
        assert collector.runtime_errors[0] == mock_evidence

        # Check the mock was called correctly
        mock_create_evidence.assert_called_once_with("before.log", "after.log", {"app.py": "old"}, {"app.py": "new"})

        # Test with no errors found
        mock_create_evidence.reset_mock()
        mock_create_evidence.return_value = []

        collector = EvidenceCollector()
        collector.collect_runtime_error_evidence(before_log="before.log", after_log="after.log")

        # Check that no evidence was added
        assert ValidationEvidenceType.RUNTIME_ERROR_RESOLUTION not in collector.evidence_types
        assert len(collector.runtime_errors) == 0

    @patch("chroma_mcp_client.validation.evidence_collector.create_code_quality_evidence")
    def test_collect_code_quality_evidence(self, mock_create_evidence):
        """Test collecting code quality evidence."""
        # Mock the code quality evidence creation
        mock_evidence = CodeQualityEvidence(
            metric_type="linting",
            before_value=5.0,
            after_value=0.0,
            percentage_improvement=100.0,
            tool="ruff",
            file_path="utils.py",
            measured_at="2023-04-15T15:00:00Z",
        )
        mock_create_evidence.return_value = [mock_evidence]

        # Create collector and collect evidence
        collector = EvidenceCollector()
        before_results = {"utils.py": [{"line": 1, "column": 1, "code": "E123", "description": "Error"}]}
        after_results = {"utils.py": []}
        collector.collect_code_quality_evidence(
            before_results=before_results,
            after_results=after_results,
            tool_name="ruff",
            code_before={"utils.py": "old"},
            code_after={"utils.py": "new"},
        )

        # Check the evidence was collected
        assert ValidationEvidenceType.CODE_QUALITY_IMPROVEMENT in collector.evidence_types
        assert len(collector.code_quality) == 1
        assert collector.code_quality[0] == mock_evidence

        # Check the mock was called correctly
        mock_create_evidence.assert_called_once_with(
            before_results, after_results, "ruff", {"utils.py": "old"}, {"utils.py": "new"}
        )

        # Test with no improvements found
        mock_create_evidence.reset_mock()
        mock_create_evidence.return_value = []

        collector = EvidenceCollector()
        collector.collect_code_quality_evidence(
            before_results=before_results, after_results=after_results, tool_name="ruff"
        )

        # Check that no evidence was added
        assert ValidationEvidenceType.CODE_QUALITY_IMPROVEMENT not in collector.evidence_types
        assert len(collector.code_quality) == 0

    @patch("chroma_mcp_client.validation.evidence_collector.run_quality_check")
    def test_run_code_quality_check(self, mock_run_quality_check):
        """Test running code quality check."""
        # Mock the quality check
        mock_issues = {"utils.py": [{"line": 1, "column": 1, "code": "E123", "description": "Error"}]}
        mock_run_quality_check.return_value = (1, mock_issues)

        # Run quality check
        collector = EvidenceCollector()
        total_issues, issues = collector.run_code_quality_check(target_paths=["utils.py"], tool="ruff")

        # Check the results
        assert total_issues == 1
        assert issues == mock_issues

        # Check the mock was called correctly
        mock_run_quality_check.assert_called_once_with(["utils.py"], "ruff")

    def test_build_evidence(self):
        """Test building ValidationEvidence from collected evidence."""
        # Create a collector with various evidence items
        collector = EvidenceCollector()

        # Add test transition evidence
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
        collector.test_transitions.append(test_transition)
        collector.evidence_types.append(ValidationEvidenceType.TEST_TRANSITION)

        # Add runtime error evidence
        runtime_error = RuntimeErrorEvidence(
            error_id="error-123",
            error_message="IndexError: list index out of range",
            error_type="IndexError",
            first_occurrence="2023-04-15T14:30:00Z",
            stacktrace="File 'app.py', line 42\n  result = items[10]\nIndexError: list index out of range",
            resolution_timestamp="2023-04-15T15:00:00Z",
            resolution_verified=True,
            code_changes={"app.py": {"before": "old", "after": "new"}},
        )
        collector.runtime_errors.append(runtime_error)
        collector.evidence_types.append(ValidationEvidenceType.RUNTIME_ERROR_RESOLUTION)

        # Build evidence
        evidence = collector.build_evidence()

        # Check the evidence
        assert isinstance(evidence, ValidationEvidence)
        assert len(evidence.evidence_types) == 2
        assert ValidationEvidenceType.TEST_TRANSITION in evidence.evidence_types
        assert ValidationEvidenceType.RUNTIME_ERROR_RESOLUTION in evidence.evidence_types
        assert len(evidence.test_transitions) == 1
        assert len(evidence.runtime_errors) == 1
        assert evidence.test_transitions[0] == test_transition
        assert evidence.runtime_errors[0] == runtime_error
        assert evidence.score > 0.0

    @patch("chroma_mcp_client.validation.evidence_collector.EvidenceCollector.build_evidence")
    def test_meets_threshold(self, mock_build_evidence):
        """Test checking if evidence meets threshold."""
        # Create a mock evidence with a score above threshold
        mock_evidence = MagicMock()
        mock_evidence.meets_threshold.return_value = True
        mock_build_evidence.return_value = mock_evidence

        # Check threshold
        collector = EvidenceCollector()
        result = collector.meets_threshold()

        # Check the result
        assert result is True
        mock_evidence.meets_threshold.assert_called_once()

    @patch("chroma_mcp.utils.chroma_client.get_chroma_client")
    @patch("uuid.uuid4")
    @patch("datetime.datetime")
    def test_store_evidence(self, mock_datetime, mock_uuid, mock_get_chroma_client):
        """Test storing validation evidence in ChromaDB."""
        # Set up mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        mock_get_chroma_client.return_value = mock_client
        mock_uuid.return_value = "test-uuid"
        mock_now = MagicMock()
        mock_now.isoformat.return_value = "2023-04-15T12:00:00Z"
        mock_datetime.now.return_value = mock_now

        # Create collector with evidence
        collector = EvidenceCollector()
        test_transition = TestTransitionEvidence(
            test_id="test-123",
            test_file="tests/test_module.py",
            test_name="test_function",
            before_status="fail",
            after_status="pass",
            before_timestamp="2023-04-15T14:30:00Z",
            after_timestamp="2023-04-15T15:45:00Z",
            code_changes={"file.py": {"before": "old", "after": "new"}},
        )
        collector.test_transitions.append(test_transition)
        collector.evidence_types.append(ValidationEvidenceType.TEST_TRANSITION)

        # Mock the json method to avoid AttributeError for code_quality_improvements
        with patch.object(ValidationEvidence, "model_dump_json", return_value='{"mocked": "json"}'):
            # Store evidence
            evidence_id = collector.store_evidence(collection_name="test_collection", metadata={"chat_id": "chat-123"})

            # Check the result
            assert evidence_id == "test-uuid"

            # Verify ChromaDB interactions
            mock_get_chroma_client.assert_called_once()
            mock_client.get_collection.assert_called_once_with(name="test_collection")

            # Verify the documents were added
            mock_collection.add.assert_called_once()
            args = mock_collection.add.call_args

            # Check the arguments
            call_kwargs = args[1]
            assert len(call_kwargs["documents"]) == 1
            assert len(call_kwargs["metadatas"]) == 1
            assert len(call_kwargs["ids"]) == 1
            assert call_kwargs["ids"][0] == "test-uuid"

            # Check metadata
            metadata = call_kwargs["metadatas"][0]
            assert metadata["evidence_id"] == "test-uuid"
            assert metadata["chat_id"] == "chat-123"
            assert metadata["evidence_types"] == "test_transition"
            assert metadata["score"] == 0.7
            assert metadata["meets_threshold"] is True

            # Test with collection creation
            mock_client.reset_mock()
            mock_client.get_collection.side_effect = Exception("Collection not found")

            collector = EvidenceCollector(chroma_client=mock_client)
            collector.test_transitions.append(test_transition)
            collector.evidence_types.append(ValidationEvidenceType.TEST_TRANSITION)

            with patch.object(ValidationEvidence, "model_dump_json", return_value='{"mocked": "json"}'):
                evidence_id = collector.store_evidence()

                # Verify that create_collection was called
                mock_client.create_collection.assert_called_once_with(name="validation_evidence_v1")


@patch("chroma_mcp_client.validation.evidence_collector.EvidenceCollector")
def test_collect_and_score_evidence(mock_evidence_collector_class):
    """Test the convenience function for collecting and scoring evidence."""
    # Set up mocks
    mock_collector = MagicMock()
    mock_evidence = MagicMock()
    mock_evidence.score = 0.8
    mock_evidence.meets_threshold.return_value = True
    mock_collector.build_evidence.return_value = mock_evidence

    # Mock the run_code_quality_check to return values showing improvement
    mock_collector.run_code_quality_check.side_effect = [
        (5, {"file.py": []}),  # Before result: 5 issues
        (2, {"file.py": []}),  # After result: 2 issues (improvement)
    ]

    mock_evidence_collector_class.return_value = mock_collector

    # Call the function
    evidence, meets_threshold = collect_and_score_evidence(
        before_test_xml="before.xml",
        after_test_xml="after.xml",
        before_error_log="before.log",
        after_error_log="after.log",
        target_paths=["src"],
        quality_tool="ruff",
        chat_id="chat-123",
    )

    # Check the results
    assert evidence == mock_evidence
    assert meets_threshold is True

    # Verify collector methods were called
    mock_collector.collect_test_evidence.assert_called_once()
    mock_collector.collect_runtime_error_evidence.assert_called_once()
    mock_collector.run_code_quality_check.assert_called()
    mock_collector.collect_code_quality_evidence.assert_called_once()
    mock_collector.build_evidence.assert_called_once()
    mock_collector.store_evidence.assert_called_once()
