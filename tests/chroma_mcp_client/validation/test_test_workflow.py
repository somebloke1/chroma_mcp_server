"""
Unit tests for the automated test-driven learning workflow.

Tests the TestWorkflowManager class and related functionality in the
validation.test_workflow module.
"""

import os
import json
import pytest
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from chroma_mcp_client.validation.test_workflow import (
    TestWorkflowManager,
    check_for_completed_workflows,
    setup_automated_workflow,
)


class TestTestWorkflowManager:
    """
    Test the TestWorkflowManager class used for automating test-driven learning.
    """

    @pytest.fixture
    def mock_chroma_client(self):
        """Create a mock ChromaDB client with required methods."""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        mock_client.create_collection.return_value = mock_collection
        return mock_client

    @pytest.fixture
    def workflow_manager(self, mock_chroma_client):
        """Create a TestWorkflowManager instance with mocked dependencies."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = TestWorkflowManager(workspace_dir=tmp_dir, chroma_client=mock_chroma_client)
            yield manager

    def test_init(self, workflow_manager, mock_chroma_client):
        """Test initialization of the TestWorkflowManager."""
        # Assert collections are created
        assert mock_chroma_client.get_collection.call_count == 3

        # Check default collection names
        assert workflow_manager.test_results_collection == "test_results_v1"
        assert workflow_manager.chat_history_collection == "chat_history_v1"
        assert workflow_manager.evidence_collection == "validation_evidence_v1"

    def test_ensure_collections(self, workflow_manager, mock_chroma_client):
        """Test _ensure_collections method."""
        # Reset call count
        mock_chroma_client.get_collection.reset_mock()
        mock_chroma_client.create_collection.reset_mock()

        # Test with existing collections
        workflow_manager._ensure_collections()
        assert mock_chroma_client.get_collection.call_count == 3
        assert mock_chroma_client.create_collection.call_count == 0

        # Test with non-existing collection (simulate exception)
        mock_chroma_client.get_collection.side_effect = Exception("Collection not found")
        workflow_manager._ensure_collections()
        assert mock_chroma_client.create_collection.call_count == 3

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.chmod")
    def test_setup_git_hooks(self, mock_chmod, mock_open, workflow_manager):
        """Test setup_git_hooks method."""
        # Create a temp path for .git/hooks
        hooks_dir = Path(workflow_manager.workspace_dir) / ".git" / "hooks"
        os.makedirs(hooks_dir, exist_ok=True)

        # Run the method
        result = workflow_manager.setup_git_hooks()

        # Check results
        assert result is True
        assert mock_open.call_count == 2  # Two files should be created
        mock_chmod.assert_called()  # Should set permissions

    @patch("chroma_mcp_client.validation.test_workflow.parse_junit_xml")
    @patch("chroma_mcp_client.validation.test_workflow.store_test_results")
    @patch("subprocess.check_output")
    @patch("builtins.open", new_callable=mock_open)
    def test_capture_test_failure(
        self, mock_open, mock_subprocess, mock_store_results, mock_parse_xml, workflow_manager
    ):
        """Test capture_test_failure method."""
        # Setup mocks
        mock_parse_xml.return_value = {
            "test1": {"status": "fail", "message": "Test failed"},
            "test2": {"status": "pass"},
        }
        mock_store_results.return_value = "test-run-123"
        mock_subprocess.return_value = b"abc123\n"

        # Call method
        run_id = workflow_manager.capture_test_failure("test-results.xml")

        # Check results
        assert run_id == "test-run-123"
        mock_parse_xml.assert_called_once_with("test-results.xml")
        mock_store_results.assert_called_once()
        mock_open.assert_called_once()

        # Test with provided commit hash
        run_id = workflow_manager.capture_test_failure("test-results.xml", "def456")
        assert run_id == "test-run-123"
        # Subprocess shouldn't be called if commit hash is provided
        assert mock_subprocess.call_count == 1

    @patch("subprocess.check_output")
    def test_find_chat_sessions_for_code_changes(self, mock_subprocess, workflow_manager, mock_chroma_client):
        """Test find_chat_sessions_for_code_changes method."""
        # Setup mocks
        mock_subprocess.return_value = b"file1.py\nfile2.py\n"

        # Set up chat collection query mock
        chat_collection = mock_chroma_client.get_collection.return_value
        chat_collection.query.return_value = {"ids": [["chat1", "chat2"]]}

        # Call method
        chat_ids = workflow_manager.find_chat_sessions_for_code_changes("abc123", "def456")

        # Check results
        assert len(chat_ids) == 2
        assert "chat1" in chat_ids
        assert "chat2" in chat_ids
        mock_subprocess.assert_called_once_with(
            ["git", "diff", "--name-only", "abc123", "def456"], cwd=workflow_manager.workspace_dir
        )
        chat_collection.query.assert_called()

        # Test with no changed files
        mock_subprocess.return_value = b"\n"
        chat_ids = workflow_manager.find_chat_sessions_for_code_changes("abc123", "def456")
        assert len(chat_ids) == 0

    @patch("chroma_mcp_client.validation.test_workflow.create_test_transition_evidence")
    @patch("chroma_mcp_client.validation.test_workflow.collect_validation_evidence")
    def test_create_validation_from_test_transition(
        self, mock_collect_evidence, mock_create_transitions, workflow_manager
    ):
        """Test create_validation_from_test_transition method."""
        # Setup mocks
        mock_transitions = [MagicMock()]
        mock_create_transitions.return_value = mock_transitions

        mock_evidence = MagicMock()
        mock_evidence.test_transitions = mock_transitions
        mock_evidence.meets_threshold.return_value = True
        mock_collect_evidence.return_value = mock_evidence

        # Patch the find_chat_sessions method to return some chat IDs
        with patch.object(workflow_manager, "find_chat_sessions_for_code_changes", return_value=["chat1", "chat2"]):
            # Call method
            evidence, chat_ids = workflow_manager.create_validation_from_test_transition(
                "before.xml", "after.xml", "abc123", "def456"
            )

        # Check results
        assert evidence == mock_evidence
        assert len(chat_ids) == 2
        assert "chat1" in chat_ids
        mock_create_transitions.assert_called_once_with(
            before_xml="before.xml", after_xml="after.xml", commit_before="abc123", commit_after="def456"
        )
        mock_collect_evidence.assert_called_once()

        # Check that related_chat_ids is set on transitions
        assert mock_transitions[0].related_chat_ids == ["chat1", "chat2"]

    def test_auto_promote_learning(self, workflow_manager):
        """Test auto_promote_learning method."""
        # This will need more implementation as the feature develops
        mock_evidence = MagicMock()
        mock_evidence.meets_threshold.return_value = False
        mock_evidence.score = 0.5

        result = workflow_manager.auto_promote_learning(
            evidence=mock_evidence, chat_ids=["chat1", "chat2"], confidence_threshold=0.8
        )

        # Should not promote if below threshold
        assert result is None

        # Test with high score
        mock_evidence.meets_threshold.return_value = True
        mock_evidence.score = 0.9

        # Still None until implementation is complete
        assert (
            workflow_manager.auto_promote_learning(
                evidence=mock_evidence, chat_ids=[], confidence_threshold=0.8  # Empty chat IDs
            )
            is None
        )

    def test_setup_git_hooks_preserves_existing_content(self, tmp_path):
        """Test that setup_git_hooks preserves existing content in post-commit hook."""
        # Setup mock workspace with .git/hooks
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        git_dir = workspace_dir / ".git"
        git_dir.mkdir()
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir()

        # Create existing post-commit hook with custom content only (no standard components)
        post_commit_path = hooks_dir / "post-commit"
        existing_content = """#!/bin/bash
