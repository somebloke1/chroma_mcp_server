"""Tests for the code quality collector module in the validation package."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import uuid
import datetime
from pathlib import Path
import subprocess
from typing import Dict, List, Any

from chroma_mcp_client.validation.code_quality_collector import (
    parse_ruff_output,
    parse_pylint_output,
    run_quality_tool,
    extract_code_with_issues,
    compare_quality_results,
    create_code_quality_evidence,
    run_quality_check,
    store_quality_results,
)
from chroma_mcp_client.validation.schemas import CodeQualityEvidence


# Sample linter outputs for testing
RUFF_OUTPUT = """
file1.py:10:5: E501 Line too long (120 > 88 characters)
file1.py:15:1: F401 'os' imported but unused
file2.py:20:9: E203 Whitespace before ':'
"""

PYLINT_OUTPUT = """
file1.py:10:5: C0303: Trailing whitespace (trailing-whitespace)
file1.py:15:1: C0410: Multiple imports on one line (os, sys) (multiple-imports)
file2.py:20:9: C0326: No space allowed before : (bad-whitespace)
"""


class TestCodeQualityCollector:
    """Test cases for the code quality collector module."""

    def test_parse_ruff_output(self):
        """Test parsing Ruff linter output."""
        issues = parse_ruff_output(RUFF_OUTPUT)

        # Check the parsed issues
        assert len(issues) == 2  # Two files with issues
        assert "file1.py" in issues
        assert "file2.py" in issues

        # Check the first file's issues
        file1_issues = issues["file1.py"]
        assert len(file1_issues) == 2

        # Check a specific issue
        issue = next(i for i in file1_issues if "E501" in i["code"])
        assert issue["line"] == 10
        assert issue["column"] == 5
        assert issue["code"] == "E501"
        assert "Line too long" in issue["description"]

    def test_parse_pylint_output(self):
        """Test parsing Pylint output."""
        issues = parse_pylint_output(PYLINT_OUTPUT)

        # Check the parsed issues
        assert len(issues) == 2  # Two files with issues
        assert "file1.py" in issues
        assert "file2.py" in issues

        # Check the first file's issues
        file1_issues = issues["file1.py"]
        assert len(file1_issues) == 2

        # Check a specific issue
        issue = next(i for i in file1_issues if "C0303" in i["code"])
        assert issue["line"] == 10
        assert issue["column"] == 5
        assert issue["code"] == "C0303"
        assert "Trailing whitespace" in issue["description"]

    @patch("subprocess.run")
    def test_run_quality_tool_ruff(self, mock_run):
        """Test running Ruff quality tool."""
        # Mock subprocess run
        mock_process = MagicMock()
        mock_process.stdout = RUFF_OUTPUT
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        # Run the quality tool
        issues, total = run_quality_tool("ruff", ["file1.py", "file2.py"])

        # Check the results
        assert total == 3  # Total of 3 issues
        assert len(issues) == 2  # Two files with issues

        # Check the subprocess call
        mock_run.assert_called_once_with(["ruff", "check", "file1.py", "file2.py"], capture_output=True, text=True)

    @patch("subprocess.run")
    def test_run_quality_tool_pylint(self, mock_run):
        """Test running Pylint quality tool."""
        # Mock subprocess run
        mock_process = MagicMock()
        mock_process.stdout = PYLINT_OUTPUT
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        # Run the quality tool
        issues, total = run_quality_tool("pylint", ["file1.py", "file2.py"])

        # Check the results
        assert total == 3  # Total of 3 issues
        assert len(issues) == 2  # Two files with issues

        # Check the subprocess call
        mock_run.assert_called_once_with(["pylint", "file1.py", "file2.py"], capture_output=True, text=True)

    @patch("subprocess.run")
    def test_run_quality_tool_unsupported(self, mock_run):
        """Test running an unsupported quality tool."""
        with pytest.raises(ValueError, match="Unsupported quality tool"):
            run_quality_tool("unsupported", ["file1.py"])

    @patch("subprocess.run")
    def test_run_quality_tool_error(self, mock_run):
        """Test handling errors when running quality tools."""
        mock_run.side_effect = Exception("Command failed")

        # Run should handle the exception and return empty results
        issues, total = run_quality_tool("ruff", ["file1.py"])
        assert issues == {}
        assert total == 0

    @patch("builtins.open", new_callable=mock_open, read_data="line1\nline2\nline3\nline4\nline5\n")
    @patch("os.path.exists", return_value=True)
    def test_extract_code_with_issues(self, mock_exists, mock_file):
        """Test extracting code snippets with issues."""
        issues = [
            {"line": 2, "column": 1, "code": "E123", "description": "Error"},
            {"line": 4, "column": 5, "code": "E456", "description": "Another error"},
        ]

        code = extract_code_with_issues("test.py", issues)

        # Check that code contains line numbers and issue descriptions
        assert "Line 2" in code
        assert "E123" in code
        assert "Error" in code
        assert "Line 4" in code
        assert "E456" in code
        assert "Another error" in code

        # Check that the mock file was read
        mock_file.assert_called_once_with("test.py", "r")

    @patch("os.path.exists", return_value=False)
    def test_extract_code_file_not_found(self, mock_exists):
        """Test extracting code when file doesn't exist."""
        issues = [{"line": 2, "column": 1, "code": "E123", "description": "Error"}]
        result = extract_code_with_issues("nonexistent.py", issues)
        assert "File not found" in result

    @patch("builtins.open")
    def test_extract_code_with_error(self, mock_open):
        """Test handling errors when extracting code."""
        mock_open.side_effect = Exception("Error opening file")
        issues = [{"line": 2, "column": 1, "code": "E123", "description": "Error"}]

        result = extract_code_with_issues("test.py", issues)
        assert "Error extracting code" in result

    def test_compare_quality_results(self):
        """Test comparing before and after quality results."""
        # Create before and after issues
        before_issues = {
            "file1.py": [
                {"line": 10, "column": 5, "code": "E501", "description": "Line too long"},
                {"line": 15, "column": 1, "code": "F401", "description": "Unused import"},
            ],
            "file2.py": [{"line": 20, "column": 9, "code": "E203", "description": "Whitespace before :"}],
        }

        after_issues = {
            "file1.py": [{"line": 15, "column": 1, "code": "F401", "description": "Unused import"}],  # One issue fixed
            "file3.py": [  # New file with issues
                {"line": 5, "column": 3, "code": "E101", "description": "Mixed spaces/tabs"}
            ],
        }

        improvements = compare_quality_results(before_issues, after_issues)

        # Check the improvements
        assert len(improvements) == 2  # Two files with improvements (file1.py and file2.py)

        # Check file1.py improvements
        assert "file1.py" in improvements
        assert improvements["file1.py"]["before_count"] == 2
        assert improvements["file1.py"]["after_count"] == 1
        assert improvements["file1.py"]["fixed_count"] == 1

        # Check file2.py improvements
        assert "file2.py" in improvements
        assert improvements["file2.py"]["before_count"] == 1
        assert improvements["file2.py"]["after_count"] == 0
        assert improvements["file2.py"]["fixed_count"] == 1

    def test_create_code_quality_evidence(self):
        """Test creating CodeQualityEvidence objects."""
        # Create before and after issues
        before_issues = {
            "file1.py": [
                {"line": 10, "column": 5, "code": "E501", "description": "Line too long"},
                {"line": 15, "column": 1, "code": "F401", "description": "Unused import"},
            ],
            "file2.py": [{"line": 20, "column": 9, "code": "E203", "description": "Whitespace before :"}],
        }

        after_issues = {
            "file1.py": [{"line": 15, "column": 1, "code": "F401", "description": "Unused import"}]  # One issue fixed
        }

        # Create mock code
        code_before = {
            "file1.py": "def func():\n    return 'very long line that exceeds the limit'\n    import os",
            "file2.py": "x = {'key':value}",
        }
        code_after = {
            "file1.py": "def func():\n    return 'shortened'\n    import os",
            "file2.py": "x = {'key': value}",
        }

        # Mock datetime for measured_at
        with patch("datetime.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_now.isoformat.return_value = "2023-04-15T15:00:00Z"
            mock_datetime.now.return_value = mock_now

            # Create evidence
            evidence_list = create_code_quality_evidence(before_issues, after_issues, "ruff", code_before, code_after)

        # Check the evidence list
        assert len(evidence_list) == 2  # Two files with improvements

        # Find evidence for each file
        file1_evidence = next(e for e in evidence_list if e.file_path == "file1.py")
        file2_evidence = next(e for e in evidence_list if e.file_path == "file2.py")

        # Check file1 evidence
        assert isinstance(file1_evidence, CodeQualityEvidence)
        assert file1_evidence.tool == "ruff"
        assert file1_evidence.metric_type == "linting"
        assert file1_evidence.before_value == 2.0  # 2 issues
        assert file1_evidence.after_value == 1.0  # 1 issue
        assert file1_evidence.percentage_improvement == 50.0  # 50% improvement (1 of 2 issues fixed)
        assert file1_evidence.file_path == "file1.py"
        assert file1_evidence.measured_at == "2023-04-15T15:00:00Z"

        # Check file2 evidence
        assert isinstance(file2_evidence, CodeQualityEvidence)
        assert file2_evidence.tool == "ruff"
        assert file2_evidence.metric_type == "linting"
        assert file2_evidence.before_value == 1.0  # 1 issue
        assert file2_evidence.after_value == 0.0  # 0 issues
        assert file2_evidence.percentage_improvement == 100.0  # 100% improvement (all issues fixed)
        assert file2_evidence.file_path == "file2.py"
        assert file2_evidence.measured_at == "2023-04-15T15:00:00Z"

    @patch("chroma_mcp_client.validation.code_quality_collector.run_quality_tool")
    def test_run_quality_check(self, mock_run_quality_tool):
        """Test running a quality check."""
        # Mock the quality tool run
        mock_issues = {"file1.py": [{"line": 10, "column": 5, "code": "E501", "description": "Line too long"}]}
        mock_run_quality_tool.return_value = (1, mock_issues)

        # Run the quality check
        total_issues, issues = run_quality_check(["file1.py"], tool="ruff")

        # Check the results
        assert total_issues == 1
        assert issues == mock_issues

        # Check the mock was called correctly
        mock_run_quality_tool.assert_called_once_with("ruff", ["file1.py"])

    @patch("chroma_mcp.utils.chroma_client.get_chroma_client")
    @patch("uuid.uuid4")
    @patch("datetime.datetime")
    def test_store_quality_results(self, mock_datetime, mock_uuid, mock_get_chroma_client):
        """Test storing quality results in ChromaDB."""
        # Set up mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        mock_get_chroma_client.return_value = mock_client
        mock_uuid.return_value = "test-uuid"
        mock_now = MagicMock()
        mock_now.isoformat.return_value = "2023-04-15T12:00:00Z"
        mock_datetime.now.return_value = mock_now

        # Set up quality results
        results = {"file1.py": [{"line": 10, "column": 5, "code": "E501", "description": "Line too long"}]}

        # Store the results
        run_id = store_quality_results(results, 1, "ruff")

        # Check the return value
        assert run_id == "test-uuid"

        # Verify ChromaDB interactions
        mock_get_chroma_client.assert_called_once()
        mock_client.get_collection.assert_called_once_with(name="code_quality_v1")

        # Verify the documents were added
        mock_collection.add.assert_called_once()
        args = mock_collection.add.call_args

        # Check the arguments
        call_kwargs = args[1]
        assert len(call_kwargs["documents"]) == 2  # One summary document and one per-file document
        assert len(call_kwargs["metadatas"]) == 2
        assert len(call_kwargs["ids"]) == 2

        # Check metadata
        metadata = call_kwargs["metadatas"][0]
        assert metadata["results_id"] == "test-uuid"
        assert metadata["tool"] == "ruff"
        assert metadata["timestamp"] == "2023-04-15T12:00:00Z"
