# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.22] - 2025-05-21

**Fixed:**

- Corrected `coverage.xml` output path in GitHub Actions workflow (`.github/workflows/tests.yml`) for proper Codecov integration.
- Ensured `publish.py` handles `getpass` failures gracefully in non-interactive environments (e.g., CI).

**Changed:**

- Enhanced `publish.py` with an `--upload-retries` argument and verbose output for `twine` on retry attempts.
- Updated `release.py` to include `--upload-retries` and to check if a version already exists on PyPI/TestPyPI before attempting to publish, skipping redundant uploads.
- Updated documentation (including `docs/rules/testing-and-build-guide.md`, `docs/refactoring/shell_script_migration_plan.md`) to reflect deprecation of `build.sh`, `publish.sh`, `release.sh` and promote Python-based equivalents.

## [0.2.21] - 2025-05-21

**Changed:**

- Removed `develop.py` script for interactive Hatch shell development, as it's being replaced by `hatch shell`
- Updated Developer Guide to note deprecation of `curl` and `jq` in v0.3.0

## [0.2.20] - 2025-05-21

**Added:**

- Introduced a guided release process in `src/chroma_mcp/dev_scripts/release.py` with interactive flags (`--yes`, `--skip-testpypi`, `--test-only`, `--skip-tests`, `--skip-build`) and automated TestPyPI and Production publication via `hatch run publish-mcp`.
- Implemented enhanced changelog insertion logic in `release.py` to insert new entries before existing ones.

**Changed:**

- Updated `TestWorkflowManager.setup_git_hooks` in `src/chroma_mcp_client/validation/test_workflow.py` to use `hatch test --cover -v` for pre-push, `hatch run chroma-mcp-client index` for post-commit indexing, and `chroma-mcp-client check-test-transitions` for transition checks.

## [0.2.19] - 2025-05-21

**Added:**

- Extracted `get_project_root()` into a dedicated `project_root.py` module under `src/chroma_mcp/dev_scripts/`, and updated `build.py`, `develop.py`, `release.py`, and `publish.py` to import from it for cleaner dependencies.
- Completed migration of development scripts by removing the deprecated `test.py` and adding comprehensive unit tests for `build.py`, `develop.py`, `release.py`, and `publish.py` in `tests/scripts/`.

**Changed:**

- Updated unit tests under `tests/scripts/` to align with the new `get_project_root()` implementation and consolidated test execution via `hatch test`.

## [0.2.18] - 2025-05-17

**Added:**

- Added test artifacts organization with dedicated `logs/tests/` directory structure for JUnit XML reports, coverage data, and workflow tracking files.
- Added automatic cleanup of test artifacts after successful processing to reduce clutter.
- Updated coverage configuration in pyproject.toml to store `.coverage` file and HTML reports in the `logs/tests/coverage/` directory.
- Implemented automatic log rotation to remove log files older than the specified retention period (default 7 days).
- Restored Git integration documentation in getting_started.md and developer_guide.md with instructions for automatic codebase indexing using Git hooks.

**Fixed:**

- Fixed critical bug in TestWorkflowManager's `cleanup_processed_artifacts` method to properly clean up test artifacts.
- Enhanced cleanup logic to only remove files that have been successfully processed.
- Added safety checks to prevent accidental removal of important data.

## [0.2.17] - 2025-05-17

**Added:**

- Added `chroma-mcp-client` command as a replacement for `chroma-client` for better naming consistency.

**Changed:**

- Deprecated `chroma-client` command in favor of `chroma-mcp-client`. The old command will be removed in version 0.3.0.
- Updated all documentation and scripts across the repository to use `chroma-mcp-client` instead of `chroma-client`.
- Implemented backward compatibility wrapper in `deprecated_cli.py` that shows a warning when using the old command.
- Modified GitHub Actions workflow to use the new test artifact locations.

All notable changes to the Chroma MCP Server will be documented in this file.

## [0.2.16] - 2025-05-17

**Fixed:**

- Fixed critical bug in TestWorkflowManager's `setup_git_hooks` method to properly preserve existing hooks
- Enhanced hook preservation logic to maintain both indexing and test transition functionality
- Improved detection and handling of various hook configurations (empty, partial, complete)
- Added comprehensive tests for different hook preservation scenarios
- Ensured custom hook content is preserved when updating existing hooks

## [0.2.15] - 2025-05-17

**Added:**

- Implemented robust Git hook preservation in `setup-test-workflow` to maintain existing functionality
- Enhanced TestWorkflowManager to detect and append to existing post-commit hooks
- Added automatic correlation between test transitions and chat history
- Improved bidirectional linking between test results, code changes, and discussions
- Added comprehensive documentation for the test-driven learning workflow setup
- Enhanced CLI integration with workflow management commands

## [0.2.14] - 2025-05-17

**Added:**

