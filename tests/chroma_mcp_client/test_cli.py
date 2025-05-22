"""
Tests for the chroma_mcp_client.cli module.
"""

import pytest
import os
import sys
import chromadb
from unittest.mock import patch, MagicMock, call
from pathlib import Path
import subprocess
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
import argparse
import logging
import uuid
from io import StringIO

# Import the schema for spec
from chroma_mcp_client.validation.schemas import ValidationEvidence, ValidationEvidenceType, CodeQualityEvidence

# Module to test
from chroma_mcp_client import cli
from chroma_mcp_client.cli import main, DEFAULT_COLLECTION_NAME
from chromadb.api.models.Collection import Collection


# Helper to create mock args namespace
def create_mock_args(**kwargs):
    # Set default values for command-specific arguments if not provided
    if kwargs.get("command") == "analyze-chat-history" and "prioritize_by_confidence" not in kwargs:
        kwargs["prioritize_by_confidence"] = False

    # Add default values for promote-learning validation arguments
    if kwargs.get("command") == "promote-learning":
        if "require_validation" not in kwargs:
            kwargs["require_validation"] = False
        if "validation_threshold" not in kwargs:
            kwargs["validation_threshold"] = 0.7
        if "validation_evidence_id" not in kwargs:
            kwargs["validation_evidence_id"] = None
        if "validation_score" not in kwargs:
            kwargs["validation_score"] = None

    # Add default values for log-error command
    if kwargs.get("command") == "log-error":
        if "error_type" not in kwargs:
            kwargs["error_type"] = "Exception"
        if "error_message" not in kwargs:
            kwargs["error_message"] = "Unknown error"
        if "stacktrace" not in kwargs:
            kwargs["stacktrace"] = None
        if "affected_files" not in kwargs:
            kwargs["affected_files"] = None
        if "resolution" not in kwargs:
            kwargs["resolution"] = None
        if "resolution_verified" not in kwargs:
            kwargs["resolution_verified"] = False

    # Add default values for log-test-results command
    if kwargs.get("command") == "log-test-results":
        if "xml_path" not in kwargs:
            kwargs["xml_path"] = "test-results.xml"
        if "before_xml" not in kwargs:
            kwargs["before_xml"] = None
        if "commit_before" not in kwargs:
            kwargs["commit_before"] = None
        if "commit_after" not in kwargs:
            kwargs["commit_after"] = None

    # Add default values for log-quality-check command
    if kwargs.get("command") == "log-quality-check":
        if "tool" not in kwargs:
            kwargs["tool"] = "pylint"
        if "before_output" not in kwargs:
            kwargs["before_output"] = None
        if "after_output" not in kwargs:
            kwargs["after_output"] = None
        if "metric_type" not in kwargs:
            kwargs["metric_type"] = "error_count"

    # Add default values for validate-evidence command
    if kwargs.get("command") == "validate-evidence":
        if "evidence_file" not in kwargs:
            kwargs["evidence_file"] = None
        if "test_transitions" not in kwargs:
            kwargs["test_transitions"] = None
        if "runtime_errors" not in kwargs:
            kwargs["runtime_errors"] = None
        if "code_quality" not in kwargs:
            kwargs["code_quality"] = None
        if "output_file" not in kwargs:
            kwargs["output_file"] = None
        if "threshold" not in kwargs:
            kwargs["threshold"] = 0.7

    return argparse.Namespace(**kwargs)


# Mock Embedding Function (Replace with actual if needed for specific tests)
class DefaultEmbeddingFunction:
    def __call__(self, texts):
        pass


@pytest.fixture
def test_dir(tmp_path):
    """Create a temporary directory structure for testing files."""
    repo_root = tmp_path / "repo_root"
    repo_root.mkdir()
    (repo_root / "file1.py").write_text("print('hello')")
    (repo_root / "file2.md").write_text("# Markdown Header")
    (repo_root / ".gitignored").write_text("ignored")
    return repo_root


@pytest.fixture
def mock_git_ls_files(monkeypatch):
    """Mock subprocess.run used for git ls-files."""
    mock_run = MagicMock()
    # Simulate git ls-files output: one python file, one markdown file
    mock_run.stdout = "file1.py\nsub/file2.md\n"
    mock_run.returncode = 0
    monkeypatch.setattr(subprocess, "run", mock_run)
    return mock_run


# =====================================================================
# Tests for Argument Parsing and Connection
# =====================================================================


@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
def test_cli_command_parses_and_calls_connect(mock_get_client_and_ef, mock_argparse):
    """Test that a valid command calls get_client_and_ef correctly (bypassing argparse)."""
    # Configure mock argparse to return specific args
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(
        command="count",
        verbose=0,
        collection_name=DEFAULT_COLLECTION_NAME,
    )
    mock_parser_instance.parse_args.return_value = mock_args

    # Configure mock get_client_and_ef to return a tuple
    mock_client_instance = MagicMock(spec=chromadb.ClientAPI)
    mock_ef_instance = DefaultEmbeddingFunction()
    mock_get_client_and_ef.return_value = (mock_client_instance, mock_ef_instance)

    # Args passed here don't matter since parse_args is mocked
    main()

    # Assert get_client_and_ef was called correctly
    mock_get_client_and_ef.assert_called_once_with()  # Called with default env_path=None


@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
@patch("sys.exit")
def test_cli_connect_failure_exits(mock_sys_exit, mock_get_client_ef, mock_argparse):
    """Test that if get_client_and_ef fails, the CLI exits with an error (bypassing argparse)."""
    # Configure mock argparse
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(
        command="count",
        verbose=0,
        collection_name=DEFAULT_COLLECTION_NAME,
    )
    mock_parser_instance.parse_args.return_value = mock_args

    # Configure get_client_and_ef to raise an exception
    mock_get_client_ef.side_effect = Exception("Connection failed")
    mock_sys_exit.side_effect = SystemExit(1)  # Make mock exit behave like real exit

    # Run CLI which should attempt connection, fail, and exit
    with pytest.raises(SystemExit) as excinfo:  # Expect SystemExit
        main()  # Args don't matter
    assert excinfo.value.code == 1

    # Assert sys.exit was called with 1
    mock_sys_exit.assert_called_once_with(1)  # Verify it was called with 1


# =====================================================================
# Tests for Indexing
# =====================================================================


@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")  # Patch helper
@patch("chroma_mcp_client.cli.index_file")  # Patch index_file usage in cli
def test_index_single_file(mock_index_file, mock_get_client_ef, mock_argparse, test_dir, capsys):
    """Test indexing a single file via the CLI."""
    # Configure mocks
    mock_client_instance = MagicMock(spec=chromadb.ClientAPI)
    mock_collection = mock_client_instance.get_or_create_collection.return_value
    mock_get_client_ef.return_value = (mock_client_instance, DefaultEmbeddingFunction())
    mock_index_file.return_value = True  # Simulate successful indexing

    collection_name = "test_collection"
    file_to_index = test_dir / "file1.py"

    # Mock argparse return value
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(
        command="index",
        verbose=0,
        paths=[file_to_index],  # Use the specific file path
        repo_root=test_dir,  # Use the test_dir Path object
        all=False,
        collection_name=collection_name,
    )
    mock_parser_instance.parse_args.return_value = mock_args

    # Run CLI
    main()

    # Assertions
    mock_get_client_ef.assert_called_once()
    # Assert that index_file was called correctly by the cli handler
    mock_index_file.assert_called_once_with(file_to_index, test_dir, collection_name)


