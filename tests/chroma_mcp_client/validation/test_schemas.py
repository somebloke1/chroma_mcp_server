"""
Unit tests for the validation schemas.

Tests the evidence schemas and validation scoring mechanisms.
"""

import pytest
from pydantic import ValidationError
from datetime import datetime

from chroma_mcp_client.validation.schemas import (
    TestTransitionEvidence,
    RuntimeErrorEvidence,
    CodeQualityEvidence,
    ValidationEvidence,
    ValidationEvidenceType,
    calculate_validation_score,
)


class TestTestTransitionEvidence:
    """Tests for TestTransitionEvidence schema."""

    def test_create_valid_instance(self):
        """Test creating a valid TestTransitionEvidence instance."""
        evidence = TestTransitionEvidence(
            test_id="tests.test_module.test_function",
            test_file="tests/test_module.py",
            test_name="test_function",
            before_status="fail",
            after_status="pass",
            before_timestamp=datetime.now().isoformat(),
            after_timestamp=datetime.now().isoformat(),
            error_message_before="AssertionError: test failed",
            code_changes={"src/module.py": {"before": "# Code before change", "after": "# Code after change"}},
        )

        assert evidence.test_id == "tests.test_module.test_function"
        assert evidence.test_file == "tests/test_module.py"
        assert evidence.test_name == "test_function"
        assert evidence.before_status == "fail"
        assert evidence.after_status == "pass"
        assert evidence.error_message_before == "AssertionError: test failed"
        assert evidence.error_message_after is None
        assert "src/module.py" in evidence.code_changes

    def test_missing_required_fields(self):
        """Test validation for missing required fields."""
        with pytest.raises(ValidationError):
            TestTransitionEvidence(
                test_id="tests.test_module.test_function",
                before_status="fail",
                after_status="pass",
                # Missing required fields
            )

    def test_valid_status_values(self):
        """Test validation with valid status values.

        Note: The current implementation does not validate status values
        against a fixed set, so we test that various status values are accepted.
        """
        # Test with various valid status values to ensure they're accepted
        evidence = TestTransitionEvidence(
            test_id="tests.test_module.test_function",
            test_file="tests/test_module.py",
            test_name="test_function",
            before_status="fail",  # Valid status
            after_status="pass",  # Valid status
            before_timestamp=datetime.now().isoformat(),
            after_timestamp=datetime.now().isoformat(),
            code_changes={"src/module.py": {"before": "# Code before change", "after": "# Code after change"}},
        )
        assert evidence.before_status == "fail"
        assert evidence.after_status == "pass"

        # Test with other valid status values
        evidence2 = TestTransitionEvidence(
            test_id="tests.test_module.test_function",
            test_file="tests/test_module.py",
            test_name="test_function",
            before_status="error",  # Valid status
            after_status="skip",  # Valid status
            before_timestamp=datetime.now().isoformat(),
            after_timestamp=datetime.now().isoformat(),
            code_changes={"src/module.py": {"before": "# Code before change", "after": "# Code after change"}},
        )
        assert evidence2.before_status == "error"
        assert evidence2.after_status == "skip"


class TestRuntimeErrorEvidence:
    """Tests for RuntimeErrorEvidence schema."""

    def test_create_valid_instance(self):
        """Test creating a valid RuntimeErrorEvidence instance."""
        evidence = RuntimeErrorEvidence(
            error_type="ValueError",
            error_message="Invalid value",
            stacktrace="Traceback (most recent call last):\n  File 'test.py', line 10",
            timestamp=datetime.now().isoformat(),
            code_changes={"src/module.py": {"before": "# Code before change", "after": "# Code after change"}},
        )

        assert evidence.error_type == "ValueError"
        assert evidence.error_message == "Invalid value"
        assert evidence.stacktrace == "Traceback (most recent call last):\n  File 'test.py', line 10"
        assert "src/module.py" in evidence.code_changes

    def test_auto_generated_fields(self):
        """Test that certain fields are auto-generated if not provided."""
        evidence = RuntimeErrorEvidence(
            error_type="ValueError",
            error_message="Invalid value",
            code_changes={"src/module.py": {"before": "# Code before change", "after": "# Code after change"}},
        )

        assert evidence.error_id is not None
        assert evidence.first_occurrence is not None
        assert evidence.resolved is False
        assert evidence.resolution_verified is False


class TestCodeQualityEvidence:
    """Tests for CodeQualityEvidence schema."""

    def test_create_valid_instance(self):
        """Test creating a valid CodeQualityEvidence instance."""
        evidence = CodeQualityEvidence(
            metric_type="coverage",
            tool="pytest-cov",
            before_value=75.5,
            after_value=92.3,
            percentage_improvement=22.25,  # (92.3-75.5)/75.5*100
            file_path="src/module.py",
            measured_at=datetime.now().isoformat(),
        )

        assert evidence.metric_type == "coverage"
        assert evidence.tool == "pytest-cov"
        assert evidence.before_value == 75.5
        assert evidence.after_value == 92.3
        assert evidence.percentage_improvement == 22.25
        assert evidence.file_path == "src/module.py"

    def test_auto_calculated_improvement(self):
        """Test that percentage improvement is auto-calculated if not provided."""
        evidence = CodeQualityEvidence(
            metric_type="complexity", tool="radon", before_value=10.0, after_value=5.0, file_path="src/module.py"
        )

        # Should calculate (10-5)/10 * 100 = 50%
        assert evidence.percentage_improvement == 50.0

    def test_legacy_fields_conversion(self):
        """Test that legacy fields are properly converted."""
        evidence = CodeQualityEvidence(
            quality_type="maintainability",  # Legacy field
            tool="pylint",
            before_issues=20,  # Legacy field
            after_issues=5,  # Legacy field
            file_path="src/module.py",
        )

        assert evidence.metric_type == "maintainability"  # Converted from quality_type
        assert evidence.before_value == 20.0  # Converted from before_issues
        assert evidence.after_value == 5.0  # Converted from after_issues
        assert evidence.percentage_improvement == 75.0  # Calculated from converted values


