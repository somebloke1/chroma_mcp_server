# Migration Plan: Transitioning to Hatch Build System

This document outlines a structured plan to migrate the Chroma MCP Server from its current complex build setup to a streamlined approach using Hatch build management.

## Current State Assessment

Based on the status documented in `uvx_integration_status.md`, we have:

- Multiple approaches attempted for building and running the package
- Several custom scripts for different build and run scenarios
- Issues with UVX integration and package discovery
- Overly complex dependency management
- Working local development setup but cumbersome distribution process

**Current files that handle packaging/running:**

- `run_chroma_mcp_uvx.py`: Attempts to build and run via UVX (not working)
- `run_chromamcp_local.py`: Creates venv and runs locally (working, but duplicate to run_choma_mcp.py due to uv/uvx tests)
- `run_with_uvx.py`: Tries to use UVX for the installed package (not working)
- `setup_for_uvx.py`: Installs in dev mode for UVX (partially working)
- `build_package.py`: Custom build logic (not working)
- `setup.py`: Minimal setup file (should be removed, as we have pyproject.html)
- `publish.sh`: Publication script (not working)
- `run_chroma_mcp.py`: Simplified run script (primary and main wrapper so far, working)
- `pyproject.toml`: Current project configuration and in use

## Migration Goals

1. Simplify the build and packaging process
2. Enable seamless integration with UVX
3. Create a clean, maintainable project structure
4. Follow modern Python packaging best practices
5. Reduce the number of custom scripts
6. Make the package easily distributable via PyPI

## Implementation Plan

### Phase 1: Project Restructuring

1. [x] Ensure source code is properly organized in `src/chroma_mcp/`
   - [x] Verify `__init__.py` contains proper version information
   - [x] Check that modules are correctly organized

2. [x] Create a `.python-version` file with the required Python version

   ```bash
   3.10
   ```

   **Note:** We also should explicitely in pyproject.toml support 3.11 and 3.12 as we want to use the latest available version due to performance and compatibility reasons.

3. [x] Update or create necessary configuration files:
   - [x] `.gitignore` for Python/Hatch specific files
   - [ ] `.editorconfig` for consistent formatting

### Phase 2: Hatch Configuration

1. [x] Replace the current `pyproject.toml` with a Hatch-compatible version:

    ```toml
    [build-system]
    requires = ["hatchling"]
    build-backend = "hatchling.build"

    [project]
    name = "chroma-mcp-server"
    version = "0.1.0"
    description = "Chroma MCP Server - Vector Database Integration for LLM Applications"
    readme = "README.md"
    requires-python = ">=3.10"
    license = "MIT"
    authors = [
        { name = "Nold Coaching & Consulting", email = "info@noldcoaching.de" }
    ]
    keywords = ["chroma", "mcp", "vector-database", "llm", "embeddings"]
    classifiers = [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ]
    dependencies = [
        "chromadb>=0.6.3",
        "fastmcp>=0.4.1",
        "python-dotenv>=0.19.0",
    ]

    [project.optional-dependencies]
    dev = [
        "pytest>=8.3.5",
        "pytest-cov>=6.0.0",
        "black>=25.1.0",
        "isort>=6.0.1",
        "mypy>=1.15.0",
    ]

    [project.scripts]
    chroma-mcp-server = "chroma_mcp.server:main"

    [tool.hatch.build.targets.wheel]
    packages = ["src/chroma_mcp"]

    [tool.hatch.build.targets.sdist]
    include = [
        "/src",
        "/tests",
    ]
    ```

2. [x] Verify that the entry point function (`main()`) exists in `server.py` or create it

### Phase 3: Setup Hatch Environment

1. [x] Install Hatch globally:

   ```bash
   pip install hatch
   ```

2. [x] Initialize Hatch environment:

   ```bash
   hatch env create
   ```

3. [x] Test running the server in the Hatch environment:

   ```bash
   hatch run python -m chroma_mcp.server
   ```

### Phase 3.5: Fix Module Imports

1. [x] Update all imports in the codebase to use the correct package structure:
   - [x] Fix any `src.chroma_mcp` imports to use relative imports or direct `chroma_mcp` imports
   - [x] Update code that relies on the src module structure to work with the installed package
   - [x] Test imports in the development environment

   **Issue resolved**: Converted absolute imports with `src.chroma_mcp` prefix to relative imports using `..module` syntax in handler files and in test files.

### Phase 4: Build and Test

1. [x] Build the package with Hatch:

   ```bash
   hatch build
   ```

2. [x] Install the built wheel for testing:

   ```bash
   pip install dist/chroma_mcp_server-*.whl
   ```

3. [x] Test the installed package:

   ```bash
   chroma-mcp-server
   ```

   **Note**: Command works but terminal hangs as expected (server waiting for input).

4. [x] Test with UV:

   ```bash
   uv pip install dist/chroma_mcp_server-*.whl
   uv run chroma-mcp-server
   ```

   **Current Status:** UV installation works successfully. When using UVX, you may need a specific installation method as `uvx install` isn't available directly. The package might need to be published to a registry for UVX to find it.

   Note: Continued Cursor MCP integration will use the UVX command line tool to run the package.

### Phase 5: Create Simplified Development Scripts

1. [x] Create a simple `develop.sh` script for local development:

   ```bash
   #!/bin/bash
   # Simplified development setup
   
   hatch shell
   ```