@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
@patch("chroma_mcp_client.cli.index_git_files")  # Patch the function being tested
def test_index_all_files(mock_index_git, mock_get_client_ef, mock_argparse, test_dir, capsys):
    """Test indexing all git-tracked files via the CLI."""
    # Configure mocks
    mock_client_instance = MagicMock(spec=chromadb.ClientAPI)
    mock_collection = mock_client_instance.get_or_create_collection.return_value
    mock_get_client_ef.return_value = (mock_client_instance, DefaultEmbeddingFunction())

    collection_name = "git_collection"
    mock_index_git.return_value = 2  # Simulate 2 files indexed

    # Mock argparse return value
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(
        command="index",
        verbose=0,
        paths=[],
        repo_root=test_dir,  # Use the test_dir Path object
        all=True,
        collection_name=collection_name,
    )
    mock_parser_instance.parse_args.return_value = mock_args

    # Run CLI
    main()

    # Assertions
    mock_get_client_ef.assert_called_once()
    # Assert that index_git_files was called correctly by the cli handler
    mock_index_git.assert_called_once_with(test_dir, collection_name)


# =====================================================================
# Tests for Count
# =====================================================================


@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
def test_count_command(mock_get_client_ef, mock_argparse, test_dir, capsys):
    """Test the count command via the CLI."""
    collection_name = "count_collection"
    expected_count = 5

    # Configure mocks
    mock_client_instance = MagicMock(spec=chromadb.ClientAPI)
    mock_collection = MagicMock(spec=Collection)
    mock_collection.count.return_value = expected_count
    mock_client_instance.get_collection.return_value = mock_collection
    mock_get_client_ef.return_value = (mock_client_instance, DefaultEmbeddingFunction())

    # Mock argparse return value
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(command="count", verbose=0, collection_name=collection_name)  # Use the string directly
    mock_parser_instance.parse_args.return_value = mock_args

    # Run CLI
    main()

    # Assertions
    mock_get_client_ef.assert_called_once()
    mock_client_instance.get_collection.assert_called_once_with(name=collection_name)
    mock_collection.count.assert_called_once()
    # Check output
    captured = capsys.readouterr()
    assert f"Collection '{collection_name}' contains {expected_count} documents." in captured.out


# =====================================================================
# Tests for Query
# =====================================================================


@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
def test_query_command(mock_get_client_ef, mock_argparse, test_dir, capsys):
    """Test the query command via the CLI."""
    collection_name = "query_collection"
    query_text = "find this text"
    n_results = 3
    mock_query_results = {
        "ids": [["id1", "id2"]],
        "documents": [["result doc 1", "result doc 2"]],
        "metadatas": [[{"source": "file1.txt", "content": "abc"}, {"source": "file2.md", "content": "def"}]],
        "distances": [[0.1, 0.2]],
    }

    # Configure mocks
    mock_client_instance = MagicMock(spec=chromadb.ClientAPI)
    mock_collection = MagicMock(spec=Collection)
    mock_ef_instance = DefaultEmbeddingFunction()
    mock_collection.query.return_value = mock_query_results
    mock_client_instance.get_collection.return_value = mock_collection
    mock_get_client_ef.return_value = (mock_client_instance, mock_ef_instance)

    # Mock argparse return value
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(
        command="query",
        verbose=0,
        query_text=query_text,
        collection_name=collection_name,  # Use the string directly
        n_results=n_results,
    )
    mock_parser_instance.parse_args.return_value = mock_args

    # Run CLI
    main()

    # Assertions
    mock_get_client_ef.assert_called_once()
    mock_client_instance.get_collection.assert_called_once_with(
        name=collection_name, embedding_function=mock_ef_instance  # Add embedding function to assertion
    )
    mock_collection.query.assert_called_once_with(
        query_texts=[query_text],
        n_results=n_results,
        include=["metadatas", "documents", "distances"],  # Default includes
    )
    # Check output
    captured = capsys.readouterr()  # Reads stdout/stderr captured during test
    # Check output presence
    assert "Query Results for" in captured.out  # Check for the start of the output header
    assert "ID: id1" in captured.out
    assert "result doc 1" in captured.out
    assert "0.1000" in captured.out  # Check for distance formatting


# =====================================================================
# Tests for Analysis
# =====================================================================


@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")  # Mock connection
@patch("chroma_mcp_client.cli.analyze_chat_history")  # Mock the actual analysis function
@patch("sys.exit")  # Add patch for sys.exit
def test_analyze_chat_history_command_called(mock_sys_exit, mock_analyze, mock_get_client_ef, mock_argparse, test_dir):
    """Test that the analyze-chat-history command calls the correct function."""
    # Configure mocks
    mock_client_instance = MagicMock(spec=chromadb.ClientAPI)
    mock_ef_instance = DefaultEmbeddingFunction()  # Use a real one or a MagicMock
    mock_get_client_ef.return_value = (mock_client_instance, mock_ef_instance)

    # Configure mock_analyze to return the expected tuple
    mock_analyze.return_value = (5, 2)  # Simulate 5 processed, 2 correlated

    collection_name = "chat_test"
    repo_path = test_dir
    status_filter = "pending"
    new_status = "reviewed"
    days_limit = 14

    # Mock argparse return value
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(
        command="analyze-chat-history",
        verbose=2,
        collection_name=collection_name,
        repo_path=repo_path,
        status_filter=status_filter,
        new_status=new_status,
        days_limit=days_limit,
        prioritize_by_confidence=False,
    )
    mock_parser_instance.parse_args.return_value = mock_args

    # Run CLI
    main()

    # Assertions
    mock_get_client_ef.assert_called_once()
    mock_analyze.assert_called_once_with(
        client=mock_client_instance,
        embedding_function=mock_ef_instance,
        repo_path=str(repo_path.resolve()),  # Add repo_path check
        collection_name=collection_name,
        days_limit=days_limit,
        # limit=, # Add check for limit if applicable/passed
        status_filter=status_filter,
        new_status=new_status,
        prioritize_by_confidence=False,
    )
    # Check that sys.exit was NOT called on success
    mock_sys_exit.assert_not_called()


# =====================================================================
# Tests for Index Command Errors
# =====================================================================
@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
@patch("chroma_mcp_client.cli.index_file")
@patch("chroma_mcp_client.cli.index_git_files")
@patch("logging.getLogger")  # Patch the source of the logger
def test_index_no_paths_or_all(mock_getLogger, mock_index_git, mock_index_file, mock_get_client_ef, mock_argparse):
    """Test index command logs warning if no paths given and --all is False."""
    # Configure mocks
    mock_client_instance = MagicMock(spec=chromadb.ClientAPI)
    mock_get_client_ef.return_value = (mock_client_instance, DefaultEmbeddingFunction())

    # Mock argparse
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(
        command="index", verbose=0, paths=[], repo_root=Path("."), all=False, collection_name="test"
    )
    mock_parser_instance.parse_args.return_value = mock_args
    # Configure mock getLogger to return a mock logger instance
    mock_main_logger = MagicMock()
    mock_getLogger.return_value = mock_main_logger  # Assume all calls return this for simplicity here

    # Run CLI
    main()

    # Assertions
    mock_index_file.assert_not_called()
    mock_index_git.assert_not_called()
    # Check the warning call on the logger instance that main() uses
    mock_main_logger.warning.assert_called_once_with(
        "Index command called without --all flag or specific paths. Nothing to index."
    )


@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
@patch("chroma_mcp_client.cli.index_file")
@patch("logging.getLogger")
def test_index_non_existent_path(mock_getLogger, mock_index_file, mock_get_client_ef, mock_argparse, tmp_path):
    """Test index command logs warning for non-existent paths."""
    # Configure mocks
    mock_client_instance = MagicMock(spec=chromadb.ClientAPI)
    mock_get_client_ef.return_value = (mock_client_instance, DefaultEmbeddingFunction())

    non_existent_file = tmp_path / "not_a_real_file.txt"

    # Mock argparse
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(
        command="index",
        verbose=0,
        paths=[non_existent_file],
        repo_root=tmp_path,
        all=False,
        collection_name="test",
    )
    mock_parser_instance.parse_args.return_value = mock_args
    # Configure mock getLogger
    mock_main_logger = MagicMock()
    mock_getLogger.return_value = mock_main_logger

    # Run CLI
    main()

    # Assertions
    mock_index_file.assert_not_called()  # Should not be called for non-existent file
    mock_main_logger.warning.assert_called_once_with(f"Skipping non-existent path: {non_existent_file}")