- Implemented test-driven learning flow with structured test result capture
- Added JUnit XML integration for automatic test result processing
- Created `test_results_v1` collection with schema for tracking test execution outcomes
- Implemented bidirectional linking between test results, code chunks, and discussions
- Added validation evidence framework with scoring system for quality measurement
- Developed `log-test-results` CLI command for capturing test transitions
- Enhanced `analyze-chat-history` to incorporate validation scores
- Added failure-to-success transition tracking for concrete learning validation
- Implemented automated test-driven learning workflow with TestWorkflowManager
- Added `setup-test-workflow` command to automatically create Git hooks for test tracking
- Added `check-test-transitions` command to detect and promote successful test transitions
- Enhanced `test.sh` script with `--auto-capture-workflow` flag for seamless integration
- Created comprehensive unit tests for the new test workflow functionality
- Enhanced "Second Brain" documentation with comprehensive diagrams and explanations
- Improved Mermaid diagrams with consistent styling and color schema across all documentation
- Added detailed documentation for sequential thinking process and tools
- Enhanced documentation for bidirectional linking between code and chat history
- Added comprehensive explanation of test-driven learning workflow
- Created detailed `automated_test_workflow.md` guide for the new functionality

**Improved:**

- Enhanced `test.sh` script to generate structured test results for analysis
- Updated promotion workflow to prioritize learnings with test validation evidence
- Refined learning validation with weighted scoring for different evidence types
- Standardized all Mermaid diagrams to use dark theme and consistent color coding
- Better visualization of the three key learning flows in the Second Brain ecosystem
- More detailed explanations of knowledge capture mechanisms

## [0.2.10] - 2025-05-15

**Changed:**

- Updated license to MIT with Commons Clause extension to prevent direct competition
- License now explicitly disallows selling Chroma MCP Server itself, offering it as a hosted service, or creating competing products based on Chroma MCP Server
- Added clarification in README.md about allowed and disallowed uses of the software

## [0.2.9] - 2025-05-14

**Added:**

- Comprehensive tool_usage_format.md documentation for standardized tool usage format
- Enhanced test script with ability to specify test paths and Python versions
- Improved MCP test flow documentation with updated tool parameters
- Cross-references between log-chat.md and tool_usage_format.md

**Fixed:**

- Standardized tool_usage parameter format in auto_log_chat functionality
- Enhanced auto_log_chat_impl.py for backwards compatibility
- Updated IDE configuration files (.cursorrules, .windsurfrules, .github/.copilot-instructions.md) for consistency
- Added reminder to manually reload MCP server in IDE after installation

## [0.2.8] - 2025-05-13

**Added:**

- Enhanced interactive promotion workflow with auto-promote mode
- Smart defaults for all fields in promotion process
- Low confidence warnings for quality control
- Improved bidirectional linking code selection
- Testing and build guide for better development workflow
- Documentation updates for new features

**Fixed:**

- More robust logging system for MCP server
- Test suite improvements and refactoring
- Enhanced error handling in promotion workflow

## [0.2.6] - 2025-05-12

**Added:**

- Memory integration with sequential thinking architecture
- Improved integration with derived learnings module

## [0.2.4] - 2025-05-12

**Added:**

- Enhanced developer documentation for testing workflow
- Improved error handling for chat history analysis

## [0.2.3] - 2025-05-12

**Fixed:**

- Test stability improvements for client library
- Fixed logging configuration issues

## [0.2.2] - 2025-05-11

**Added:**

- Additional embeddings support for different model types
- Improved session handling for sequential thinking

## [0.2.1] - 2025-05-10

**Fixed:**

- Documentation improvements for new features
- Fixed version dependencies for Python 3.10-3.12 compatibility

## [0.2.0] - 2025-05-09

**Added:**

- Restructured documentation for better navigation
- Improved embedding function handling in indexer
- Enhanced logging setup with better configuration
- Derived learnings promotion workflow
- Memory integration tools for sequential thinking
- More comprehensive test coverage

**Fixed:**

- Fixed client-side logging configuration
- Test suite stability improvements

## [0.1.119] - 2025-05-07

**Added:**

- RAG plan v4 implementation
- Improved Mermaid diagram documentation
- Enhanced thinking tools for cognitive architecture

## [0.1.116] - 2025-05-06

**Fixed:**

- Improved verbosity flag handling in CLI
- Fixed command-line interface documentation

## [0.1.115] - 2025-05-05

**Added:**

- Enhanced working memory modules with sequential thinking integration
- Improved context management for thinking tools

## [0.1.114] - 2025-05-05

**Added:**

- Updated Chroma to version 1.x
- Enhanced working memory capabilities
- Automated chat logging feature with rich context
- RAG chat history analysis tools
- Second brain concept documentation
- Improved CLI verbosity controls

**Fixed:**

- Release script for PyPI publishing
- CLI log level consistency with environment variables
- Post-commit path warnings

## [0.1.113] - 2025-05-04

