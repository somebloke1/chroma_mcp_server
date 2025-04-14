# Chroma MCP Server - Developer Guide

This guide provides instructions for developers working on the `chroma-mcp-server` codebase, including setup, testing, building, and releasing.

## Development Environment Setup

This project uses [Hatch](https://hatch.pypa.io/) for development and package management.

1. **Prerequisites:**
    * Python 3.10 or higher
    * Git
    * `curl` and `jq` (required by the `release.sh` script)
    * Hatch (Install globally if you don't have it: `pip install hatch`)

2. **Clone the Repository:**

    ```bash
    git clone https://github.com/djm81/chroma_mcp_server.git # Or your fork
    cd chroma_mcp_server
    ```

3. **Activate Hatch Environment:** Use the provided script or run `hatch shell` directly:

    ```bash
    # Using the script
    ./scripts/develop.sh

    # Or directly with Hatch
    hatch shell
    ```

    This command creates (if needed) and activates a virtual environment managed by Hatch, installing all necessary development dependencies listed in `pyproject.toml`.

4. **Configure Local MCP Servers (Optional, for Cursor):**
    If you intend to test integration with Cursor locally:
    * Copy the example configuration: `cp .cursor/mcp.example.json .cursor/mcp.json`
    * Edit `.cursor/mcp.json` and adjust environment variables as needed, especially:
        * `CHROMA_DATA_DIR`: Set a path for persistent storage.
        * `CHROMA_LOG_DIR`: Set a path for log files.
        * `LOG_LEVEL`: Adjust logging verbosity (e.g., `DEBUG`, `INFO`).
        * `CHROMA_EMBEDDING_FUNCTION`: Ensure consistency if set.
    * The `.cursor/mcp.json` file allows defining multiple server configurations. By convention, this project often includes:
        * `"chroma"`: Runs the version of `chroma-mcp-server` last installed locally via `uvx` (typically the production version installed by `release.sh`).
        * `"chroma_test"`: Configured to automatically fetch and run the *latest* version available on **TestPyPI**. This is useful for testing release candidates or development versions before a full production release.

    Here's an example snippet for the `chroma_test` configuration:

    ```json
    {
      "mcpServers": {
        "chroma_test": {
          "command": "uvx",
          "args": [
            "--refresh", // Ensures latest is checked
            "--default-index", "https://test.pypi.org/simple/", // Prioritize TestPyPI
            "--index", "https://pypi.org/simple/", // Fallback to PyPI
            "--index-strategy", "unsafe-best-match", // Strategy for finding packages
            "chroma-mcp-server@latest",
            "--client-type=ephemeral",
            "--embedding-function=default" // Example: Choose your embedding function
          ],
          "env": {
            "CHROMA_CLIENT_TYPE": "persistent",
            "CHROMA_DATA_DIR": "/path/to/your/test_data", // Use a separate test data dir
            "CHROMA_LOG_DIR": "/path/to/your/test_logs", // Use separate test logs
            "LOG_LEVEL": "DEBUG",
            "MCP_LOG_LEVEL": "DEBUG",
            "CHROMA_EMBEDDING_FUNCTION": "default" // Ensure consistency if set
          }
        },
        // ... other server definitions like "chroma"
      }
    }
    ```

    Remember to replace the placeholder paths for `CHROMA_DATA_DIR` and `CHROMA_LOG_DIR`.

## Development Scripts Overview

The project includes several utility scripts in the `scripts/` directory to streamline common tasks:

* `develop.sh`: Activates the Hatch development environment.
* `test.sh`: Runs tests using pytest (via Hatch). Supports flags like `--coverage`, `--clean`.
* `build.sh`: Cleans the build directory and builds the package wheel.
* `publish.sh`: Publishes the package to PyPI or TestPyPI. Requires credentials and version.
* `test_uvx_install.sh`: Builds the package locally and tests installing it via `uv pip install`.
* `release.sh`: Automates the full release process (TestPyPI -> Prod PyPI -> Install specified version locally for `uvx` command). See script help (`./scripts/release.sh --help`) for options.

## Common Development Workflow

1. **Activate Environment:** Run `./scripts/develop.sh` or `hatch shell`.
2. **Make Code Changes:** Edit the source code in the `src/` directory.
3. **Run Tests:** Execute `./scripts/test.sh` to run the test suite. Add `--coverage` for a coverage report or `--clean` to force a rebuild of the test environment.

    ```bash
    # Using the script (recommended for matrix testing & coverage)
    ./scripts/test.sh # Runs test matrix

    # Or using hatch directly for the default environment
    hatch run test
    ```

4. **Build (Optional):** Run `./scripts/build.sh` to create a package wheel locally.
5. **Test Local Install (Optional):** Run `./scripts/test_uvx_install.sh` to verify the locally built wheel installs correctly via `uv pip install`.

## Running the Server Locally

While developing, you can run the server directly within the Hatch environment:

```bash
# Ensure the Hatch environment is active (./scripts/develop.sh or hatch shell)
# Run the server using python -m
python -m chroma_mcp.server [OPTIONS]

# Example with persistent storage:
python -m chroma_mcp.server --client-type persistent --data-dir ./dev_data --log-dir ./dev_logs
```

Alternatively, for testing integration with tools like Cursor that use `uvx`, you might use the `release.sh` script to build, publish (e.g., to TestPyPI), and install that specific version for the `uvx chroma-mcp-server` command (see Releasing below).

## Testing

Tests are located in the `tests/` directory and use `pytest`. Run tests using the script:

```bash
# Run all tests across the Python matrix (defined in pyproject.toml)
# Using the script (recommended for matrix testing & coverage)
# This uses hatch run test:run internally for matrix.
./scripts/test.sh # Runs test matrix

# Or run tests only for the default environment using Hatch
hatch run test

# Run tests across the matrix and generate coverage reports.
# This runs tests first, then combines data, then generates:
# 1. Terminal report (with missing lines)
# 2. XML report (coverage.xml for Codecov)
./scripts/test.sh --coverage 
# or shorthand:
./scripts/test.sh -c

# Run tests across the matrix and generate an HTML coverage report.
# This runs tests first, then combines data, then generates the report
# in the coverage_html/ directory (as configured in pyproject.toml).
./scripts/test.sh --html

# Force environment rebuild before testing (useful if dependencies change)
./scripts/test.sh --clean
```

Note that coverage reports (`terminal`, `XML`, `HTML`) are generated *after* all tests across all configured Python versions have completed.

```bash
# Run specific tests within the Hatch environment
hatch run test:run tests/tools/test_collection_tools.py::TestCollectionTools::test_create_collection_success
```

## Building the Package

Use the provided script or Hatch directly:

```bash
# Using the script (cleans first)
./scripts/build.sh

# Or manually with Hatch
hatch build
```

This will generate the distributable files (wheel and sdist) in the `dist/` directory.

## Publishing to PyPI/TestPyPI

The `publish.sh` script handles publishing. It requires the target (`-t` for TestPyPI, `-p` for PyPI) and the version (`-v`). Credentials can be supplied via environment variables (`PYPI_USERNAME`, `PYPI_PASSWORD`) or interactively.

```bash
# Publish version 0.2.0 to TestPyPI
./scripts/publish.sh -t -v 0.2.0

# Publish version 0.2.0 to Production PyPI
./scripts/publish.sh -p -v 0.2.0
```

**Note:** Publishing is usually handled automatically as part of the `release.sh` script.

## Releasing a New Version

The `release.sh` script provides a streamlined process for releasing a new version:

1. Prompts for the version number (if not provided via `--version`).
2. Optionally builds and publishes to TestPyPI.
3. Optionally tests local installation from TestPyPI.
4. Builds and publishes to Production PyPI.
5. Installs the newly released version (from PyPI or TestPyPI based on `--update-target`) locally for use with the standard `uvx chroma-mcp-server` command.

```bash
# Run interactively, prompted for version and options
./scripts/release.sh

# Release version 0.2.0 non-interactively, update local uvx from Prod PyPI
./scripts/release.sh --version 0.2.0 -y --update-target prod

# Run only TestPyPI steps for version 0.2.1
./scripts/release.sh --version 0.2.1 --test-only

# See script help for all options
./scripts/release.sh --help
```

## Dependencies

* **Core:** `python-dotenv`, `pydantic`, `fastapi`, `uvicorn`, `chromadb`, `fastmcp`, `numpy`, `onnxruntime`.
* **Optional (`[full]`):** `sentence-transformers`, `httpx`.
* **Development (`dev`):** `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-mock`, `pytest-xdist`, `black`, `isort`, `mypy`, `pylint`, `types-PyYAML`.

See `pyproject.toml` for specific version constraints.

## Troubleshooting

* **UVX Cache Issues:** If `uvx` seems stuck on an old version after a release or install, try refreshing its cache: `uvx --refresh chroma-mcp-server --version`
* **Dependency Conflicts:** Ensure your Hatch environment is clean (`hatch env remove default && hatch env create`) or run tests with `./scripts/test.sh --clean`.
* **Release Script Errors:** Ensure `curl` and `jq` are installed. Check PyPI/TestPyPI credentials if publishing fails.