# Existing hook content
echo "Custom operation..."
"""
        with open(post_commit_path, "w") as f:
            f.write(existing_content)
        os.chmod(post_commit_path, 0o755)

        # Mock ChromaDB client
        mock_client = MagicMock()

        # Initialize TestWorkflowManager with mocked client
        manager = TestWorkflowManager(workspace_dir=str(workspace_dir), chroma_client=mock_client)

        # Run the hook setup
        result = manager.setup_git_hooks()

        # Verify the result
        assert result is True

        # Read the updated hook content
        with open(post_commit_path, "r") as f:
            updated_content = f.read()

        # Verify existing content is preserved
        assert "Existing hook content" in updated_content
        assert "Custom operation..." in updated_content

        # Verify both standard components are added when missing
        assert "Running post-commit hook: Indexing changed files" in updated_content
        assert "Checking for test transitions" in updated_content
        assert "python -m chroma_mcp_client.cli check-test-transitions" in updated_content

    def test_setup_git_hooks_with_partial_components(self, tmp_path):
        """Test setup_git_hooks when hook exists with only some components."""
        # Setup mock workspace with .git/hooks
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        git_dir = workspace_dir / ".git"
        git_dir.mkdir()
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir()

        # Create existing post-commit hook with only the test transition check
        post_commit_path = hooks_dir / "post-commit"
        existing_content = """#!/bin/bash
# Existing hook with test check only
echo "Custom operation..."

# Added by TestWorkflowManager for test transition tracking
echo "Checking for test transitions..."
python -m chroma_mcp_client.cli check-test-transitions
"""
        with open(post_commit_path, "w") as f:
            f.write(existing_content)
        os.chmod(post_commit_path, 0o755)

        # Mock ChromaDB client
        mock_client = MagicMock()

        # Initialize TestWorkflowManager with mocked client
        manager = TestWorkflowManager(workspace_dir=str(workspace_dir), chroma_client=mock_client)

        # Run the hook setup
        result = manager.setup_git_hooks()

        # Verify the result
        assert result is True

        # Read the updated hook content
        with open(post_commit_path, "r") as f:
            updated_content = f.read()

        # Verify existing content is preserved
        assert "Existing hook with test check only" in updated_content
        assert "Custom operation..." in updated_content

        # Verify test transition check is still there
        assert "Checking for test transitions" in updated_content
        assert "python -m chroma_mcp_client.cli check-test-transitions" in updated_content

        # Verify indexing code was added
        assert "Running post-commit hook: Indexing changed files" in updated_content
        assert "hatch run python -m chroma_mcp_client.cli index" in updated_content

    def test_setup_git_hooks_with_all_components(self, tmp_path):
        """Test setup_git_hooks when hook exists with all components already."""
        # Setup mock workspace with .git/hooks
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        git_dir = workspace_dir / ".git"
        git_dir.mkdir()
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir()

        # Create existing post-commit hook with both components
        post_commit_path = hooks_dir / "post-commit"
        existing_content = """#!/bin/bash