**Added:**

- Improved auto-chat logging feature with bidirectional linking
- Entity extraction and linking for related concepts

## [0.1.112] - 2025-05-04

**Fixed:**

- Fixed CLI log level handling to respect environment variables
- Removed forced DEBUG level in indexing module

## [0.1.111] - 2025-05-03

**Added:**

- Enhanced thinking tools for sequential reasoning
- Fixed MCP CLI integration with new tools

## [0.1.109] - 2025-05-02

**Fixed:**

- Improved test coverage to meet 80% target
- Fixed post-commit hook reliability

## [0.1.106] - 2025-05-01

**Added:**

- Improved thinking tools support with better embedding models
- Enhanced sequential thinking architecture

## [0.1.105] - 2025-04-30

**Added:**

- Client library for Chroma interactions with improved testing
- Fixed test suite for Python 3.12 compatibility

## [0.1.102] - 2025-04-24

**Added:**

- Support for Smithery integration and local execution
- Updated RAG implementation plan for better performance

## [0.1.101] - 2025-04-23

**Added:**

- Prepared local RAG implementation for embedding support
- Improved documentation with architectural diagrams

## [0.1.100] - 2025-04-22

**Added:**

- Added Windsurf rules support for AI assistants
- Refactored AI rules for better maintainability

## [0.1.99] - 2025-04-18

**Added:**

- Updated ChromaDB to version 1.x compatibility
- Adjusted code and tests for new API structure

## [0.1.98] - 2025-04-14

**Added:**

- Improved similar thoughts workflow
- Fixed embedding issues in thinking tools
- Added support for external embedding APIs

## [0.1.84] - 2025-04-13

**Fixed:**

- Removed Optional[T] from tool arguments for compatibility
- Improved refactoring plan with clearer architecture

## [0.1.82] - 2025-04-12

**Fixed:**

- Increased test coverage and stability
- Refactored types to avoid MCP client compatibility issues

## [0.1.65] - 2025-04-11

**Added:**

- Enhanced debug logging for tool requests
- Fixed peek_collection functionality

## [0.1.64] - 2025-04-11

**Changed:**

- Major refactoring for better compatibility with Cursor and GitHub CoPilot
- Fixed failing tools and improved error handling

## [0.1.60] - 2025-04-09

**Fixed:**

- Fixed collection creation and metadata handling
- Added proper docstrings for all functions

## [0.1.54] - 2025-04-09

**Changed:**

- Refactored MCP to align to SDK standards
- Improved metadata method handling and return values

## [0.1.45] - 2025-04-08

**Fixed:**

- Fixed GitHub Actions workflow for testing
- Added XML export for code coverage reporting

## [0.1.44] - 2025-04-07

**Added:**

- Improved test coverage to 78%
- Fixed MCP handling for stdio communications

## [0.1.43] - 2025-04-06

**Changed:**

- Cleaned up duplicate handlers
- Improved scripts and documentation
- Simplified README format
- Fixed tools to avoid Optional/Union types

## [0.1.40] - 2025-04-05

**Fixed:**

- Fixed release script for PyPI publishing
- Improved build process for testing with test.pypi.org

## [0.1.37] - 2025-04-04

**Fixed:**

- Fixed coverage reporting for sub-folder tests
- Added --clean parameter for test script

## [0.1.36] - 2025-04-01

**Changed:**

- Refactored build, test and publish process
- Enhanced Hatch usage for consistent builds

## [0.1.31] - 2025-03-31

**Added:**

- Refactored for PyPI publishing using Hatch build system
- Improved documentation for installation

## [0.1.30] - 2025-03-30

**Added:**

- Package build preparation
- Simplified installation with uv(x)

## [0.1.25] - 2025-03-29

**Fixed:**

- Updated email addresses and documentation
- Improved README with correct test run badge

## [0.1.17] - 2025-03-29

**Added:**

- Enhanced collection management tools
- Improved documentation structure

## [0.1.15] - 2025-03-29

**Added:**

- Document query capabilities
- Improved test coverage

## [0.1.13] - 2025-03-29

**Added:**

- Enhanced sequential thinking tools
- Better error handling

## [0.1.12] - 2025-03-29

**Added:**

- Improved collection management
- Better testing infrastructure

## [0.1.4] - 2025-03-29

**Added:**

- Basic testing structure
- Improved documentation

## [0.1.3] - 2025-04-30

**Added:**

- Client library for Chroma interactions
- Thinking tools for sequential reasoning
- First stable release with complete test suite
- Basic client commands for ChromaDB operations
- Development and usage documentation

**Changed:**

- Improved MCP tool structure
- Enhanced error handling and reporting
- Better test coverage

## [0.0.1] - 2025-03-29

**Added:**

- Initial release of Chroma MCP Server
- Collection management tools
- Document operation tools
- Sequential thinking tools
- Comprehensive test suite
- Documentation
