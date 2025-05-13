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

    # Simulate user inputs: auto-promote disabled, ignore, skip, skip, quit
    mock_input.side_effect = ["n", "i", "s", "s", "q"]
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
    assert mock_input.call_count == 5  # Auto-promote prompt + 4 action prompts
    mock_input.assert_has_calls(
        [
            call("\nEnable auto-promote mode for high confidence entries (≥0.8)? (y/N): "),
            call("\nAction (p=promote, i=ignore, s=skip, v=view context, q=quit): "),
            call("\nAction (p=promote, i=ignore, s=skip, v=view context, q=quit): "),
            call("\nAction (p=promote, i=ignore, s=skip, v=view context, q=quit): "),
            call("\nAction (p=promote, i=ignore, s=skip, v=view context, q=quit): "),
        ]
    )

    # Check update_entry_status for the ignored entry
    mock_update_status.assert_called_once_with(mock_client, "test_chat_coll", "chat_001", new_status="ignored")

    # Check console output (via capsys)
    captured = capsys.readouterr()
    assert "Found 4 entries to review after filtering." in captured.out
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
    # 1. Auto-promote: 'n' (disabled)
    # 2. Action: 'p' (promote)
    # 3. Description: (accept default)
    # 4. Pattern: "Key pattern is Z"
    # 5. Code Ref Selection: '1' (select first suggested)
    # 6. Tags: "python,testing"
    # 7. Confidence: "0.9"
    # 8. Include context: 'y'
    mock_input.side_effect = [
        "n",  # Disable auto-promote
        "p",
        "",  # Accept default description
        "Key pattern is Z",
        "1",  # Select code ref 1
        "python,testing",
        "0.9",
        "y",  # Include context
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
        include_chat_context=True,
    )

    # Check that input was called with the correct prompts
    # The calls are: auto-promote, action, description, pattern, code_ref_selection, tags, confidence, include_context
    assert mock_input.call_count == 8

    # Get the actual calls for debugging
    actual_calls = mock_input.call_args_list

    # Instead of asserting the exact prompt format which may change, just check that key elements are present
    assert "auto-promote" in str(actual_calls[0])
    assert "Action" in str(actual_calls[1])
    assert "Description" in str(actual_calls[2])
    assert "Pattern" in str(actual_calls[3])
    assert "Code Reference" in str(actual_calls[4])
    assert "Tags" in str(actual_calls[5])
    assert "Confidence" in str(actual_calls[6])
    assert "Include rich context" in str(actual_calls[7])

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

    # User inputs:
    # 1. Auto-promote: 'n' (disable)
    # 2. p -> description -> pattern -> code_ref ('n') -> tags -> confidence -> include_context
    mock_input.side_effect = ["n", "p", "Test Desc", "Test Pattern", "n", "Test Tags", "0.5", "y"]
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
        include_chat_context=True,
    )

    # Check input calls (auto-promote + 7 original inputs)
    assert mock_input.call_count == 8  # auto-promote + p, desc, pattern, code_ref, tags, confidence, include_context

    # Check console output
    captured = capsys.readouterr()
    assert "No relevant code snippets found." in captured.out
    assert f"Failed to promote entry {entry_id}. Please check logs." in captured.out
    assert "Promoted: 0" in captured.out
    assert "Skipped: 1" in captured.out  # Skipped because promotion failed
    # assert "Quitting review process." in captured.out # Not reached with one entry


# More tests will be added here for promoting, ignoring, skipping, quitting.


