"""Tests for the validation schemas used in error-driven learning."""

import pytest
from pydantic import ValidationError

from chroma_mcp_client.validation.schemas import (
    ValidationEvidenceType,
    TestTransitionEvidence,
    RuntimeErrorEvidence,
    CodeQualityEvidence,
    ValidationEvidence,
    calculate_validation_score,
)


class TestValidationSchemas:
    """Test cases for the validation schemas."""

    def test_test_transition_evidence_schema(self):
        """Test creating and validating TestTransitionEvidence objects."""
        # Valid test transition evidence
        evidence = TestTransitionEvidence(
            test_id="test-123",
            test_file="tests/test_module.py",
            test_name="test_function_handles_edge_case",
            before_status="fail",
            after_status="pass",
            before_timestamp="2023-04-15T14:30:00Z",
            after_timestamp="2023-04-15T15:45:00Z",
            error_message_before="AssertionError: Expected 42, got None",
            code_changes={
                "src/module.py": {
                    "before": "def function(value):\n    return None",
                    "after": "def function(value):\n    return 42 if value > 0 else None",
                }
            },
        )

        assert evidence.test_id == "test-123"
        assert evidence.before_status == "fail"
        assert evidence.after_status == "pass"
        assert "src/module.py" in evidence.code_changes

        # Invalid test transition - missing required fields
        with pytest.raises(ValidationError):
            TestTransitionEvidence(
                test_id="test-123",
                # Missing test_file
                test_name="test_function",
                before_status="fail",
                after_status="pass",
                before_timestamp="2023-04-15T14:30:00Z",
                after_timestamp="2023-04-15T15:45:00Z",
            )

    def test_runtime_error_evidence_schema(self):
        """Test creating and validating RuntimeErrorEvidence objects."""
        # Valid runtime error evidence
        evidence = RuntimeErrorEvidence(
            error_message="IndexError: list index out of range",
            error_type="IndexError",
            timestamp="2023-04-15T14:30:00Z",
            stacktrace="File 'app.py', line 42\n  result = items[10]\nIndexError: list index out of range",
            resolved=True,
            resolution_timestamp="2023-04-15T15:00:00Z",
            code_changes={
                "app.py": {
                    "before": "result = items[10]",
                    "after": "if len(items) > 10:\n    result = items[10]\nelse:\n    result = None",
                }
            },
        )

        assert evidence.error_type == "IndexError"
        assert evidence.resolved is True
        assert "app.py" in evidence.code_changes

        # Invalid runtime error - missing required fields
        with pytest.raises(ValidationError):
            RuntimeErrorEvidence(
                # Missing error_message
                error_type="TypeError",
                timestamp="2023-04-15T14:30:00Z",
            )

    def test_code_quality_evidence_schema(self):
        """Test creating and validating CodeQualityEvidence objects."""
        # Valid code quality evidence
        evidence = CodeQualityEvidence(
            quality_type="linting",
            tool="ruff",
            before_issues=5,
            after_issues=0,
            before_timestamp="2023-04-15T14:30:00Z",
            after_timestamp="2023-04-15T15:00:00Z",
            code_changes={
                "utils.py": {"before": "def func(x,y):\n  return x+y", "after": "def func(x, y):\n    return x + y"}
            },
        )

        assert evidence.quality_type == "linting"
        assert evidence.before_issues == 5
        assert evidence.after_issues == 0
        assert "utils.py" in evidence.code_changes

        # Invalid code quality evidence - missing required fields
        with pytest.raises(ValidationError):
            CodeQualityEvidence(
                quality_type="linting",
                # Missing tool
                before_issues=5,
                after_issues=0,
                before_timestamp="2023-04-15T14:30:00Z",
                after_timestamp="2023-04-15T15:00:00Z",
            )

    def test_validation_evidence_schema(self):
        """Test creating and validating ValidationEvidence objects."""
        # Create test transition evidence
        test_transition = TestTransitionEvidence(
            test_id="test-123",
            test_file="tests/test_module.py",
            test_name="test_function_handles_edge_case",
            before_status="fail",
            after_status="pass",
            before_timestamp="2023-04-15T14:30:00Z",
            after_timestamp="2023-04-15T15:45:00Z",
            error_message_before="AssertionError: Expected 42, got None",
            code_changes={
                "src/module.py": {
                    "before": "def function(value):\n    return None",
                    "after": "def function(value):\n    return 42 if value > 0 else None",
                }
            },
        )

        # Valid validation evidence
        evidence = ValidationEvidence(
            evidence_types=[ValidationEvidenceType.TEST_TRANSITION], score=0.0, test_transitions=[test_transition]
        )

        assert ValidationEvidenceType.TEST_TRANSITION in evidence.evidence_types
        assert len(evidence.test_transitions) == 1
        assert evidence.test_transitions[0].test_id == "test-123"

        # Recalculate score
        score = calculate_validation_score(evidence)
        assert score > 0, "Test transition should yield a positive validation score"

        # Test with multiple evidence types
        runtime_error = RuntimeErrorEvidence(
            error_message="IndexError: list index out of range",
            error_type="IndexError",
            timestamp="2023-04-15T14:30:00Z",
            stacktrace="File 'app.py', line 42\n  result = items[10]\nIndexError: list index out of range",
            resolved=True,
            resolution_timestamp="2023-04-15T15:00:00Z",
            code_changes={
                "app.py": {
                    "before": "result = items[10]",
                    "after": "if len(items) > 10:\n    result = items[10]\nelse:\n    result = None",
                }
            },
        )

        combined_evidence = ValidationEvidence(
            evidence_types=[ValidationEvidenceType.TEST_TRANSITION, ValidationEvidenceType.RUNTIME_ERROR_RESOLUTION],
            score=0.0,
            test_transitions=[test_transition],
            runtime_errors=[runtime_error],
        )

        combined_score = calculate_validation_score(combined_evidence)
        assert combined_score > score, "Combined evidence should yield a higher score than single evidence"

        # Test threshold checking
        combined_evidence.score = combined_score
        assert combined_evidence.meets_threshold(), "Combined evidence should meet the threshold"

        # Test with low score
        low_evidence = ValidationEvidence(evidence_types=[ValidationEvidenceType.CODE_QUALITY_IMPROVEMENT], score=0.1)
        assert not low_evidence.meets_threshold(), "Low score evidence should not meet the threshold"

    def test_score_calculation(self):
        """Test the calculate_validation_score function."""
        # Empty evidence
        empty_evidence = ValidationEvidence(evidence_types=[], score=0.0)
        assert calculate_validation_score(empty_evidence) == 0.0

        # Test transition: fail -> pass (highest value)
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

        evidence = ValidationEvidence(
            evidence_types=[ValidationEvidenceType.TEST_TRANSITION], score=0.0, test_transitions=[test_transition]
        )

        score = calculate_validation_score(evidence)
        assert score >= 0.7, "Test fail->pass transition should score highly"

        # Test transition: error -> pass (also high value)
        test_transition.before_status = "error"
        score = calculate_validation_score(evidence)
        assert score >= 0.7, "Test error->pass transition should score highly"

        # Runtime error resolution (high value)
        runtime_error = RuntimeErrorEvidence(
            error_message="Error message",
            error_type="TypeError",
            timestamp="2023-04-15T14:30:00Z",
            resolved=True,
            resolution_timestamp="2023-04-15T15:00:00Z",
            code_changes={"file.py": {"before": "old", "after": "new"}},
        )

        evidence = ValidationEvidence(
            evidence_types=[ValidationEvidenceType.RUNTIME_ERROR_RESOLUTION], score=0.0, runtime_errors=[runtime_error]
        )

        score = calculate_validation_score(evidence)
        assert score >= 0.6, "Runtime error resolution should score well"

        # Code quality improvement (moderate value)
        code_quality = CodeQualityEvidence(
            quality_type="linting",
            tool="ruff",
            before_issues=10,
            after_issues=0,
            before_timestamp="2023-04-15T14:30:00Z",
            after_timestamp="2023-04-15T15:00:00Z",
            code_changes={"file.py": {"before": "old", "after": "new"}},
        )

        evidence = ValidationEvidence(
            evidence_types=[ValidationEvidenceType.CODE_QUALITY_IMPROVEMENT],
            score=0.0,
            code_quality_improvements=[code_quality],
        )

        score = calculate_validation_score(evidence)
        assert 0.3 <= score <= 0.6, "Code quality improvement should score moderately"

        # Minor code quality improvement (lower value)
        code_quality.before_issues = 3
        code_quality.after_issues = 2
        score = calculate_validation_score(evidence)
        assert score < 0.4, "Minor code quality improvement should score lower"

        # Combined evidence (should get highest values)
        combined_evidence = ValidationEvidence(
            evidence_types=[
                ValidationEvidenceType.TEST_TRANSITION,
                ValidationEvidenceType.RUNTIME_ERROR_RESOLUTION,
                ValidationEvidenceType.CODE_QUALITY_IMPROVEMENT,
            ],
            score=0.0,
            test_transitions=[test_transition],
            runtime_errors=[runtime_error],
            code_quality_improvements=[code_quality],
        )

        score = calculate_validation_score(combined_evidence)
        assert score > 0.8, "Combined significant evidence should score very highly"