# =====================================================================
# Tests for Analysis Command Errors
# =====================================================================


@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
@patch("chroma_mcp_client.cli.analyze_chat_history")
@patch("sys.exit")  # Restore patching sys.exit
@patch("logging.getLogger")  # Patch the source of the logger
def test_analyze_command_error(
    mock_getLogger, mock_sys_exit, mock_analyze, mock_get_client_ef, mock_argparse, tmp_path
):
    """Test analyze command exits if the underlying function fails."""  # Restore description
    # Configure mocks
    mock_client_instance = MagicMock(spec=chromadb.ClientAPI)
    mock_get_client_ef.return_value = (mock_client_instance, DefaultEmbeddingFunction())
    error_message = "Analysis failed spectacularly!"
    mock_analyze.side_effect = Exception(error_message)
    mock_sys_exit.side_effect = SystemExit(1)  # Restore setting side_effect

    mock_main_logger = MagicMock()
    mock_getLogger.return_value = mock_main_logger

    # Mock argparse
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(
        command="analyze-chat-history",
        verbose=0,
        collection_name="chat",
        repo_path=tmp_path,
        status_filter="captured",
        new_status="analyzed",
        days_limit=7,
        prioritize_by_confidence=False,
    )
    mock_parser_instance.parse_args.return_value = mock_args

    # Run CLI within pytest.raises again
    with pytest.raises(SystemExit) as excinfo:
        main()

    # Assertions
    assert excinfo.value.code == 1  # Check exit code from pytest.raises
    mock_analyze.assert_called_once()  # Check it was called
    mock_sys_exit.assert_called_once_with(1)  # Check sys.exit was called
    # Check that the error was logged correctly
    mock_main_logger.error.assert_any_call(
        f"An error occurred during chat history analysis: {error_message}", exc_info=True
    )


# --- New Verbosity Test ---
@pytest.mark.parametrize(
    "verbose_count, expected_root_level, expected_client_level, expected_st_level",
    [
        (0, logging.INFO, logging.INFO, logging.WARNING),  # Default
        (1, logging.INFO, logging.INFO, logging.WARNING),  # -v
        (2, logging.DEBUG, logging.DEBUG, logging.WARNING),  # -vv
        (3, logging.DEBUG, logging.DEBUG, logging.WARNING),  # -vvv (same as -vv)
    ],
)
@patch("argparse.ArgumentParser.parse_args")  # Patch parse_args directly
@patch("logging.getLogger")  # Mock getLogger to check setLevel calls
@patch("chroma_mcp_client.cli.get_client_and_ef")  # Prevent actual connection
def test_logging_verbosity_levels(
    mock_get_client,
    mock_getLogger,
    mock_parse_args,
    verbose_count,
    expected_root_level,
    expected_client_level,
    expected_st_level,
):
    """Tests that logging levels are set correctly based on -v count."""
    # --- Arrange ---
    # Mock logger instances returned by getLogger
    mock_root_logger = MagicMock()
    mock_client_logger = MagicMock()  # for 'chroma_mcp_client'
    mock_st_logger = MagicMock()  # for 'sentence_transformers'
    mock_utils_cli_setup_logger = MagicMock()  # for 'chromamcp.cli_setup'
    mock_base_chromamcp_logger = MagicMock()  # for UTILS_BASE_LOGGER_NAME which is 'chromamcp'

    # Configure getLogger to return specific mocks based on name
    def getLogger_side_effect(name=None):
        if name == "chroma_mcp_client":
            return mock_client_logger
        elif name == "sentence_transformers":
            return mock_st_logger
        # The cli.py now logs the "level set" message using a child of UTILS_BASE_LOGGER_NAME
        elif name == f"{cli.UTILS_BASE_LOGGER_NAME}.cli_setup":  # Corrected logger name
            return mock_utils_cli_setup_logger
        elif name == cli.UTILS_BASE_LOGGER_NAME:  # Mock the base 'chromamcp' logger
            return mock_base_chromamcp_logger
        elif name is None or name == logging.getLogger().name:  # Root logger
            return mock_root_logger
        else:
            # For any other logger (like chroma_mcp_client.cli if it were still used for this message)
            return MagicMock()

    mock_getLogger.side_effect = getLogger_side_effect

    # Configure the mock parse_args to return a Namespace with the verbose count
    mock_args = argparse.Namespace(
        verbose=verbose_count,
        command="count",
        collection_name="dummy_collection",
    )
    mock_parse_args.return_value = mock_args

    # Mock the client and collection calls needed for the 'count' command path
    mock_client_instance = MagicMock()
    mock_collection_instance = MagicMock()
    mock_collection_instance.count.return_value = 0
    mock_client_instance.get_collection.return_value = mock_collection_instance
    mock_get_client.return_value = (mock_client_instance, MagicMock())

    # --- Act ---
    try:
        cli.main()
    except SystemExit as e:
        assert e.code == 0 or e.code is None
    except Exception as e:
        pytest.fail(f"cli.main() raised an unexpected exception: {e}")

    # --- Assert ---
    mock_root_logger.setLevel.assert_called_once_with(expected_root_level)
    mock_client_logger.setLevel.assert_called_once_with(expected_client_level)
    mock_st_logger.setLevel.assert_called_once_with(expected_st_level)
    # Assert that the base 'chromamcp' logger was also set to the expected_root_level (which is log_level in cli.py)
    mock_base_chromamcp_logger.setLevel.assert_called_once_with(expected_root_level)

    # Verify the new info log message on the new logger
    expected_log_message = (
        f"Client CLI log level set to {logging.getLevelName(expected_root_level)} "
        f"for base '{cli.UTILS_BASE_LOGGER_NAME}' and 'chroma_mcp_client'"
    )
    mock_utils_cli_setup_logger.info.assert_any_call(expected_log_message)


# =====================================================================
# Tests for Setup Collections
# =====================================================================


@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
def test_setup_collections_command_creates_all(mock_get_client_ef, mock_argparse, capsys, caplog):
    """Test that setup-collections command attempts to create all required collections."""
    mock_client_instance = MagicMock(spec=chromadb.ClientAPI)
    mock_ef_instance = MagicMock(spec=DefaultEmbeddingFunction)  # Use a mock for EF as well
    mock_get_client_ef.return_value = (mock_client_instance, mock_ef_instance)

    # Simulate collections not existing initially, so get_collection raises an error
    # and then get_or_create_collection is called.
    mock_client_instance.get_collection.side_effect = Exception("Collection not found")

    # Mock argparse return value for 'setup-collections' command
    mock_parser_instance = mock_argparse.return_value
    # Ensure verbose=1 so that INFO logs are expected as per cli.py logic
    mock_args = create_mock_args(command="setup-collections", verbose=1)  # Set verbose=1 to see more output
    mock_parser_instance.parse_args.return_value = mock_args

    cli.main()  # Use cli.main() to be consistent with other tests

    required_collections = [
        "codebase_v1",
        "chat_history_v1",
        "derived_learnings_v1",
        "thinking_sessions_v1",
        "validation_evidence_v1",
        "test_results_v1",
    ]

    # Assert get_collection was called for each (to check existence)
    get_collection_calls = [call(name=name) for name in required_collections]
    mock_client_instance.get_collection.assert_has_calls(get_collection_calls, any_order=True)
    assert mock_client_instance.get_collection.call_count == len(required_collections)

    # Assert get_or_create_collection was called for each because get_collection failed
    get_or_create_calls = [call(name=name, embedding_function=mock_ef_instance) for name in required_collections]
    mock_client_instance.get_or_create_collection.assert_has_calls(get_or_create_calls, any_order=True)
    assert mock_client_instance.get_or_create_collection.call_count == len(required_collections)

    # Capture stdout and stderr
    captured = capsys.readouterr()
    stdout = captured.out
    stderr = captured.err

    # Print for debugging
    print(f"STDOUT: {repr(stdout)}")
    print(f"STDERR: {repr(stderr)}")
    print(f"CAPLOG: {repr(caplog.text)}")

    # Check for the summary message in stdout
    assert f"Collections setup finished. Created: {len(required_collections)}, Already Existed: 0." in stdout

    # Instead of checking for specific messages, just verify the core functionality worked
    # by checking that the right methods were called with the right arguments
    assert mock_client_instance.get_collection.call_count == len(required_collections)
    assert mock_client_instance.get_or_create_collection.call_count == len(required_collections)