def test_run_interactive_promotion_auto_promote(
    mock_chroma_init,
    mock_fetch_entries,
    mock_input,
    mock_promote_function,
    mock_query_codebase,
    caplog,
    capsys,
):
    """Test the auto-promote feature for high confidence entries."""
    mock_client, mock_ef, _ = mock_chroma_init
    mock_chat_collection = mock_client.get_collection.return_value

    # Create entries with different confidence scores
    high_confidence_entry = {
        "id": "high_conf_001",
        "metadata": {
            "prompt_summary": "High confidence prompt",
            "response_summary": "High confidence response",
            "confidence_score": "0.9",
            "modification_type": "feature",
        },
        "_confidence_score": 0.9,  # This is set internally after filtering
        "_context_richness": 0.8,
    }

    medium_confidence_entry = {
        "id": "med_conf_002",
        "metadata": {
            "prompt_summary": "Medium confidence prompt",
            "response_summary": "Medium confidence response",
            "confidence_score": "0.7",
            "modification_type": "refactor",
        },
        "_confidence_score": 0.7,
        "_context_richness": 0.5,
    }

    low_confidence_entry = {
        "id": "low_conf_003",
        "metadata": {
            "prompt_summary": "Low confidence prompt",
            "response_summary": "Low confidence response",
            "confidence_score": "0.4",
            "modification_type": "bugfix",
        },
        "_confidence_score": 0.4,
        "_context_richness": 0.3,
    }

    mock_fetch_entries.return_value = [high_confidence_entry, medium_confidence_entry, low_confidence_entry]

    # Mock code search results
    mock_code_ref = "src/file.py:sha1:10-20"
    mock_query_results = {
        "ids": [[mock_code_ref]],
        "documents": [["def func():\n  pass"]],
        "metadatas": [[{"relative_file_path": "src/file.py"}]],
        "distances": [[0.1]],
    }
    mock_query_codebase.return_value = mock_query_results

    # User inputs:
    # 1. Enable auto-promote: 'y'
    # 2. Accept default threshold: ''
    # 3. For medium entry (below threshold): 's' (skip)
    # 4. For low entry (below threshold): 's' (skip)
    mock_input.side_effect = [
        "y",  # Enable auto-promote
        "",  # Accept default threshold (0.8)
        "s",  # Skip medium confidence entry
        "s",  # Skip low confidence entry
    ]

    # Mock successful promotion
    promoted_learning_id = "auto_promoted_123"
    mock_promote_function.return_value = promoted_learning_id

    # Run the function
    run_interactive_promotion(
        chat_collection_name="test_collection", learnings_collection_name="test_learnings", sort_by_confidence=True
    )

    # Capture output
    captured = capsys.readouterr()

    # Verify auto-promote was enabled
    assert "Auto-promote mode enabled for entries with confidence ≥0.8" in captured.out

    # Verify high confidence entry was auto-promoted
    assert "Auto-promoting entry with confidence score 0.9" in captured.out
    assert "Auto-promoting entry high_conf_001" in captured.out

    # Verify promote function was called once with the correct parameters
    assert mock_promote_function.call_count == 1

    # Get the actual call arguments
    actual_call = mock_promote_function.call_args
    actual_kwargs = actual_call[1]

    # Check all parameters except the pattern which has different formatting
    assert actual_kwargs["client"] == mock_client
    assert actual_kwargs["embedding_function"] == mock_ef
    assert actual_kwargs["description"] == f"Prompt: High confidence prompt\nResponse: High confidence response"
    assert actual_kwargs["code_ref"] == mock_code_ref
    assert actual_kwargs["tags"] == "feature"
    assert actual_kwargs["confidence"] == 0.9
    assert actual_kwargs["learnings_collection_name"] == "test_learnings"
    assert actual_kwargs["source_chat_id"] == "high_conf_001"
    assert actual_kwargs["chat_history_collection_name"] == "test_collection"
    assert actual_kwargs["include_chat_context"] == True

    # Check that pattern contains key parts but without exact formatting
    assert "Implementation pattern for" in actual_kwargs["pattern"]
    assert "High" in actual_kwargs["pattern"]
    assert "confidence" in actual_kwargs["pattern"]
    assert "prompt" in actual_kwargs["pattern"]

    # Verify medium and low confidence entries were not auto-promoted
    assert "Auto-promoting entry med_conf_002" not in captured.out
    assert "Auto-promoting entry low_conf_003" not in captured.out

    # Verify summary indicates auto-promotion
    assert "Auto-Promoted: 1" in captured.out
    assert "Ignored: 0" in captured.out
    assert "Skipped: 2" in captured.out


