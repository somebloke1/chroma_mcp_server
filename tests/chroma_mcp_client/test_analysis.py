import pytest
from unittest.mock import patch, MagicMock, call
from pathlib import Path
from datetime import datetime, timezone, timedelta
import subprocess
import json
import numpy as np  # Make sure numpy is imported
import chromadb  # Add missing import

# Module to test
from chroma_mcp_client import analysis
from chroma_mcp_client.analysis import SIMILARITY_THRESHOLD  # Import threshold


# Mock ChromaDB client for testing
@pytest.fixture
def mock_chroma_client():
    """Fixture for a mock ChromaDB client."""
    client = MagicMock(name="MockChromaClient")
    mock_collection = MagicMock(name="MockCollection")

    # Configure get_collection to return the mock collection
    client.get_collection.return_value = mock_collection

    # Configure mock collection methods (default responses)
    mock_collection.get.return_value = {  # Simulate a get response structure
        "ids": [],
        "metadatas": [],
        "documents": [],  # Even if not used, good to have default
    }
    # Mock other methods if needed, e.g., update
    # mock_collection.update.return_value = None
    return client


# Fixture for the mock collection, accessible if needed directly
@pytest.fixture
def mock_chroma_collection(mock_chroma_client):
    """Fixture to get the mock collection object returned by the mock client."""
    return mock_chroma_client.get_collection.return_value


# =====================================================================
# Tests for fetch_recent_chat_entries
# =====================================================================


@patch("chroma_mcp_client.analysis.datetime")  # Mock datetime to control 'now'
@patch("chroma_mcp_client.analysis.logger")  # Mock logger instead of log
def test_fetch_recent_chat_entries_filters_correctly(
    mock_logger,  # Updated parameter name
    mock_datetime,
    mock_chroma_client,  # Keep client fixture to ensure collection is mocked
    mock_chroma_collection,  # Use the collection fixture directly
):
    """Test that entries are filtered correctly by status and timestamp using client methods."""
    # Setup mock 'now'
    mock_now = datetime(2024, 7, 26, 12, 0, 0, tzinfo=timezone.utc)
    mock_datetime.now.return_value = mock_now
    mock_datetime.fromisoformat.side_effect = lambda s: datetime.fromisoformat(
        s.replace("Z", "+00:00")
    )  # Keep real parsing, handle Z

    # Mock the collection.get() result
    mock_results = {
        "ids": ["id1", "id2", "id3", "id4", "id5", "id6"],
        "metadatas": [
            {"timestamp": (mock_now - timedelta(days=1)).isoformat(), "status": "captured"},  # Keep (within 7 days)
            {"timestamp": (mock_now - timedelta(days=8)).isoformat(), "status": "captured"},  # Filter out (too old)
            {
                "timestamp": (mock_now - timedelta(days=3)).isoformat(),
                "status": "analyzed",
            },  # Filter out (wrong status - initially fetched, but filtered locally)
            {"timestamp": (mock_now - timedelta(days=6)).isoformat(), "status": "captured"},  # Keep (within 7 days)
            {"timestamp": "invalid-timestamp", "status": "captured"},  # Filter out (bad timestamp)
            {"status": "captured"},  # Filter out (missing timestamp)
        ],
    }
    mock_chroma_collection.get.return_value = mock_results
    mock_chroma_collection.name = "chat_test"  # Set name attribute on mock collection

    # --- Call the function --- Pass the mock collection object directly
    filtered = analysis.fetch_recent_chat_entries(mock_chroma_collection, "captured", 7, 200)

    # --- Assertions ---
    # Check collection.get was called (no client call needed)
    # mock_chroma_client.get_collection.assert_called_once_with(name="chat_test") # REMOVE THIS CHECK
    expected_where = {"status": "captured"}
    mock_chroma_collection.get.assert_called_once_with(where=expected_where, include=["metadatas"])

    # Check the filtered results (should match the logic inside the function)
    # id3 has wrong status, but might be fetched initially if where filter includes it
    # The *local* filtering should remove it.
    assert len(filtered) == 2
    # Result should be sorted by timestamp desc before returning
    assert filtered[0]["id"] == "id1"  # Most recent kept
    assert filtered[1]["id"] == "id4"  # Older kept
    assert filtered[0]["metadata"]["status"] == "captured"
    assert filtered[1]["metadata"]["status"] == "captured"

    # Check warnings for bad/missing timestamps during sorting/filtering
    assert mock_logger.warning.call_count >= 2
    mock_logger.warning.assert_any_call("Could not parse timestamp 'invalid-timestamp' for entry id5 during sorting.")
    mock_logger.warning.assert_any_call("Missing timestamp for entry id6 during sorting.")


