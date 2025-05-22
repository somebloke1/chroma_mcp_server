# Using the Automated Test Workflow Pytest Plugin

The `chroma-mcp-server` package includes a Pytest plugin that enables automated capture of test failures and transitions, linking them to your ChromaDB instance for enhanced learning and analysis. This guide explains how to leverage this plugin in your own Python projects when you have `chroma-mcp-server` installed as a dependency.

## Prerequisites

1. **`chroma-mcp-server` Installed with Client Extras in Your Project:**
    Ensure that `chroma-mcp-server` is installed **in your project's environment** with the `client` extras. This is what provides the pytest plugin.

    ```bash
    pip install "chroma-mcp-server[client]"
    # or if using a specific version
    # pip install "chroma-mcp-server[client]==0.2.23"
    ```

2. **Pytest Installed in Your Project:**
    Your project must use `pytest` for running tests.

    ```bash
    pip install pytest
    ```

3. **ChromaDB Setup for Your Project:**
    You need a running ChromaDB instance and your project environment should be configured to connect to it.

4. **`.env` File in Your Project (Recommended):**
    Place a `.env` file in your project root with the necessary ChromaDB connection details.

    Example `.env` for a local persistent ChromaDB:

    ```dotenv
    CHROMA_DB_IMPL="persistent"
    CHROMA_DB_PATH="./data/my_project_chroma_db" # Path relative to your project root
    CHROMA_LOG_DIR="./logs/my_project_chroma_logs"
    LOG_LEVEL="INFO"
    TOKENIZERS_PARALLELISM="false"
    ```

## Integrating the Plugin into Your Project

To use the `--auto-capture-workflow` functionality in your own project (let's call it `your-project`), follow these steps:

**1. Declare `chroma-mcp-server[client]` as a Dependency:**

In `your-project/pyproject.toml` (or your project's equivalent dependency file, like `requirements.txt`), add `chroma-mcp-server` with the `[client]` extra:

```toml
# In your-project/pyproject.toml

[project]
# ... other project metadata for your-project ...
dependencies = [
    "chroma-mcp-server[client]>=0.2.24", # Replace with the desired or latest version
    # ... other dependencies for your-project ...
]

# If you are not using a [project] table, but perhaps directly defining
# dependencies for a Hatch environment, it would look like:
# [tool.hatch.envs.default.dependencies]
# "chroma-mcp-server[client]>=0.2.24"
```

The `[client]` extra is essential as it ensures the `chroma_mcp_client.pytest_plugin` module and its dependencies are installed.

**2. Install/Update Your Project's Environment:**

Ensure that this dependency is installed into the Python environment you use for running `pytest` in `your-project`.

- If using Hatch for `your-project`:

  Hatch typically installs/updates dependencies when an environment is created or when you run commands like `hatch build` or `hatch dep sync <your-env-name>`.
  
  If you've just added the dependency, ensure your environment is up-to-date. You might need to:

  - Recreate the environment: `hatch env remove <your-env-name>` (e.g., `hatch-test.py3.12`) and then let Hatch rebuild it on the next `hatch run <your-env-name>:pytest ...` command.
  - Or explicitly install/update: `hatch run <your-env-name>:pip install --upgrade "chroma-mcp-server[client]"`

**3. Verify Plugin Discovery (Crucial):**

Before using the `--auto-capture-workflow` flag, confirm that `pytest` in `your-project`'s environment can find the plugin:

   a. **Activate your project's test environment:**
      ```bash
      # Example if using Hatch for your-project
      hatch shell <your-env-name>
      hatch shell hatch-test.py3.12 # if you have such a matrix
      ```

   b. **Check installed packages:**
      Inside the activated shell, run:
      ```bash
      pip list
      ```
      Verify that `chroma-mcp-server` is listed and is the version you expect.

   c. **Check `pytest` plugin registration:**
      Still inside the activated shell, run:
      ```bash
      pytest --trace-config
      ```
      The output **must** include a line similar to this (the path will vary):
      `PLUGIN registered: chroma_mcp_workflow (<...>/dist-packages/chroma_mcp_client/pytest_plugin.py)`
      If `chroma_mcp_workflow` is *not* listed here, `pytest` does not see the plugin, and the `--auto-capture-workflow` flag will be unrecognized. This usually means `chroma-mcp-server[client]` is not correctly installed in *this specific active environment*.

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

Assuming your project uses `pytest` and you have your environment set up **as described in "Integrating the Plugin into Your Project"**:

**Running Pytest with the Workflow Capture:**

Directly with `pytest` (if it's in your PATH and the environment is active):

```bash
pytest --auto-capture-workflow
```

**If using `hatch`:**

If your project has a `pyproject.toml` with a test script defined (as shown in the `chroma-mcp-server` example):

You can define a script alias in your project's `pyproject.toml`:

```toml
[tool.hatch.envs.hatch-test.scripts]
# Example: always run tests with the workflow capture
cov = "coverage run -m pytest --auto-capture-workflow {args}"
# Or a simpler version without coverage directly in the alias
test-workflow = "pytest --auto-capture-workflow {args}"
```

Then you can run:

```bash
hatch run hatch-test:cov # (or hatch run hatch-test:test-workflow)
# or, if 'cov' is the default script for the 'test' or 'hatch-test' environment
# hatch test --cover (using the 'cov' script)
```

**Using `hatch run` (Recommended for projects without specific `pyproject.toml` test scripts):**

If your project doesn't have a `pyproject.toml` or you don't want to add custom scripts, you can directly invoke `pytest` within the Hatch environment:

```bash
# Assuming 'pytest' is available in the default Hatch environment
hatch run pytest --auto-capture-workflow

# If you use a specific environment, e.g., 'test' or 'hatch-test'
hatch run test:pytest --auto-capture-workflow

# To include coverage:
hatch run test:coverage run -m pytest --auto-capture-workflow
```

This method bypasses the need for `pyproject.toml` script definitions for the simple execution of `pytest` with the required flag.
The `--auto-capture-workflow` flag is passed directly to `pytest`.

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
