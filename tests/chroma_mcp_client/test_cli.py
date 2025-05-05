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

# Module to test
from chroma_mcp_client import cli
from chroma_mcp_client.cli import main, DEFAULT_COLLECTION_NAME
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings


# Helper to create mock args namespace
def create_mock_args(**kwargs):
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
    mock_client_logger = MagicMock()
    mock_st_logger = MagicMock()
    mock_cli_logger = MagicMock()  # Add mock for the cli logger

    # Configure getLogger to return specific mocks based on name
    def getLogger_side_effect(name=None):
        if name == "chroma_mcp_client":
            return mock_client_logger
        elif name == "sentence_transformers":
            return mock_st_logger
        elif name == "chroma_mcp_client.cli":  # Handle specific cli logger name
            return mock_cli_logger
        # Handle both getLogger() and getLogger(None) for root
        elif name is None or name == logging.getLogger().name:
            return mock_root_logger
        else:
            # Return a default mock for any other logger
            return MagicMock()

    mock_getLogger.side_effect = getLogger_side_effect

    # Configure the mock parse_args to return a Namespace with the verbose count
    # Add a dummy command and other required args to prevent errors later in main()
    mock_args = argparse.Namespace(
        verbose=verbose_count,
        command="count",  # Use a simple command that requires fewer mocks
        collection_name="dummy_collection",  # Needed for the 'count' command path
    )
    mock_parse_args.return_value = mock_args

    # Mock the client and collection calls needed for the 'count' command path
    mock_client_instance = MagicMock()
    mock_collection_instance = MagicMock()
    mock_collection_instance.count.return_value = 0  # Return dummy count
    mock_client_instance.get_collection.return_value = mock_collection_instance
    mock_get_client.return_value = (mock_client_instance, MagicMock())  # Return mock client/ef

    # --- Act ---
    # Run the main function. Use try-except SystemExit(0) for graceful exit of 'count'
    try:
        cli.main()
    except SystemExit as e:
        assert e.code == 0 or e.code is None  # Allow successful exit
    except Exception as e:
        pytest.fail(f"cli.main() raised an unexpected exception: {e}")

    # --- Assert ---
    # Verify setLevel was called correctly on each relevant logger
    mock_root_logger.setLevel.assert_called_once_with(expected_root_level)
    mock_client_logger.setLevel.assert_called_once_with(expected_client_level)
    mock_st_logger.setLevel.assert_called_once_with(expected_st_level)

    # Check the initial basicConfig level (should be WARNING before adjustment)
    # Get the call_args_list for basicConfig
    # basicConfig_calls = [call for call in mock_getLogger.call_args_list if call[0] == ()]
    # TODO: This assertion is tricky because basicConfig is called before getLogger is patched
    # for the individual loggers. We might need a different approach to verify basicConfig,
    # perhaps by patching logging.basicConfig itself. For now, focus on setLevel calls.

    # Verify the info log message about the level being set
    # This log comes from logger = logging.getLogger(__name__) within main()
    # which is logging.getLogger("chroma_mcp_client.cli")
    mock_cli_logger.info.assert_any_call(f"Log level set to {logging.getLevelName(expected_root_level)}")


if __name__ == "__main__":
    main()