@patch("chroma_mcp_client.analysis.logger")  # Mock logger instead of log
def test_fetch_recent_chat_entries_no_results(
    mock_logger,  # Updated parameter name
    mock_chroma_client,  # Keep client fixture
    mock_chroma_collection,  # Use the collection fixture directly
):
    """Test behavior when the collection.get() returns no documents."""
    mock_results = {"ids": [], "metadatas": []}
    mock_chroma_collection.get.return_value = mock_results
    mock_chroma_collection.name = "chat_empty"  # Set name attribute

    filtered = analysis.fetch_recent_chat_entries(mock_chroma_collection, "captured", 7, 200)

    assert filtered == []
    # mock_chroma_client.get_collection.assert_called_once_with(name="chat_empty") # REMOVE THIS CHECK
    mock_chroma_collection.get.assert_called_once_with(
        where={"status": "captured"}, include=["metadatas"]  # Default filter
    )
    # Check info log
    mock_logger.info.assert_any_call("No documents found matching the status filter.")


@patch("chroma_mcp_client.analysis.logger")  # Mock logger instead of log
def test_fetch_recent_chat_entries_client_error(  # Rename test slightly
    mock_logger,  # Updated parameter name
    mock_chroma_client,  # Keep client fixture
    mock_chroma_collection,  # Use the collection fixture directly
):
    """Test behavior when the collection.get() call raises an exception."""
    mock_chroma_collection.get.side_effect = Exception("DB Boom!")
    mock_chroma_collection.name = "chat_error"  # Set name attribute

    filtered = analysis.fetch_recent_chat_entries(mock_chroma_collection, "captured", 7, 200)

    assert filtered == []  # Should return empty list on error
    # mock_chroma_client.get_collection.assert_called_once_with(name="chat_error") # REMOVE THIS CHECK
    mock_chroma_collection.get.assert_called_once()  # Check it was called
    # Check error log
    mock_logger.error.assert_called_once()
    assert "Error fetching chat entries" in mock_logger.error.call_args[0][0]
    assert mock_logger.error.call_args[1]["exc_info"] is True  # Check exc_info was logged


# =====================================================================
# Tests for get_git_diff_after_timestamp
# =====================================================================


@patch("subprocess.run")
def test_get_git_diff_found(mock_subprocess_run, tmp_path):
    repo_path = tmp_path
    file_path = repo_path / "src/code.py"
    file_path.parent.mkdir()
    file_path.touch()
    timestamp_str = "2024-07-26T12:00:00Z"
    commit_hash = "abcdef123"
    diff_content = "+ new line\n- old line"

    # Mock 'git log' call to find commits
    mock_log_result = MagicMock()
    mock_log_result.returncode = 0
    mock_log_result.stdout = f"{commit_hash}\noldhash456"  # Newest first, need oldest
    mock_log_result.stderr = ""

    # Mock 'git show' call for the *earliest* commit found
    mock_show_result = MagicMock()
    mock_show_result.returncode = 0
    mock_show_result.stdout = diff_content
    mock_show_result.stderr = ""

    mock_subprocess_run.side_effect = [mock_log_result, mock_show_result]

    result = analysis.get_git_diff_after_timestamp(repo_path, str(file_path), timestamp_str)

    assert result == diff_content
    assert mock_subprocess_run.call_count == 2
    # Check git log call args
    log_call_args = mock_subprocess_run.call_args_list[0].args[0]
    assert "log" in log_call_args
    assert "--format=%H" in log_call_args
    assert "--since" in log_call_args
    assert str(file_path.relative_to(repo_path)) in log_call_args
    # Check git show call args for the earliest commit (last in log output)
    show_call_args = mock_subprocess_run.call_args_list[1].args[0]
    assert "show" in show_call_args
    assert "oldhash456" in show_call_args
    assert "--patch" in show_call_args
    assert str(file_path.relative_to(repo_path)) in show_call_args