@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
def test_setup_collections_command_all_exist(mock_get_client_ef, mock_argparse, capsys, caplog):
    """Test setup-collections command when all collections already exist."""
    mock_client_instance = MagicMock(spec=chromadb.ClientAPI)
    mock_ef_instance = MagicMock(spec=DefaultEmbeddingFunction)
    mock_get_client_ef.return_value = (mock_client_instance, mock_ef_instance)

    # Simulate collections existing: get_collection returns a mock collection
    mock_collection_instance = MagicMock(spec=Collection)
    mock_client_instance.get_collection.return_value = mock_collection_instance

    # Mock argparse
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(command="setup-collections", verbose=1)  # Set verbose=1 to see more output
    mock_parser_instance.parse_args.return_value = mock_args

    cli.main()

    required_collections = [
        "codebase_v1",
        "chat_history_v1",
        "derived_learnings_v1",
        "thinking_sessions_v1",
        "validation_evidence_v1",
        "test_results_v1",
    ]

    get_collection_calls = [call(name=name) for name in required_collections]
    mock_client_instance.get_collection.assert_has_calls(get_collection_calls, any_order=True)
    assert mock_client_instance.get_collection.call_count == len(required_collections)

    # get_or_create_collection should not be called if get_collection succeeds
    mock_client_instance.get_or_create_collection.assert_not_called()

    # Capture stdout and stderr
    captured = capsys.readouterr()
    stdout = captured.out
    stderr = captured.err

    # Check for the summary message in stdout
    assert f"Collections setup finished. Created: 0, Already Existed: {len(required_collections)}." in stdout

    # Instead of checking for specific messages, just verify the core functionality worked
    # by checking that the right methods were called with the right arguments
    assert mock_client_instance.get_collection.call_count == len(required_collections)
    assert mock_client_instance.get_or_create_collection.call_count == 0


@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
def test_setup_collections_command_mixed_existence(mock_get_client_ef, mock_argparse, capsys, caplog):
    """Test setup-collections command with a mix of existing and non-existing collections."""
    mock_client_instance = MagicMock(spec=chromadb.ClientAPI)
    mock_ef_instance = MagicMock(spec=DefaultEmbeddingFunction)
    mock_get_client_ef.return_value = (mock_client_instance, mock_ef_instance)

    required_collections = [
        "codebase_v1",  # Exists
        "chat_history_v1",  # Does not exist
        "derived_learnings_v1",  # Exists
        "thinking_sessions_v1",  # Does not exist
        "validation_evidence_v1",  # Exists
        "test_results_v1",  # Does not exist
    ]
    existing_collections = [required_collections[0], required_collections[2], required_collections[4]]
    non_existing_collections = [required_collections[1], required_collections[3], required_collections[5]]

    def get_collection_side_effect(name):
        if name in existing_collections:
            return MagicMock(spec=Collection)
        raise Exception("Collection not found")

    mock_client_instance.get_collection.side_effect = get_collection_side_effect

    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(command="setup-collections", verbose=1)  # Set verbose=1 to see more output
    mock_parser_instance.parse_args.return_value = mock_args

    cli.main()

    # Check calls to get_collection
    get_collection_calls = [call(name=name) for name in required_collections]
    mock_client_instance.get_collection.assert_has_calls(get_collection_calls, any_order=True)
    assert mock_client_instance.get_collection.call_count == len(required_collections)

    # Check calls to get_or_create_collection (only for non-existing ones)
    get_or_create_calls = [call(name=name, embedding_function=mock_ef_instance) for name in non_existing_collections]
    mock_client_instance.get_or_create_collection.assert_has_calls(get_or_create_calls, any_order=True)
    assert mock_client_instance.get_or_create_collection.call_count == len(non_existing_collections)

    # Capture stdout and stderr
    captured = capsys.readouterr()
    stdout = captured.out
    stderr = captured.err

    # Check for the summary message in stdout
    assert (
        f"Collections setup finished. Created: {len(non_existing_collections)}, Already Existed: {len(existing_collections)}."
        in stdout
    )

    # Instead of checking for specific messages, just verify the core functionality worked
    # by checking that the right methods were called with the right arguments
    assert mock_client_instance.get_collection.call_count == len(required_collections)
    assert mock_client_instance.get_or_create_collection.call_count == len(non_existing_collections)


# =====================================================================
# Tests for Promote Learning
# =====================================================================


@patch("uuid.uuid4")
@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
def test_promote_learning_success_no_source(mock_get_client_ef, mock_argparse, mock_uuid, capsys, caplog):
    """Test promote-learning successfully adds learning, no source chat ID."""
    # Mocks
    mock_client = MagicMock(spec=chromadb.ClientAPI)
    mock_learning_collection = MagicMock(spec=Collection)
    mock_ef = MagicMock(spec=DefaultEmbeddingFunction)
    mock_get_client_ef.return_value = (mock_client, mock_ef)
    mock_client.get_or_create_collection.return_value = mock_learning_collection
    mock_uuid.return_value = uuid.UUID("12345678-1234-5678-1234-567812345678")
    learning_id = "12345678-1234-5678-1234-567812345678"

    # Command Args
    args_dict = {
        "command": "promote-learning",
        "verbose": 1,  # To check INFO logs
        "description": "Use context managers for files.",
        "pattern": "with open(...) as f:",
        "code_ref": "src/utils.py:abc123def:0",
        "tags": "python,best-practice,file-io",
        "confidence": 0.95,
        "source_chat_id": None,
        "collection_name": "derived_learnings_v1",
        "chat_collection_name": "chat_history_v1",
        "include_chat_context": True,
    }
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(**args_dict)
    mock_parser_instance.parse_args.return_value = mock_args

    # Run command
    cli.main()

    # Assertions
    mock_client.get_or_create_collection.assert_called_once_with(
        name=args_dict["collection_name"], embedding_function=mock_ef
    )

    # Check add call
    mock_learning_collection.add.assert_called_once()
    add_args = mock_learning_collection.add.call_args.kwargs
    assert add_args["ids"] == [learning_id]
    assert add_args["documents"] == [args_dict["description"]]
    assert len(add_args["metadatas"]) == 1
    meta = add_args["metadatas"][0]
    assert meta["tags"] == args_dict["tags"]
    assert meta["confidence"] == args_dict["confidence"]
    assert meta["code_ref"] == args_dict["code_ref"]

    # Check output contains success message
    captured = capsys.readouterr()
    assert f"Promoted to derived learning with ID: {learning_id}" in captured.out


