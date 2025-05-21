"""
Unit tests for the publish.py script module.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from chroma_mcp.dev_scripts.publish import run_command, check_dist_files, main


def test_run_command(tmp_path, monkeypatch):
    """Test the run_command helper."""
    calls = []

    def fake_run(cmd, cwd=None):
        calls.append((cmd, cwd))

        class R:
            returncode = 321

        return R()

    monkeypatch.setattr("subprocess.run", fake_run)
    result = run_command(["ls"], cwd=Path("/tmp"))
    assert result == 321
    assert calls == [(["ls"], Path("/tmp"))]


def test_check_dist_files_no_files(tmp_path):
    """Check that check_dist_files returns False when no dist files."""
    assert not check_dist_files(tmp_path)


def test_check_dist_files_with_files(tmp_path):
    """Check that check_dist_files returns True when both wheel and tar.gz exist."""
    project = tmp_path
    dist_dir = project / "dist"
    dist_dir.mkdir()
    (dist_dir / "file.whl").write_text("")
    (dist_dir / "file.tar.gz").write_text("")
    assert check_dist_files(project)


@patch("sys.argv", ["publish"])
@patch("chroma_mcp.dev_scripts.publish.check_dist_files", return_value=True)
@patch("subprocess.run")
@patch("chroma_mcp.dev_scripts.publish.run_command")
def test_main_full_flow(mock_run_command, mock_subprocess_run, mock_check_dist):
    """Test publish main full flow without skip flags."""
    # Mock run_command and subprocess.run to succeed
    # run_command calls: pip install, tests, build, upload
    mock_run_command.side_effect = [0, 0, 0, 0]
    mock_subprocess_run.return_value = MagicMock(returncode=0)

    ret = main()
    assert ret == 0
    # Check that pip install, test, build, and upload are invoked
    tokens = [token for call, _ in mock_run_command.call_args_list for token in call[0]]
    assert "pip" in tokens
    assert "test" in tokens
    assert "build" in tokens
    assert "twine" in tokens


@patch("sys.argv", ["publish", "--skip-build", "--skip-tests"])
@patch("chroma_mcp.dev_scripts.publish.check_dist_files", return_value=True)
@patch("subprocess.run")
@patch("chroma_mcp.dev_scripts.publish.run_command")
def test_main_skip_flags(mock_run_command, mock_subprocess_run, mock_check_dist):
    """Test publish main with skip-build and skip-tests flags."""
    # run_command calls: pip install deps and upload
    mock_run_command.side_effect = [0, 0]
    mock_subprocess_run.return_value = MagicMock(returncode=0)

    ret = main()
    assert ret == 0
    calls = mock_run_command.call_args_list
    # Expect two calls: dependencies install and upload
    assert len(calls) == 2
    # First call installs dependencies
    assert sys.executable in calls[0][0][0]
    assert "pip" in calls[0][0][0]
    # Second call uploads via twine
    assert "twine" in calls[1][0][0]


@patch("sys.argv", ["publish"])
@patch("chroma_mcp.dev_scripts.publish.check_dist_files", return_value=True)
@patch("subprocess.run")
@patch("chroma_mcp.dev_scripts.publish.run_command")
def test_main_hatch_installation_flow(mock_run_command, mock_subprocess_run, mock_check_dist):
    """Test publish main when hatch is not installed, triggering installation of hatch."""
    # run_command calls: deps, pip install hatch, test, build, upload
    mock_run_command.side_effect = [0, 0, 0, 0, 0]

    def fake_run(cmd, cwd=None, check=False, capture_output=False):
        # Simulate FileNotFoundError for hatch version check
        raise FileNotFoundError()

    mock_subprocess_run.side_effect = fake_run

    ret = main()
    assert ret == 0
    calls = mock_run_command.call_args_list
    # Ensure pip install dependencies is first
    assert "pip" in calls[0][0][0]
    # Ensure pip install hatch is called
    tokens_install_hatch = calls[1][0][0]
    assert "install" in tokens_install_hatch
    assert "hatch" in tokens_install_hatch
    # Ensure test and build commands are called
    assert any("test" in token for token in calls[2][0][0])
    assert any("build" in token for token in calls[3][0][0])
    # Ensure upload via twine is last
    assert any("twine" in token for token in calls[4][0][0])


@patch("sys.argv", ["publish"])
@patch("chroma_mcp.dev_scripts.publish.check_dist_files", return_value=True)
@patch("subprocess.run")
@patch("chroma_mcp.dev_scripts.publish.run_command")
def test_publish_dep_install_fail(mock_run_command, mock_subprocess_run, mock_check_dist):
    """Test publish main returns error when dependency installation fails."""
    # run_command pip install dependencies fails
    mock_run_command.return_value = 1
    mock_subprocess_run.return_value = MagicMock(returncode=0)
    ret = main()
    assert ret == 1


@patch("sys.argv", ["publish"])
@patch("chroma_mcp.dev_scripts.publish.check_dist_files", return_value=True)
@patch("subprocess.run")
@patch("chroma_mcp.dev_scripts.publish.run_command")
def test_publish_tests_fail(mock_run_command, mock_subprocess_run, mock_check_dist):
    """Test publish main returns error when tests fail."""
    # pip install deps succeeds
    # run tests fails
    # Provide side_effect: [dep_install, tests_fail]
    mock_run_command.side_effect = [0, 1]
    mock_subprocess_run.return_value = MagicMock(returncode=0)
    ret = main()
    assert ret == 1


@patch("sys.argv", ["publish"])
@patch("chroma_mcp.dev_scripts.publish.check_dist_files", return_value=True)
@patch("subprocess.run")
@patch("chroma_mcp.dev_scripts.publish.run_command")
def test_publish_build_fail(mock_run_command, mock_subprocess_run, mock_check_dist):
    """Test publish main returns error when build fails."""
    # side_effect: [dep_install, test_success, build_fail]
    mock_run_command.side_effect = [0, 0, 1]
    mock_subprocess_run.return_value = MagicMock(returncode=0)
    ret = main()
    assert ret == 1


@patch("sys.argv", ["publish"])
@patch("chroma_mcp.dev_scripts.publish.check_dist_files", return_value=False)
@patch("subprocess.run")
@patch("chroma_mcp.dev_scripts.publish.run_command")
def test_publish_check_dist_fail(mock_run_command, mock_subprocess_run, mock_check_dist):
    """Test publish main returns error when distribution files are missing."""
    mock_run_command.side_effect = [0, 0, 0]
    mock_subprocess_run.return_value = MagicMock(returncode=0)
    ret = main()
    assert ret == 1


@patch("sys.argv", ["publish"])
@patch("chroma_mcp.dev_scripts.publish.check_dist_files", return_value=True)
@patch("subprocess.run")
@patch("chroma_mcp.dev_scripts.publish.run_command")
def test_publish_upload_fail(mock_run_command, mock_subprocess_run, mock_check_dist):
    """Test publish main returns error when upload fails."""
    # side_effect: [dep_install, test_success, build_success, upload_fail]
    mock_run_command.side_effect = [0, 0, 0, 1]
    mock_subprocess_run.return_value = MagicMock(returncode=0)
    ret = main()
    assert ret == 1


@patch("sys.argv", ["publish"])
@patch("chroma_mcp.dev_scripts.publish.check_dist_files", return_value=True)
@patch("subprocess.run")
@patch("chroma_mcp.dev_scripts.publish.run_command")
def test_publish_hatch_install_fail(mock_run_command, mock_subprocess_run, mock_check_dist):
    """Test publish main aborts when hatch installation fails."""
    # pip install deps succeeds, hatch not installed -> pip install hatch fails
    mock_run_command.side_effect = [0, 1]

    def fake_run(cmd, cwd=None, check=False, capture_output=False):
        raise FileNotFoundError()

    mock_subprocess_run.side_effect = fake_run
    ret = main()
    assert ret == 1