@patch("subprocess.run")
def test_get_git_diff_no_commits(mock_subprocess_run, tmp_path):
    repo_path = tmp_path
    file_path = repo_path / "src/code.py"
    file_path.parent.mkdir()
    file_path.touch()
    timestamp_str = "2024-07-26T12:00:00Z"

    # Mock 'git log' call returning no commits
    mock_log_result = MagicMock()
    mock_log_result.returncode = 0
    mock_log_result.stdout = ""  # No commit hashes
    mock_log_result.stderr = ""
    mock_subprocess_run.return_value = mock_log_result

    result = analysis.get_git_diff_after_timestamp(repo_path, str(file_path), timestamp_str)

    assert result is None
    mock_subprocess_run.assert_called_once()  # Only git log should be called
    assert "log" in mock_subprocess_run.call_args.args[0]


@patch("subprocess.run")
@patch("chroma_mcp_client.analysis.logger")  # Mock logger instead of log
def test_get_git_diff_log_error(mock_logger, mock_subprocess_run, tmp_path):
    repo_path = tmp_path
    file_path = repo_path / "src/code.py"
    file_path.parent.mkdir()
    file_path.touch()
    timestamp_str = "2024-07-26T12:00:00Z"

    # Mock 'git log' call returning error
    mock_log_result = MagicMock()
    mock_log_result.returncode = 1
    mock_log_result.stdout = ""
    mock_log_result.stderr = "Git log error"
    mock_subprocess_run.return_value = mock_log_result

    result = analysis.get_git_diff_after_timestamp(repo_path, str(file_path), timestamp_str)

    assert result is None
    mock_subprocess_run.assert_called_once()
    mock_logger.error.assert_called_once_with(f"Git log command failed: {mock_log_result.stderr}")


@patch("subprocess.run")
@patch("chroma_mcp_client.analysis.logger")  # Mock logger instead of log
def test_get_git_diff_show_error(mock_logger, mock_subprocess_run, tmp_path):
    repo_path = tmp_path
    file_path = repo_path / "src/code.py"
    file_path.parent.mkdir()
    file_path.touch()
    timestamp_str = "2024-07-26T12:00:00Z"
    commit_hash = "abcdef123"

    # Mock 'git log' call
    mock_log_result = MagicMock()
    mock_log_result.returncode = 0
    mock_log_result.stdout = commit_hash
    mock_log_result.stderr = ""

    # Mock 'git show' call returning error
    mock_show_result = MagicMock()
    mock_show_result.returncode = 1
    mock_show_result.stdout = ""
    mock_show_result.stderr = "Git show error"

    mock_subprocess_run.side_effect = [mock_log_result, mock_show_result]

    result = analysis.get_git_diff_after_timestamp(repo_path, str(file_path), timestamp_str)

    assert result is None
    assert mock_subprocess_run.call_count == 2
    mock_logger.error.assert_called_once_with(
        f"Git show command failed for commit {commit_hash}: {mock_show_result.stderr}"
    )


# =====================================================================
# Tests for correlate_summary_with_diff (Updated for Embeddings)
# =====================================================================

# Remove the old parametrize decorator for word matching
# @pytest.mark.parametrize(...)


