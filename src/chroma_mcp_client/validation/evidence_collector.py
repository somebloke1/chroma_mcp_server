"""
Combined evidence collection module for the validation system.

This module provides unified interfaces to:
1. Collect test transition evidence
2. Collect runtime error resolution evidence
3. Collect code quality improvement evidence
4. Calculate and store validation scores for code changes
"""

import os
import uuid
import datetime
import json
from typing import Dict, List, Optional, Any, Tuple, Union

from .schemas import (
    ValidationEvidenceType,
    ValidationEvidence,
    TestTransitionEvidence,
    RuntimeErrorEvidence,
    CodeQualityEvidence,
    calculate_validation_score,
)
from .test_collector import create_test_transition_evidence, store_test_results
from .runtime_collector import create_runtime_error_evidence, store_runtime_errors
from .code_quality_collector import create_code_quality_evidence, run_quality_check


def collect_validation_evidence(
    test_transitions: List[TestTransitionEvidence] = None,
    runtime_errors: List[RuntimeErrorEvidence] = None,
    code_quality_improvements: List[CodeQualityEvidence] = None,
) -> ValidationEvidence:
    """
    Collect and combine multiple forms of validation evidence.

    Args:
        test_transitions: List of test transition evidence
        runtime_errors: List of runtime error resolution evidence
        code_quality_improvements: List of code quality improvement evidence

    Returns:
        A ValidationEvidence object combining all evidence types
    """
    # Initialize lists
    if test_transitions is None:
        test_transitions = []
    if runtime_errors is None:
        runtime_errors = []
    if code_quality_improvements is None:
        code_quality_improvements = []

    # Determine evidence types
    evidence_types = []
    if test_transitions:
        evidence_types.append(ValidationEvidenceType.TEST_TRANSITION)
    if runtime_errors:
        evidence_types.append(ValidationEvidenceType.RUNTIME_ERROR_RESOLUTION)
    if code_quality_improvements:
        evidence_types.append(ValidationEvidenceType.CODE_QUALITY_IMPROVEMENT)

    # Create the evidence object
    evidence = ValidationEvidence(
        id=str(uuid.uuid4()),
        score=0.0,  # Will be calculated
        evidence_types=evidence_types,
        test_transitions=test_transitions,
        runtime_errors=runtime_errors,
        code_quality_improvements=code_quality_improvements,
    )

    # Calculate the score using schema-defined method
    evidence.score = calculate_validation_score(evidence)

    return evidence


