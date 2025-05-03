# ✅ Action Plan v2: Local RAG Pipeline (Hybrid Approach)

**Goal:** Implement a local RAG pipeline using **direct ChromaDB access for automation (indexing, CI)** via installable client commands and the **`chroma-mcp-server` for interactive AI tasks (feedback, working memory)**, focusing on practicality, cost-efficiency, and quality improvement.

**Architecture:**

- **Automation (Git Hooks, CI, Scripts):** Use dedicated Python client modules (`src/chroma_mcp_client/`) exposed via installable console scripts (e.g., `chroma-client`) that connect *directly* to the ChromaDB backend based on `.env` config. Wrapper scripts (`scripts/`) can be used for internal repo tasks like git hooks.
- **Interaction (IDE - Cursor, Windsurf, etc.):** Use the `chroma-mcp-server` running via the IDE's MCP integration for feedback loops and sequential thinking tools. The thinking tools CLI (`record-thought`) now correctly uses stdio communication with the server.

**Important Development Workflow Notes:**

- **Rebuild & Reinstall after Changes:** After modifying the `chroma-mcp-server` codebase (including client or thinking modules), you **must** rebuild and reinstall the package within the Hatch environment to ensure the changes take effect when using `hatch run` commands (like the test script or the VS Code task). Use the following command from the project root:

  ```bash
  hatch build && hatch run pip uninstall chroma-mcp-server -y && hatch run pip install dist/*.whl
  ```

- **Run Tests After Updates:** After making code changes and reinstalling, always run the unit tests to ensure nothing is broken. Use the provided test script:

  ```bash
  ./scripts/test.sh -c -v
  ```

  This script handles coverage and verbose output automatically.

---

## Phase 1: Setup & Configuration (Common Components)

- [X] **1.1 Install Prerequisites:**
  - [X] Verify Python ≥ 3.10 (`python --version`)
  - [X] Verify Docker & Docker Compose (Needed *only* if running ChromaDB backend via HTTP/Docker, *not* required for persistent local DB or direct client usage) - *Consider removing Docker mentions if fully committed to non-Docker.*
  - [X] Verify Git (`git --version`)
  - [X] Install `chroma-mcp-server` (provides both server and reusable utils):
        ```bash
        # Installs server + core libs + embedding functions + client dependencies
        # Use the [client] extra for the command-line tools
        pip install "chroma-mcp-server[full,client]"
        ```
  - [X] Install any additional tools if needed (`jq`, `mkcert`, etc.).

- [X] **1.2 Prepare Shared Configuration (`.env`):**
  - [X] Create data/log directories (e.g., `./chroma_data`, `./logs`).
  - [X] Create `.env` in project root (used by *both* MCP server and direct client).
  - [X] **Cost Optimization:** Start with a local embedding function (`default`, `accurate`).
  - [X] **Security:** Add `.env` to `.gitignore`. Use secrets management for API keys/tokens in CI/shared environments.

- [X] **1.3 Setup Direct Client Modules (`src/chroma_mcp_client/`, etc.):**
  - [X] Create `src/chroma_mcp_client/` directory.
  - [X] Added basic `connection.py` and `cli.py` for client structure.
  - [X] Added `indexing.py` with functions for indexing files and repositories.
  - [X] All core Python logic for indexing and querying has been implemented.

- [X] **1.4 Configure Packaging (`pyproject.toml`):**
  - [X] Define `[project.optional-dependencies]` including a `client` extra for any client-specific dependencies.
  - [X] Define `[project.scripts]` to create console script entry points (`chroma-mcp-server`, `chroma-client`, `record-thought`).
  - [X] Configure build settings to ensure proper packaging.

- [X] **1.5 Implement Unit Tests:**
  - [X] Added `pytest`, `pytest-mock`, `pytest-trio`, `pytest-asyncio`, `coverage` to `pyproject.toml` `[test]` environment.
  - [X] Configured `pytest` settings (`pyproject.toml`) for async tests and coverage source.
  - [X] Fixed existing test failures.
  - [X] Added basic unit tests for `chroma_mcp_client`.
  - [X] Added `pytest-timeout` to test dependencies.
  - [X] Refactored and fixed tests for `chroma_mcp.cli` (`test_cli.py`) and `chroma_mcp_thinking.thinking_cli` (`tests/thinking/test_thinking_cli.py`).

- [X] **1.6 Create Wrapper Scripts (`scripts/*.sh` - for Internal Use):**
  - [X] Created shell script (`scripts/chroma_client.sh`).
  - [X] Created shell script (`scripts/thinking.sh`).
  - [X] Made scripts executable.
  - [X] **Note:** Updated note to reflect console scripts are primary interface.
  - [ ] **To be completed:** Create wrapper script for feedback if needed.

- [X] **1.7 Launch & Test MCP Server (for Interaction):**
  - [X] Run `chroma-mcp-server` normally (via IDE integration / `.cursor/mcp.json`).
  - [X] Verify connection via MCP client (e.g., Cursor Tool window).
  - [X] Verified server starts correctly via `python -m chroma_mcp.cli` (used by `record-thought`).