# Add a fixture for a mock embedding function
@pytest.fixture
def mock_embedding_function():
    mock_ef = MagicMock(name="MockEmbeddingFunction")
    # Default behavior: return distinct, non-zero vectors
    mock_ef.side_effect = lambda texts: [[i + 1.0] * 10 for i, _ in enumerate(texts)]  # Simple unique vectors
    return mock_ef


@patch("chroma_mcp_client.analysis.np.dot")
@patch("chroma_mcp_client.analysis.np.linalg.norm")
@patch("chroma_mcp_client.analysis.logger")  # Add missing patch for logger
def test_correlate_summary_with_diff_logic(
    mock_logger, mock_norm, mock_dot, mock_embedding_function
):  # Add mock_logger to args
    """Test the correlation logic specifically, including numpy mocks."""
    summary = "summary text"
    diff_high_sim = "diff text high sim"
    diff_low_sim = "diff text low sim"

    # --- High Similarity Case ---
    # Mock EF to return similar vectors (e.g., same direction)
    mock_embedding_function.side_effect = lambda texts: (
        [[1.0, 0.0]] if texts == [summary] else ([[0.7, 0.0]] if texts == [diff_high_sim] else [[0.0, 1.0]])
    )
    # Mock norm to return 1.0 (as if vectors were normalized)
    mock_norm.return_value = 1.0
    # Mock dot product of normalized vectors to be high (e.g., 0.8)
    mock_dot.return_value = np.array(0.8)  # Mock dot product result (needs to be array for .item())

    result_high = analysis.correlate_summary_with_diff(summary, diff_high_sim, mock_embedding_function)
    assert result_high is True  # 0.8 >= 0.6
    # Check EF calls
    mock_embedding_function.assert_has_calls([call([summary]), call([diff_high_sim])])
    # Check norm calls (called twice: once for summary, once for diff)
    assert mock_norm.call_count == 2
    # Check dot call (called once with the normalized vectors implicitly)
    mock_dot.assert_called_once()
    # Check log message
    mock_logger.info.assert_any_call(
        f"Correlation check result: Similarity = {0.8:.4f}, Threshold = {SIMILARITY_THRESHOLD}, Correlated = True"
    )

    # --- Low Similarity Case ---
    # Reset mocks
    mock_embedding_function.reset_mock()
    mock_norm.reset_mock()
    mock_dot.reset_mock()
    mock_logger.reset_mock()

    # Mock EF to return orthogonal vectors
    mock_embedding_function.side_effect = lambda texts: (
        [[1.0, 0.0]] if texts == [summary] else ([[0.0, 1.0]] if texts == [diff_low_sim] else [[0.5, 0.5]])
    )
    mock_norm.return_value = 1.0
    mock_dot.return_value = np.array(0.1)  # Mock low dot product

    result_low = analysis.correlate_summary_with_diff(summary, diff_low_sim, mock_embedding_function)
    assert result_low is False  # 0.1 < 0.6
    mock_embedding_function.assert_has_calls([call([summary]), call([diff_low_sim])])
    assert mock_norm.call_count == 2
    mock_dot.assert_called_once()
    mock_logger.info.assert_any_call(
        f"Correlation check result: Similarity = {0.1:.4f}, Threshold = {SIMILARITY_THRESHOLD}, Correlated = False"
    )