2. [x] Create a `build.sh` script for building the package:

   ```bash
   #!/bin/bash
   # Build the package
   
   hatch build
   ```

3. [x] Create a `publish.sh` script for publishing to PyPI:

   ```bash
   #!/bin/bash
   # Publish to PyPI
   
   hatch build
   hatch publish
   ```

### Phase 5.5: Testing Setup

1. [x] Ensure testing dependencies are properly installed:

   ```bash
   # Install directly in the current environment
   pip install pytest pytest-asyncio pytest-cov

   # Or with hatch (preferred method)
   hatch env create
   hatch shell
   ```

   **Note:** You may see a message suggesting to upgrade pip. While not critical, it's good practice to follow this recommendation:

   ```bash
   pip install --upgrade pip
   ```

2. [x] Modify pytest configuration when needed:
   - During development, you can temporarily disable coverage to focus on fixing specific tests
   - For CI/CD and full test suite runs, use the complete configuration

3. [x] Use the Hatch-integrated test runner for convenience:

   ```bash
   # Run all tests with coverage (uses Hatch environment automatically)
   ./test.sh

   # Or use run_tests.py directly with more options
   python run_tests.py --coverage --verbose
   python run_tests.py --test-type unit --coverage --html --xml
   ```

   The updated Python test runner (`run_tests.py`) provides several advantages:
   - Automatically uses the Hatch environment
   - Detects if it's running outside a Hatch environment and restarts itself with Hatch
   - Supports different test types (unit, integration, all)
   - Configures coverage reporting options (terminal, HTML, XML)
   - Works consistently across platforms

### Phase 6: Documentation Updates

1. [x] Update `README.md` with new instructions for:
   - [x] Installation via pip/UVX
   - [x] Development setup using Hatch
   - [x] Building and distributing the package

2. [ ] Update `docs/getting_started.md` with the new workflow
   - [ ] Development instructions
   - [ ] Configuration options
   - [ ] Integration with Cursor MCP

3. [x] Create an example MCP integration config for `.cursor/mcp.json`:

   ```json
   {
     "mcpServers": {
       "chroma": {
         "command": "uvx",
         "args": ["chroma-mcp-server"],
         "env": {
           "CHROMA_DATA_DIR": "/path/to/data",
           "CHROMA_LOG_DIR": "/path/to/logs"
         }
       }
     }
   }
   ```

4. [x] Created `smithery.yaml` for Smithery integration

### Phase 7: Cleanup

1. [x] Remove obsolete files:
   - [x] `run_chroma_mcp_uvx.py`
   - [x] `run_chromamcp_local.py`
   - [x] `run_with_uvx.py`
   - [x] `setup_for_uvx.py`
   - [x] `build_package.py`
   - [x] `setup.py`
   - [x] Old `publish.sh`
   - [x] `run_chroma_mcp.py` (confirmed no longer required with the proper entry point)
   - [x] `run_server.py` (confirmed no longer required with the proper entry point)

2. [x] Clean up obsolete virtual environments:
   - [x] `.venv_uvx/`
   - [x] `.venv_chromamcp/`
   - [x] (Removed `.venv/` in favor of Hatch environments)

3. [x] Update `.gitignore` to exclude Hatch-specific files and directories

### Phase 8: Dependency Optimization

1. [x] Audit dependencies in `pyproject.toml`:
   - [x] Remove unused packages to reduce installation time and footprint
   - [x] Organize dependencies into logical groupings
   - [x] Move non-essential packages to optional dependencies

2. [x] Optimize `requirements.txt`:
   - [x] Align with optimized dependencies in `pyproject.toml`
   - [x] Organize into clear sections with explanatory comments
   - [x] Remove duplicated and unused packages

3. [x] Test optimized dependencies:
   - [x] Verify that all tests still pass
   - [x] Confirm that builds succeed with reduced dependencies
   - [x] Ensure development workflow remains functional

## Testing Checklist

- [x] Local development with `hatch shell` works
- [x] Building with `hatch build` produces valid wheel and sdist
- [x] The package can be installed with pip from the wheel
- [x] The package can be installed with UV from the wheel
- [x] The entry point runs correctly
- [x] Server functionality is unchanged
- [x] Integration with Cursor MCP works
- [x] Unit tests pass (with minor adjustments for new import structure)

## Validation Steps

1. [x] Verify the package structure with `pip show chroma-mcp-server`
2. [x] Confirm executable script is available in PATH
3. [x] Run the server and verify it starts correctly
4. [x] Test with Cursor MCP integration
5. [x] Verify all dependencies are correctly resolved
6. [x] Verify testing infrastructure works (pytest with coverage)

## Final Deliverables

- [x] Clean, Hatch-managed Python package
- [x] Simple, understandable build and development process
- [x] UV compatibility established (UVX integration ready pending package publishing)
- [x] Updated documentation
- [x] Streamlined codebase without duplicate functionality
- [x] Testing infrastructure with coverage reporting
- [x] Optimized dependencies with clear organization

## References

- [Hatch Documentation](https://hatch.pypa.io/latest/)
- [Python Packaging User Guide](https://packaging.python.org/en/latest/)
- [UVX Documentation](https://github.com/astral-sh/uv)
- [Chroma MCP GitHub Repository](https://github.com/chroma-core/chroma-mcp)
