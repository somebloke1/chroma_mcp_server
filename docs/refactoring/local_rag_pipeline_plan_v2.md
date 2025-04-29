# ✅ Action Plan v2: Local RAG Pipeline (Hybrid Approach)

**Goal:** Implement a local RAG pipeline using **direct ChromaDB access for automation (indexing, CI)** via installable client commands and the **`chroma-mcp-server` for interactive AI tasks (feedback, working memory)**, focusing on practicality, cost-efficiency, and quality improvement.

**Architecture:**

- **Automation (Git Hooks, CI, Scripts):** Use dedicated Python client modules (`src/chroma_mcp_client/`) exposed via installable console scripts (e.g., `chroma-client`) that connect *directly* to the ChromaDB backend based on `.env` config. Wrapper scripts (`scripts/`) can be used for internal repo tasks like git hooks.
- **Interaction (IDE - Cursor, Windsurf, etc.):** Use the `chroma-mcp-server` running via the IDE's MCP integration for feedback loops and sequential thinking tools.

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
  - [X] Create `.env` in project root (used by *both* MCP server and direct client):
        ```dotenv
        # .env - Configuration for ChromaDB Backend
        CHROMA_CLIENT_TYPE=persistent # persistent | http | cloud
        CHROMA_DATA_DIR=./chroma_data # Path for persistent client
        CHROMA_LOG_DIR=./logs
        LOG_LEVEL=INFO

        # --- HTTP Client Settings (only if CHROMA_CLIENT_TYPE=http) ---
        CHROMA_HOST=localhost
        CHROMA_PORT=8000
        CHROMA_SSL=false
        # CHROMA_HEADERS='{"Authorization":"Bearer <token>"}' # For HTTP auth
        
        # --- Cloud Client Settings (only if CHROMA_CLIENT_TYPE=cloud) ---
        # CHROMA_HOST=api.trychroma.com # Usually default
        CHROMA_TENANT=<your-tenant>
        CHROMA_DATABASE=<your-database>
        CHROMA_API_KEY=<your-api-key>
        
        # --- Embedding Function (Used by Direct Client & MCP Server) ---
        CHROMA_EMBEDDING_FUNCTION=default # e.g., default, accurate, openai...
        # Ensure necessary API keys (OPENAI_API_KEY, etc.) are set if using API EFs
        ```
  - [X] **Cost Optimization:** Start with a local embedding function (`default`, `accurate`).
  - [X] **Security:** Add `.env` to `.gitignore`. Use secrets management for API keys/tokens in CI/shared environments.

- [X] **1.3 Setup Direct Client Modules (`src/chroma_mcp_client/`, etc.):**
  - [X] Create `src/chroma_mcp_client/` directory.
  - [X] Added basic `connection.py` and `cli.py` for client structure.
  - [X] Added `indexing.py` with functions for indexing files and repositories.
  - [X] All core Python logic for indexing and querying has been implemented.

- [X] **1.4 Configure Packaging (`pyproject.toml`):**
  - [X] Define `[project.optional-dependencies]` including a `client` extra for any client-specific dependencies.
  - [X] Define `[project.scripts]` to create console script entry points for the client tools.
  - [X] Configure build settings to ensure proper packaging.

- [X] **1.5 Implement Unit Tests:**
  - [X] Added `pytest`, `pytest-mock`, `pytest-trio`, `pytest-asyncio`, `coverage` to `pyproject.toml` `[test]` environment.
  - [X] Configured `pytest` settings (`pyproject.toml`) for async tests and coverage source.
  - [X] Fixed existing test failures (e.g., API key instantiation test).
  - [X] Added basic unit tests for `chroma_mcp_client` (`test_cli.py`, `test_connection.py`).
  - [X] Refactored `tests/chroma_mcp_client/test_cli.py` to use consistent mocking via `argparse` and `get_client_and_ef` mocks, resolving previous errors.
  - [X] Added `pytest-timeout` to test dependencies.

- [~] **1.6 Create Wrapper Scripts (`scripts/*.sh` - for Internal Use):**
  - [X] Created shell script (`scripts/chroma_client.sh`) that invokes the Python client CLI module (e.g., `python -m chroma_mcp_client.cli ...`).
  - [X] Made script executable.
  - [X] **Note:** These wrappers are primarily for convenience *within this repository* (e.g., git hooks) and are *not* the primary public interface for external users (who should use the console scripts like `chroma-client`).
  - [ ] **To be completed:** Create similar wrapper scripts for feedback and thinking if needed.