@patch("chroma_mcp_client.analysis.logger")  # Mock logger instead of log
def test_correlate_summary_with_diff_edge_cases(mock_logger, mock_embedding_function):
    """Test correlation handles empty inputs and embedding errors."""
    # Empty summary
    assert analysis.correlate_summary_with_diff("", "+ diff", mock_embedding_function) is False
    mock_logger.warning.assert_called_with(
        "Correlation check skipped: Empty summary, diff, or no embedding function provided."
    )
    mock_logger.reset_mock()

    # Empty diff
    assert analysis.correlate_summary_with_diff("summary", "", mock_embedding_function) is False
    mock_logger.warning.assert_called_with(
        "Correlation check skipped: Empty summary, diff, or no embedding function provided."
    )
    mock_logger.reset_mock()

    # No embedding function
    assert analysis.correlate_summary_with_diff("summary", "+ diff", None) is False
    mock_logger.warning.assert_called_with(
        "Correlation check skipped: Empty summary, diff, or no embedding function provided."
    )
    mock_logger.reset_mock()

    # Embedding function error
    mock_embedding_function.side_effect = ValueError("Embedding failed!")
    assert analysis.correlate_summary_with_diff("summary", "+ diff", mock_embedding_function) is False
    mock_logger.error.assert_called_once()
    assert "Error during embedding generation or similarity calculation" in mock_logger.error.call_args[0][0]


# =====================================================================
# Tests for update_entry_status
# =====================================================================


@patch("chroma_mcp_client.analysis.logger")  # Mock logger instead of log
def test_update_entry_status_success(
    mock_logger,  # Updated parameter name
    mock_chroma_client,  # Use client fixture
    mock_chroma_collection,  # Use collection fixture
):
    """Test that update_entry_status calls collection.update correctly on success."""
    entry_id = "id_to_update"
    collection_name = "test_coll"
    new_status = "processed"

    # No need to mock collection.update return value unless it's checked

    # --- Call the function ---
    result = analysis.update_entry_status(mock_chroma_client, collection_name, entry_id, new_status)

    # --- Assertions ---
    assert result is True
    # Check get_collection was called
    mock_chroma_client.get_collection.assert_called_once_with(name=collection_name)
    # Check collection.update was called with correct parameters
    mock_chroma_collection.update.assert_called_once_with(ids=[entry_id], metadatas=[{"status": new_status}])
    # Check logs
    mock_logger.info.assert_any_call(
        f"Attempting to update status for entry {entry_id} in '{collection_name}' to '{new_status}'."
    )
    mock_logger.info.assert_any_call(f"Successfully updated status for entry {entry_id}.")
    mock_logger.warning.assert_not_called()  # Ensure placeholder warning is gone
    mock_logger.error.assert_not_called()


@patch("chroma_mcp_client.analysis.logger")  # Mock logger instead of log
def test_update_entry_status_failure(
    mock_logger,  # Updated parameter name
    mock_chroma_client,  # Use client fixture
    mock_chroma_collection,  # Use collection fixture
):
    """Test that update_entry_status returns False and logs error on failure."""
    entry_id = "id_fail_update"
    collection_name = "test_coll_fail"
    new_status = "failed"
    error_message = "DB update exploded!"

    # Configure collection.update to raise an exception
    mock_chroma_collection.update.side_effect = Exception(error_message)

    # --- Call the function ---
    result = analysis.update_entry_status(mock_chroma_client, collection_name, entry_id, new_status)

    # --- Assertions ---
    assert result is False
    # Check get_collection and update were called
    mock_chroma_client.get_collection.assert_called_once_with(name=collection_name)
    mock_chroma_collection.update.assert_called_once_with(ids=[entry_id], metadatas=[{"status": new_status}])
    # Check logs
    mock_logger.error.assert_called_once()
    # Check that the specific error message and exc_info=True were logged
    log_call_args = mock_logger.error.call_args
    assert f"Failed to update status for entry {entry_id}" in log_call_args[0][0]
    assert error_message in log_call_args[0][0]
    assert log_call_args[1].get("exc_info") is True
    mock_logger.info.assert_any_call(
        f"Attempting to update status for entry {entry_id} in '{collection_name}' to '{new_status}'."
    )
    # Ensure success log wasn't called
    with pytest.raises(AssertionError):
        mock_logger.info.assert_any_call(f"Successfully updated status for entry {entry_id}.")


# =====================================================================
# Tests for analyze_chat_history (main orchestration) - Updated
# =====================================================================


