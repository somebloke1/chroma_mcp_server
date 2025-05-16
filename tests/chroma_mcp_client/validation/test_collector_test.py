"""Tests for the test collector module in the validation package."""

import os
import pytest
from unittest.mock import patch, MagicMock, mock_open
import uuid
import datetime
from pathlib import Path

from chroma_mcp_client.validation.test_collector import (
    parse_junit_xml,
    compare_test_runs,
    create_test_transition_evidence,
    store_test_results,
)
from chroma_mcp_client.validation.schemas import TestTransitionEvidence


# Sample JUnit XML content for testing
JUNIT_XML_PASS = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="0" failures="0" skipped="0" tests="2" time="1.234">
    <testcase classname="tests.test_module" name="test_success" time="0.123" />
    <testcase classname="tests.test_module" name="test_another" time="0.456" />
  </testsuite>
</testsuites>
"""

JUNIT_XML_FAIL = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="0" failures="1" skipped="0" tests="2" time="1.234">
    <testcase classname="tests.test_module" name="test_success" time="0.123" />
    <testcase classname="tests.test_module" name="test_another" time="0.456">
      <failure message="AssertionError: expected 42 but got None">AssertionError: expected 42 but got None
File "tests/test_module.py", line 42
  assert func(10) == 42
       ^^^^^^^^^^^
  </failure>
    </testcase>
  </testsuite>
</testsuites>
"""