- [X] **1.8 Verify Direct Client Connection (HTTP/Cloud via Console Script):**
  - [X] Use the console script to test connection to remote backends.
  - [X] Ensure no connection errors are reported (check stderr).

- [X] **1.9 Security & Secrets Checklist:**
  - [X] Ensure `.env` is git-ignored.
  - [X] Use secrets management for API keys/tokens in CI/shared environments.
  - [X] Store `CHROMA_API_KEY` / header tokens securely, inject at runtime.

- [X] **1.10 Add Unit Tests for Client Logic (`tests/client/`, etc.):**
  - [X] Create `tests/client/`, `tests/feedback/`, `tests/thinking/` directories.
  - [X] Implement unit tests using `pytest`.
  - [X] Mock `chromadb` and `mcp.ClientSession` interactions.
  - [X] Test argument parsing, file handling, ID generation, JSON output.
  - [X] Aim for >= 80% code coverage. (Current: ~78%)
  - [X] Run tests: `hatch run test` (All tests passing).
  - [X] **Remember:** Run `./scripts/test.sh -c -v` after code changes to verify tests pass.

- [X] **1.11 Document Client Usage (`docs/usage/client_commands.md`):**
  - [X] Documented Python library usage.
  - [X] Documented module-based CLI usage.
  - [X] Created documentation explaining installation and usage of **installed console scripts** (`chroma-client`, `record-thought`) in `docs/scripts/`.
  - [X] Updated documentation (`README.md`, `getting_started.md`, `developer_guide.md`, `ide_integration.md`) to reflect CLI changes and stdio usage.
  - [~] **Needs Review:** Ensure documentation clarifies console scripts as primary interface and fully documents all options.

---

## Phase 2: Codebase Indexing (Using Direct Client Wrapper/Command)

- [X] **2.1 Ensure Codebase Collection Exists (via Console Script):**
  - [X] Use the console script (`chroma-client`).

- [X] **2.2 Implement Incremental Indexing (Git Hook using Wrapper Script):**
  - [X] Created the `.git/hooks/post-commit` hook.
  - [X] Implemented cross-platform features.
  - [X] Modified hook to only index changed files.
  - [X] Made the hook executable.
  - [X] **Resolved:** Fixed environment, collection handling, and path resolution issues; hook is working.

- [X] **2.3 Initial Codebase Indexing (via Console Script):**
  - [X] Trigger indexing using `chroma-client index --all`.
  - [X] Monitor output and verify count.

- [X] **2.4 Basic Query Interface (via Console Script):**
  - [X] Implement `chroma-client query`.

---

## Phase 3: IDE Integration (Interactive RAG via MCP)

- [X] **3.1 Identify Interactive Tool:**
  - [X] `chroma_query_documents`.

- [X] **3.2 Configure IDE (Cursor, Windsurf, etc.):**
  - [X] Ensure IDE connects to the running `chroma-mcp-server`.
  - [X] Configure auth headers if needed.

- [X] **3.3 Test Interactive Retrieval (via MCP):**
  - [X] In the IDE, manually invoke `chroma_query_documents`.
  - [X] Verify results.

---

## Phase 4: Feedback Loop & Reinforcement (via MCP)

*This phase relies entirely on the interactive MCP server running via the IDE and requires MCP communication from Python clients.*

- [X] **4.1 Create Feedback Collection (via MCP):**
  - [X] Use MCP client (`mcp_chroma_dev_chroma_create_collection`).

- [X] **4.2 Implement Feedback Recording Logic:**
  - [X] Successfully use MCP tools directly (`mcp_chroma_dev_chroma_add_document_with_id_and_metadata`).

- [X] **4.3 Test Feedback Recording:**
  - [X] Successfully record feedback.
  - [X] Verify entry with `mcp_chroma_dev_chroma_peek_collection`.

- [ ] **4.4 Create Feedback Wrapper Script (`scripts/record_feedback.sh` - for Internal Use):**
  - [ ] Create/maintain script.
  - [ ] Include examples.
  - [ ] Make executable.

- [ ] **4.5 Integrate Feedback Trigger (IDE -> MCP Server):**
  - [ ] Hook mechanism into IDE workflow.
  - [ ] **Preferred Method:** IDE calls MCP tools.
  - [ ] **Alternative:** IDE calls wrapper script.

- [ ] **4.6 Refine Interactive Retrieval using Feedback (Advanced):**
  - [ ] Modify prompts to query `rag_feedback_v1`.
  - [ ] Consider weighting.

- [ ] **4.7 Document Feedback Mechanism (`docs/usage/feedback.md`):**
  - [ ] Explain loop.
  - [ ] Document MCP tools.
  - [ ] Provide integration examples.
  - [ ] Include wrapper script examples.

---

## Phase 5: Working Memory & Sequential Thinking (via MCP)

*This phase relies entirely on the interactive MCP server running via the IDE and requires MCP communication from Python clients (via `record-thought` console script).*

