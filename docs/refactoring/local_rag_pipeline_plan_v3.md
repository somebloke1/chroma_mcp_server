# ✅ Action Plan v3: Local RAG Pipeline (Implicit Learning via Chat History)

**Goal:** Implement a local RAG pipeline using **direct ChromaDB access for automation (indexing, CI)** via installable client commands and the **`chroma-mcp-server` for interactive AI tasks (working memory, automated chat logging)**, focusing on deriving implicit learning by correlating summarized chat interactions with code changes.

**Architecture:**

- **Automation (Git Hooks, CI, Scripts):** Use dedicated Python client modules (`src/chroma_mcp_client/`) exposed via installable console scripts (e.g., `chroma-client`) that connect *directly* to the ChromaDB backend based on `.env` config. Wrapper scripts (`scripts/`) can be used for internal repo tasks like git hooks.
- **Interaction (IDE - Cursor, Windsurf, etc.):** Use the `chroma-mcp-server` running via the IDE's MCP integration. The server facilitates working memory tools and, critically, enables the AI assistant to **automatically log summarized prompt/response pairs** to a dedicated `chat_history` collection via MCP calls.
- **Learning Extraction:** A separate analysis process correlates the summarized interactions in `chat_history` with actual code changes found in `codebase_v1` (or Git history) to identify implemented suggestions and extract validated learnings.

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
  - [ ] **Removed:** No longer need a feedback wrapper script.

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

## Phase 4: Implicit Learning via Chat History Analysis (via MCP & Analysis Script)

*This phase replaces explicit feedback with automated capture and analysis.*

- [~] **4.1 Define Chat History Collection (e.g., `chat_history_v1`):**
  - [X] Use MCP client (`mcp_chroma_dev_chroma_create_collection`) to create it.
  - [ ] Define required metadata structure (when adding documents to the collection):
    - `session_id`: Identifier for the interaction session.
    - `timestamp`: ISO 8601 timestamp of the interaction.
    - `prompt_summary`: Concise summary of the user's request (the "Why").
    - `response_summary`: Concise summary of the AI's response/suggestion (the "How").
    - `involved_entities`: List of key files, functions, concepts mentioned (the "What").
    - `status`: e.g., `captured`, `analyzed`, `learning_extracted`.
    - (Optional) `raw_prompt_hash`, `raw_response_hash`: Hashes for linking to potential raw logs.

- [~] **4.2 Implement Automated Chat Capture & Summarization:**
  - [X] **Mechanism:** Define an IDE rule (e.g., `.cursor/rules/auto_log_chat.mdc` and copy in `docs/rules/auto_log_chat.md` for other IDEs) instructing the AI assistant to:
    1. After generating a response, summarize the preceding prompt and the generated response, focusing on the "Why, How, What".
    2. Call an MCP tool (e.g., `mcp_chroma_dev_chroma_add_document_with_metadata`) to store these summaries and associated metadata in the `chat_history_v1` collection.
    - [X] Ensure the `.cursor/rules/auto_log_chat.mdc` file starts with the following enclosed lines within the markdown block before the rule definition:

        ```markdown
        ---
        description: This rule helps to log chat history to the `chat_history_v1` collection
        globs:
        alwaysApply: true
        ---
        ```

    See [Automated Chat History Logging](docs/integration/automated_chat_logging.md) for details on setting up this rule.

  - [X] **Feasibility Confirmed:** ~~Investigate the reliability of enforcing such actions via IDE rules. Develop fallback or complementary mechanisms if needed.~~ **Confirmed:** Initial tests show the mechanism of using an IDE rule to trigger automated logging via MCP calls is feasible. **Note:** Continued monitoring for reliability across diverse interactions is recommended, as rule refinements were needed during initial testing.

- [ ] **4.3 Develop Analysis Engine (e.g., `scripts/analyze_chat_history.py`):**
  - [ ] Create a script or tool that:
    1. Fetches recent entries from `chat_history_v1` (e.g., status=`captured`).
    2. For each entry, identifies the `involved_entities` (files).
    3. Retrieves corresponding file versions/diffs from `codebase_v1` or Git history occurring *after* the chat timestamp.
    4. Compares the `response_summary` (How) with the actual code changes (What) to determine if the suggestion was implemented (correlation).
    5. Updates the status of analyzed chat entries (e.g., to `analyzed`).

- [ ] **4.4 Define Learning Extraction and Storage:**
  - [ ] **Extraction:** Based on correlated entries, extract structured learnings (e.g., "Applying pattern X to file Y solved problem Z described in prompt P").
  - [ ] **Storage:** Store these validated learnings in a dedicated collection (e.g., `derived_learnings_v1`) or enrich an existing one like `dev_learnings`. Define the schema for these learning entries.
  - [ ] Update the status of chat entries where learnings were extracted (e.g., to `learning_extracted`).

