import pytest
from unittest.mock import patch, MagicMock, call
import logging
import io
from contextlib import redirect_stderr

# Assuming the module is in src/chroma_mcp_client
from chroma_mcp_client.interactive_promoter import run_interactive_promotion

# Configure logging for tests if needed, or capture logs
# logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def mock_chroma_init():
    with patch("chroma_mcp_client.interactive_promoter.get_client_and_ef") as mock_init:
        mock_client = MagicMock()
        mock_ef = MagicMock()
        mock_init.return_value = (mock_client, mock_ef)
        yield mock_client, mock_ef, mock_init


@pytest.fixture
def mock_fetch_entries():
    with patch("chroma_mcp_client.interactive_promoter.fetch_recent_chat_entries") as mock_fetch:
        yield mock_fetch


@pytest.fixture
def mock_update_status():
    with patch("chroma_mcp_client.interactive_promoter.update_entry_status") as mock_update:
        yield mock_update


@pytest.fixture
def mock_input():
    with patch("builtins.input") as mock_in:
        yield mock_in


@pytest.fixture
def mock_promote_function():
    with patch("chroma_mcp_client.interactive_promoter.promote_to_learnings_collection") as mock_promote:
        yield mock_promote


@pytest.fixture
def mock_query_codebase():
    # Note the patch target is within the interactive_promoter module where it's imported
    with patch("chroma_mcp_client.interactive_promoter.query_codebase") as mock_query:
        yield mock_query


def test_run_interactive_promotion_no_entries(mock_chroma_init, mock_fetch_entries, caplog, capsys):
    """Test the behavior when no 'analyzed' entries are found."""
    mock_client, _, _ = mock_chroma_init
    mock_fetch_entries.return_value = []

    run_interactive_promotion()

    mock_fetch_entries.assert_called_once_with(
        collection=mock_client.get_collection.return_value,
        status_filter="analyzed",
        days_limit=7,  # Default
        fetch_limit=50,  # Default
    )
    # Check console print with capsys
    captured_stdout = capsys.readouterr().out
    assert "No entries with status 'analyzed' found within the specified time limit." in captured_stdout


def test_run_interactive_promotion_init_fails(caplog):
    """Test behavior when Chroma initialization fails."""
    with patch("chroma_mcp_client.interactive_promoter.get_client_and_ef", return_value=(None, None)) as mock_init_fail:
        # Capture stderr to check for error message
        with io.StringIO() as stderr_capture, redirect_stderr(stderr_capture):
            run_interactive_promotion()
            stderr_output = stderr_capture.getvalue()

        mock_init_fail.assert_called_once()
        assert "Failed to initialize Chroma connection" in stderr_output


def test_run_interactive_promotion_user_actions(
    mock_chroma_init, mock_fetch_entries, mock_update_status, mock_input, caplog, capsys
):
    """Test user choosing to ignore, skip, (pseudo)promote, and quit."""
    mock_client, mock_ef, _ = mock_chroma_init
    mock_chat_collection = mock_client.get_collection.return_value

    entry1 = {"id": "chat_001", "metadata": {"prompt_summary": "P1", "response_summary": "R1"}}
    entry2 = {"id": "chat_002", "metadata": {"prompt_summary": "P2", "response_summary": "R2"}}
    entry3 = {"id": "chat_003", "metadata": {"prompt_summary": "P3", "response_summary": "R3"}}
    entry4 = {"id": "chat_004", "metadata": {"prompt_summary": "P4", "response_summary": "R4"}}
    mock_fetch_entries.return_value = [entry1, entry2, entry3, entry4]

    # Simulate user inputs: ignore, skip, skip, quit
    mock_input.side_effect = ["i", "s", "s", "q"]
    mock_update_status.return_value = True  # Assume status update succeeds

    run_interactive_promotion(
        chat_collection_name="test_chat_coll",
        learnings_collection_name="test_learn_coll",
        days_limit=10,
        fetch_limit=100,
    )

    # Check fetch call
    mock_fetch_entries.assert_called_once_with(
        collection=mock_chat_collection, status_filter="analyzed", days_limit=10, fetch_limit=100
    )

    # Check input calls
    assert mock_input.call_count == 4
    mock_input.assert_has_calls(
        [
            call("Action (p=promote, i=ignore, s=skip, q=quit): "),
            call("Action (p=promote, i=ignore, s=skip, q=quit): "),
            call("Action (p=promote, i=ignore, s=skip, q=quit): "),
            call("Action (p=promote, i=ignore, s=skip, q=quit): "),
        ]
    )

    # Check update_entry_status for the ignored entry
    mock_update_status.assert_called_once_with(mock_client, "test_chat_coll", "chat_001", new_status="ignored")

    # Check console output (via capsys)
    captured = capsys.readouterr()
    assert "Found 4 entries to review." in captured.out
    assert "Reviewing Entry 1/4" in captured.out
    assert "ID: chat_001" in captured.out
    assert "Marking entry chat_001 as ignored..." in captured.out
    assert "Status updated to 'ignored'." in captured.out

    assert "Reviewing Entry 2/4" in captured.out
    assert "ID: chat_002" in captured.out
    assert "Skipping entry chat_002." in captured.out

    assert "Reviewing Entry 3/4" in captured.out
    assert "ID: chat_003" in captured.out
    assert "Skipping entry chat_003." in captured.out

    assert "Quitting review process." in captured.out  # For entry 4, user chose 'q'

    # Check summary in console output
    assert "Review Complete" in captured.out
    assert "Promoted: 0" in captured.out
    assert "Ignored: 1" in captured.out
    assert "Skipped: 2" in captured.out  # entry2 and entry3 are skipped