class TestTestCollector:
    """Test cases for the test collector module."""

    def test_parse_junit_xml_pass(self):
        """Test parsing a JUnit XML file with passing tests."""
        with patch("builtins.open", mock_open(read_data=JUNIT_XML_PASS)):
            with patch("os.path.exists", return_value=True):
                result = parse_junit_xml("tests/results.xml")

                # Check the overall structure
                assert len(result) == 2
                assert "tests.test_module.test_success" in result
                assert "tests.test_module.test_another" in result

                # Check details of a test case
                test_case = result["tests.test_module.test_success"]
                assert test_case["test_name"] == "test_success"
                assert test_case["test_file"] == "tests/test_module.py"
                assert test_case["status"] == "pass"
                assert test_case["error_message"] is None
                assert float(test_case["duration"]) == 0.123

    def test_parse_junit_xml_fail(self):
        """Test parsing a JUnit XML file with failing tests."""
        with patch("builtins.open", mock_open(read_data=JUNIT_XML_FAIL)):
            with patch("os.path.exists", return_value=True):
                result = parse_junit_xml("tests/results.xml")

                # Check the failing test
                test_case = result["tests.test_module.test_another"]
                assert test_case["status"] == "fail"
                assert "AssertionError: expected 42 but got None" in test_case["error_message"]
                assert "tests/test_module.py" in test_case["error_message"]

    def test_parse_junit_xml_file_not_found(self):
        """Test parsing behavior when JUnit XML file doesn't exist."""
        with patch("os.path.exists", return_value=False):
            with pytest.raises(FileNotFoundError):
                parse_junit_xml("nonexistent.xml")

    def test_compare_test_runs(self):
        """Test comparing before and after test runs."""
        # Create before and after dictionaries
        before_tests = {
            "test1": {
                "test_name": "test1",
                "test_file": "test_file.py",
                "status": "fail",
                "error_message": "Error message",
                "duration": "0.1",
            },
            "test2": {
                "test_name": "test2",
                "test_file": "test_file.py",
                "status": "pass",
                "error_message": None,
                "duration": "0.2",
            },
            "test3": {
                "test_name": "test3",
                "test_file": "test_file.py",
                "status": "error",
                "error_message": "Error message",
                "duration": "0.3",
            },
        }

        after_tests = {
            "test1": {
                "test_name": "test1",
                "test_file": "test_file.py",
                "status": "pass",
                "error_message": None,
                "duration": "0.1",
            },
            "test2": {
                "test_name": "test2",
                "test_file": "test_file.py",
                "status": "fail",
                "error_message": "New error",
                "duration": "0.2",
            },
            "test3": {
                "test_name": "test3",
                "test_file": "test_file.py",
                "status": "error",
                "error_message": "Different error",
                "duration": "0.3",
            },
            "test4": {
                "test_name": "test4",
                "test_file": "test_file.py",
                "status": "pass",
                "error_message": None,
                "duration": "0.4",
            },
        }

        transitions = compare_test_runs(before_tests, after_tests, filter_new_tests=True)

        # Should find 2 meaningful transitions: fail->pass and pass->fail
        assert len(transitions) == 2

        # Check fail->pass transition
        transition = next(t for t in transitions if t["test_id"] == "test1")
        assert transition["test_name"] == "test1"
        assert transition["before_status"] == "fail"
        assert transition["after_status"] == "pass"

        # Check pass->fail transition
        transition = next(t for t in transitions if t["test_id"] == "test2")
        assert transition["test_name"] == "test2"
        assert transition["before_status"] == "pass"
        assert transition["after_status"] == "fail"

        # No transition for test3 (error->error) even though error message changed
        assert not any(t["test_id"] == "test3" for t in transitions)

        # No transition for test4 (new test) as there's no before state

    def test_create_test_transition_evidence(self):
        """Test creating TestTransitionEvidence from XML files."""
        with (
            patch("chroma_mcp_client.validation.test_collector.parse_junit_xml") as mock_parse,
            patch("chroma_mcp_client.validation.test_collector.compare_test_runs") as mock_compare,
        ):
            # Set up mock returns
            mock_parse.side_effect = [
                # Before results (with a failing test)
                {
                    "test1": {
                        "test_name": "test1",
                        "test_file": "test_file.py",
                        "status": "fail",
                        "error_message": "Error msg",
                        "duration": "0.1",
                    }
                },
                # After results (with the test now passing)
                {
                    "test1": {
                        "test_name": "test1",
                        "test_file": "test_file.py",
                        "status": "pass",
                        "error_message": None,
                        "duration": "0.1",
                    }
                },
            ]

            mock_compare.return_value = [
                {
                    "test_id": "test1",
                    "test_name": "test1",
                    "test_file": "test_file.py",
                    "before_status": "fail",
                    "after_status": "pass",
                    "error_message_before": "Error msg",
                    "error_message_after": None,
                }
            ]

            # Mock code diff function if needed

            # Call the function
            evidence_list = create_test_transition_evidence("before.xml", "after.xml")

            # Verify results
            assert len(evidence_list) == 1
            evidence = evidence_list[0]

            assert isinstance(evidence, TestTransitionEvidence)
            assert evidence.test_id == "test1"
            assert evidence.test_name == "test1"
            assert evidence.test_file == "test_file.py"
            assert evidence.before_status == "fail"
            assert evidence.after_status == "pass"
            assert evidence.error_message_before == "Error msg"

            # Verify mock calls
            mock_parse.assert_any_call("before.xml")
            mock_parse.assert_any_call("after.xml")
            mock_compare.assert_called_once()

    def test_store_test_results(self):
        """Test storing test results in ChromaDB."""
        with patch("chromadb.Client") as mock_client_class:
            # Setup mock client
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_client.get_collection.return_value = mock_collection
            mock_client_class.return_value = mock_client

            # Set up test results
            results = {
                "test1": {"test_name": "test1", "test_file": "test_file.py", "status": "pass", "error_message": None}
            }

            # Store the results
            with patch("uuid.uuid4") as mock_uuid:
                mock_uuid.return_value = "test-uuid"
                with patch("datetime.datetime") as mock_datetime:
                    mock_now = MagicMock()
                    mock_now.isoformat.return_value = "2023-04-15T12:00:00Z"
                    mock_datetime.now.return_value = mock_now

                    run_id = store_test_results(results)

                    # Verify the return value
                    assert run_id == "test-uuid"

                    # Verify the collection was accessed
                    mock_client.get_collection.assert_called_once_with(name="test_results_v1")

                    # Verify data was added to collection
                    mock_collection.add.assert_called_once()

                    # Check the arguments passed to add
                    args = mock_collection.add.call_args

                    # Extract the positional arguments
                    call_kwargs = args[1]
                    documents = call_kwargs["documents"]
                    metadatas = call_kwargs["metadatas"]
                    ids = call_kwargs["ids"]

                    # Verify the document content
                    assert len(documents) == 1
                    assert len(metadatas) == 1
                    assert len(ids) == 1
                    assert "test1" in documents[0]
                    assert metadatas[0]["test_id"] == "test1"
                    assert ids[0] == "test-uuid_test1"