- [X] **1.7 Launch & Test MCP Server (for Interaction):**
  - [X] Run `chroma-mcp-server` normally (via IDE integration / `.cursor/mcp.json`).
  - [X] Verify connection via MCP client (e.g., Cursor Tool window).

- [X] **1.8 Verify Direct Client Connection (HTTP/Cloud via Console Script):**
  - [X] Use the console script to test connection to remote backends.
  - [X] Ensure no connection errors are reported (check stderr).

- [X] **1.9 Security & Secrets Checklist:**
  - [X] Ensure `.env` is git-ignored (`echo ".env" >> .gitignore`).
  - [X] Use secrets management for API keys/tokens in CI/shared environments.
  - [X] Store `CHROMA_API_KEY` / header tokens securely, inject at runtime.

- [X] **1.10 Add Unit Tests for Client Logic (`tests/client/`, etc.):**
  - [X] Create `tests/client/`, `tests/feedback/`, `tests/thinking/` directories.
  - [X] Implement unit tests using `pytest` for `src/chroma_mcp_client/`, `src/chroma_mcp_feedback/`, `src/chroma_mcp_thinking/` modules.
  - [X] Mock `chromadb` interactions to isolate client logic.
  - [X] Mock MCP client interactions (`mcp.ClientSession`) for thinking tests.
  - [X] Test argument parsing, file handling, ID generation, JSON output.
  - [X] Aim for >= 80% code coverage. (Current: ~78%, thinking modules covered)
  - [X] Run tests: `hatch run test` (Passing)

- [ ] **1.11 Document Client Usage (`docs/usage/client_commands.md`):**
  - [ ] Create/update documentation explaining how to install (`pip install chroma-mcp-server[client]`) and use the `chroma-client`, `record-feedback`, `record-thought` console commands.
  - [ ] Document commands, options, and configuration via `.env`.
  - [ ] Clarify that these console scripts are the primary public interface.

---

## Phase 2: Codebase Indexing (Using Direct Client Wrapper/Command)

- [X] **2.1 Ensure Codebase Collection Exists (via Console Script):**
  - [X] Use the console script (implicitly handles via `get_or_create_collection`):

        ```bash
        # Running index via console script ensures collection exists
        chroma-client index README.md --repo-root .
        # Or verify count
        chroma-client count codebase_v1
        ```

- [~] **2.2 Implement Incremental Indexing (Git Hook using Wrapper Script):**
  - [X] Created the `.git/hooks/post-commit` hook to use the internal wrapper script (`scripts/chroma_client.sh`).
  - [X] Implemented cross-platform features (MD5 calculation, portable locking mechanism)
  - [X] Made the hook executable.
  - [ ] **Issue:** Post-commit hook currently encounters an error with collection handling in ChromaDB.
        ```bash
        # Error: argument 'name': 'Collection' object cannot be converted to 'PyString'
        ```
  - [ ] **Next steps:** Fix the implementation incompatibility between CLI and the indexing modules or provide manual indexing instructions.

- [X] **2.3 Initial Codebase Indexing (via Console Script):**
  - [X] Trigger indexing for all relevant *tracked* files using the public console script:
        ```bash
        chroma-client index --all --repo-root .
        ```
  - [X] Monitor script stderr output.
  - [X] Verify collection count using the console script:
        ```bash
        chroma-client count codebase_v1
        ```

- [X] **2.4 Basic Query Interface (via Console Script):**
  - [X] Implement a basic query command in the public console script:
        ```bash
        chroma-client query "your natural language query" -n 5
        ```

---

## Phase 3: IDE Integration (Interactive RAG via MCP)

- [X] **3.1 Identify Interactive Tool:**
  - [X] The tool for *interactive* RAG is `chroma_query_documents` (from the running `chroma-mcp-server`).

- [X] **3.2 Configure IDE (Cursor, Windsurf, etc.):**
  - [X] Ensure the IDE connects to the running `chroma-mcp-server` (via `.cursor/mcp.json`, etc.).
  - [X] Configure auth headers (`CHROMA_HEADERS`) in IDE env if needed.

- [X] **3.3 Test Interactive Retrieval (via MCP):**
  - [X] In the IDE, manually invoke `chroma_query_documents`.
  - [X] Verify results.
  - [X] Compare with direct client console script query.

---

## Phase 4: Feedback Loop & Reinforcement (via MCP)

*This phase relies entirely on the interactive MCP server running via the IDE and requires MCP communication from Python clients.*

