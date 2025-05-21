# Using the Automated Test Workflow Pytest Plugin

The `chroma-mcp-server` package includes a Pytest plugin that enables automated capture of test failures and transitions, linking them to your ChromaDB instance for enhanced learning and analysis. This guide explains how to leverage this plugin in your own Python projects when you have `chroma-mcp-server` installed as a dependency.

## Prerequisites

1. **`chroma-mcp-server` Installed with Client Extras:**
    Ensure that `chroma-mcp-server` is installed in your project's environment with the `client` extras, which include the pytest plugin.

    ```bash
    pip install "chroma-mcp-server[client]"
    # or if using a specific version
    # pip install "chroma-mcp-server[client]==0.2.23"
    ```

2. **Pytest Installed:**
    Your project must use `pytest` for running tests.

    ```bash
    pip install pytest
    ```

3. **ChromaDB Setup:**
    You need a running ChromaDB instance (local or remote) and your project environment should be configured to connect to it. This typically involves setting environment variables like `CHROMA_DB_IMPL`, `CHROMA_DB_PATH` (for local persistent), or `CHROMA_HTTP_URL` (for HTTP). Refer to the main `chroma-mcp-server` documentation for ChromaDB setup.

4. **`.env` File (Recommended):**
    Place a `.env` file in your project root with the necessary ChromaDB connection details. The plugin and `chroma-mcp-client` will load these.

    Example `.env` for a local persistent ChromaDB:

    ```dotenv
    CHROMA_DB_IMPL="persistent"
    CHROMA_DB_PATH="./data/my_project_chroma_db" # Path relative to your project root
    CHROMA_LOG_DIR="./logs/my_project_chroma_logs"
    LOG_LEVEL="INFO"
    TOKENIZERS_PARALLELISM="false"
    ```

## Enabling the Plugin

Once `chroma-mcp-server[client]` is installed in your environment, Pytest should automatically discover the plugin (named `chroma_mcp_workflow`).

To activate its functionality, you need to pass the `--auto-capture-workflow` flag to your `pytest` command.

## How it Works

When you run `pytest --auto-capture-workflow`:

1. **Initial Failure Capture:** If a test fails, the plugin records details about the failure (test name, file, error message, stack trace) into your `test_results_v1` collection in ChromaDB.
2. **Transition Tracking:** The plugin sets up a `post-commit` Git hook (if you run the `setup-test-workflow` command from `chroma-mcp-client`). When you commit changes:
    - If a previously failing test now passes, the plugin identifies this transition.
    - It captures the "before" (failing) and "after" (passing) states of the test and the associated code changes (diff).
    - This rich transition information is also logged to ChromaDB, potentially linking it to chat history if that integration is also active.
3. **Learning & Analysis:** The captured failures and successful resolutions become valuable data for:
    - Understanding common error patterns.
    - Identifying effective solutions.
    - Potentially creating "derived learnings" that can be fed back into a RAG system.

## Usage Examples

Assuming your project uses `pytest` and you have your environment set up:

**Running Pytest with the Workflow Capture:**

```bash
pytest --auto-capture-workflow
```

Or, if you run tests via a script or a tool like `nox` or `tox`, ensure this flag is added to the `pytest` invocation.

**If using `hatch` (similar to `chroma-mcp-server`'s own setup):**

You can define a script alias in your project's `pyproject.toml`:

```toml
[tool.hatch.envs.hatch-test.scripts]
# Example: always run tests with the workflow capture
cov = "coverage run -m pytest --auto-capture-workflow {args}"
```

Then you can run:

```bash
hatch test --cover # (or hatch run cov)
```

## Setting up Git Hooks (Optional but Recommended)

To enable the full transition tracking (detecting when a failing test starts passing after a commit), you need to set up the Git hooks provided by `chroma-mcp-client`.

From your project's root directory (where your `.git` folder is):

```bash
chroma-mcp-client setup-test-workflow
```

This command will install/update the necessary `post-commit` hook in your local repository's `.git/hooks` directory. It's designed to be non-destructive and will attempt to preserve any existing content in your `post-commit` hook.

## Verifying Plugin Activation

When `pytest` starts, it lists active plugins. You should see `chroma-mcp-workflow` (or similar, it might show the version like `chroma-mcp-server-0.2.23`) in the list:

```bash
$ pytest
============================= test session starts ==============================
platform ... -- Python ..., pytest-..., pluggy-...
plugins: ..., chroma-mcp-server-0.2.23, ...  <-- Look for this
collected X items
...
============================== X passed in Ys ================================
```

If the `--auto-capture-workflow` flag is recognized and the plugin is working, you will see log messages from `chroma-mcp-client` in your console output during and after the test run, indicating interactions with ChromaDB.

## Benefits for Your Project

- **Automated Learning:** Automatically captures valuable data from your test cycles.
- **Reduced Manual Effort:** Less need to manually document how a failing test was fixed.
- **Data-Driven Insights:** Builds a dataset that can be analyzed to improve code quality and development practices.
- **Enhanced RAG:** If you also use `chroma-mcp-server` for RAG, these captured learnings can enrich the context provided to your AI assistant.

By integrating this plugin, you bring a part of the "error-driven learning" capabilities of `chroma-mcp-server` directly into your project's development lifecycle.