@patch("chroma_mcp_client.analysis.fetch_recent_chat_entries")
@patch("chroma_mcp_client.analysis.get_git_diff_after_timestamp")
@patch("chroma_mcp_client.analysis.correlate_summary_with_diff")
@patch("chroma_mcp_client.analysis.update_entry_status")
@patch("chroma_mcp_client.analysis.logger")  # Mock logger instead of log
def test_analyze_chat_history_orchestration(
    mock_logger, mock_update_status, mock_correlate, mock_get_diff, mock_fetch_entries, mock_chroma_client, tmp_path
):
    """Test the main analysis orchestration logic."""
    # --- Setup ---
    collection_name = "test_history"
    repo_path = tmp_path  # Although not passed to analyze_chat_history, keep for setting up paths
    status_filter = "captured"
    new_status = "analyzed"
    days_limit = 7

    # Create dummy .git dir
    (tmp_path / ".git").mkdir()

    # Create dummy files referenced in entities
    (tmp_path / "file1.py").touch()
    (tmp_path / "file2.txt").touch()

    # Mock Embedding Function (Instance to be passed)
    mock_ef_instance = MagicMock(name="MockEFInstance")
    # We don't mock the class DefaultEmbeddingFunction anymore

    # Mock fetch_recent_chat_entries response
    mock_entries = [
        {  # Entry 1: Should correlate
            "id": "id1",
            "metadata": {
                "timestamp": "2024-07-27T10:00:00Z",
                "prompt_summary": "Implement feature A",
                "response_summary": "Added code for feature A in file1.py",
                "involved_entities": "file1.py",
                "status": "captured",
            },
        },
        {  # Entry 2: No diff found - Use simplified path
            "id": "id2",
            "metadata": {
                "timestamp": "2024-07-27T11:00:00Z",
                "prompt_summary": "Fix bug B",
                "response_summary": "Investigated bug B in file2.txt, no changes needed.",
                "involved_entities": "file2.txt",  # Updated entity
                "status": "captured",
            },
        },
        {  # Entry 3: Should NOT correlate
            "id": "id3",
            "metadata": {
                "timestamp": "2024-07-27T12:00:00Z",
                "prompt_summary": "Refactor utils",
                "response_summary": "Cleaned up utility functions",
                "involved_entities": "file1.py",  # Assume unrelated change happened
                "status": "captured",
            },
        },
        {  # Entry 4: Entity is not a file
            "id": "id4",
            "metadata": {
                "timestamp": "2024-07-27T13:00:00Z",
                "prompt_summary": "Discuss pattern X",
                "response_summary": "Decided on using pattern X",
                "involved_entities": "patternX",
                "status": "captured",
            },
        },
        {  # Entry 5: Entity outside repo (should be skipped by analysis logic)
            "id": "id5",
            "metadata": {
                "timestamp": "2024-07-27T14:00:00Z",
                "prompt_summary": "Update external dep",
                "response_summary": "Updated lib Z",
                "involved_entities": "../outside_file.txt",
                "status": "captured",
            },
        },
        {  # Entry 6: Missing timestamp
            "id": "id6",
            "metadata": {
                # "timestamp": "2024-07-27T15:00:00Z", # MISSING
                "prompt_summary": "Test",
                "response_summary": "Test response",
                "involved_entities": "file1.py",
                "status": "captured",
            },
        },
    ]
    mock_fetch_entries.return_value = mock_entries

    # Mock get_git_diff_after_timestamp
    # Return diff for file1.py, None for file2.txt
    mock_get_diff.side_effect = lambda rp, fp, ts: "+ diff content" if "file1.py" in fp else None

    # Mock correlate_summary_with_diff
    # Correlate entry 1, not entry 3
    # UPDATE lambda to accept the embedding function argument ('ef')
    mock_correlate.side_effect = lambda summary, diff, ef: "feature A" in summary

    # Mock update_entry_status (just return True)
    mock_update_status.return_value = True

    # --- Act ---
    processed_count, correlated_count = analysis.analyze_chat_history(
        client=mock_chroma_client,
        embedding_function=mock_ef_instance,  # Pass the mock instance
        repo_path=str(repo_path),  # Pass repo_path from setup
        collection_name=collection_name,
        status_filter=status_filter,
        new_status=new_status,
        days_limit=days_limit,
        limit=200,
    )

    # --- Assert ---
    # Check fetch called correctly (now takes collection object)
    mock_fetch_entries.assert_called_once_with(
        mock_chroma_client.get_collection.return_value,  # Pass the *result* of the mock client's get_collection
        status_filter,
        days_limit,
        200,  # Check the hardcoded limit passed from analyze_chat_history
    )

    # Verify client.get_collection was called correctly
    mock_chroma_client.get_collection.assert_called_once_with(name=collection_name)

    # Verify embedding function passed to correlate
    # Check if correlate was called at all (it should be for id1 and id3)
    if mock_correlate.call_args_list:
        assert mock_correlate.call_args_list[0].args[2] == mock_ef_instance
        if len(mock_correlate.call_args_list) > 1:
            assert mock_correlate.call_args_list[1].args[2] == mock_ef_instance
    else:
        # If correlate wasn't called, something else is wrong in the setup/logic
        pass  # Or add a specific assertion like assert False, "Correlate was not called"

    # Check get_git_diff called for valid files
    assert mock_get_diff.call_count == 3
    mock_get_diff.assert_has_calls(
        [
            # Expect resolved repo_path and absolute file paths
            call(repo_path.resolve(), str(tmp_path / "file1.py"), "2024-07-27T10:00:00Z"),
            call(repo_path.resolve(), str(tmp_path / "file2.txt"), "2024-07-27T11:00:00Z"),
            call(repo_path.resolve(), str(tmp_path / "file1.py"), "2024-07-27T12:00:00Z"),
        ],
        any_order=True,
    )

    # Check correlate called when diff exists
    assert mock_correlate.call_count == 2  # Expected 2 again
    mock_correlate.assert_has_calls(
        [
            # Entry 1: Summary contains "feature A", should correlate
            call("Implement feature A Added code for feature A in file1.py", "+ diff content", mock_ef_instance),
            # Entry 3: Summary does not contain "feature A", should not correlate - Restored
            call("Refactor utils Cleaned up utility functions", "+ diff content", mock_ef_instance),
        ],
        any_order=True,
    )

    # Check update_entry_status called for processed entries
    assert mock_update_status.call_count == 5
    mock_update_status.assert_has_calls(
        [
            call(mock_chroma_client, collection_name, "id1", new_status),
            call(mock_chroma_client, collection_name, "id2", new_status),
            call(mock_chroma_client, collection_name, "id3", new_status),
            call(mock_chroma_client, collection_name, "id4", new_status),
            call(mock_chroma_client, collection_name, "id5", new_status),  # Added id5
        ],
        any_order=True,
    )

    # Check log warnings for skipped entities/entries
    # Construct expected absolute paths for warnings
    patternX_abs_path = (repo_path / "patternX").resolve()
    outside_file_abs_path = (repo_path / "../outside_file.txt").resolve()

    mock_logger.warning.assert_has_calls(
        [
            # Use the updated log message format and expected absolute paths
            call(f"Skipping entity 'patternX': Resolved path '{patternX_abs_path}' is not a valid file."),
            call(
                f"Skipping entity '../outside_file.txt': Resolved path '{outside_file_abs_path}' is not a valid file."
            ),
            call("Skipping entry id6: Missing required metadata."),
        ],
        any_order=True,
    )

    # Check final counts
    assert processed_count == 5  # Based on update status calls
    assert correlated_count == 1  # Based on correlate mock side effect

    # Check final log message counts using assert_any_call
    mock_logger.info.assert_any_call(
        f"Analysis complete. Processed {processed_count} entries. Found potential correlation in {correlated_count} entries."
    )


# ... (rest of the tests, if any) ...
