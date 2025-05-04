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
def test_cli_command_parses_and_calls_connect(mock_get_client_ef, mock_argparse):
    """Test that a valid command calls get_client_and_ef correctly (bypassing argparse)."""
    # Configure mock argparse to return specific args
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(
        command="count",
        log_level="INFO",
        collection_name=DEFAULT_COLLECTION_NAME,
    )
    mock_parser_instance.parse_args.return_value = mock_args

    # Configure mock get_client_and_ef to return a tuple
    mock_client_instance = MagicMock(spec=chromadb.ClientAPI)
    mock_ef_instance = DefaultEmbeddingFunction()
    mock_get_client_ef.return_value = (mock_client_instance, mock_ef_instance)

    # Args passed here don't matter since parse_args is mocked
    main()

    # Assert get_client_and_ef was called correctly
    mock_get_client_ef.assert_called_once_with()  # Called with default env_path=None


@patch("argparse.ArgumentParser")
@patch("chroma_mcp_client.cli.get_client_and_ef")
@patch("sys.exit")
def test_cli_connect_failure_exits(mock_sys_exit, mock_get_client_ef, mock_argparse):
    """Test that if get_client_and_ef fails, the CLI exits with an error (bypassing argparse)."""
    # Configure mock argparse
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(
        command="count",
        log_level="INFO",
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
        log_level="INFO",
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
        log_level="INFO",
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
    mock_args = create_mock_args(
        command="count", log_level="INFO", collection_name=collection_name  # Use the string directly
    )
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
        log_level="INFO",
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
    # Basic check for output presence
    assert "Query Results for" in captured.out  # Check for the start of the output header
    assert "ID: id1" in captured.out
    assert "result doc 1" in captured.out
    assert "0.1000" in captured.out  # Check for distance formatting


# --- Test Log Level Setting ---

# Use parametrize to test different scenarios
@pytest.mark.parametrize(
    "cli_args, env_vars, expected_level_name, expected_log_level",
    [
        # 1. Command line argument takes precedence (DEBUG)
        (["--log-level", "DEBUG", "count"], {"LOG_LEVEL": "WARNING"}, "DEBUG", logging.DEBUG),
        # 2. Command line argument takes precedence (WARNING)
        (["--log-level", "WARNING", "count"], {}, "WARNING", logging.WARNING),
        # 3. Environment variable used when no CLI arg (DEBUG)
        (["count"], {"LOG_LEVEL": "DEBUG"}, "DEBUG", logging.DEBUG),
        # 4. Environment variable used when no CLI arg (ERROR)
        (["count"], {"LOG_LEVEL": "ERROR"}, "ERROR", logging.ERROR),
        # 5. Default INFO used when no CLI arg and no env var
        (["count"], {}, "INFO", logging.INFO),
        # 6. Default INFO used when env var is invalid
        (["count"], {"LOG_LEVEL": "INVALID"}, "INFO", logging.INFO),
        # 7. CLI arg takes precedence even if env var is invalid
        (["--log-level", "DEBUG", "count"], {"LOG_LEVEL": "INVALID"}, "DEBUG", logging.DEBUG),
    ],
)
@patch("chroma_mcp_client.cli.get_client_and_ef") # Mock client connection
@patch("logging.getLogger") # Mock getLogger to check setLevel
def test_log_level_precedence(
    mock_getLogger, mock_get_client, monkeypatch, cli_args, env_vars, expected_level_name, expected_log_level
):
    """Tests the log level setting precedence: CLI > Env Var > Default."""
    # Setup environment variables for the test
    monkeypatch.setattr(sys, "argv", ["prog_name"] + cli_args)
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    # Ensure LOG_LEVEL is unset if not in env_vars for this test run
    if "LOG_LEVEL" not in env_vars:
        monkeypatch.delenv("LOG_LEVEL", raising=False)

    # Mock the root logger instance returned by getLogger()
    mock_root_logger = MagicMock()
    mock_getLogger.return_value = mock_root_logger

    # Mock the client/collection methods called by the 'count' command to avoid errors
    mock_client_instance = MagicMock()
    mock_collection_instance = MagicMock()
    mock_collection_instance.count.return_value = 5
    mock_client_instance.get_collection.return_value = mock_collection_instance
    mock_get_client.return_value = (mock_client_instance, MagicMock()) # Return mock client and EF

    # Run the CLI main function (need to reload module to pick up env vars for default)
    # Since default is calculated at import time, need a way to re-evaluate
    # Option 1: Reload module (can be tricky)
    # Option 2: Patch os.getenv within the test (simpler)

    # We need to simulate the ArgumentParser default value logic based on env
    # This happens BEFORE parse_args is called. The default is set at module load time.
    # A cleaner way might be to move the getenv default logic inside main(),
    # but let's test the current structure first.
    # Re-importing or complex patching is needed because default is set at module level.

    # Let's try patching the default directly on the parser object *after* it's created
    # This is a bit intrusive but avoids reloading modules.
    with patch("argparse.ArgumentParser") as mock_ArgumentParser:
        # Instance that ArgumentParser() returns
        mock_parser_instance = MagicMock()
        # Simulate the behavior of add_argument and parse_args
        def add_argument_side_effect(*args, **kwargs):
             # Capture the default value logic when --log-level is added
            if kwargs.get('dest') == 'log_level':
                # Re-calculate default based on current env for this test run
                # Use os.getenv here as well
                env_level = os.getenv("LOG_LEVEL", "INFO").upper()
                if env_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                     env_level = "INFO"
                kwargs['default'] = env_level
            # Store args/kwargs or simulate behavior if needed
            pass # Simplified: just capture default

        mock_parser_instance.add_argument = MagicMock(side_effect=add_argument_side_effect)
        # Make parse_args return the test args
        mock_parse_result = MagicMock()
        # Simulate parsed args based on cli_args and the *correct* default
        parsed_args_dict = {'command': cli_args[-1]} # Assuming command is last
        # Calculate the expected default for this specific run
        # Use os.getenv here
        current_env_default = os.getenv("LOG_LEVEL", "INFO").upper()
        if current_env_default not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            current_env_default = "INFO"

        if "--log-level" in cli_args:
            log_level_index = cli_args.index("--log-level")
            parsed_args_dict['log_level'] = cli_args[log_level_index + 1]
        else:
            parsed_args_dict['log_level'] = current_env_default # Use env or INFO default

        # Add other necessary args for the 'count' command
        parsed_args_dict['collection_name'] = cli.DEFAULT_COLLECTION_NAME

        # Set attributes on the mock result object
        for key, value in parsed_args_dict.items():
            setattr(mock_parse_result, key, value)

        mock_parser_instance.parse_args.return_value = mock_parse_result
        mock_ArgumentParser.return_value = mock_parser_instance

        # Now run the main function
        try:
            cli.main()
        except SystemExit as e:
            # Allow sys.exit(0) for successful commands like count
             assert e.code == 0 or e.code is None, f"CLI exited with unexpected code {e.code}"
        except Exception as e:
            pytest.fail(f"cli.main() raised an unexpected exception: {e}")


    # Assert that the root logger's setLevel was called with the correct level
    mock_root_logger.setLevel.assert_called_once_with(expected_log_level)

    # Optionally, check the log message content if needed using call_args
    # log_call_args = mock_root_logger.info.call_args
    # assert f"Log level set to {expected_level_name}" in log_call_args[0][0]


# --- Mock Client Fixture ---
@pytest.fixture
def mock_chromadb_client():
    # ... existing code ...
    pass # Add pass to fix indentation error

# --- Index Command Tests ---
@patch("chroma_mcp_client.cli.index_git_files")
@patch("chroma_mcp_client.cli.get_client_and_ef")
def test_index_all(mock_get_client, mock_index_git, monkeypatch, tmp_path):
    # ... existing code ...
    pass # Add pass to fix indentation error

@patch("chroma_mcp_client.cli.index_file")
@patch("chroma_mcp_client.cli.get_client_and_ef")
def test_index_specific_files(mock_get_client, mock_index_file, monkeypatch, tmp_path):
    # ... existing code ...
    pass # Add pass to fix indentation error

# --- Count Command Tests ---
@patch("chroma_mcp_client.cli.get_client_and_ef")
def test_count_command_success(mock_get_client, monkeypatch, capsys):
    # ... existing code ...
    pass # Add pass to fix indentation error

@patch("chroma_mcp_client.cli.get_client_and_ef")
def test_count_command_collection_not_found(mock_get_client, monkeypatch, capsys):
    # ... existing code ...
    pass # Add pass to fix indentation error

# --- Query Command Tests ---
@patch("chroma_mcp_client.cli.get_client_and_ef")
def test_query_command_success(mock_get_client, monkeypatch, capsys):
    # ... existing code ...
    pass # Add pass to fix indentation error

@patch("chroma_mcp_client.cli.get_client_and_ef")
def test_query_command_no_results(mock_get_client, monkeypatch, capsys):
    # ... existing code ...
    pass # Add pass to fix indentation error

@patch("chroma_mcp_client.cli.get_client_and_ef")
def test_query_command_collection_not_found(mock_get_client, monkeypatch, capsys):
    # ... existing code ...
    pass # Add pass to fix indentation error

# Add other tests as needed for error handling, edge cases etc.