- [ ] **4.5 Integrate Analysis into Workflow:**
  - [ ] Determine trigger mechanism: Manual execution of the analysis script, scheduled job (e.g., nightly), or a Git hook (e.g., post-merge on the main branch). Start with manual execution.

- [ ] **4.6 Refine Interactive Retrieval using Derived Learnings:**
  - [ ] Modify prompts/rules for interactive RAG (`chroma_query_documents`) to also query the `derived_learnings_v1` collection, potentially giving higher weight to these validated insights.

- [ ] **4.7 Document Implicit Learning Mechanism (`docs/usage/implicit_learning.md`):**
  - [ ] Explain the automated capture, summarization, analysis, and learning extraction process.
  - [ ] Document the `chat_history_v1` and `derived_learnings_v1` schemas.
  - [ ] Provide examples of how to run the analysis script.
  - [ ] Explain how derived learnings improve future RAG results.

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
  - [ ] Rules for using interactive MCP tools (RAG, memory).
  - [ ] Define how derived learnings (Phase 4) influence prompts.
  - [ ] Identify potential uses for client console commands beyond indexing.

- [ ] **6.2 Performance & Cost Tuning:**
  - [ ] Chunking strategy for `codebase_v1`.
  - [ ] Embedding Model Choice (consider cost vs. accuracy for indexing, chat history, learnings).
  - [ ] Hardware Monitoring.
  - [ ] Quantization/Optimization.
  - [ ] Manage size of `chat_history_v1` and `codebase_v1`.

- [ ] **6.3 Monitoring & Maintenance:**
  - [ ] Monitor logs & output (server, client, analysis script).
  - [ ] Check relevance/quality of derived learnings.
  - [ ] Re-indexing strategy for `codebase_v1`.
  - [ ] Backup strategy for all Chroma data directories (`codebase_v1`, `chat_history_v1`, `derived_learnings_v1`, etc.).

- [ ] **6.4 HTTP Resilience & Retries:**
  - [ ] Apply retry logic if using HTTP/Cloud backend for *any* collection.

- [ ] **6.5 Observability / Metrics Dashboard (optional):**
  - [ ] Monitor backend or server performance, collection sizes, analysis script runs.

- [ ] **6.6 Custom Embedding Functions (advanced):**
  - [ ] Implement and use via `.env`.

- [ ] **6.7 Automated Daily Backup Script:**
  - [ ] Implement `scripts/backup_chroma.sh` to back up *all* relevant data directories.

---

## Phase 7: Verification (Hybrid)

- [X] **7.1 End-to-End Test (Automation):** Verified git hook for `codebase_v1` indexing.
- [ ] **7.2 End-to-End Test (Interaction & Logging):** IDE -> MCP Server -> RAG -> AI generates response -> AI summarizes & logs to `chat_history_v1`.
- [X] **7.3 End-to-End Test (Working Memory):** Tested `record-thought` extensively via CLI.
- [ ] **7.4 Test Analysis Engine:** Execute the analysis script and verify correlation & learning extraction.
- [X] **7.5 Test Console Scripts:** Verified `record-thought` works. Assumed `chroma-client` works based on tests.
- [X] **7.6 Run Unit Tests:** Execute `hatch run test`. (Current: All tests passing, ~78% coverage).
- [ ] **7.7 Cost Check:** Monitor API costs (embedding, potential AI summarization).
- [ ] **7.8 Quality Assessment:** Evaluate quality/usefulness of derived learnings.
- [ ] **7.9 Latency Benchmark:** Measure interactive MCP query latency, including potential overhead from auto-logging.
- [ ] **7.10 Index Size & Storage Check:** Monitor data dir sizes, especially `chat_history_v1`.
- [ ] **7.11 Restore-from-Backup Test:** Verify backup/restore for all relevant collections.
- [~] **7.12 Documentation Review:** Review all updated docs (`README`, `developer_guide`, `record-thought`, `ide_integration`, `implicit_learning.md`). Ensure clarity and completeness.

---

**Outcome:** A functional local RAG pipeline using a **hybrid architecture**: direct client access (via installable console commands) for robust automation (indexing), and the `chroma-mcp-server` for interactive AI tasks (working memory) and **automated capture of summarized chat interactions**. An analysis engine correlates chat history with code changes to **implicitly derive validated learnings**, improving the system over time without requiring explicit user feedback.
