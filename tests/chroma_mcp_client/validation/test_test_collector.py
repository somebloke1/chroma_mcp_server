"""
Unit tests for the test collector module.

Tests the functionality for parsing JUnit XML output, storing test results,
and creating test transition evidence.
"""

import os
import tempfile
import pytest
import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock

from chroma_mcp_client.validation.test_collector import (
    parse_junit_xml,
    store_test_results,
    create_test_transition_evidence,
)


@pytest.fixture
def sample_junit_xml():
    """Create a sample JUnit XML file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(
            """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="3" errors="0" failures="1" skipped="1">
    <testcase classname="tests.test_module" name="test_success" time="0.123">
    </testcase>
    <testcase classname="tests.test_module" name="test_failure" time="0.456">
      <failure message="AssertionError: Failed test">
        File "tests/test_module.py", line 42
        AssertionError: Failed test
      </failure>
    </testcase>
    <testcase classname="tests.test_module" name="test_skip" time="0.001">
      <skipped message="Skip reason">
        Skipped test
      </skipped>
    </testcase>
  </testsuite>
</testsuites>
"""
        )
        f.flush()
        return f.name


def test_parse_junit_xml(sample_junit_xml):
    """Test parsing a JUnit XML file."""
    result = parse_junit_xml(sample_junit_xml)

    # Check that we got the right number of test results
    assert len(result) == 3

    # Check individual test results
    assert "tests.test_module.test_success" in result
    assert result["tests.test_module.test_success"]["status"] == "pass"
    assert float(result["tests.test_module.test_success"]["time"]) == 0.123

    assert "tests.test_module.test_failure" in result
    assert result["tests.test_module.test_failure"]["status"] == "fail"
    assert float(result["tests.test_module.test_failure"]["time"]) == 0.456
    assert "AssertionError: Failed test" in result["tests.test_module.test_failure"]["error_message"]

    assert "tests.test_module.test_skip" in result
    assert result["tests.test_module.test_skip"]["status"] == "skip"


def test_parse_junit_xml_missing_file():
    """Test parsing with a missing file."""
    with pytest.raises(FileNotFoundError):
        parse_junit_xml("/nonexistent/path/to/tests.xml")


def test_parse_junit_xml_derives_file_from_classname():
    """Test that file paths are derived from classnames if not provided."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(
            """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest">
    <testcase classname="package.submodule.test_class" name="test_method" time="0.123">
    </testcase>
  </testsuite>
</testsuites>
"""
        )
        f.flush()
        path = f.name

    try:
        result = parse_junit_xml(path)
        assert result["package.submodule.test_class.test_method"]["test_file"] == "package/submodule/test_class.py"
    finally:
        os.unlink(path)


@pytest.fixture
def mock_chroma_client():
    """Create a mock Chroma client for testing."""
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.get_collection.return_value = mock_collection

    return mock_client, mock_collection


def test_store_test_results(mock_chroma_client):
    """Test storing test results in ChromaDB."""
    mock_client, mock_collection = mock_chroma_client

    # Sample test results with correct fields as expected by the implementation
    test_results = {
        "tests.test_module.test_1": {
            "test_id": "tests.test_module.test_1",
            "test_name": "test_1",
            "test_file": "tests/test_module.py",
            "status": "pass",
            "time": 0.1,
            "error_message": None,
        },
        "tests.test_module.test_2": {
            "test_id": "tests.test_module.test_2",
            "test_name": "test_2",
            "test_file": "tests/test_module.py",
            "status": "fail",
            "time": 0.2,
            "error_message": "Failed",
        },
    }

    # Call the function
    with patch("uuid.uuid4", return_value="test-uuid"):
        result = store_test_results(
            results_dict=test_results, collection_name="test_results_v1", chroma_client=mock_client
        )

    # Check the result
    assert result == "test-uuid"

    # Verify the mock was called correctly
    mock_client.get_collection.assert_called_once_with(name="test_results_v1")

    # Check add was called on the collection
    mock_collection.add.assert_called_once()

    # Verify the documents and metadata were prepared correctly
    call_kwargs = mock_collection.add.call_args[1]

    # Check we have 2 documents
    assert len(call_kwargs["documents"]) == 2
    assert len(call_kwargs["metadatas"]) == 2
    assert len(call_kwargs["ids"]) == 2


def test_create_test_transition_evidence(sample_junit_xml):
    """Test creating evidence from test transitions."""
    # Create a second JUnit XML with different results (fixed test_failure)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(
            """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="3" errors="0" failures="0" skipped="1">
    <testcase classname="tests.test_module" name="test_success" time="0.123">
    </testcase>
    <testcase classname="tests.test_module" name="test_failure" time="0.456">
      <!-- This test is now passing -->
    </testcase>
    <testcase classname="tests.test_module" name="test_skip" time="0.001">
      <skipped message="Skip reason">
        Skipped test
      </skipped>
    </testcase>
  </testsuite>
</testsuites>
"""
        )
        f.flush()
        after_xml = f.name

    try:
        # Create test transition evidence
        transitions = create_test_transition_evidence(
            before_xml=sample_junit_xml, after_xml=after_xml, commit_before="abc123", commit_after="def456"
        )

        # Check we got the expected transitions
        assert len(transitions) == 1

        # Verify the transition details
        transition = transitions[0]
        assert transition.test_id == "tests.test_module.test_failure"
        assert transition.before_status == "fail"
        assert transition.after_status == "pass"
        assert "AssertionError: Failed test" in transition.error_message_before
        assert transition.error_message_after is None

        # Check code changes was populated
        assert len(transition.code_changes) > 0
    finally:
        os.unlink(after_xml)


def test_create_test_transition_evidence_no_transitions():
    """Test creating evidence when there are no relevant transitions."""
    # Create two identical XML files
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f1:
        f1.write(
            """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1" errors="0" failures="0" skipped="0">
    <testcase classname="tests.test_module" name="test_success" time="0.123">
    </testcase>
  </testsuite>
</testsuites>
"""
        )
        f1.flush()
        xml1 = f1.name

    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f2:
        f2.write(
            """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1" errors="0" failures="0" skipped="0">
    <testcase classname="tests.test_module" name="test_success" time="0.124">
    </testcase>
  </testsuite>
</testsuites>
"""
        )
        f2.flush()
        xml2 = f2.name

    try:
        # Create test transition evidence
        transitions = create_test_transition_evidence(before_xml=xml1, after_xml=xml2)

        # Check we got no transitions (all tests still pass)
        assert len(transitions) == 0
    finally:
        os.unlink(xml1)
        os.unlink(xml2)