# More tests will be added here for promoting, ignoring, skipping, quitting.


def test_run_interactive_promotion_promote_action_success(
    mock_chroma_init,
    mock_fetch_entries,
    mock_input,
    mock_promote_function,  # Use the new fixture
    mock_query_codebase,  # Use the new fixture
    caplog,
    capsys,
):
    """Test the 'promote' action successfully calls the promotion function."""
    mock_client, mock_ef, _ = mock_chroma_init
    mock_chat_collection = mock_client.get_collection.return_value

    entry_id = "chat_promote_001"
    prompt_summary = "User asked about X"
    response_summary = "AI explained Y"
    entry_to_promote = {
        "id": entry_id,
        "metadata": {
            "prompt_summary": prompt_summary,
            "response_summary": response_summary,
            "involved_entities": "X, Y",
        },
    }
    mock_fetch_entries.return_value = [entry_to_promote]

    # Sample query results
    mock_code_ref_1 = "path/to/file.py:sha1:10-20"
    mock_code_ref_2 = "other/file.py:sha2:5-15"
    mock_query_results = {
        "ids": [[mock_code_ref_1, mock_code_ref_2]],
        "documents": [["def func():\n  pass", "class MyClass:\n  pass"]],
        "metadatas": [[{"relative_file_path": "path/to/file.py"}, {"relative_file_path": "other/file.py"}]],
        "distances": [[0.1, 0.2]],
    }
    mock_query_codebase.return_value = mock_query_results

    # User inputs for the promotion process:
    # 1. Action: 'p' (promote)
    # 2. Description: (accept default)
    # 3. Pattern: "Key pattern is Z"
    # 4. Code Ref Selection: '1' (select first suggested)
    # 5. Tags: "python,testing"
    # 6. Confidence: "0.9"
    mock_input.side_effect = [
        "p",
        "",  # Accept default description
        "Key pattern is Z",
        "1",  # Select code ref 1
        "python,testing",
        "0.9",
    ]

    promoted_learning_id = "new_learning_uuid_123"
    mock_promote_function.return_value = promoted_learning_id  # Simulate successful promotion

    caplog.set_level(logging.INFO)

    run_interactive_promotion(
        chat_collection_name="chat_coll_for_promote", learnings_collection_name="learn_coll_for_promote"
    )

    # Check query_codebase call
    expected_query = f"{prompt_summary}\n{response_summary}"
    mock_query_codebase.assert_called_once_with(
        client=mock_client,
        embedding_function=mock_ef,
        query_texts=[expected_query],
        collection_name="codebase_v1",  # Default
        n_results=5,  # Default in interactive_promoter
    )

    # Check that promote_to_learnings_collection was called correctly
    expected_description = f"Prompt: {prompt_summary}\nResponse: {response_summary}"
    mock_promote_function.assert_called_once_with(
        client=mock_client,
        embedding_function=mock_ef,
        description=expected_description,
        pattern="Key pattern is Z",
        code_ref=mock_code_ref_1,  # Check the selected code ref is used
        tags="python,testing",
        confidence=0.9,
        learnings_collection_name="learn_coll_for_promote",
        source_chat_id=entry_id,
        chat_history_collection_name="chat_coll_for_promote",
    )

    # Check that input was called with the correct prompts
    # The calls are: action, description, pattern, code_ref_selection, tags, confidence
    assert mock_input.call_count == 6
    input_calls = [
        call("Action (p=promote, i=ignore, s=skip, q=quit): "),
        call(f"Description (default: '{expected_description}'): "),
        call("Pattern (e.g., code snippet, regex, textual key insight): "),
        call(f"Code Reference (select 1-2, type manually, or 'n' for N/A): "),  # Prompt shows number of choices
        call("Tags (comma-separated, e.g., python,refactor,logging): "),
        call("Confidence (0.0 to 1.0): "),
    ]
    mock_input.assert_has_calls(input_calls, any_order=False)  # Ensure order

    # Check console output for other messages
    captured = capsys.readouterr()
    assert "Searching codebase for relevant snippets..." in captured.out
    assert "Suggested Code References:" in captured.out
    assert f"1. ID: {mock_code_ref_1}" in captured.out  # Check suggested refs are printed
    assert f"2. ID: {mock_code_ref_2}" in captured.out
    assert f"Selected: {mock_code_ref_1}" in captured.out  # Check selection confirmation
    assert f"Successfully promoted entry {entry_id} to learning {promoted_learning_id}." in captured.out

    # Check summary counts
    assert "Promoted: 1" in captured.out
    assert "Ignored: 0" in captured.out
    assert "Skipped: 0" in captured.out

    # Check logs from interactive_promoter, not the mocked function
    assert (
        f"Successfully promoted entry {entry_id} to learning {promoted_learning_id}." in captured.out
    )  # This print is in interactive_promoter