class TestValidationEvidence:
    """Tests for ValidationEvidence schema."""

    def test_create_valid_instance(self):
        """Test creating a valid ValidationEvidence instance."""
        # Create test transitions
        test_transition = TestTransitionEvidence(
            test_id="tests.test_module.test_function",
            test_file="tests/test_module.py",
            test_name="test_function",
            before_status="fail",
            after_status="pass",
            before_timestamp=datetime.now().isoformat(),
            after_timestamp=datetime.now().isoformat(),
            error_message_before="AssertionError: test failed",
            code_changes={"src/module.py": {"before": "# Code before change", "after": "# Code after change"}},
        )

        # Create code quality evidence
        code_quality = CodeQualityEvidence(
            metric_type="complexity", tool="radon", before_value=10.0, after_value=5.0, file_path="src/module.py"
        )

        # Create validation evidence
        evidence = ValidationEvidence(
            evidence_types=[ValidationEvidenceType.TEST_TRANSITION, ValidationEvidenceType.CODE_QUALITY_IMPROVEMENT],
            score=0.8,
            test_transitions=[test_transition],
            code_quality_improvements=[code_quality],
        )

        assert ValidationEvidenceType.TEST_TRANSITION in evidence.evidence_types
        assert ValidationEvidenceType.CODE_QUALITY_IMPROVEMENT in evidence.evidence_types
        assert evidence.score == 0.8
        assert len(evidence.test_transitions) == 1
        assert len(evidence.code_quality_improvements) == 1

    def test_backwards_compatibility(self):
        """Test backwards compatibility with the code_quality property."""
        evidence = ValidationEvidence(
            evidence_types=[ValidationEvidenceType.CODE_QUALITY_IMPROVEMENT],
            score=0.5,
            code_quality_improvements=[
                CodeQualityEvidence(
                    metric_type="complexity",
                    tool="radon",
                    before_value=10.0,
                    after_value=5.0,
                    file_path="src/module.py",
                )
            ],
        )

        # code_quality should be an alias for code_quality_improvements
        assert evidence.code_quality is evidence.code_quality_improvements
        assert len(evidence.code_quality) == 1

    def test_meets_threshold(self):
        """Test the meets_threshold method."""
        evidence = ValidationEvidence(evidence_types=[ValidationEvidenceType.TEST_TRANSITION], score=0.75)

        assert evidence.meets_threshold(threshold=0.7) is True
        assert evidence.meets_threshold(threshold=0.8) is False


def test_calculate_validation_score():
    """Test the calculate_validation_score function."""
    # Create test transitions
    test_transition = TestTransitionEvidence(
        test_id="tests.test_module.test_function",
        test_file="tests/test_module.py",
        test_name="test_function",
        before_status="fail",
        after_status="pass",
        before_timestamp=datetime.now().isoformat(),
        after_timestamp=datetime.now().isoformat(),
        error_message_before="AssertionError: test failed",
        code_changes={"src/module.py": {"before": "# Code before change", "after": "# Code after change"}},
    )

    # Create evidence with a test transition
    evidence = ValidationEvidence(
        evidence_types=[ValidationEvidenceType.TEST_TRANSITION],
        score=0.0,  # Will be calculated
        test_transitions=[test_transition],
    )

    score = calculate_validation_score(evidence)

    # Expected score based on weights in calculate_validation_score
    assert score == 0.7  # Weight for TEST_TRANSITION (from actual implementation)

    # Test with multiple evidence types
    code_quality = CodeQualityEvidence(
        metric_type="complexity", tool="radon", before_value=10.0, after_value=5.0, file_path="src/module.py"
    )

    evidence = ValidationEvidence(
        evidence_types=[ValidationEvidenceType.TEST_TRANSITION, ValidationEvidenceType.CODE_QUALITY_IMPROVEMENT],
        score=0.0,  # Will be calculated
        test_transitions=[test_transition],
        code_quality_improvements=[code_quality],
    )

    score = calculate_validation_score(evidence)

    # Expected combined score (TEST_TRANSITION + CODE_QUALITY_IMPROVEMENT)
    # Should be at least 0.7 (test) + 0.32 (quality * 0.8)
    assert score >= 1.0  # Capped at 1.0

    # Test with no successful transitions
    evidence = ValidationEvidence(
        evidence_types=[ValidationEvidenceType.TEST_TRANSITION],
        score=0.0,
        test_transitions=[
            TestTransitionEvidence(
                test_id="tests.test_module.test_function",
                test_file="tests/test_module.py",
                test_name="test_function",
                before_status="pass",  # Already passing, not a transition that counts
                after_status="pass",
                before_timestamp=datetime.now().isoformat(),
                after_timestamp=datetime.now().isoformat(),
                code_changes={"src/module.py": {"before": "# No real change", "after": "# No real change"}},
            )
        ],
    )

    score = calculate_validation_score(evidence)
    assert score == 0.0
