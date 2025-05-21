# Shell Script Migration Plan

This plan outlines the conversion of shell scripts to Python modules in the chroma-mcp-server codebase. All scripts are being migrated to Python to improve maintainability, testability, and platform compatibility.

## Migration Approach

Scripts are being moved to one of two locations:

1. **Client Scripts** (`src/chroma_mcp_client/scripts/`) - Scripts for end users
2. **Development Scripts** (`src/chroma_mcp/dev_scripts/`) - Scripts for internal development

Each script module should have a corresponding test file in `tests/scripts/` with the pattern `test_<script_name>.py`.

## Migration Status

### Client Scripts

These scripts are moved to `src/chroma_mcp_client/scripts/`:

- [x] `log_chat.py` - Converted from `scripts/log_chat.sh`
- [x] `analyze_chat.py` - Converted from `scripts/analyze_chat_history.sh`
- [x] `promote_learning.py` - Converted from `scripts/promote_learning.sh`
- [x] `review_promote.py` - Converted from `scripts/review_and_promote.sh`
- [x] `log_error.py` - Converted from `scripts/log_error.sh`
- [x] `log_test.py` - Converted from `scripts/log_test_results.sh`
- [x] `log_quality.py` - Converted from `scripts/log_quality_check.sh`
- [x] `validate_evidence.py` - Converted from `scripts/validate_evidence.sh`

### Development Scripts

These scripts are moved to `src/chroma_mcp/dev_scripts/`:

- [x] `build.py` - Converted from `scripts/build.sh`
- [x] `develop.py` - Converted from `scripts/develop.sh`
- [x] `test.py` - Deprecated: replaced by the built-in `hatch test` command. This script has been removed and will be deprecated in version 0.3.0.
- [x] `release.py` - Converted from `scripts/release.sh`
- [x] `publish.py` - Converted from `scripts/publish.sh`

Usage of `hatch test` command is described and needs to be updated in the [Testing and Build Guide](docs/rules/testing-and-build-guide.md) to reflect the new way of running the tests including coverage, HTML report, and auto-capture workflow.

### Test Coverage

Tests for the migrated scripts:

- [x] `test_log_chat.py` - Tests for `log_chat.py`
- [x] `test_analyze_chat.py` - Tests for `analyze_chat.py`
- [x] `test_promote_learning.py` - Tests for `promote_learning.py`
- [x] `test_review_promote.py` - Tests for `review_promote.py`
- [x] `test_log_error.py` - Tests for `log_error.py`
- [x] `test_log_test.py` - Tests for `log_test.py`
- [x] `test_log_quality.py` - Tests for `log_quality.py`
- [x] `test_validate_evidence.py` - Tests for `validate_evidence.py`
- [x] `test_build.py` - Tests for `build.py`
- [x] `test_develop.py` - Tests for `develop.py`
- [x] `test_release.py` - Tests for `release.py`
- [x] `test_publish.py` - Tests for `publish.py`

## Next Steps

The following tasks remain to complete the shell script migration:

### 1. Complete Test Implementation

Create tests for all remaining scripts following the established patterns:

- **For Client Scripts:** Follow the pattern in `test_log_chat.py`
  - Test with required arguments only
  - Test with all possible arguments
  - Test error handling

- **For Dev Scripts:** Follow the pattern in `test_build.py`
  - Test utility functions (e.g., `run_command`)
  - Test the main function with successful execution
  - Test error handling and failure scenarios

### 2. Build and Installation

- Rebuild the package to include the new Python modules
- Test installation without cloning the repo to verify that scripts are properly installed and accessible

### 3. Documentation

- Update documentation to reflect the new script organization
- Add usage examples for the new Python modules
- Remove references to the old shell scripts from documentation

### 4. Validation

- Ensure comprehensive test coverage (aim for >80%)
- Verify all scripts work properly in various environments (Linux, macOS, Windows)
- Confirm that scripts function correctly regardless of installation method (PyPI or from repo)

These changes will ensure that the scripts work properly regardless of how the package is installed, providing a more robust and maintainable solution.

## Implementation Requirements

Each migrated script must:

1. Maintain the same command-line interface as the original shell script
2. Have a `main()` function that returns an exit code
3. Include proper error handling
4. Include comprehensive tests in `tests/scripts/`
5. Be referenced in the pyproject.toml as a console entry point
6. Have proper type hints and docstrings

## Test Structure

Tests for scripts should follow these patterns:

### For Client Scripts

1. Test with required arguments only
2. Test with all possible arguments
3. Test error handling

### For Dev Scripts

1. Test utility functions (e.g., `run_command`)
2. Test the main function with successful execution
3. Test error handling and failure scenarios

## Common Mocking Patterns

1. Use `@patch("sys.argv", [...])` to mock command-line arguments
2. Use `@patch("module.path.function")` to mock external dependencies
3. For functions that call subprocess:
   - Mock `subprocess.run` to control return codes
   - Use `side_effect` to simulate different behaviors for different calls

## Running Tests (old shell scripts, deprecated)

```bash
# Run all script tests
./scripts/test.sh -v tests/scripts/

# Run a specific test file
./scripts/test.sh -v tests/scripts/test_log_chat.py

# With coverage report
./scripts/test.sh -c -v tests/scripts/
```

## Running Tests (new Python scripts, preferred method)

**Note:** The `--py` flag is used to specify the Python version to use for the tests. This speeds up the tests by using only one Python version instead of the default of using matrix based on all defined Python versions.

```bash
# Run all script tests
python -m chroma_mcp.dev_scripts.test -v --py 3.10 --auto-capture-workflow tests/scripts/

# Run a specific test file
python -m chroma_mcp.dev_scripts.test -v --py 3.10 --auto-capture-workflow tests/scripts/test_log_chat.py

# Run all script tests with coverage report
python -m chroma_mcp.dev_scripts.test -c -v --py 3.10 --auto-capture-workflow tests/scripts/

# Run a specific test file with coverage report
python -m chroma_mcp.dev_scripts.test -c -v --py 3.10 --auto-capture-workflow tests/scripts/test_log_chat.py
```

## Deprecation Plan

The original shell scripts located in the `scripts/` directory are deprecated and will be removed in version 0.3.0 of the package. Please migrate any automation to use the console entry points provided by the installed Python package, such as:

- `chroma-mcp-client log-chat`
- `chroma-mcp-client analyze-chat-history`
- `chroma-mcp-client promote-learning`
- `chroma-mcp-client review-promote`
- `chroma-mcp-client log-error`
- `chroma-mcp-client log-test`
- `chroma-mcp-client log-quality`
- `chroma-mcp-client validate-evidence`
