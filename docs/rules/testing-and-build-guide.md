# Rule: Testing and Build Guidelines

**Description:** This rule provides essential instructions for testing and building the project correctly, avoiding common pitfalls with test environment management.

## Testing Guidelines

### Always Use Hatch for Running Tests

Standard tests should **always** be run through Hatch or the provided test script, not directly with pytest:

```bash
# Preferred: Using the test script (runs test matrix, handles coverage)
./scripts/test.sh

# Alternative: Using Hatch directly
hatch run test
```

### Common Test Commands

```bash
# Run all tests with coverage report
./scripts/test.sh --coverage

# Run tests with HTML coverage report
./scripts/test.sh --html

# Force environment rebuild before testing (when dependencies change)
./scripts/test.sh --clean

# Run specific tests within the test matrix (new feature)
./scripts/test.sh tests/tools/test_auto_log_chat_bridge.py

# Run tests for a specific Python version only
./scripts/test.sh --python 3.10
# or
./scripts/test.sh --py 3.11

# Run tests with automated test failure/success tracking
./scripts/test.sh --auto-capture-workflow
# With coverage and verbose output
./scripts/test.sh --coverage --verbose --auto-capture-workflow
# or shorthand
./scripts/test.sh -c -v --auto-capture-workflow

# Combine options
./scripts/test.sh --coverage --python 3.12 tests/tools/
```

### Automated Test-Driven Learning

The `--auto-capture-workflow` flag enables the automated test-driven learning system which:

1. Automatically captures test failures with context
2. Monitors for transitions from failure to success after code changes
3. Creates validation evidence linking failures, fixes, and chat history
4. Promotes high-quality fixes to derived learnings

**Setup required before first use:**

```bash
chroma-mcp-client setup-test-workflow --workspace-dir .
```

After running tests with fixes, check for completed workflows:

```bash
chroma-mcp-client check-test-transitions --workspace-dir .
```

For complete details, see the [Automated Test Workflow Guide](../usage/automated_test_workflow.md).

### Avoid Direct pytest Usage

❌ **Incorrect:**

```bash
python -m pytest tests/
```

✅ **Correct:**

```bash
hatch run test
```

Using Hatch ensures:

- The proper Python matrix is used
- Dependencies are correctly resolved
- Environment variables are properly set
- Coverage reports are correctly generated

## Build Guidelines

Build the package using either:

```bash
# Using the provided script (cleans first)
./scripts/build.sh

# Or with Hatch directly
hatch build
```

This generates the distributable files in the `dist/` directory.

## Installing for IDE and CLI Usage

After modifying and testing the MCP server package, you need to rebuild and install it in the Hatch environment for the changes to take effect in Cursor (or any other IDE) or when using the `chroma-mcp-client` CLI:

### Full Version (with AI models for embeddings)

Use this approach when you need all embedding models available and have configured them in `mcp.json` or `.env`:

```bash
# Replace <version> with the actual version built (e.g., 0.2.7)
hatch build && hatch run pip uninstall chroma-mcp-server -y && hatch run pip install 'dist/chroma_mcp_server-<version>-py3-none-any.whl[full,dev]'
```

### Smaller Version (default embeddings only)

Use this lighter approach for faster installation with only fast and accurate embedding variants:

```bash
# Replace <version> with the actual version built (e.g., 0.2.7)
hatch build && hatch run pip uninstall chroma-mcp-server -y && hatch run pip install 'dist/chroma_mcp_server-<version>-py3-none-any.whl[client,dev]'
```

Please note, that for the MCP to be updated within the IDE, ask the user to manually reload the MCP server as there is no automated way available as of now, before continuing to try to talk to the updated MCP via tools call.

## Development Environment

Remember to activate the Hatch environment before making changes:

```bash
# Using the script
./scripts/develop.sh

# Or directly with Hatch
hatch shell
```

## Release Guidelines

When preparing a new release or updating the version:

1. **Update CHANGELOG.md** with the new version information:
   - Add a new section at the top with the new version number and date
   - Document all significant changes under "Added", "Fixed", "Changed", or "Removed" sections
   - Use clear, concise language to describe each change

    ```markdown
    ## [0.2.x] - YYYY-MM-DD

    **Added:**
    - New feature description

    **Fixed:**
    - Bug fix description

    **Changed:**
    - Change description
    ```

2. Ensure the version number is updated in `pyproject.toml`
3. Build the package and verify the correct version appears in the build artifacts
4. Test the new version to ensure all changes work correctly

## Complete Documentation

For comprehensive instructions, refer to the [Developer Guide](../developer_guide.md).