def test_run_interactive_promotion_promote_action_failure(
    mock_chroma_init,
    mock_fetch_entries,
    mock_input,
    mock_promote_function,
    mock_query_codebase,  # Use the new fixture
    caplog,
    capsys,
):
    """Test the 'promote' action when the promotion function fails."""
    mock_client, mock_ef, _ = mock_chroma_init
    entry_id = "chat_promote_fail_001"
    entry_to_promote = {"id": entry_id, "metadata": {"prompt_summary": "P", "response_summary": "R"}}
    mock_fetch_entries.return_value = [entry_to_promote]

    # Simulate no code results found
    mock_query_codebase.return_value = None

    # User inputs: p -> description -> pattern -> code_ref ('n') -> tags -> confidence
    # The final 'q' is removed as it won't be called when only one entry is processed
    mock_input.side_effect = ["p", "Test Desc", "Test Pattern", "n", "Test Tags", "0.5"]
    mock_promote_function.return_value = None  # Simulate promotion failure

    run_interactive_promotion()

    # Check query was called
    mock_query_codebase.assert_called_once()

    # Check promote was called (with code_ref="N/A")
    mock_promote_function.assert_called_once_with(
        client=mock_client,
        embedding_function=mock_ef,
        description="Test Desc",
        pattern="Test Pattern",
        code_ref="N/A",
        tags="Test Tags",
        confidence=0.5,
        learnings_collection_name="derived_learnings_v1",  # Default
        source_chat_id=entry_id,
        chat_history_collection_name="chat_history_v1",  # Default
    )

    # Check input calls
    assert mock_input.call_count == 6  # p, desc, pattern, code_ref, tags, confidence
    input_calls = [
        call("Action (p=promote, i=ignore, s=skip, q=quit): "),
        call(f"Description (default: 'Prompt: P\nResponse: R'): "),
        call("Pattern (e.g., code snippet, regex, textual key insight): "),
        call(f"Code Reference (select 1-0, type manually, or 'n' for N/A): "),  # No suggestions here
        call("Tags (comma-separated, e.g., python,refactor,logging): "),
        call("Confidence (0.0 to 1.0): "),
        # Removed final 'q' call
    ]
    mock_input.assert_has_calls(input_calls, any_order=False)

    # Check console output
    captured = capsys.readouterr()
    assert "No relevant code snippets found." in captured.out
    assert f"Failed to promote entry {entry_id}. Please check logs." in captured.out
    assert "Promoted: 0" in captured.out
    assert "Skipped: 1" in captured.out  # Skipped because promotion failed
    # assert "Quitting review process." in captured.out # Not reached with one entry


# More tests will be added here for promoting, ignoring, skipping, quitting.