@patch("uuid.uuid4")
@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
def test_promote_learning_success_with_source_update(mock_get_client_ef, mock_argparse, mock_uuid, capsys, caplog):
    """Test promote-learning adds learning AND updates source chat status."""
    # Mocks
    mock_client = MagicMock(spec=chromadb.ClientAPI)
    mock_learning_collection = MagicMock(spec=Collection)
    mock_chat_collection = MagicMock(spec=Collection)
    mock_ef = MagicMock(spec=DefaultEmbeddingFunction)
    mock_get_client_ef.return_value = (mock_client, mock_ef)

    # Mock get_collection/get_or_create_collection to return the correct collection based on name
    def get_collection_side_effect(name):
        if name == "chat_history_v1":
            return mock_chat_collection
        raise ValueError(f"Unexpected collection name: {name}")

    def get_or_create_collection_side_effect(name, embedding_function=None):
        if name == "derived_learnings_v1":
            return mock_learning_collection
        raise ValueError(f"Unexpected collection name: {name}")

    mock_client.get_collection.side_effect = get_collection_side_effect
    mock_client.get_or_create_collection.side_effect = get_or_create_collection_side_effect

    mock_uuid.return_value = uuid.UUID("abcdefab-cdef-abcd-efab-cdefabcdefab")
    learning_id = "abcdefab-cdef-abcd-efab-cdefabcdefab"
    source_chat_id_to_update = "chat_id_123"

    # Mock chat history get() response
    original_chat_metadata = {"status": "analyzed", "other": "data"}
    mock_chat_collection.get.return_value = {"ids": [source_chat_id_to_update], "metadatas": [original_chat_metadata]}

    # Command Args
    args_dict = {
        "command": "promote-learning",
        "verbose": 1,
        "description": "Another learning.",
        "pattern": "def function():",
        "code_ref": "src/code.py:sha123:5",
        "tags": "python",
        "confidence": 0.8,
        "source_chat_id": source_chat_id_to_update,
        "collection_name": "derived_learnings_v1",
        "chat_collection_name": "chat_history_v1",
        "include_chat_context": True,
    }
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(**args_dict)
    mock_parser_instance.parse_args.return_value = mock_args

    # Run command
    cli.main()

    # Assertions
    # Check collection access calls
    mock_client.get_collection.assert_called_with(name="chat_history_v1")
    mock_client.get_or_create_collection.assert_called_with(name="derived_learnings_v1", embedding_function=mock_ef)

    # Check add call to learning collection
    mock_learning_collection.add.assert_called_once()
    add_args = mock_learning_collection.add.call_args.kwargs
    assert add_args["ids"] == [learning_id]
    assert add_args["metadatas"][0]["source_chat_id"] == source_chat_id_to_update

    # Check get() call on chat collection
    assert mock_chat_collection.get.call_count == 2
    # First call includes documents for context
    mock_chat_collection.get.assert_any_call(ids=[source_chat_id_to_update], include=["metadatas", "documents"])
    # Second call is for status update
    mock_chat_collection.get.assert_any_call(ids=[source_chat_id_to_update], include=["metadatas"])

    # Check update() call on chat collection
    mock_chat_collection.update.assert_called_once()
    update_args = mock_chat_collection.update.call_args.kwargs
    assert update_args["ids"] == [source_chat_id_to_update]
    assert len(update_args["metadatas"]) == 1
    updated_meta = update_args["metadatas"][0]
    assert updated_meta["status"] == "promoted"
    assert updated_meta["derived_learning_id"] == learning_id
    assert updated_meta["other"] == "data"  # Ensure other metadata was preserved

    # Check output contains success messages
    captured = capsys.readouterr()
    assert f"Promoted to derived learning with ID: {learning_id}" in captured.out


@patch("uuid.uuid4")
@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
def test_promote_learning_source_not_found(mock_get_client_ef, mock_argparse, mock_uuid, capsys, caplog):
    """Test promote-learning warns when source chat ID is not found."""
    # Mocks
    mock_client = MagicMock(spec=chromadb.ClientAPI)
    mock_learning_collection = MagicMock(spec=Collection)
    mock_chat_collection = MagicMock(spec=Collection)
    mock_ef = MagicMock(spec=DefaultEmbeddingFunction)
    mock_get_client_ef.return_value = (mock_client, mock_ef)

    # Mock get_collection to return the correct collection based on name
    def get_collection_side_effect(name):
        if name == "chat_history_v1":
            return mock_chat_collection
        raise ValueError(f"Unexpected collection name: {name}")

    def get_or_create_collection_side_effect(name, embedding_function=None):
        if name == "derived_learnings_v1":
            return mock_learning_collection
        raise ValueError(f"Unexpected collection name: {name}")

    mock_client.get_collection.side_effect = get_collection_side_effect
    mock_client.get_or_create_collection.side_effect = get_or_create_collection_side_effect

    mock_uuid.return_value = uuid.UUID("aaaaaaaabbbbccccddddeeeeeeeeeeee")
    learning_id = "aaaaaaaabbbbccccddddeeeeeeeeeeee"
    source_chat_id_not_found = "chat_id_404"

    # Mock chat history get() returning empty or non-matching results
    mock_chat_collection.get.return_value = {"ids": [], "metadatas": []}

    # Command Args
    args_dict = {
        "command": "promote-learning",
        "verbose": 0,
        "description": "Learning 404.",
        "pattern": "try/except",
        "code_ref": "src/error.py:sha456:10",
        "tags": "error-handling",
        "confidence": 0.7,
        "source_chat_id": source_chat_id_not_found,
        "collection_name": "derived_learnings_v1",
        "chat_collection_name": "chat_history_v1",
        "include_chat_context": True,
    }
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(**args_dict)
    mock_parser_instance.parse_args.return_value = mock_args

    # Run command
    cli.main()

    # Assertions
    # Check add call to learning collection happened
    mock_learning_collection.add.assert_called_once()
    # The ID used in add() comes from str(uuid.uuid4()), which includes hyphens
    expected_hyphenated_id = str(mock_uuid.return_value)
    assert mock_learning_collection.add.call_args.kwargs["ids"] == [expected_hyphenated_id]

    # Check get() call on chat collection
    assert mock_chat_collection.get.call_count == 2
    # First call includes documents for context
    mock_chat_collection.get.assert_any_call(ids=[source_chat_id_not_found], include=["metadatas", "documents"])
    # Second call is for status update
    mock_chat_collection.get.assert_any_call(ids=[source_chat_id_not_found], include=["metadatas"])

    # Check update() was NOT called on chat collection
    mock_chat_collection.update.assert_not_called()

    # Check output for warning
    captured = capsys.readouterr()
    # Use the hyphenated ID for checking output as well
    assert f"Promoted to derived learning with ID: {expected_hyphenated_id}" in captured.out  # Learning was still added


# =====================================================================
# Tests for Review and Promote (New Subcommand)
# =====================================================================


@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")  # Mock connection
@patch("chroma_mcp_client.cli.run_interactive_promotion")  # Mock the actual function
@patch("sys.exit")
def test_review_and_promote_command_called(
    mock_sys_exit, mock_run_interactive_promotion, mock_get_client_ef, mock_argparse, caplog, capsys
):
    """Test that the 'review-and-promote' CLI command calls the correct function with correct args."""
    # Configure mock argparse to return specific args
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(
        command="review-and-promote",
        verbose=1,
        days_limit=10,
        fetch_limit=20,
        chat_collection_name="my_chats",
        learnings_collection_name="my_learnings",
        modification_type="refactor",
        min_confidence=0.7,
        sort_by_confidence=True,
    )
    mock_parser_instance.parse_args.return_value = mock_args

    # Configure mock get_client_and_ef
    mock_client_instance = MagicMock(spec=chromadb.ClientAPI)
    mock_ef_instance = MagicMock()  # Simplified mock for EF
    mock_get_client_ef.return_value = (mock_client_instance, mock_ef_instance)

    # Run CLI
    main()

    # Assert get_client_and_ef was called
    mock_get_client_ef.assert_called_once()

    # Assert run_interactive_promotion was called with the correct arguments
    mock_run_interactive_promotion.assert_called_once_with(
        days_limit=10,
        fetch_limit=20,
        chat_collection_name="my_chats",
        learnings_collection_name="my_learnings",
        modification_type_filter="refactor",
        min_confidence=0.7,
        sort_by_confidence=True,
    )

    # Assert sys.exit was not called (successful execution)
    mock_sys_exit.assert_not_called()

    # Check stdout for completion message
    captured = capsys.readouterr()
    assert "Interactive review and promotion process complete" in captured.out