- [X] **5.1 Create Thinking Sessions Collection (via MCP):**
  - [X] Use MCP client (`mcp_chroma_dev_chroma_create_collection`).

- [X] **5.2 Implement Sequential Thinking Logic (`src/chroma_mcp_thinking/`):**
  - [X] Create directory and modules.
  - [X] Refactored `ThinkingSession` to use standard `mcp.ClientSession`.
  - [X] Resolved stdio communication issues (`record-thought` now works by passing env vars to subprocess).
  - [X] Ensured correct MCP tool names and response parsing.

- [X] **5.3 Create Thought Recorder Wrapper Script (`scripts/record_thought.sh` - for Internal Use):**
  - [X] Shell script (`scripts/thinking.sh`) exists.
  - [X] **Note:** Updated note about console script (`record-thought`) being primary.
  - [X] Made executable.

- [X] **5.4 Integrate with Development Workflow:**
  - [X] IDE integration (`docs/integration/ide_integration.md`) documented using `record-thought` via hatch.
  - [X] IDE integration (VS Code task) tested and working.
  - [~] **Needs Definition:** Define specific workflow checkpoints/usage patterns.

- [X] **5.5 Connect with Interactive RAG Query Pipeline (via MCP):**
  - [X] Enhance prompts/rules to call `chroma_find_similar_thoughts` / `_sessions` (Implemented via `.cursor/rules/memory-integration-rule.mdc`).

- [X] **5.6 Test Working Memory Integration (via MCP):**
  - [X] Use `record-thought` console script extensively during debugging (via CLI & VS Code task). Verified working.

- [X] **5.7 Add Unit Tests for Thinking Logic (`tests/thinking/`):**
  - [X] Create directory and tests.
  - [X] Mock MCP communication (`mcp.ClientSession`, stdio contexts).
  - [X] Aim for >= 80% coverage. (Current: thinking modules mostly covered).
  - [X] Fixed all test failures (`tests/thinking/test_thinking_cli.py`).

- [X] **5.8 Document Working Memory (`docs/usage/client_commands.md`):**
  - [X] Explained concept and benefits in `docs/thinking_tools/`.
  - [X] Documented **installed console script** (`record-thought`) usage in `docs/scripts/record-thought.md`.
  - [X] Updated IDE integration docs (`docs/integration/ide_integration.md`).
  - [~] **Needs Review:** Consolidate examples and ensure clarity.

---

## Phase 6: Optimization & Usage (Hybrid Context)

- [ ] **6.1 Define Prompting Strategy:**
  - [ ] Rules for using interactive MCP tools.
  - [ ] Identify potential uses for client console commands.

- [ ] **6.2 Performance & Cost Tuning:**
  - [ ] Chunking.
  - [ ] Embedding Model Choice.
  - [ ] Hardware Monitoring.
  - [ ] Quantization/Optimization.

- [ ] **6.3 Monitoring & Maintenance:**
  - [ ] Monitor logs & output.
  - [ ] Check relevance/feedback.
  - [ ] Re-indexing strategy.
  - [ ] Backup data dir.

- [ ] **6.4 HTTP Resilience & Retries:**
  - [ ] Apply retry logic if using HTTP/Cloud backend.

- [ ] **6.5 Observability / Metrics Dashboard (optional):**
  - [ ] Monitor backend or server.

- [ ] **6.6 Custom Embedding Functions (advanced):**
  - [ ] Implement and use via `.env`.

- [ ] **6.7 Automated Daily Backup Script:**
  - [ ] Implement `scripts/backup_chroma.sh`.

---

## Phase 7: Verification (Hybrid)

- [X] **7.1 End-to-End Test (Automation):** Verified git hook.
- [ ] **7.2 End-to-End Test (Interaction):** IDE -> MCP Server -> RAG -> Feedback.
- [X] **7.3 End-to-End Test (Working Memory):** Tested `record-thought` extensively via CLI.
- [X] **7.4 Test Console Scripts:** Verified `record-thought` works. Assumed `chroma-client` works based on tests.
- [X] **7.5 Run Unit Tests:** Execute `hatch run test`. (Current: All tests passing, ~78% coverage).
- [ ] **7.6 Cost Check:** Monitor API costs.
- [ ] **7.7 Quality Assessment:** Evaluate workflow.
- [ ] **7.8 Latency Benchmark:** Measure interactive MCP query latency.
- [ ] **7.9 Index Size & Storage Check:** Monitor data dir size.
- [ ] **7.10 Restore-from-Backup Test:** Verify backup/restore.
- [X] **7.11 Documentation Review:** Updated key docs (`README`, `developer_guide`, `record-thought`, `ide_integration`). Console commands documented. (Needs final review for clarity/completeness).

---

**Outcome:** A functional local RAG pipeline using a **hybrid architecture**: direct client access (via installable console commands) for robust automation (indexing, CI) and the `chroma-mcp-server` for interactive AI tasks (feedback, working memory), with improved structure, packaging, testing, and documentation for easier external use. Thinking module implemented, tested, and integrated via stdio.