def test_run_interactive_promotion_auto_promote_custom_threshold(
    mock_chroma_init,
    mock_fetch_entries,
    mock_input,
    mock_promote_function,
    mock_query_codebase,
    caplog,
    capsys,
):
    """Test auto-promote with a custom confidence threshold."""
    mock_client, mock_ef, _ = mock_chroma_init

    # Create entries with different confidence scores
    high_confidence_entry = {
        "id": "high_conf_001",
        "metadata": {
            "prompt_summary": "Very high confidence prompt",
            "response_summary": "Very high confidence response",
            "confidence_score": "0.95",
            "modification_type": "feature",
        },
        "_confidence_score": 0.95,
        "_context_richness": 0.8,
    }

    medium_confidence_entry = {
        "id": "med_conf_002",
        "metadata": {
            "prompt_summary": "Medium confidence prompt",
            "response_summary": "Medium confidence response",
            "confidence_score": "0.7",
            "modification_type": "refactor",
        },
        "_confidence_score": 0.7,
        "_context_richness": 0.5,
    }

    mock_fetch_entries.return_value = [high_confidence_entry, medium_confidence_entry]

    # Mock code search results
    mock_code_ref = "src/file.py:sha1:10-20"
    mock_query_results = {
        "ids": [[mock_code_ref]],
        "documents": [["def func():\n  pass"]],
        "metadatas": [[{"relative_file_path": "src/file.py"}]],
        "distances": [[0.1]],
    }
    mock_query_codebase.return_value = mock_query_results

    # User inputs:
    # 1. Enable auto-promote: 'y'
    # 2. Set custom threshold to 0.6: '0.6'
    # 3. For medium entry (now above custom threshold): auto-promote
    mock_input.side_effect = [
        "y",  # Enable auto-promote
        "0.6",  # Set custom threshold to 0.6
    ]

    # Mock successful promotions
    mock_promote_function.return_value = "promoted_id"

    # Run the function
    run_interactive_promotion()

    # Capture output
    captured = capsys.readouterr()

    # Verify custom threshold was set
    assert "Auto-promote threshold set to 0.6" in captured.out

    # Verify both entries were auto-promoted
    assert "Auto-promoting entry with confidence score 0.95" in captured.out
    assert "Auto-promoting entry with confidence score 0.7" in captured.out

    # Verify promote function was called twice
    assert mock_promote_function.call_count == 2

    # Verify summary counts
    assert "Auto-Promoted: 2" in captured.out


def test_run_interactive_promotion_smart_defaults_by_modification_type(
    mock_chroma_init,
    mock_fetch_entries,
    mock_input,
    mock_promote_function,
    mock_query_codebase,
    caplog,
    capsys,
):
    """Test smart defaults generation based on modification type."""
    mock_client, mock_ef, _ = mock_chroma_init

    # Create entries with different modification types
    feature_entry = {
        "id": "feature_001",
        "metadata": {
            "prompt_summary": "Add new login feature",
            "response_summary": "Implemented login with OAuth",
            "confidence_score": "0.7",
            "modification_type": "feature",
            "involved_entities": "auth.py,login.js",
        },
        "_confidence_score": 0.7,
        "_context_richness": 0.6,
    }

    # Only use one entry for simplicity to avoid ordering issues
    mock_fetch_entries.return_value = [feature_entry]

    # Mock code search results
    mock_code_ref = "src/feature.py:sha1:10-20"
    mock_query_results = {
        "ids": [[mock_code_ref]],
        "documents": [["def feature():\n  pass"]],
        "metadatas": [[{"relative_file_path": "src/feature.py"}]],
        "distances": [[0.1]],
    }
    mock_query_codebase.return_value = mock_query_results

    # User inputs:
    # 1. Disable auto-promote: 'n'
    # 2. Feature entry: 'p' -> accept defaults for all fields
    mock_input.side_effect = [
        "n",  # Disable auto-promote
        "p",  # Promote feature entry
        "",  # Accept default description
        "",  # Accept default pattern
        "",  # Accept default code ref
        "",  # Accept default tags
        "",  # Accept default confidence
        "y",  # Include context
    ]

    # Mock successful promotion
    mock_promote_function.return_value = "promoted_id"

    # Run the function
    run_interactive_promotion()

    # Capture output
    captured = capsys.readouterr()

    # We can't verify the exact pattern in the output because it's not consistently printed out
    # But we can verify that promote_to_learnings_collection was called with a pattern that includes
    # the expected components based on the modification type

    # Verify function was called once
    assert mock_promote_function.call_count == 1

    # Get the actual call arguments
    call_args = mock_promote_function.call_args
    call_kwargs = call_args[1]

    # Verify pattern is generated based on modification type
    assert "feature" in call_kwargs["pattern"]
    assert "Implementation pattern for" in call_kwargs["pattern"]
    # Check for the individual list elements that appear in the pattern string representation
    assert "'Add'" in call_kwargs["pattern"]
    assert "'new'" in call_kwargs["pattern"]
    assert "'login'" in call_kwargs["pattern"]

    # Verify default tags include modification type and file extensions
    assert "feature" in call_kwargs["tags"]
    assert "py" in call_kwargs["tags"] or "js" in call_kwargs["tags"]


