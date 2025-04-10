"""Tests for the CLI argument parsing."""

import pytest
import argparse
import os
from unittest.mock import patch

# Import the function to test
from src.chroma_mcp.cli import parse_args

# Define a dictionary of default expected values (based on cli.py defaults and getenv fallbacks)
# Note: data_dir, log_dir, host, port, tenant, database, api_key default to None if env var not set
DEFAULT_EXPECTED = {
    "client_type": "ephemeral",
    "data_dir": None,
    "log_dir": None,
    "host": None,
    "port": None,
    "ssl": True,  # Default from getenv is 'true'
    "tenant": None,
    "database": None,
    "api_key": None,
    "dotenv_path": ".env",
    "cpu_execution_provider": "auto",
}


def test_parse_args_defaults():
    """Test parsing with default values (no args, no env vars)."""
    # Ensure environment variables are clear for this test
    with patch.dict(os.environ, {}, clear=True):
        args = parse_args([])
        for key, value in DEFAULT_EXPECTED.items():
            assert getattr(args, key) == value, f"Default failed for {key}"


def test_parse_args_cmd_line_overrides():
    """Test parsing with command line arguments overriding defaults."""
    cmd_args = [
        "--client-type",
        "persistent",
        "--data-dir",
        "/tmp/chroma_data",
        "--log-dir",
        "/var/log/chroma",
        "--host",
        "localhost",
        "--port",
        "9000",
        "--ssl",
        "false",  # Test boolean parsing
        "--tenant",
        "my-tenant",
        "--database",
        "my-db",
        "--api-key",
        "ABCDEF",
        "--dotenv-path",
        "/etc/chroma/.env",
        "--cpu-execution-provider",
        "true",
    ]
    # Ensure environment variables are clear
    with patch.dict(os.environ, {}, clear=True):
        args = parse_args(cmd_args)
        assert args.client_type == "persistent"
        assert args.data_dir == "/tmp/chroma_data"
        assert args.log_dir == "/var/log/chroma"
        assert args.host == "localhost"
        assert args.port == "9000"
        assert args.ssl is False  # Check boolean conversion
        assert args.tenant == "my-tenant"
        assert args.database == "my-db"
        assert args.api_key == "ABCDEF"
        assert args.dotenv_path == "/etc/chroma/.env"
        assert args.cpu_execution_provider == "true"


def test_parse_args_env_vars():
    """Test parsing with environment variables providing values."""
    env_vars = {
        "CHROMA_CLIENT_TYPE": "http",
        "CHROMA_DATA_DIR": "/data",
        "CHROMA_LOG_DIR": "/logs",
        "CHROMA_HOST": "192.168.1.100",
        "CHROMA_PORT": "8888",
        "CHROMA_SSL": "false",
        "CHROMA_TENANT": "env-tenant",
        "CHROMA_DATABASE": "env-db",
        "CHROMA_API_KEY": "XYZ123",
        "CHROMA_DOTENV_PATH": ".env.prod",
        "CHROMA_CPU_EXECUTION_PROVIDER": "false",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        args = parse_args([])  # No command line args
        assert args.client_type == "http"
        assert args.data_dir == "/data"
        assert args.log_dir == "/logs"
        assert args.host == "192.168.1.100"
        assert args.port == "8888"
        assert args.ssl is False
        assert args.tenant == "env-tenant"
        assert args.database == "env-db"
        assert args.api_key == "XYZ123"
        assert args.dotenv_path == ".env.prod"
        assert args.cpu_execution_provider == "false"


def test_parse_args_cmd_line_overrides_env():
    """Test command line args overriding environment variables."""
    env_vars = {"CHROMA_CLIENT_TYPE": "http", "CHROMA_PORT": "8000", "CHROMA_SSL": "true"}
    cmd_args = [
        "--client-type",
        "persistent",  # Override env
        "--port",
        "9999",  # Override env
        "--ssl",
        "false",  # Override env
    ]
    with patch.dict(os.environ, env_vars, clear=True):
        args = parse_args(cmd_args)
        assert args.client_type == "persistent"  # Prefers cmd line
        assert args.port == "9999"  # Prefers cmd line
        assert args.ssl is False  # Prefers cmd line
        # Check that unset values still use defaults (or None if no default env)
        assert args.host is None
        assert args.data_dir is None


def test_parse_args_ssl_variations():
    """Test various inputs for the boolean --ssl flag."""
    with patch.dict(os.environ, {}, clear=True):
        # True variations
        assert parse_args(["--ssl", "true"]).ssl is True
        assert parse_args(["--ssl", "YES"]).ssl is True
        assert parse_args(["--ssl", "1"]).ssl is True
        assert parse_args(["--ssl", "T"]).ssl is True
        assert parse_args(["--ssl", "y"]).ssl is True

        # False variations
        assert parse_args(["--ssl", "false"]).ssl is False
        assert parse_args(["--ssl", "NO"]).ssl is False
        assert parse_args(["--ssl", "0"]).ssl is False
        assert parse_args(["--ssl", "F"]).ssl is False
        assert parse_args(["--ssl", "n"]).ssl is False
        assert parse_args(["--ssl", "any_other_string"]).ssl is False  # Default argparse bool behavior

        # Default (should be True based on cli.py getenv default)
        assert parse_args([]).ssl is True