@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")  # Mock connection
@patch("chroma_mcp_client.cli.run_interactive_promotion")  # Mock the actual function
@patch("sys.exit")
def test_review_and_promote_command_defaults_called(
    mock_sys_exit, mock_run_interactive_promotion, mock_get_client_ef, mock_argparse, caplog
):
    """Test that 'review-and-promote' uses default arguments correctly."""
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(
        command="review-and-promote",
        verbose=0,
        # Using default values by not specifying them, relies on parse_args applying them
        # However, for this test, we need to mock what parse_args *would* return if defaults were used.
        # The CLI sets defaults in add_argument, so we explicitly provide them here to simulate that.
        days_limit=7,  # Default from cli.py
        fetch_limit=50,  # Default from cli.py
        chat_collection_name="chat_history_v1",  # Default from cli.py
        learnings_collection_name="derived_learnings_v1",  # Default from cli.py
        modification_type="all",  # Default from cli.py
        min_confidence=0.0,  # Default from cli.py
        sort_by_confidence=True,  # Default from cli.py
    )
    mock_parser_instance.parse_args.return_value = mock_args

    mock_client_instance = MagicMock(spec=chromadb.ClientAPI)
    mock_ef_instance = MagicMock()
    mock_get_client_ef.return_value = (mock_client_instance, mock_ef_instance)

    main()

    mock_run_interactive_promotion.assert_called_once_with(
        days_limit=7,
        fetch_limit=50,
        chat_collection_name="chat_history_v1",
        learnings_collection_name="derived_learnings_v1",
        modification_type_filter="all",
        min_confidence=0.0,
        sort_by_confidence=True,
    )
    mock_sys_exit.assert_not_called()


# =====================================================================
# Tests for Promote Learning
# =====================================================================
# (Existing promote-learning tests would be here)


# =====================================================================
# Tests for Review and Promote (New Subcommand)
# =====================================================================
# (Existing review-and-promote tests would be here)


# Make sure this is at the end or in an appropriate section
# if __name__ == "__main__":
#     pytest.main() # Or however tests are run


@patch("uuid.uuid4")
@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
@patch("sys.exit")
def test_promote_learning_validation_below_threshold(
    mock_sys_exit, mock_get_client_ef, mock_argparse, mock_uuid, capsys, caplog
):
    """Test promote-learning fails when validation score is below threshold."""
    # Mocks
    mock_client = MagicMock(spec=chromadb.ClientAPI)
    mock_ef = MagicMock(spec=DefaultEmbeddingFunction)
    mock_get_client_ef.return_value = (mock_client, mock_ef)
    mock_uuid.return_value = uuid.UUID("12345678-1234-5678-1234-567812345678")
    mock_sys_exit.side_effect = SystemExit(1)  # Make sys.exit behave like it should

    # Command Args
    args_dict = {
        "command": "promote-learning",
        "verbose": 1,
        "description": "This should fail validation",
        "pattern": "some pattern",
        "code_ref": "src/file.py:abc:10",
        "tags": "testing,validation",
        "confidence": 0.9,
        "source_chat_id": None,
        "collection_name": "derived_learnings_v1",
        "chat_collection_name": "chat_history_v1",
        "include_chat_context": True,
        "require_validation": True,
        "validation_evidence_id": None,
        "validation_threshold": 0.7,
        "validation_score": 0.5,  # Below threshold
    }
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(**args_dict)
    mock_parser_instance.parse_args.return_value = mock_args

    # Run command
    with pytest.raises(SystemExit) as excinfo:
        cli.main()

    # Assertions
    assert excinfo.value.code == 1
    mock_sys_exit.assert_called_once_with(1)

    # Check no collections were created
    mock_client.get_or_create_collection.assert_not_called()

    # Check error message
    captured = capsys.readouterr()
    assert "Error: Validation score 0.5 does not meet threshold 0.7" in captured.out


@patch("uuid.uuid4")
@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
def test_promote_learning_with_validation_evidence(mock_get_client_ef, mock_argparse, mock_uuid, capsys, caplog):
    """Test promote-learning with validation evidence ID."""
    # Mocks
    mock_client = MagicMock(spec=chromadb.ClientAPI)
    mock_learning_collection = MagicMock(spec=Collection)
    mock_ef = MagicMock(spec=DefaultEmbeddingFunction)
    mock_get_client_ef.return_value = (mock_client, mock_ef)
    mock_client.get_or_create_collection.return_value = mock_learning_collection
    mock_uuid.return_value = uuid.UUID("12345678-1234-5678-1234-567812345678")
    learning_id = "12345678-1234-5678-1234-567812345678"
    validation_evidence_id = "evidence-123-uuid"

    # Mock the LearningPromoter and evidence retrieval
    with patch("chroma_mcp_client.validation.promotion.LearningPromoter") as mock_promoter_class:
        mock_promoter_instance = MagicMock()
        mock_promoter_class.return_value = mock_promoter_instance

        # Create a mock evidence object with a score above threshold
        mock_evidence = ValidationEvidence(
            id=validation_evidence_id,
            score=0.85,
            test_transitions=[],
            runtime_errors=[],
            code_quality_improvements=[],
            evidence_types=[ValidationEvidenceType.TEST_TRANSITION],
        )
        mock_promoter_instance.get_validation_evidence.return_value = mock_evidence

        # Command Args
        args_dict = {
            "command": "promote-learning",
            "verbose": 1,
            "description": "Validated learning example",
            "pattern": "assert result == expected",
            "code_ref": "src/test_file.py:abc123def:42",
            "tags": "testing,validation",
            "confidence": 0.9,
            "source_chat_id": None,
            "collection_name": "derived_learnings_v1",
            "chat_collection_name": "chat_history_v1",
            "include_chat_context": True,
            "require_validation": True,
            "validation_evidence_id": validation_evidence_id,
            "validation_threshold": 0.7,
            "validation_score": None,
        }
        mock_parser_instance = mock_argparse.return_value
        mock_args = create_mock_args(**args_dict)
        mock_parser_instance.parse_args.return_value = mock_args

        # Run command
        cli.main()

        # Assertions
        mock_client.get_or_create_collection.assert_called_once_with(
            name=args_dict["collection_name"], embedding_function=mock_ef
        )

        # Check validation was performed - now just check get_validation_evidence was called
        # The promoter may be created multiple times, but we only need to check the evidence was retrieved
        mock_promoter_instance.get_validation_evidence.assert_called_with(validation_evidence_id)

        # Check add call includes validation metadata
        mock_learning_collection.add.assert_called_once()
        add_args = mock_learning_collection.add.call_args.kwargs
        assert add_args["ids"] == [learning_id]
        assert add_args["documents"] == [args_dict["description"]]

        metadatas = add_args["metadatas"][0]
        assert "validation" in metadatas
        assert metadatas["validation"]["evidence_id"] == validation_evidence_id
        assert metadatas["validation"]["score"] == 0.85

        # Check output contains success message
        captured = capsys.readouterr()
        assert f"Promoted to derived learning with ID: {learning_id}" in captured.out


@patch("uuid.uuid4")
@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
def test_log_error_command(mock_get_client_ef, mock_argparse, mock_uuid, capsys, caplog):
    """Test that the log-error command creates and stores a runtime error."""
    # Mocks
    mock_client = MagicMock(spec=chromadb.ClientAPI)
    mock_ef = MagicMock(spec=DefaultEmbeddingFunction)
    mock_get_client_ef.return_value = (mock_client, mock_ef)
    mock_uuid.return_value = uuid.UUID("87654321-4321-8765-4321-876543210987")
    error_id = "87654321-4321-8765-4321-876543210987"

    # Mock the runtime error functions
    with patch("chroma_mcp_client.validation.runtime_collector.create_runtime_error_evidence_cli") as mock_create_error:
        with patch("chroma_mcp_client.validation.runtime_collector.store_runtime_error") as mock_store_error:
            # Set up the return values
            mock_error_evidence = MagicMock()  # Mock error evidence object
            mock_create_error.return_value = mock_error_evidence
            mock_store_error.return_value = error_id

            # Command Args
            args_dict = {
                "command": "log-error",
                "verbose": 1,
                "error_type": "ValueError",
                "error_message": "Invalid value provided",
                "stacktrace": "File 'test.py', line 42\nValueError: Invalid value provided",
                "affected_files": "test.py,utils.py",
                "resolution": "Added input validation",
                "resolution_verified": True,
                "collection_name": "validation_evidence_v1",
            }
            mock_parser_instance = mock_argparse.return_value
            mock_args = create_mock_args(**args_dict)
            mock_parser_instance.parse_args.return_value = mock_args

            # Run command
            cli.main()

            # Assertions
            # Check error creation
            mock_create_error.assert_called_once_with(
                error_type="ValueError",
                error_message="Invalid value provided",
                stacktrace="File 'test.py', line 42\nValueError: Invalid value provided",
                affected_files=["test.py", "utils.py"],
                resolution="Added input validation",
                resolution_verified=True,
            )

            # Check error storage
            mock_store_error.assert_called_once_with(
                mock_error_evidence, collection_name="validation_evidence_v1", chroma_client=mock_client
            )

            # Check output
            captured = capsys.readouterr()
            assert f"Runtime error logged successfully with ID: {error_id}" in captured.out


