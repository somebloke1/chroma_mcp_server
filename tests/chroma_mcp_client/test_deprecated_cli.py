import pytest
import warnings
from unittest.mock import patch

from chroma_mcp_client import deprecated_cli, cli


def test_deprecated_cli_shows_warning():
    """Test that the deprecated CLI shows a warning message"""
    with pytest.warns(DeprecationWarning, match="chroma-client.*deprecated.*removed.*0.3.0.*chroma-mcp-client"):
        with patch.object(cli, "main", return_value=0):
            deprecated_cli.main()


def test_deprecated_cli_calls_main():
    """Test that the deprecated CLI calls the main CLI function"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with patch.object(cli, "main", return_value=42) as mock_main:
            result = deprecated_cli.main()
            mock_main.assert_called_once()
            assert result == 42, "Should return the result from cli.main()"