# Auto-generated by TestWorkflowManager

# Index changed files for RAG
echo "Running post-commit hook: Indexing changed files..."
# ... rest of indexing code ...
fi

# Added by TestWorkflowManager for test transition tracking
echo "Checking for test transitions..."
python -m chroma_mcp_client.cli check-test-transitions
"""
        with open(post_commit_path, "w") as f:
            f.write(existing_content)
        os.chmod(post_commit_path, 0o755)

        # Mock ChromaDB client
        mock_client = MagicMock()

        # Initialize TestWorkflowManager with mocked client
        manager = TestWorkflowManager(workspace_dir=str(workspace_dir), chroma_client=mock_client)

        # Run the hook setup - should not modify the file
        result = manager.setup_git_hooks()

        # Verify the result
        assert result is True

        # Read the updated hook content - should be identical
        with open(post_commit_path, "r") as f:
            updated_content = f.read()

        # Assert file content was not changed (compare with original)
        assert updated_content == existing_content

    @patch("chroma_mcp_client.validation.test_workflow.get_chroma_client")
    def test_cleanup_processed_artifacts(self, mock_get_client, tmp_path):
        """Test that the cleanup_processed_artifacts method correctly cleans up test artifacts."""
        # Create a mock client and collection
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        mock_get_client.return_value = mock_client

        # Setup test directories
        logs_dir = tmp_path / "logs"
        tests_dir = logs_dir / "tests"
        junit_dir = tests_dir / "junit"
        workflows_dir = tests_dir / "workflows"

        for d in [logs_dir, tests_dir, junit_dir, workflows_dir]:
            d.mkdir(exist_ok=True)

        # Create test files
        before_xml = junit_dir / "failed_tests_20250101_010101.xml"
        before_xml.write_text("<test></test>")  # Simple XML content

        before_xml_commit = Path(str(before_xml) + ".commit")
        before_xml_commit.write_text("abcdef123456")  # Fake commit hash

        after_xml = junit_dir / "test-results.xml"
        after_xml.write_text("<test></test>")  # Simple XML content

        # Create a linked workflow file
        workflow_file = workflows_dir / "test_workflow_old.json"
        old_workflow_content = {
            "status": "failed",
            "timestamp": "2025-01-01T01:01:01Z",
            "xml_path": str(before_xml),
            "commit": "abcdef123456",
        }
        workflow_file.write_text(json.dumps(old_workflow_content))

        # Create a completed workflow file
        completed_workflow = workflows_dir / "test_workflow_complete_20250101_020202.json"
        completed_workflow_content = {
            "status": "transitioned",
            "timestamp": "2025-01-01T02:02:02Z",
            "before_xml": str(before_xml),
            "after_xml": str(after_xml),
            "before_commit": "abcdef123456",
            "after_commit": "fedcba654321",
        }
        completed_workflow.write_text(json.dumps(completed_workflow_content))

        # Initialize the test workflow manager with the test workspace and mock client
        manager = TestWorkflowManager(workspace_dir=str(tmp_path), chroma_client=mock_client)

        # Call the cleanup method
        result = manager.cleanup_processed_artifacts(str(completed_workflow))

        # Verify the result
        assert result is True

        # Verify that files were removed
        assert not before_xml.exists()
        assert not before_xml_commit.exists()
        assert not workflow_file.exists()  # The old workflow file should be removed
        assert not completed_workflow.exists()  # The completed workflow file should be removed

        # The "after" XML should still exist (current test results)
        assert after_xml.exists()


@patch("chroma_mcp_client.validation.test_workflow.TestWorkflowManager")
def test_setup_automated_workflow(mock_manager_class):
    """Test setup_automated_workflow function."""
    # Setup mock
    mock_manager = MagicMock()
    mock_manager.setup_git_hooks.return_value = True
    mock_manager_class.return_value = mock_manager

    # Call function
    result = setup_automated_workflow("/test/workspace")

    # Check results
    assert result is True
    mock_manager_class.assert_called_once_with(workspace_dir="/test/workspace")
    mock_manager.setup_git_hooks.assert_called_once()

    # Test failure case
    mock_manager.setup_git_hooks.return_value = False
    result = setup_automated_workflow()
    assert result is False


@patch("chroma_mcp_client.validation.test_workflow.TestWorkflowManager")
def test_check_for_completed_workflows(mock_manager_class):
    """Test check_for_completed_workflows function."""
    # As this function is not fully implemented, we mostly test that it runs
    # and returns the expected type
    result = check_for_completed_workflows()
    assert isinstance(result, int)
    assert result == 0  # Currently just returns 0