- [X] **4.1 Create Feedback Collection (via MCP):**
  - [X] Use MCP client:

        ```tool_code
        print(default_api.mcp_chroma_dev_chroma_create_collection(collection_name="rag_feedback_v1"))
        ```

- [X] **4.2 Implement Feedback Recording Logic:**
  - [X] Successfully use MCP tools directly instead of separate Python module:

        ```tool_code
        # Example: Using MCP tool to directly add feedback with ID and metadata
        print(default_api.mcp_chroma_dev_chroma_add_document_with_id_and_metadata(
            collection_name="rag_feedback_v1",
            document="code snippet here",
            id="feedback_uuid",
            metadata=json.dumps({
                "source_query": "query that produced the result",
                "source_file": "file path where result came from",
                "accepted": True,
                "timestamp": "2023-01-01T00:00:00Z"
            })
        ))
        ```

- [X] **4.3 Test Feedback Recording:**
  - [X] Successfully record feedback into `rag_feedback_v1` collection.
  - [X] Verify the entry was added with `mcp_chroma_dev_chroma_peek_collection`.

- [ ] **4.4 Create Feedback Wrapper Script (`scripts/record_feedback.sh` - for Internal Use):**
  - [ ] Create/maintain a shell script (`scripts/record_feedback.sh`) to invoke the MCP feedback tools directly.
  - [ ] Include examples for different use cases (accept/reject feedback).
  - [ ] Make executable.

- [ ] **4.5 Integrate Feedback Trigger (IDE -> MCP Server):**
  - [ ] Hook the feedback mechanism into the IDE workflow.
  - [ ] **Preferred Method:** IDE directly calls the MCP tools as demonstrated in 4.2.
  - [ ] **Alternative:** IDE calls the `scripts/record_feedback.sh` wrapper script.

- [ ] **4.6 Refine Interactive Retrieval using Feedback (Advanced):**
  - [ ] Modify interactive retrieval prompts (Phase 3) to query `rag_feedback_v1` via MCP server *before* or *alongside* `codebase_v1`.
  - [ ] Consider implementing a simple weighting system based on feedback acceptance ratio.

- [ ] **4.7 Document Feedback Mechanism (`docs/usage/feedback.md`):**
  - [ ] Explain how the feedback loop works.
  - [ ] Document the MCP tools used for feedback.
  - [ ] Provide examples of how to integrate feedback in different development workflows.
  - [ ] Include command-line examples using the wrapper script.

---

## Phase 5: Working Memory & Sequential Thinking (via MCP)

*This phase relies entirely on the interactive MCP server running via the IDE and requires MCP communication from Python clients.*

- [X] **5.1 Create Thinking Sessions Collection (via MCP):**
  - [X] Use MCP client:

        ```tool_code
        print(default_api.mcp_chroma_dev_chroma_create_collection(collection_name="thinking_sessions_v1"))
        ```
        
        Output:
        ```
        {
          "name": "thinking_sessions_v1",
          "id": "ab8a794e-ab4d-49e8-8fa4-4cf0baf88b28", 
          "metadata": {
            "settings": {
              "hnsw:search:ef": 10,
              "hnsw:num:threads": 4,
              "hnsw:M": 16,
              "hnsw:construction:ef": 100,
              "hnsw:space": "cosine"
            }
          },
          "count": 0
        }
        ```

- [X] **5.2 Implement Sequential Thinking Logic (`src/chroma_mcp_thinking/`):**
  - [X] Create `src/chroma_mcp_thinking/` directory.
  - [X] Develop Python modules (`thinking_session.py`, `utils.py`, `thinking_cli.py`) for managing thinking sessions via MCP.
  - [X] Refactored `ThinkingSession` to use standard `mcp.ClientSession` for MCP communication.

- [ ] **5.3 Create Thought Recorder Wrapper Script (`scripts/record_thought.sh` - for Internal Use):**
  - [ ] Create/maintain a shell script (`scripts/record_thought.sh`) to invoke the thinking session Python CLI module (`python -m chroma_mcp_thinking.cli ...`).
  - [ ] **Note:** Mainly for internal repo use. External users should use `record-thought` console command.
        ```bash
        #!/bin/bash
        # scripts/record_thought.sh - Internal wrapper
        # ... (setup as before) ...
        # Execute the Python CLI module
        "${PYTHON_EXECUTABLE:-python}" -m chroma_mcp_thinking.cli "$@"
        ```
  - [ ] Make executable.

