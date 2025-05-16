"""Tests for the runtime error collector module in the validation package."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import uuid
import datetime
from pathlib import Path

from chroma_mcp_client.validation.runtime_collector import (
    parse_error_log,
    compare_error_logs,
    create_runtime_error_evidence,
    store_runtime_errors,
)
from chroma_mcp_client.validation.schemas import RuntimeErrorEvidence


# Sample error logs for testing
ERROR_LOG_BEFORE = """
[2023-04-15 14:30:00] ERROR: IndexError: list index out of range
Stack trace:
  File "app.py", line 42
    result = items[10]
IndexError: list index out of range

[2023-04-15 14:35:00] ERROR: TypeError: cannot use + operator with str and int
Stack trace:
  File "app.py", line 50
    result = "value" + counter
TypeError: cannot use + operator with str and int
"""

ERROR_LOG_AFTER = """
[2023-04-15 15:30:00] INFO: Application started successfully

[2023-04-15 15:35:00] ERROR: TypeError: cannot use + operator with str and int
Stack trace:
  File "app.py", line 50
    result = "value" + counter
TypeError: cannot use + operator with str and int
"""


class TestRuntimeCollector:
    """Test cases for the runtime error collector module."""

    def test_parse_error_log(self):
        """Test parsing error logs."""
        with patch("builtins.open", mock_open(read_data=ERROR_LOG_BEFORE)):
            with patch("os.path.exists", return_value=True):
                with patch("uuid.uuid4") as mock_uuid:
                    # Mock the UUID to have predictable IDs
                    mock_uuid.side_effect = ["error-id-1", "error-id-2"]

                    result = parse_error_log("errors.log")

                    # Check the parsed errors
                    assert len(result) == 2

                    # Verify the result is a dictionary of error objects indexed by ID
                    assert "error-id-1" in result
                    assert "error-id-2" in result

                    # Find errors by type
                    index_error = next(
                        (result[e_id] for e_id in result if result[e_id]["error_type"] == "IndexError"), None
                    )
                    type_error = next(
                        (result[e_id] for e_id in result if result[e_id]["error_type"] == "TypeError"), None
                    )

                    # Check the first error
                    assert index_error is not None
                    assert index_error["error_type"] == "IndexError"
                    assert "list index out of range" in index_error["error_message"]
                    assert "app.py" in index_error["stacktrace"]
                    assert "line 42" in index_error["stacktrace"]

                    # Check the second error
                    assert type_error is not None
                    assert type_error["error_type"] == "TypeError"
                    assert "cannot use + operator with str and int" in type_error["error_message"]
                    assert "app.py" in type_error["stacktrace"]
                    assert "line 50" in type_error["stacktrace"]

    def test_parse_error_log_file_not_found(self):
        """Test parsing behavior when error log doesn't exist."""
        with patch("os.path.exists", return_value=False):
            with pytest.raises(FileNotFoundError):
                parse_error_log("nonexistent.log")

    def test_compare_error_logs(self):
        """Test comparing before and after error logs."""
        # Define test data with dictionary structure
        before_errors = {
            "error-1": {
                "error_id": "error-1",
                "error_type": "IndexError",
                "error_message": "list index out of range",
                "timestamp": "2023-04-15T14:30:00Z",
                "stacktrace": "File 'app.py', line 42\n  result = items[10]\nIndexError: list index out of range",
                "affected_files": ["app.py"],
            },
            "error-2": {
                "error_id": "error-2",
                "error_type": "TypeError",
                "error_message": "cannot use + operator with str and int",
                "timestamp": "2023-04-15T14:35:00Z",
                "stacktrace": "File 'app.py', line 50\n  result = 'value' + counter\nTypeError: cannot use + operator with str and int",
                "affected_files": ["app.py"],
            },
        }

        after_errors = {
            "error-2": {
                "error_id": "error-2",
                "error_type": "TypeError",
                "error_message": "cannot use + operator with str and int",
                "timestamp": "2023-04-15T15:35:00Z",
                "stacktrace": "File 'app.py', line 50\n  result = 'value' + counter\nTypeError: cannot use + operator with str and int",
                "affected_files": ["app.py"],
            }
        }

        # Compare the logs
        with patch("datetime.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_now.isoformat.return_value = "2023-04-15T15:30:00Z"
            mock_datetime.now.return_value = mock_now

            resolved_errors = compare_error_logs(before_errors, after_errors)

            # Should find 1 resolved error (IndexError)
            assert len(resolved_errors) == 1

            # Check the resolved error
            error = resolved_errors[0]
            assert error["error_id"] == "error-1"
            assert error["error_type"] == "IndexError"
            assert "list index out of range" in error["error_message"]
            assert error["resolution_timestamp"] == "2023-04-15T15:30:00Z"

    @patch("chroma_mcp_client.validation.runtime_collector.parse_error_log")
    @patch("chroma_mcp_client.validation.runtime_collector.compare_error_logs")
    @patch("uuid.uuid4")
    def test_create_runtime_error_evidence(self, mock_uuid, mock_compare, mock_parse):
        """Test creating RuntimeErrorEvidence from log files."""
        # Set up mocks
        mock_uuid.return_value = "error-123"

        mock_parse.side_effect = [
            # Before errors
            {
                "error-123": {
                    "error_id": "error-123",
                    "error_message": "IndexError: list index out of range",
                    "error_type": "IndexError",
                    "timestamp": "2023-04-15T14:30:00Z",
                    "stacktrace": "File 'app.py', line 42\n  result = items[10]\nIndexError: list index out of range",
                    "affected_files": ["app.py"],
                }
            },
            # After errors (empty, so the error is resolved)
            {},
        ]

        mock_compare.return_value = [
            {
                "error_id": "error-123",
                "error_message": "IndexError: list index out of range",
                "error_type": "IndexError",
                "timestamp": "2023-04-15T14:30:00Z",
                "stacktrace": "File 'app.py', line 42\n  result = items[10]\nIndexError: list index out of range",
                "affected_files": ["app.py"],
                "resolution_timestamp": "2023-04-15T15:30:00Z",
            }
        ]

        # Call the function with mock code changes
        code_before = {"app.py": "def func():\n    result = items[10]"}
        code_after = {
            "app.py": "def func():\n    if len(items) > 10:\n        result = items[10]\n    else:\n        result = None"
        }

        evidence_list = create_runtime_error_evidence("before.log", "after.log", code_before, code_after)

        # Verify results
        assert len(evidence_list) == 1
        evidence = evidence_list[0]

        assert isinstance(evidence, RuntimeErrorEvidence)
        assert evidence.error_id == "error-123"
        assert evidence.error_message == "IndexError: list index out of range"
        assert evidence.error_type == "IndexError"
        assert evidence.first_occurrence == "2023-04-15T14:30:00Z"
        assert evidence.resolution_timestamp == "2023-04-15T15:30:00Z"
        assert evidence.resolution_verified is True
        assert "app.py" in evidence.code_changes
        assert evidence.code_changes["app.py"]["before"] == code_before["app.py"]
        assert evidence.code_changes["app.py"]["after"] == code_after["app.py"]

        # Verify mock calls
        mock_parse.assert_any_call("before.log")
        mock_parse.assert_any_call("after.log")
        mock_compare.assert_called_once()

    def test_store_runtime_errors(self):
        """Test storing runtime errors in ChromaDB."""
        with patch("chroma_mcp.utils.chroma_client.get_chroma_client") as mock_get_client:
            # Setup mock client
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_client.get_collection.return_value = mock_collection
            mock_get_client.return_value = mock_client

            # Set up runtime errors
            errors = {
                "error-123": {
                    "error_id": "error-123",
                    "error_message": "IndexError: list index out of range",
                    "error_type": "IndexError",
                    "timestamp": "2023-04-15T14:30:00Z",
                    "stacktrace": "File 'app.py', line 42\n  result = items[10]\nIndexError: list index out of range",
                }
            }

            # Store the errors
            with patch("uuid.uuid4") as mock_uuid:
                mock_uuid.return_value = "test-uuid"
                with patch("datetime.datetime") as mock_datetime:
                    mock_now = MagicMock()
                    mock_now.isoformat.return_value = "2023-04-15T12:00:00Z"
                    mock_datetime.now.return_value = mock_now

                    run_id = store_runtime_errors(errors)

                    # Verify the return value
                    assert run_id == "test-uuid"

                    # Verify the collection was accessed
                    mock_client.get_collection.assert_called_once_with(name="runtime_errors_v1")

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
                    assert "IndexError" in documents[0]
                    assert metadatas[0]["error_type"] == "IndexError"
                    assert ids[0].startswith("test-uuid_")