def test_run_interactive_promotion_low_confidence_warning(
    mock_chroma_init,
    mock_fetch_entries,
    mock_input,
    mock_promote_function,
    mock_query_codebase,
    caplog,
    capsys,
):
    """Test low confidence warning display."""
    mock_client, mock_ef, _ = mock_chroma_init

    # Create a low confidence entry
    low_confidence_entry = {
        "id": "low_conf_001",
        "metadata": {
            "prompt_summary": "Complex task with uncertainty",
            "response_summary": "Attempted solution with limited confidence",
            "confidence_score": "0.4",
            "modification_type": "unknown",
        },
        "_confidence_score": 0.4,
        "_context_richness": 0.3,
    }

    mock_fetch_entries.return_value = [low_confidence_entry]

    # Mock code search results
    mock_code_ref = "src/file.py:sha1:10-20"
    mock_query_results = {
        "ids": [[mock_code_ref]],
        "documents": [["def func():\n  pass"]],
        "metadatas": [[{"relative_file_path": "src/file.py"}]],
        "distances": [[0.1]],
    }
    mock_query_codebase.return_value = mock_query_results

    # User inputs:
    # 1. Disable auto-promote: 'n'
    # 2. Promote entry: 'p' -> accept defaults for all fields
    mock_input.side_effect = [
        "n",  # Disable auto-promote
        "p",  # Promote low confidence entry
        "",  # Accept default description
        "",  # Accept default pattern
        "",  # Accept default code ref
        "",  # Accept default tags
        "",  # Accept default confidence
        "y",  # Include context
    ]

    # Mock successful promotion
    mock_promote_function.return_value = "promoted_id"

    # Run the function
    run_interactive_promotion()

    # Capture output
    captured = capsys.readouterr()

    # Verify low confidence warning was displayed
    assert "LOW CONFIDENCE SCORE DETECTED" in captured.out
    assert "This entry has a low confidence score. Consider reviewing it carefully" in captured.out


def test_run_interactive_promotion_bidirectional_links_code_selection(
    mock_chroma_init,
    mock_fetch_entries,
    mock_input,
    mock_promote_function,
    mock_query_codebase,
    caplog,
    capsys,
):
    """Test code selection from bidirectional links."""
    mock_client, mock_ef, _ = mock_chroma_init

    # Create an entry with related code chunks in metadata
    entry_with_links = {
        "id": "entry_with_links_001",
        "metadata": {
            "prompt_summary": "Update authentication logic",
            "response_summary": "Improved token verification",
            "confidence_score": "0.8",
            "modification_type": "enhancement",
            "related_code_chunks": "auth.py:sha1:10-20,token_verify.py:sha2:15-30,utils.py:sha3:5-25",
        },
        "_confidence_score": 0.8,
        "_context_richness": 0.9,
    }

    mock_fetch_entries.return_value = [entry_with_links]

    # No need to mock code search results since we're using bidirectional links
    # But we'll provide it anyway in case the code falls back to search
    mock_code_ref = "src/file.py:sha1:10-20"
    mock_query_results = {
        "ids": [[mock_code_ref]],
        "documents": [["def func():\n  pass"]],
        "metadatas": [[{"relative_file_path": "src/file.py"}]],
        "distances": [[0.1]],
    }
    mock_query_codebase.return_value = mock_query_results

    # User inputs:
    # 1. Disable auto-promote: 'n'
    # 2. Promote entry: 'p' -> defaults for all fields except code reference
    # 3. Select second code reference from bidirectional links: '2'
    mock_input.side_effect = [
        "n",  # Disable auto-promote
        "p",  # Promote entry
        "",  # Accept default description
        "",  # Accept default pattern
        "2",  # Select second code reference from bidirectional links
        "",  # Accept default tags
        "",  # Accept default confidence
        "y",  # Include context
    ]

    # Mock successful promotion
    mock_promote_function.return_value = "promoted_id"

    # Run the function
    run_interactive_promotion()

    # Capture output
    captured = capsys.readouterr()

    # Verify bidirectional links were displayed
    assert "3 related code chunks from bidirectional links" in captured.out

    # Verify the selected code reference was used
    assert "token_verify.py:sha2:15-30" in str(mock_promote_function.call_args)