- [ ] **5.4 Integrate with Development Workflow:**
  - [ ] Define checkpoints.
  - [ ] Create IDE shortcuts calling the `record-thought` console command or the `scripts/record_thought.sh` wrapper.

- [ ] **5.5 Connect with Interactive RAG Query Pipeline (via MCP):**
  - [ ] Enhance prompts to call `chroma_find_similar_thoughts` / `_sessions` via MCP server tools.

- [ ] **5.6 Test Working Memory Integration (via MCP):**
  - [ ] Use IDE integration (calling console command or wrapper script) to record/query thoughts.

- [X] **5.7 Add Unit Tests for Thinking Logic (`tests/thinking/`):**
  - [X] Create `tests/thinking/` directory.
  - [X] Test session management and parameter construction in `src/chroma_mcp_thinking/`.
  - [X] Mock MCP communication (`mcp.ClientSession`).
  - [X] Aim for >= 80% coverage. (Current: thinking session 93%, utils 100%, cli 69%)

- [ ] **5.8 Document Working Memory (`docs/usage/client_commands.md`):**
  - [ ] Explain the concept and benefits.
  - [ ] Document `record-thought` console command usage.
  - [ ] Provide examples of checkpoints and IDE integration (using console command preferably).

---

## Phase 6: Optimization & Usage (Hybrid Context)

- [ ] **6.1 Define Prompting Strategy:**
  - [ ] Rules for using *interactive* MCP tools (`query_documents`, `find_similar_thoughts`).
  - [ ] Identify potential uses for *client console commands* (`chroma-client`, etc.) in offline analysis or scripting.

- [ ] **6.2 Performance & Cost Tuning:**
  - [ ] Chunking (in `src/chroma_mcp_client/indexing.py`).
  - [ ] Embedding Model Choice (consistent via `.env`).
  - [ ] Hardware/Resource Monitoring.
  - [ ] Quantization/Optimization.

- [ ] **6.3 Monitoring & Maintenance:**
  - [ ] Monitor MCP server logs & client command (stderr) output.
  - [ ] Periodically check relevance/feedback.
  - [ ] Re-indexing strategy (via `chroma-client index --all`).
  - [ ] Backup `CHROMA_DATA_DIR`.

- [ ] **6.4 HTTP Resilience & Retries:**
  - [ ] Apply retry logic within Python client/feedback/thinking modules if using HTTP/Cloud backend.

- [ ] **6.5 Observability / Metrics Dashboard (optional):**
  - [ ] Monitor ChromaDB backend directly or MCP server if networked.

- [ ] **6.6 Custom Embedding Functions (advanced):**
  - [ ] Implement in `src/chroma_mcp_server/utils/embeddings.py` (or separate module), use via `.env`. Ensure direct client and server use the *same* implementation.

- [ ] **6.7 Automated Daily Backup Script:**
  - [ ] Implement `scripts/backup_chroma.sh` (remains unchanged, backs up data dir).

---

## Phase 7: Verification (Hybrid)

- [ ] **7.1 End-to-End Test (Automation):** Verify git hook -> `scripts/chroma_client.sh index` -> Python client -> indexing.
- [ ] **7.2 End-to-End Test (Interaction):** IDE -> MCP Server -> RAG -> Trigger `record-feedback` command -> Python feedback -> MCP Server -> Feedback Recorded.
- [ ] **7.3 End-to-End Test (Working Memory):** IDE -> Trigger `record-thought` command -> Python thinking -> MCP Server -> Record Thought -> Query Thought via MCP.
- [ ] **7.4 Test Console Scripts:** Verify `chroma-client`, `record-feedback`, `record-thought` commands work as expected after installation.
- [X] **7.5 Run Unit Tests:** Execute `hatch run test` and check coverage report. Verify >= 80%. (Current: ~78%, All tests passing)
- [ ] **7.6 Cost Check:** Monitor API costs.
- [ ] **7.7 Quality Assessment:** Evaluate workflow.
- [ ] **7.8 Latency Benchmark:** Measure interactive MCP query latency.
- [ ] **7.9 Index Size & Storage Check:** Monitor data dir size.
- [ ] **7.10 Restore-from-Backup Test:** Verify backup/restore.
- [ ] **7.11 Documentation Review:** Ensure console commands and overall workflow are clearly documented.

---

**Outcome:** A functional local RAG pipeline using a **hybrid architecture**: direct client access (via installable console commands) for robust automation (indexing, CI) and the `chroma-mcp-server` for interactive AI tasks (feedback, working memory), with improved structure, packaging, testing, and documentation for easier external use. Thinking module implemented and tested.