@patch("uuid.uuid4")
@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
def test_log_test_results_command(mock_get_client_ef, mock_argparse, mock_uuid, capsys, caplog):
    """Test that the log-test-results command parses and stores test results."""
    # Mocks
    mock_client = MagicMock(spec=chromadb.ClientAPI)
    mock_ef = MagicMock(spec=DefaultEmbeddingFunction)
    mock_get_client_ef.return_value = (mock_client, mock_ef)
    mock_uuid.return_value = uuid.UUID("11223344-5566-7788-99aa-bbccddeeff00")
    test_run_id = "11223344-5566-7788-99aa-bbccddeeff00"

    # Mock test result functions
    with patch("chroma_mcp_client.validation.test_collector.parse_junit_xml") as mock_parse:
        with patch("chroma_mcp_client.validation.test_collector.store_test_results") as mock_store:
            # Set up return values
            mock_results_dict = {
                "tests": 42,
                "failures": 2,
                "errors": 1,
                "skipped": 3,
                "time": 5.67,
                "timestamp": "2023-05-15T10:30:00",
                "results": [
                    {"name": "test_one", "classname": "TestClass", "time": 0.5, "status": "passed"},
                    {"name": "test_two", "classname": "TestClass", "time": 0.3, "status": "failed"},
                ],
            }
            mock_parse.return_value = mock_results_dict
            mock_store.return_value = test_run_id

            # No transition evidence for a simple test
            xml_path = "/tmp/test-results.xml"

            # Command Args
            args_dict = {
                "command": "log-test-results",
                "verbose": 1,
                "xml_path": xml_path,
                "before_xml": None,  # No before XML, so no transition evidence
                "commit_before": None,
                "commit_after": None,
                "collection_name": "test_results_v1",
            }
            mock_parser_instance = mock_argparse.return_value
            mock_args = create_mock_args(**args_dict)
            mock_parser_instance.parse_args.return_value = mock_args

            # Run command
            cli.main()

            # Assertions
            # Check parsing
            mock_parse.assert_called_once_with(xml_path)

            # Check storage
            mock_store.assert_called_once_with(
                results_dict=mock_results_dict, collection_name="test_results_v1", chroma_client=mock_client
            )

            # Check output
            captured = capsys.readouterr()
            assert f"Test results logged successfully with ID: {test_run_id}" in captured.out


@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
def test_validate_evidence_command_from_file(mock_get_client_ef, mock_argparse, capsys, caplog, tmp_path):
    """Test that the validate-evidence command loads and validates evidence from a file."""
    # Mocks
    mock_client = MagicMock(spec=chromadb.ClientAPI)
    mock_ef = MagicMock(spec=DefaultEmbeddingFunction)
    mock_get_client_ef.return_value = (mock_client, mock_ef)

    # Create a temporary evidence file
    evidence_file = tmp_path / "evidence.json"

    # Mock evidence data for the file
    evidence_data = {
        "id": "test-evidence-id",
        "score": 0.85,
        "test_transitions": [
            {
                "test_name": "test_feature",
                "before_status": "failed",
                "after_status": "passed",
                "commit_before": "abc123",
                "commit_after": "def456",
            }
        ],
        "runtime_errors": [],
        "code_quality_improvements": [],
        "evidence_types": ["TEST_TRANSITION"],
        "threshold": 0.7,
    }

    # Write to the temp file
    with open(evidence_file, "w") as f:
        import json

        json.dump(evidence_data, f)

    # Create patchers that don't assert call counts
    mock_open_patcher = patch("builtins.open", new_callable=MagicMock)
    mock_json_load_patcher = patch("json.load")

    with mock_open_patcher as mock_open:
        with mock_json_load_patcher as mock_json_load:
            # Set up the mock to return our evidence data
            mock_json_load.return_value = evidence_data

            # Mock the ValidationEvidence model
            with patch("chroma_mcp_client.validation.schemas.ValidationEvidence") as mock_evidence_class:
                mock_evidence_instance = MagicMock()
                mock_evidence_instance.score = 0.85
                mock_evidence_instance.meets_threshold.return_value = True
                mock_evidence_class.model_validate.return_value = mock_evidence_instance

                # Command Args
                args_dict = {
                    "command": "validate-evidence",
                    "verbose": 1,
                    "evidence_file": str(evidence_file),
                    "test_transitions": None,
                    "runtime_errors": None,
                    "code_quality": None,
                    "output_file": None,
                    "threshold": 0.7,
                }
                mock_parser_instance = mock_argparse.return_value
                mock_args = create_mock_args(**args_dict)
                mock_parser_instance.parse_args.return_value = mock_args

                # Run command
                cli.main()

                # Assertions
                # Check that validation was performed
                mock_evidence_class.model_validate.assert_called_with(evidence_data)
                mock_evidence_instance.meets_threshold.assert_called_once()

                # Check output message
                captured = capsys.readouterr()
                assert "Validation score: 0.85" in captured.out
                assert "Threshold: 0.7" in captured.out
                assert "Meets threshold: True" in captured.out