class EvidenceCollector:
    """
    Main class for collecting, scoring, and storing validation evidence
    from multiple sources.
    """

    def __init__(self, chroma_client=None):
        """
        Initialize the evidence collector.

        Args:
            chroma_client: Optional ChromaDB client
        """
        self.chroma_client = chroma_client
        self.evidence_types = []
        self.test_transitions = []
        self.runtime_errors = []
        self.code_quality = []
        self.knowledge_gap_resolutions = []
        self.security_fixes = []
        self.performance_improvements = []

    def collect_test_evidence(
        self,
        before_xml: str,
        after_xml: str,
        code_before: Optional[Dict[str, str]] = None,
        code_after: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Collect evidence from test transitions.

        Args:
            before_xml: Path to JUnit XML before changes
            after_xml: Path to JUnit XML after changes
            code_before: Optional dictionary of code before changes
            code_after: Optional dictionary of code after changes
        """
        transitions = create_test_transition_evidence(before_xml, after_xml, code_before, code_after)

        if transitions:
            self.evidence_types.append(ValidationEvidenceType.TEST_TRANSITION)
            self.test_transitions.extend(transitions)

    def collect_runtime_error_evidence(
        self,
        before_log: str,
        after_log: str,
        code_before: Optional[Dict[str, str]] = None,
        code_after: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Collect evidence from runtime error resolutions.

        Args:
            before_log: Path to error log before changes
            after_log: Path to error log after changes
            code_before: Optional dictionary of code before changes
            code_after: Optional dictionary of code after changes
        """
        errors = create_runtime_error_evidence(before_log, after_log, code_before, code_after)

        if errors:
            self.evidence_types.append(ValidationEvidenceType.RUNTIME_ERROR_RESOLUTION)
            self.runtime_errors.extend(errors)

    def collect_code_quality_evidence(
        self,
        before_results: Dict[str, List[Dict[str, Any]]],
        after_results: Dict[str, List[Dict[str, Any]]],
        tool_name: str,
        code_before: Optional[Dict[str, str]] = None,
        code_after: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Collect evidence from code quality improvements.

        Args:
            before_results: Quality issues before changes
            after_results: Quality issues after changes
            tool_name: Name of the quality tool used
            code_before: Optional dictionary of code before changes
            code_after: Optional dictionary of code after changes
        """
        improvements = create_code_quality_evidence(before_results, after_results, tool_name, code_before, code_after)

        if improvements:
            self.evidence_types.append(ValidationEvidenceType.CODE_QUALITY_IMPROVEMENT)
            self.code_quality.extend(improvements)

    def run_code_quality_check(
        self, target_paths: List[str], tool: str = "ruff"
    ) -> Tuple[int, Dict[str, List[Dict[str, Any]]]]:
        """
        Run a code quality check.

        Args:
            target_paths: List of file or directory paths to analyze
            tool: Tool name ('ruff', 'pylint', etc.)

        Returns:
            Tuple of (total issues count, issues dictionary)
        """
        return run_quality_check(target_paths, tool)

    def build_evidence(self) -> ValidationEvidence:
        """
        Build a ValidationEvidence object from all collected evidence.

        Returns:
            ValidationEvidence object
        """
        evidence = ValidationEvidence(
            evidence_types=self.evidence_types,
            score=0.0,
            test_transitions=self.test_transitions,
            runtime_errors=self.runtime_errors,
            code_quality=self.code_quality,
            knowledge_gap_resolutions=self.knowledge_gap_resolutions,
            security_fixes=self.security_fixes,
            performance_improvements=self.performance_improvements,
        )

        # Calculate validation score
        evidence.score = calculate_validation_score(evidence)

        return evidence

    def meets_threshold(self) -> bool:
        """
        Check if the current evidence meets the promotion threshold.

        Returns:
            True if the evidence meets the threshold, False otherwise
        """
        evidence = self.build_evidence()
        return evidence.meets_threshold()

    def store_evidence(
        self, collection_name: str = "validation_evidence_v1", metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store validation evidence in ChromaDB.

        Args:
            collection_name: ChromaDB collection name
            metadata: Optional additional metadata

        Returns:
            ID of the stored evidence
        """
        # Import here to avoid circular imports
        from chroma_mcp.utils.chroma_client import get_chroma_client

        if self.chroma_client is None:
            self.chroma_client = get_chroma_client()

        # Ensure collection exists
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
        except Exception:
            collection = self.chroma_client.create_collection(name=collection_name)

        # Build evidence and get score
        evidence = self.build_evidence()

        # Generate evidence ID
        evidence_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()

        # Prepare document and metadata
        document = evidence.model_dump_json()

        # Convert evidence types to simple strings without enum prefix
        evidence_type_strings = [t.value for t in evidence.evidence_types]

        base_metadata = {
            "evidence_id": evidence_id,
            "timestamp": timestamp,
            "score": evidence.score,
            "meets_threshold": evidence.meets_threshold(),
            "evidence_types": evidence_type_strings,
            "test_transition_count": len(evidence.test_transitions or []),
            "runtime_error_count": len(evidence.runtime_errors or []),
            "code_quality_count": len(evidence.code_quality or []),
        }

        # Combine with provided metadata if any
        if metadata:
            base_metadata.update(metadata)

        # Store in collection
        collection.add(documents=[document], metadatas=[base_metadata], ids=[evidence_id])

        return evidence_id


def collect_and_score_evidence(
    before_test_xml: Optional[str] = None,
    after_test_xml: Optional[str] = None,
    before_error_log: Optional[str] = None,
    after_error_log: Optional[str] = None,
    target_paths: Optional[List[str]] = None,
    quality_tool: str = "ruff",
    code_before: Optional[Dict[str, str]] = None,
    code_after: Optional[Dict[str, str]] = None,
    chat_id: Optional[str] = None,
    file_changes: Optional[List[str]] = None,
) -> Tuple[ValidationEvidence, bool]:
    """
    Convenience function to collect and score all types of evidence.

    Args:
        before_test_xml: Path to JUnit XML before changes
        after_test_xml: Path to JUnit XML after changes
        before_error_log: Path to error log before changes
        after_error_log: Path to error log after changes
        target_paths: List of file paths for quality checks
        quality_tool: Quality tool name
        code_before: Dictionary of code before changes
        code_after: Dictionary of code after changes
        chat_id: Optional chat ID related to the changes
        file_changes: Optional list of file paths that were changed

    Returns:
        Tuple of (ValidationEvidence, meets_threshold)
    """
    collector = EvidenceCollector()

    # Collect test evidence if available
    if before_test_xml and after_test_xml:
        collector.collect_test_evidence(before_test_xml, after_test_xml, code_before, code_after)

    # Collect runtime error evidence if available
    if before_error_log and after_error_log:
        collector.collect_runtime_error_evidence(before_error_log, after_error_log, code_before, code_after)

    # Collect code quality evidence if target paths available
    if target_paths:
        before_issues_count, before_issues = collector.run_code_quality_check(target_paths, quality_tool)
        after_issues_count, after_issues = collector.run_code_quality_check(target_paths, quality_tool)

        if before_issues_count > after_issues_count:
            collector.collect_code_quality_evidence(before_issues, after_issues, quality_tool, code_before, code_after)

    # Build evidence and check threshold
    evidence = collector.build_evidence()
    meets_threshold = evidence.meets_threshold()

    # Store if meets threshold and chat_id provided
    if meets_threshold and chat_id:
        metadata = {"chat_id": chat_id, "file_changes": file_changes or []}
        collector.store_evidence(metadata=metadata)

    return evidence, meets_threshold


def store_validation_evidence(
    evidence: ValidationEvidence,
    collection_name: str = "validation_evidence_v1",
    chat_id: Optional[str] = None,
    chroma_client=None,
) -> str:
    """
    Store validation evidence in ChromaDB.

    Args:
        evidence: ValidationEvidence object
        collection_name: ChromaDB collection name
        chat_id: Optional chat ID for metadata
        chroma_client: Optional ChromaDB client

    Returns:
        ID of the stored evidence
    """
    # Import here to avoid circular imports
    try:
        from chroma_mcp.utils.chroma_client import get_chroma_client

        if chroma_client is None:
            chroma_client = get_chroma_client()
    except ImportError:
        # Support using the client passed directly
        if chroma_client is None:
            raise ValueError("ChromaDB client is required")

    # Ensure collection exists
    try:
        collection = chroma_client.get_collection(name=collection_name)
    except Exception:
        collection = chroma_client.get_or_create_collection(name=collection_name)

    # Generate evidence ID if not present
    evidence_id = getattr(evidence, "id", None) or str(uuid.uuid4())
    timestamp = datetime.datetime.now().isoformat()

    # Prepare document and metadata
    document = evidence.model_dump_json()

    # Convert evidence types to simple strings without enum prefix
    evidence_type_strings = [t.value for t in evidence.evidence_types]

    metadata = {
        "evidence_id": evidence_id,
        "timestamp": timestamp,
        "score": evidence.score,
        "meets_threshold": evidence.meets_threshold(),
        "evidence_types": evidence_type_strings,
        "test_transition_count": len(evidence.test_transitions or []),
        "runtime_error_count": len(evidence.runtime_errors or []),
        "code_quality_count": len(evidence.code_quality_improvements or []),
    }

    # Add chat ID if provided
    if chat_id:
        metadata["chat_id"] = chat_id

    # Store in collection
    collection.add(documents=[document], metadatas=[metadata], ids=[evidence_id])

    return evidence_id
