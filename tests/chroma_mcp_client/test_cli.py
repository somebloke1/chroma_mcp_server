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
    monkeypatch.setattr(subprocess, 'run', mock_run)
    return mock_run

# =====================================================================
# Tests for Argument Parsing and Connection
# =====================================================================

@patch('argparse.ArgumentParser')
@patch('chroma_mcp_client.cli.get_client_and_ef')
def test_cli_command_parses_and_calls_connect(mock_get_client_ef, mock_argparse):
    """Test that a valid command calls get_client_and_ef correctly (bypassing argparse)."""
    # Configure mock argparse to return specific args
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(
        command='count',
        log_level='INFO',
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
    mock_get_client_ef.assert_called_once_with() # Called with default env_path=None


@patch('argparse.ArgumentParser')
@patch('chroma_mcp_client.cli.get_client_and_ef')
@patch('sys.exit')
def test_cli_connect_failure_exits(mock_sys_exit, mock_get_client_ef, mock_argparse):
    """Test that if get_client_and_ef fails, the CLI exits with an error (bypassing argparse)."""
    # Configure mock argparse
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(
        command='count',
        log_level='INFO',
        collection_name=DEFAULT_COLLECTION_NAME,
    )
    mock_parser_instance.parse_args.return_value = mock_args

    # Configure get_client_and_ef to raise an exception
    mock_get_client_ef.side_effect = Exception("Connection failed")
    mock_sys_exit.side_effect = SystemExit(1) # Make mock exit behave like real exit

    # Run CLI which should attempt connection, fail, and exit
    with pytest.raises(SystemExit) as excinfo: # Expect SystemExit
        main() # Args don't matter
    assert excinfo.value.code == 1

    # Assert sys.exit was called with 1
    mock_sys_exit.assert_called_once_with(1) # Verify it was called with 1


# =====================================================================
# Tests for Indexing
# =====================================================================

@patch('argparse.ArgumentParser')
@patch('chroma_mcp_client.cli.get_client_and_ef')       # Patch helper
@patch('chroma_mcp_client.cli.index_file')              # Patch index_file usage in cli
def test_index_single_file(mock_index_file, mock_get_client_ef, mock_argparse, test_dir, capsys):
    """Test indexing a single file via the CLI."""
    # Configure mocks
    mock_client_instance = MagicMock(spec=chromadb.ClientAPI)
    mock_collection = mock_client_instance.get_or_create_collection.return_value
    mock_get_client_ef.return_value = (mock_client_instance, DefaultEmbeddingFunction())
    mock_index_file.return_value = True # Simulate successful indexing

    collection_name = "test_collection"
    file_to_index = test_dir / "file1.py"

    # Mock argparse return value
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(
        command='index',
        log_level='INFO',
        paths=[file_to_index], # Use the specific file path
        repo_root=test_dir, # Use the test_dir Path object
        all=False,
        collection_name=collection_name
    )
    mock_parser_instance.parse_args.return_value = mock_args

    # Run CLI
    main()

    # Assertions
    mock_get_client_ef.assert_called_once()
    mock_client_instance.get_or_create_collection.assert_called_once_with(name=collection_name, embedding_function=mock_get_client_ef.return_value[1])
    # Check that index_file was called correctly from within cli.main
    mock_index_file.assert_called_once_with(
        file_to_index, # Path object
        test_dir.resolve(), # Resolved repo root path
        mock_collection # The mock collection object
    )


@patch('argparse.ArgumentParser')
@patch('chroma_mcp_client.cli.get_client_and_ef')
@patch('chroma_mcp_client.cli.index_git_files') # Patch the function being tested
def test_index_all_files(mock_index_git, mock_get_client_ef, mock_argparse, test_dir, capsys):
    """Test indexing all git-tracked files via the CLI."""
    # Configure mocks
    mock_client_instance = MagicMock(spec=chromadb.ClientAPI)
    mock_collection = mock_client_instance.get_or_create_collection.return_value
    mock_get_client_ef.return_value = (mock_client_instance, DefaultEmbeddingFunction())

    collection_name = "git_collection"
    mock_index_git.return_value = 2 # Simulate 2 files indexed

    # Mock argparse return value
    mock_parser_instance = mock_argparse.return_value
    mock_args = create_mock_args(
        command='index',
        log_level='INFO',
        paths=[],
        repo_root=test_dir, # Use the test_dir Path object
        all=True,
        collection_name=collection_name
    )
    mock_parser_instance.parse_args.return_value = mock_args

    # Run CLI
    main()

    # Assertions
    mock_get_client_ef.assert_called_once()
    mock_client_instance.get_or_create_collection.assert_called_once_with(name=collection_name, embedding_function=mock_get_client_ef.return_value[1])
    # Check that index_git_files was called correctly from within cli.main
    mock_index_git.assert_called_once_with(
        test_dir.resolve(), # Resolved repo root path
        mock_collection # The mock collection object
    )


# =====================================================================
# Tests for Count
# =====================================================================

@patch('argparse.ArgumentParser')
@patch('chroma_mcp_client.cli.get_client_and_ef')
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
        command='count',
        log_level='INFO',
        collection_name=collection_name # Use the string directly
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

@patch('argparse.ArgumentParser')
@patch('chroma_mcp_client.cli.get_client_and_ef')
def test_query_command(mock_get_client_ef, mock_argparse, test_dir, capsys):
    """Test the query command via the CLI."""
    collection_name = "query_collection"
    query_text = "find this text"
    n_results = 3
    mock_query_results = {
        'ids': [['id1', 'id2']],
        'documents': [['result doc 1', 'result doc 2']],
        'metadatas': [[{'source': 'file1.txt', 'content': 'abc'}, {'source': 'file2.md', 'content': 'def'}]],
        'distances': [[0.1, 0.2]]
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
        command='query',
        log_level='INFO',
        query_text=query_text,
        collection_name=collection_name, # Use the string directly
        n_results=n_results
    )
    mock_parser_instance.parse_args.return_value = mock_args

    # Run CLI
    main()

    # Assertions
    mock_get_client_ef.assert_called_once()
    mock_client_instance.get_collection.assert_called_once_with(
        name=collection_name,
        embedding_function=mock_ef_instance # Add embedding function to assertion
    )
    mock_collection.query.assert_called_once_with(
        query_texts=[query_text],
        n_results=n_results,
        include=['metadatas', 'documents', 'distances'] # Default includes
    )
    # Check output
    captured = capsys.readouterr() # Reads stdout/stderr captured during test
    # Basic check for output presence
    assert "Query Results for" in captured.out # Check for the start of the output header
    assert "ID: id1" in captured.out
    assert "result doc 1" in captured.out
    assert "0.1000" in captured.out # Check for distance formatting