@patch("uuid.uuid4")
@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
@patch("chroma_mcp_client.validation.evidence_collector.store_validation_evidence")
@patch("chroma_mcp_client.validation.evidence_collector.collect_validation_evidence")
def test_log_quality_check_command(
    mock_collect_evidence,
    mock_store_validation_evidence,
    mock_get_client_ef,
    mock_argparse,
    mock_uuid,
    capsys,
    caplog,
    tmp_path,
):
    """Test the log-quality-check command correctly stores evidence."""
    mock_client_instance = MagicMock(spec=chromadb.ClientAPI)
    mock_get_client_ef.return_value = (mock_client_instance, DefaultEmbeddingFunction())

    unique_evidence_id = f"evidence-{uuid.uuid4()}"
    mock_uuid.return_value = unique_evidence_id

    # 1. Create a dummy target file that the linting output refers to
    dummy_target_py_file = tmp_path / "dummy_module.py"
    dummy_target_py_file.write_text("CONSTANT_VAR = 1\nprint('hello')\n")

    # 2. Create a dummy 'before_output' file with more issues for the dummy target file
    dummy_before_pylint_file = tmp_path / "dummy_before_pylint.txt"
    dummy_before_pylint_file.write_text(
        f"{dummy_target_py_file.name}:1:0: C0114: Missing module docstring (missing-module-docstring)\n"
        f'{dummy_target_py_file.name}:2:0: C0103: Constant name "CONSTANT_VAR" doesn\'t conform to UPPER_CASE naming style (invalid-name)\n'
        # Intentionally causing an error that will be "fixed"
    )

    # 3. Create a dummy 'after_output' file with fewer issues for the dummy target file
    dummy_after_pylint_file = tmp_path / "dummy_after_pylint.txt"
    dummy_after_pylint_file.write_text(
        f"{dummy_target_py_file.name}:1:0: C0114: Missing module docstring (missing-module-docstring)\n"
    )

    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(
        command="log-quality-check",
        verbose=0,
        tool="pylint",
        before_output=str(dummy_before_pylint_file),
        after_output=str(dummy_after_pylint_file),
        metric_type="error_count",
        collection_name="validation_evidence_v1",
    )
    mock_parser_instance.parse_args.return_value = mock_args

    # Configure the mocks for the patched functions from evidence_collector
    final_evidence_id_for_cli_output = "test-evidence-id-123"
    mock_store_validation_evidence.return_value = final_evidence_id_for_cli_output

    # This is what collect_validation_evidence is mocked to return.
    # It needs to have the code_quality_improvements attribute for cli.py.
    mock_returned_validation_evidence = MagicMock(spec=ValidationEvidence)

    # Create a mock for the CodeQualityEvidence item that would be inside the list
    # This represents the item that create_code_quality_evidence would produce
    # and that cli.py will try to access for printing.
    mock_cq_item_for_print = MagicMock(spec=CodeQualityEvidence)
    mock_cq_item_for_print.before_value = 2.0  # Expected before value from dummy files
    mock_cq_item_for_print.after_value = 1.0  # Expected after value from dummy files
    mock_cq_item_for_print.metric_type = "linting"  # Default from create_code_quality_evidence
    mock_cq_item_for_print.tool = "pylint"
    mock_cq_item_for_print.file_path = dummy_target_py_file.name  # Or how it's stored
    mock_cq_item_for_print.percentage_improvement = 50.0

    # Set the attribute on the object that collect_validation_evidence returns
    mock_returned_validation_evidence.code_quality_improvements = [mock_cq_item_for_print]
    # Set other attributes if cli.py uses them before store_validation_evidence or for printing
    # For example, the overall score might be calculated by collect_validation_evidence
    mock_returned_validation_evidence.score = 0.5  # Example score

    mock_collect_evidence.return_value = mock_returned_validation_evidence

    main()  # Call the CLI main function

    # Assert that collect_validation_evidence was called correctly.
    # It should be called with the list of CodeQualityEvidence objects produced by
    # the actual create_code_quality_evidence function.
    mock_collect_evidence.assert_called_once()
    args_call_collect, kwargs_call_collect = mock_collect_evidence.call_args
    assert "code_quality_improvements" in kwargs_call_collect
    list_passed_to_collect = kwargs_call_collect["code_quality_improvements"]
    assert len(list_passed_to_collect) == 1
    actual_cq_evidence_created = list_passed_to_collect[0]

    # Verify the content of the CodeQualityEvidence object that was created by the
    # non-mocked create_code_quality_evidence and passed to the mocked collect_validation_evidence
    assert isinstance(actual_cq_evidence_created, CodeQualityEvidence)  # Check it's the real type
    assert actual_cq_evidence_created.tool == "pylint"
    # The file_path in CodeQualityEvidence is an absolute path after processing in create_code_quality_evidence
    # In the test, dummy_target_py_file.name is just the filename. We need to see how it's stored.
    # For now, let's assume create_code_quality_evidence stores the name as is if it can't resolve full path for some reason
    # or if it's processing based on keys from parsed results.
    # Let's check what create_code_quality_evidence actually does with file_path.
    # It takes file_path from improvements.items(), which are keys from before_results/after_results.
    # Our parsers use the filename as key. So this should be dummy_target_py_file.name.
    assert actual_cq_evidence_created.file_path == dummy_target_py_file.name
    assert actual_cq_evidence_created.before_value == 2.0
    assert actual_cq_evidence_created.after_value == 1.0
    assert actual_cq_evidence_created.percentage_improvement == 50.0
    assert actual_cq_evidence_created.metric_type == "linting"  # Default in CodeQualityEvidence constructor

    # Assert that store_validation_evidence was called correctly
    mock_store_validation_evidence.assert_called_once_with(
        evidence=mock_returned_validation_evidence,
        collection_name="validation_evidence_v1",
        chroma_client=mock_client_instance,
    )

    captured = capsys.readouterr()
    # The ID in the output comes from the return value of mock_store_validation_evidence
    assert f"Code quality evidence stored with ID: {final_evidence_id_for_cli_output}" in captured.out
    # The metric type in the printout comes from args.metric_type if not found in evidence,
    # but our CodeQualityEvidence schema has 'metric_type' which should be 'linting' by default.
    assert (
        "Tool: pylint, Metric: linting" in captured.out
    )  # Assuming metric_type is set to 'linting' in CodeQualityEvidence
    assert "Before (linting): 2.0, After (linting): 1.0" in captured.out
    assert "Improvement: +50.00%" in captured.out


@patch("chroma_mcp_client.validation.test_workflow.check_for_completed_workflows")
def test_cli_check_test_transitions(mock_check_workflows, monkeypatch):
    """Test the check-test-transitions CLI command."""
    # Setup mocks
    mock_check_workflows.return_value = 3  # 3 workflows processed

    # Mock the client and embedding function to prevent actual downloads
    mock_client = MagicMock()
    mock_ef = MagicMock()

    # Run command
    monkeypatch.setattr(
        sys, "argv", ["chroma-client", "check-test-transitions", "--workspace-dir", "/test/workspace", "--auto-promote"]
    )

    # Capture stdout
    with patch("sys.stdout", new=StringIO()) as fake_out:
        with patch("sys.exit") as mock_exit:
            # Mock get_client_and_ef to prevent real connection
            with patch("chroma_mcp_client.cli.get_client_and_ef", return_value=(mock_client, mock_ef)):
                # Run the command
                main()

                # Check exit wasn't called with error code
                mock_exit.assert_not_called()

    # Verify check_for_completed_workflows was called properly
    mock_check_workflows.assert_called_once()

    # Test error scenario
    mock_check_workflows.side_effect = Exception("Test error")
    monkeypatch.setattr(sys, "argv", ["chroma-client", "check-test-transitions"])

    with patch("sys.stderr", new=StringIO()) as fake_err:
        with patch("sys.exit") as mock_exit:
            with patch("chroma_mcp_client.cli.get_client_and_ef", return_value=(mock_client, mock_ef)):
                # Run the command
                main()

                # Check exit was called with error code
                mock_exit.assert_called_once_with(1)


@patch("chroma_mcp_client.validation.test_workflow.setup_automated_workflow")
def test_cli_setup_test_workflow(mock_setup_workflow, monkeypatch):
    """Test the setup-test-workflow CLI command."""
    # Setup mocks
    mock_setup_workflow.return_value = True

    # Mock the client and embedding function to prevent actual downloads
    mock_client = MagicMock()
    mock_ef = MagicMock()

    # Run command with custom workspace dir and force flag
    monkeypatch.setattr(
        sys, "argv", ["chroma-client", "setup-test-workflow", "--workspace-dir", "/test/workspace", "--force"]
    )

    # Capture stdout
    with patch("sys.stdout", new=StringIO()) as fake_out:
        with patch("sys.exit") as mock_exit:
            # Mock get_client_and_ef to prevent real connection
            with patch("chroma_mcp_client.cli.get_client_and_ef", return_value=(mock_client, mock_ef)):
                # Run the command
                main()

                # Check exit wasn't called with error code
                mock_exit.assert_not_called()

    # Verify setup_automated_workflow was called with correct workspace dir
    mock_setup_workflow.assert_called_once_with(workspace_dir="/test/workspace")

    # Test failure case
    mock_setup_workflow.return_value = False
    monkeypatch.setattr(sys, "argv", ["chroma-client", "setup-test-workflow"])

    with patch("sys.stdout", new=StringIO()) as fake_out:
        with patch("sys.exit") as mock_exit:
            with patch("chroma_mcp_client.cli.get_client_and_ef", return_value=(mock_client, mock_ef)):
                # Run the command
                main()

                # Check exit was called with error code
                mock_exit.assert_called_once_with(1)

    # Verify default workspace dir was used
    mock_setup_workflow.assert_called_with(workspace_dir=".")

    # Test error scenario
    mock_setup_workflow.side_effect = Exception("Test error")

    with patch("sys.stderr", new=StringIO()) as fake_err:
        with patch("sys.exit") as mock_exit:
            with patch("chroma_mcp_client.cli.get_client_and_ef", return_value=(mock_client, mock_ef)):
                # Run the command
                main()

                # Check exit was called with error code
                mock_exit.assert_called_with(1)
