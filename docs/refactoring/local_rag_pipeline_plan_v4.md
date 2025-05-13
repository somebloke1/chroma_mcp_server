# Action Plan v4: Evolvable Local RAG to Reinforcement Learning Pipeline

**Purpose:** Provide a seamless and forward-compatible plan to evolve from a simple local RAG setup (no fine-tuning) toward a full reinforcement learning + model fine-tuning (LoRA) workflow – without breaking ChromaDB collections or needing to reindex existing code or chat history. This plan allows individual developers or teams to start at any phase and progressively adopt more advanced features.

**Core Architecture (Consistent Across Phases):**

- **ChromaDB:** Vector database for storing code chunks, chat summaries, and derived learnings. Can be local (SQLite-backed) or a shared server instance.
- **Automation (Git Hooks, CI, Scripts):** Uses dedicated Python client modules (`src/chroma_mcp_client/`) exposed via installable console scripts (e.g., `chroma-client`) that connect *directly* to the ChromaDB backend based on `.env` configuration.
- **Interaction (IDE - Cursor, Windsurf, etc.):** Leverages the `chroma-mcp-server` running via IDE's MCP integration. The server facilitates working memory tools and automated logging of summarized prompt/response pairs to `chat_history_v1`.
- **Learning Extraction & Application:** Processes evolve from manual analysis to automated pipelines that identify valuable interactions, train models, and feed insights back into the RAG system.

**Important Development Workflow Notes (Applies to all phases):**

- **Rebuild & Reinstall after Changes:** After modifying the `chroma-mcp-server` codebase (including client or thinking modules), you **must** rebuild and reinstall the package within the Hatch environment:

  ```bash
  hatch build && hatch run pip uninstall chroma-mcp-server -y && hatch run pip install 'dist/chroma_mcp_server-<version>-py3-none-any.whl[full,dev]'
  ```

- **Run Tests After Updates:** Always run unit tests after code changes and reinstalling:

  ```bash
  ./scripts/test.sh -c -v
  ```

---

## Overview of Evolution Phases

| Phase | Description                                                           | Core Chroma Collections Used                                 | Key Requirements                                                                 | Compatible with Next Phase? |
| ----- | --------------------------------------------------------------------- | ------------------------------------------------------------ | -------------------------------------------------------------------------------- | --------------------------- |
| **1** | Local RAG-Only (Implicit Learning via Chat History)                   | `codebase_v1`, `chat_history_v1`, `derived_learnings_v1`     | ChromaDB (local/shared), IDE + Git + MCP Rules, `chroma-client` CLI              | ✅ Yes                       |
| **2** | RAG + LoRA Fine-Tuning (Manual/Optional)                              | (Same as Phase 1)                                            | Adds reward dataset export, manual LoRA adapter training, optional adapter use   | ✅ Yes                       |
| **3** | Full RL Pipeline: Nightly Analysis, Automated Training, LoRA Deployment | (Same as Phase 1, enriched metadata)                         | Adds scheduling, auto-promotion, CI/CD ops, potentially shared ChromaDB for team | ✅ Yes                       |

---

## Phase 1: Local RAG-Only (Implicit Learning & Enhanced Context Capture)

**Goal:** Establish a robust local RAG system with automated codebase indexing, rich contextual chat history logging, bi-directional linking between code and conversations, and a semi-automated mechanism for curating high-quality "derived learnings".

**Collections Used & Schema Definition:**

- `codebase_v1`: Indexed code chunks from the repository.
  - [X] Ensure schema includes `file_path`, `commit_sha`, `chunk_id`, timestamps, etc. (Partially from v3 [~] 4.1, expanded for v4, in particular for `chunk_id` and `commit_sha`)
  - [X] **Add new fields:** `related_chat_ids` (comma-separated list of `chat_history_v1` entry IDs that modified this code)
- `chat_history_v1`: Summarized AI prompt/response pairs with rich context.
  - [X] Create collection using MCP client (`#chroma_create_collection`).
  - [X] **Define and fully implement required metadata structure:** `session_id`, `timestamp`, `prompt_summary`, `response_summary`, `involved_entities`, `raw_prompt_hash`, `raw_response_hash`, and `status` (e.g., `captured`, `analyzed`, `promoted_to_learning`, `exported_for_reward`, `rewarded_implemented`, `ignored_not_implemented`). (Partially from v3 [~] 4.1, expanded for v4)
  - [X] **Add enhanced context fields:** `code_context` (before/after code snippets), `diff_summary` (key changes made), `tool_sequence` (e.g., "read_file→edit_file→run_terminal_cmd"), `modification_type` (refactor/bugfix/feature/documentation), and `confidence_score` (AI-assessed value from 0.0-1.0)
- `derived_learnings_v1`: Manually validated and promoted insights.
  - [X] **Define and implement schema:** `learning_id` (UUID string), `source_chat_id` (optional string FK to `chat_history_v1`), `description` (document content), `pattern` (string), `example_code_reference` (chunk_id string from `codebase_v1`), `tags` (comma-sep string), `confidence` (float).
  - [X] **Create collection using MCP client or `chroma-client`.**
- `thinking_sessions_v1`: For working memory.
  - [X] Create collection using MCP client.

**Key Features & Workflow Implementation:**

1. **Setup & Configuration (Common Components):**
    - [X] Install prerequisites (Python, Git, `chroma-mcp-server[full,client,dev]`).
    - [X] Prepare shared `.env` for ChromaDB connection (local path or server URL), API keys, embedding model choice (handling both local persistent and remote HTTP ChromaDB configs).
    - [X] Setup client modules (`src/chroma_mcp_client/`), packaging (`pyproject.toml`).
    - [X] Implement and configure unit tests (pytest, mock, coverage, etc.).
    - [X] Ensure `chroma-mcp-server` is launchable via IDE / `python -m chroma_mcp.cli`.
    - [X] Implement `chroma-client` console script for CLI operations and wrapper scripts (`scripts/*.sh`).
    - [X] **Implement `chroma-client setup-collections` command to check and create all required collections (`codebase_v1`, `chat_history_v1`, `derived_learnings_v1`, `thinking_sessions_v1`) if they don't exist.**
    - [X] Verify direct client connection (HTTP/Cloud via console script).
    - [X] Ensure security & secrets checklist followed (`.env` gitignored, etc.).
    - [X] Add comprehensive unit tests for client logic (`tests/client/`, etc., 80% coverage).

2. **Codebase Indexing with Contextual Chunking:**
    - [X] Ensure `codebase_v1` collection exists/is created by client.
    - [X] `chroma-client index --all`: Initial full codebase indexing into `codebase_v1`.
    - [X] Git `post-commit` hook using `chroma-client index --changed` for incremental updates.
    - [X] Implement basic query interface (`chroma-client query`).
    - [X] **Enhance the chunking strategy to use semantic boundaries (function/class definitions, logical sections) instead of fixed-size chunks.**
    - [X] **Update indexing to support bi-directional linking by tracking which chat sessions modify which code files.**

3. **Enhanced Interactive RAG & Rich Chat Logging (IDE Integration):**
    - [X] IDE connects to `chroma-mcp-server`.
    - [X] AI Assistant uses `chroma_query_documents` (MCP tool) to retrieve context from `codebase_v1`.
    - [X] **Refine `chroma_query_documents` (MCP tool) to also query `derived_learnings_v1` (mixed query or separate, with weighting).** (v3 [ ] 4.6)
    - [X] **Automated Chat Capture:** IDE rule (`auto_log_chat`) for summarizing prompt/response and logging to `chat_history_v1` via `#chroma_add_document_with_metadata`.
    - [X] **Enhance the `auto_log_chat` rule to:**
      - [X] **Extract code context (before/after snippets) when edits are made**
      - [X] **Generate diff summaries for code modifications**
      - [X] **Track tool usage sequences (e.g., read_file→edit_file→run_terminal_cmd)**
      - [X] **Assign confidence scores during creation to help identify valuable interactions**
      - [X] **Categorize interactions (refactor/bugfix/feature/documentation)**
      - [X] **Store enriched contextual information in the document and metadata**

4. **Working Memory (Sequential Thinking):**
    - [X] `record-thought` console script logs to `thinking_sessions_v1`.
    - [X] Implement sequential thinking logic in `src/chroma_mcp_thinking/`.
    - [X] IDE integration (`memory-integration-rule`) allows AI to query `chroma_find_similar_thoughts`.
    - [X] Add unit tests for thinking logic (`tests/thinking/`).

5. **Enhanced Implicit Learning Analysis & Semi-Automated Promotion:**
    - [X] `analyze-chat-history` (CLI subcommand) fetches `captured` entries from `chat_history_v1`, correlates with code changes, updates status to `analyzed`.
    - [X] **Implement `promote-learning` CLI subcommand or define a robust manual process to create entries in `derived_learnings_v1` from `analyzed` chat history or other sources.**
    - [X] **Ensure `promote-learning` process updates the status of source `chat_history_v1` entries to `promoted_to_learning`.**
    - [X] **Integrate analysis and promotion steps into a documented developer workflow (initially manual execution).** (v3 [ ] 4.5)
    - [X] **Manual Promotion Workflow:** Implement `promote-learning` command.
    - [X] **Interactive Promotion Workflow:** Implement `review-and-promote` command. (Provides interactive review, codebase search for code refs, calls refactored promotion logic, and includes robust error handling for embedding function mismatches).
    - [X] **Enhance `analyze-chat-history` to:**
      - [X] **Leverage the new rich context fields to identify high-value interactions**
      - [X] **Use confidence scores to prioritize entries for review**
      - [X] **Flag interactions that have significant code impact based on diff analysis**
    - [X] **Improve `review-and-promote` to implement a streamlined approval interface for candidate learnings.**

**Phase 1 Verification:**

- [X] End-to-End Test (Automation: Git hook for `codebase_v1` indexing).
- [X] **End-to-End Test (Interaction & Logging: IDE -> MCP Server -> RAG from `codebase_v1` & `derived_learnings_v1` -> AI response -> AI logs to `chat_history_v1`).** (Adapted from v3 [ ] 7.2)
- [X] End-to-End Test (Working Memory: `record-thought` via CLI/IDE task).
- [X] **Test `analyze-chat-history` command thoroughly.** (Adapted from v3 [ ] 7.4)
- [X] **Test `promote-learning` workflow and `derived_learnings_v1` creation.**
- [X] Test All Console Scripts (`chroma-client` subcommands, `record-thought`).
- [X] Run All Unit Tests (maintain >=80% coverage).
- [X] **Quality Assessment:** Periodically evaluate usefulness/accuracy of `derived_learnings_v1` entries.
- [X] **Test enhanced context capture in `auto_log_chat` rule.**
- [X] **Verify bi-directional links between code and chat history.**

**Forward Compatibility:** ✅ Fully forward-compatible with Phase 2. No schema changes required for existing collections. New metadata fields are additive and non-breaking.

---

## Phase 2: RAG + LoRA Fine-Tuning (Optional & Manual)

**Goal:** Enable developers to optionally fine-tune a LoRA adapter using validated learnings, and apply this adapter on-demand within their IDE.

**Additions to Phase 1 (New Collections/Files - External to ChromaDB):**

- `rl_dataset_YYYYMMDD.jsonl`: Exported reward dataset.
- `lora_codelearn_YYYYMMDD.safetensors`: Trained LoRA adapter file.

**Workflow Changes & Implementation:**

1. **Export Reward Dataset:**
    - [ ] **Develop `chroma-client export-rl-dataset` command.**
    - [ ] **Define the schema for `rl_dataset_YYYYMMDD.jsonl` (e.g., prompt-completion pairs).**
    - [ ] **Implement logic in `export-rl-dataset` to extract and transform data from `chat_history_v1` (status `promoted_to_learning` or `rewarded_implemented`) or `derived_learnings_v1`.**
    - [ ] **Ensure `chat_history_v1` entries used are marked with status `exported_for_reward`.**

2. **Manual LoRA Fine-Tuning:**
    - [ ] **Provide an example `scripts/train_lora.sh` (wrapper for a fine-tuning framework like `lit-gpt`, `axolotl`, etc.).**
    - [ ] **Document the manual LoRA fine-tuning process using the exported dataset.**

3. **On-Demand Adapter Usage in IDE:**
    - [ ] **Investigate and document how to load and use LoRA adapters on-demand with target LLMs/IDEs.**
    - [ ] (Optional) Implement any necessary MCP tools or IDE commands if dynamic loading needs server assistance.

**Phase 2 Verification:**

- [ ] **Test `chroma-client export-rl-dataset` command and the format of `rl_dataset.jsonl`.**
- [ ] **Manually train a sample LoRA adapter using an exported dataset.**
- [ ] **Test on-demand usage of the trained LoRA adapter in an IDE setup and evaluate its impact.**
- [ ] Cost Check: Monitor API costs if using paid models for fine-tuning or inference. (v3 [ ] 7.7)

**ChromaDB Compatibility:** ✅ `codebase_v1`, `chat_history_v1`, `derived_learnings_v1` schemas are unchanged. New additive `status` values in `chat_history_v1` are non-breaking.

---

## Phase 3: Full Reinforcement Learning Pipeline (Automated & Scheduled)

**Goal:** Automate the analysis, reward dataset generation, LoRA training, and adapter deployment processes, creating a continuous learning loop, ideally with a shared ChromaDB.

**Additions to Phase 2 (Automation & Scripts):**

- `scripts/nightly_analysis.sh`: Automates `analyze-chat-history` and potentially `export-rl-dataset`.
- `scripts/retrain_lora_incrementally.sh`: Automates LoRA training.
- `scripts/deploy_adapter.sh`: Automates LoRA adapter deployment.

**Automation Layers & Workflow Implementation:**

1. **Automated Chat History Tagging & Reward Signal Generation:**
    - [ ] **Enhance `analyze-chat-history` script for more robust correlation (e.g., AST changes, specific code patterns) to automatically tag `chat_history_v1` entries with statuses like `rewarded_implemented` or `ignored_not_implemented`.**
    - [ ] **Ensure the automated `export-rl-dataset` (called by `nightly_analysis.sh`) uses these refined statuses.**

2. **Scheduled LoRA Retraining:**
    - [ ] **Develop `scripts/nightly_analysis.sh` to run data preparation tasks.**
    - [ ] **Develop `scripts/retrain_lora_incrementally.sh` for automated, scheduled LoRA training.**
    - [ ] **Implement LoRA adapter versioning (e.g., `lora_codelearn_YYYY-MM-DD.safetensors`).**
    - [ ] **Document setup for scheduled jobs (e.g., cron).**

3. **Automated Adapter Deployment/Rotation:**
    - [ ] **Develop `scripts/deploy_adapter.sh` to manage LoRA adapter deployment/availability (e.g., copy to shared location, update config).**
    - [ ] **Define and implement a strategy for selecting/distributing the active LoRA adapter for IDEs/models.**

4. **CI/CD Optional Enhancements (Primarily for Shared ChromaDB):**
    - [ ] (Optional) **Merge Gate:** CI checks if new code adheres to patterns found in `derived_learnings_v1`.
    - [ ] (Optional) **Automated Diff Validation:** AI (potentially using the latest LoRA) reviews PRs.
    - [ ] (Optional) **Document setup for Team Learning Aggregation with a shared ChromaDB instance.**

**Phase 3 Verification:**

- [ ] **Test the full automated pipeline: `nightly_analysis.sh` -> `retrain_lora_incrementally.sh` -> `deploy_adapter.sh`.**
- [ ] **Verify LoRA adapter versioning and correct deployment of the latest adapter.**
- [ ] **Evaluate the quality and impact of automatically trained and deployed LoRA adapters over time.**
- [ ] Latency Benchmark: Measure interactive query latency with automatically updated LoRAs. (v3 [ ] 7.9 adapted)

**ChromaDB Compatibility:** ✅ Existing collections remain compatible. Metadata enrichments are non-breaking.

---

## Collection Compatibility Matrix

| Collection                     | Phase 1 | Phase 2 | Phase 3 | Notes                                                                 |
| ------------------------------ | ------- | ------- | ------- | --------------------------------------------------------------------- |
| `codebase_v1`                  | ✅       | ✅       | ✅       | Static chunks + metadata                                              |
| `chat_history_v1`              | ✅       | ✅       | ✅       | New statuses/metadata non-breaking (e.g., `rewarded`, `ignored`)      |
| `derived_learnings_v1`         | ✅       | ✅       | ✅       | Learning pattern stable; new optional fields non-breaking             |
| `thinking_sessions_v1`         | ✅       | ✅       | ✅       | For working memory, largely independent of RL cycle                   |
| `rl_dataset_*.jsonl`           | ❌       | ✅       | ✅       | Export-only format, external to ChromaDB                            |
| `lora_codelearn_*.safetensors` | ❌       | ✅       | ✅       | Trained model adapter, external to ChromaDB                         |

---

## CLI & Tooling Compatibility

| Script/Command                 | Phase 1                    | Phase 2                    | Phase 3                        | Notes                                                       |
| ------------------------------ | -------------------------- | -------------------------- | ------------------------------ | ----------------------------------------------------------- |
| `chroma-client index`          | ✅                          | ✅                          | ✅                              | Core indexing                                               |
| `chroma-client query`          | ✅                          | ✅                          | ✅                              | Core querying (may evolve to use LoRA contextually)         |
| `chroma-client analyze-chat-history` | ✅ (manual trigger)         | ✅ (manual trigger)         | ✅ (automated, enhanced)       | Analyzes chat for learning signals                        |
| `chroma-client promote-learning` | ✅ (manual)                 | ✅ (manual)                 | ✅ (manual, or semi-automated) | Curates `derived_learnings_v1`                            |
| `record-thought`               | ✅                          | ✅                          | ✅                              | For working memory                                          |
| `chroma-client export-rl-dataset` | ❌                          | ✅ (manual trigger)         | ✅ (automated)                 | Creates fine-tuning dataset                               |
| `scripts/train_lora.sh`        | ❌                          | ✅ (manual execution)       | ✅ (automated)                 | Wrapper for LoRA training                                   |
| `scripts/deploy_adapter.sh`    | ❌                          | ❌                          | ✅ (automated)                 | Manages LoRA adapter deployment                             |
| `official-client log-chat`     | ✅ (refined implementation)  | ✅ (refined implementation)  | ✅ (refined implementation)     | Manually logs chat interactions with enhanced context      |
| Official `chroma` CLI          | ✅ (for DB admin)           | ✅ (for DB admin)           | ✅ (for DB admin)              | For tasks like `copy`, `vacuum`, server management          |

---

## Design Guarantee: Forward Compatibility

All transitions (Phase 1 → 2 → 3) are designed to be **non-breaking**.

- **No Re-indexing Required:** Existing data in `codebase_v1`, `chat_history_v1`, etc., remains valid.
- **Stable Core Schemas:** Core fields in collections are preserved. New metadata fields are additive and optional.
- **No Destructive Migrations:** Upgrades do not require deleting or rebuilding ChromaDB collections from scratch.

Developers can adopt advanced phases incrementally without losing prior work or data.

---

## Data Migration & ChromaDB Management (Local to Shared)

For individual use, a local ChromaDB (SQLite-backed, configured via `CHROMA_DB_PATH` in `.env`) is sufficient for Phases 1 and 2. Phase 3, especially with team-based learning and CI/CD integration, benefits significantly from a **shared ChromaDB server instance**.

**Implementation & Documentation Tasks:**

1. **Official Chroma CLI Usage:**
    - [X] Ensure official `chroma` CLI is installable/accessible by developers.
    - [ ] **Document usage of `chroma copy` for migrating `codebase_v1`, `chat_history_v1`, `derived_learnings_v1`, `thinking_sessions_v1` between local and shared instances.**
    - [ ] **Document usage of `chroma utils vacuum --path <your-data-directory>` for local DB optimization prior to backup/migration.** (Requires server shutdown).

2. **Backup for Local ChromaDB:**
    - [ ] **Adapt `scripts/backup_chroma.sh` for robust local filesystem backups of all relevant ChromaDB data directories (e.g., `CHROMA_DB_PATH`).** (Adapted from v3 [ ] 6.7)
    - [ ] Document procedure for stopping server/client processes before backup.

3. **Shared Server Management:**
    - [ ] Provide guidance/links to documentation for backup/maintenance of shared ChromaDB server instances (Docker, Kubernetes, Chroma Cloud).

**Verification:**

- [ ] **Test Restore-from-Backup for all relevant local ChromaDB collections using the `backup_chroma.sh` script and manual copy.** (v3 [ ] 7.11)
- [ ] **Perform a test migration of all collections from a local instance to another local instance (simulating server migration) using `chroma copy`.**

---

## Shared Configuration (`.env`) Updates for Phases

Your `.env` file will need to accommodate different ChromaDB backend configurations:

```dotenv
# --- ChromaDB Configuration ---
# For local persistent DB (Phases 1, 2, or local Phase 3)
CHROMA_DB_IMPL="persistent"
CHROMA_DB_PATH="./data/chroma_db" # Or any other local path

# For remote/shared ChromaDB server (Recommended for collaborative Phase 3)
# CHROMA_DB_IMPL="http"
# CHROMA_HTTP_URL="http://your-chroma-server-address:8000"
# CHROMA_HTTP_HEADERS="" # e.g., "Authorization: Bearer your_token" if auth is enabled

# --- Embedding Model ---
# EMBEDDING_MODEL_PROVIDER="default" # or "openai", "huggingface_hub", "vertex_ai"
# EMBEDDING_MODEL_NAME="all-MiniLM-L6-v2" # if using default or hf
# OPENAI_API_KEY="sk-..." # if using openai
# HF_TOKEN="hf_..." # if using hf for private models
# GOOGLE_APPLICATION_CREDENTIALS="/path/to/gcp-credentials.json" # if using Vertex AI

# --- Other configurations ---
LOG_LEVEL="INFO"
# ... any other relevant settings
```

- [X] Ensure `.env` is in `.gitignore`.
- [ ] (Optional) **Implement and document support for custom embedding functions configured via `.env`.** (v3 [ ] 6.6)

---

## Optional Enhancements (Consider for any Phase)

- [ ] (Optional) **Add `repo_id` to metadata in all relevant collections for multi-repository setups.**
- [ ] (Optional) **Enrich `derived_learnings_v1` schema further with `tags`, `category` (for filtering/organization).**
- [ ] (Optional) **Track `model_version` (base model and any active LoRA) in `chat_history_v1` metadata.**
- [ ] (Optional) **Implement more sophisticated performance/cost tuning measures (chunking strategies, quantization).** (v3 [ ] 6.2)
- [ ] (Optional) **Setup basic monitoring and logging for server and client operations.** (v3 [ ] 6.3)
- [ ] (Optional) **Implement HTTP resilience & retries in client if using HTTP/Cloud backend.** (v3 [ ] 6.4)
- [ ] (Optional) **Investigate/Setup Observability / Metrics Dashboard for key pipeline metrics.** (v3 [ ] 6.5)
- [ ] (Optional) **Add action-oriented tagging with structured categories like refactoring, bug fixing, feature implementation, documentation.**
- [ ] (Optional) **Implement session context enrichment to better group related interactions across multiple chat exchanges.**
- [ ] (Optional) **Create a visualization tool for navigating the connections between code changes and chat history.**
- [ ] (Optional) **Add support for multimedia content in chat summaries (e.g., screenshots, diagrams) to enhance context.**
- [ ] (Optional) **Upgrade existing CLI tools (`analyze_chat_history.sh`, `promote_learning.sh`, `review_and_promote.sh`) to fully leverage enhanced metadata captured by the logging system for better context awareness and correlation.**

---

## General Project Documentation & Workflow Refinements

- [X] This document (`local_rag_pipeline_plan_v4.md`) replaces `local_rag_pipeline_plan_v3.md` - **Mark as done once this PR is merged.**
- [X] **Update `README.md`, `developer_guide.md`, IDE integration docs, and specific tool usage docs (e.g., `record-thought.md`) to reflect the v4 phased approach, new CLI commands, and workflows.** (Adapted from v3 [~] 1.11, [~] 5.8, [~] 7.12)
- [X] **Consolidate and update client command documentation (e.g., in `docs/usage/client_commands.md` or `docs/scripts/`) covering all `chroma-client` subcommands and `record-thought`.** (Adapted from v3 [~] 1.11, [~] 5.8)
- [ ] **Create/Update `docs/usage/implicit_learning.md` for Phase 1 implicit learning and analysis workflow.** (v3 [ ] 4.7)
- [ ] **Create `docs/usage/derived_learnings.md` detailing the `derived_learnings_v1` schema, its promotion workflow, and how it's used in RAG.**
- [ ] **Create `docs/usage/lora_finetuning.md` for Phase 2 manual LoRA process and on-demand usage.**
- [ ] **Create `docs/usage/automated_rl_pipeline.md` for Phase 3 automated training and deployment.**
- [X] **Review and update Working Memory documentation (`docs/thinking_tools/`, `docs/scripts/record-thought.md`), including specific workflow checkpoints/usage patterns.** (Adapted from v3 [~] 5.4, [~] 5.8)
- [ ] **Define and document an overall prompting strategy that incorporates RAG from multiple sources (`codebase_v1`, `derived_learnings_v1`), working memory, and conditionally LoRA-adapted models.** (v3 [ ] 6.1)
- [ ] **Verify all user-facing scripts are executable and have clear usage instructions.**
- [ ] Index Size & Storage Check: Document how to monitor data directory sizes and provide guidance on managing them. (v3 [ ] 7.10)
- [X] **Create `docs/usage/enhanced_context_capture.md` explaining the enriched chat logging system and bi-directional linking.**
- [X] **Update `docs/rules/auto_log_chat.md` with new code snippet extraction and tool sequence tracking functionality.**
- [X] **Add section to developer guide on effective use of confidence scores and action-oriented tagging.**
- [X] **Develop troubleshooting guide for common issues with the enhanced context capture system.**

---

*Next Steps after this plan is adopted:*

- Prioritize implementation of remaining unchecked items for Phase 1, focusing on `derived_learnings_v1`.
- Begin development of `export-rl-dataset` for Phase 2.
- Plan detailed architecture for automation scripts and shared DB considerations for Phase 3.

*Implementation Priorities for Enhanced Context Capture:*

1. **Update `auto_log_chat` Rule First:** ✅
   - Implement code snippet extraction and diff generation
   - Add tool sequence tracking
   - Incorporate confidence scoring mechanism
   - This captures the richest information at the moment of creation

2. **Create Context Capture Module:** ✅
   - Create `src/chroma_mcp_client/context.py` for reusable context extraction logic
   - Implement functions for:
     - Code snippet extraction from before/after edits
     - Diff generation and summarization
     - Tool sequence tracking and pattern recognition
     - Confidence score calculation
     - Bidirectional link management
   - Add comprehensive documentation and examples
   - This module will be used by the enhanced `auto_log_chat` rule and potentially other tools

3. **Update Collection Schemas:** ✅
   - Enhance `chat_history_v1` schema with new context fields
   - Add bidirectional linking capabilities to `codebase_v1`

4. **Improve Analysis & Promotion Workflow:** ✅
   - Enhance `analyze-chat-history` to use new context fields
   - Update `review-and-promote` with streamlined candidate approval
   - Develop better visualization of connections between code and discussions

5. **Improve Contextual Chunking:** ✅
   - Refine the codebase chunking strategy to use semantic boundaries
   - Update indexing to support the enhanced schema

*Refactoring:*

- [X] Promotion logic extracted to `src/chroma_mcp_client/learnings.py` (`promote_to_learnings_collection`).
- [X] Query logic added to `src/chroma_mcp_client/query.py` (`query_codebase`).
- [X] Extract context capture logic to `src/chroma_mcp_client/context.py` for reusability across tools.
- [X] Refactor `auto_log_chat` rule to use the new context capture module.
- [X] Create utility functions for diff generation and code snippet extraction.

*Testing:*

- [X] Unit tests for `setup-collections`.
- [X] Unit tests for `promote-learning` (covering success, source update, source not found).
- [X] Unit tests for `review-and-promote` interactive script (`test_interactive_promoter.py`).
- [X] Unit tests for `query_codebase` (`test_query.py`), including specific checks for embedding mismatch error handling.
- [X] Unit tests for context capture logic.
- [X] End-to-end tests for enhanced `auto_log_chat` functionality.
- [X] Tests for bidirectional linking between code and chat history.

*Documentation:*

- [X] Update `docs/scripts/chroma-client.md` with new commands.
- [X] Update `docs/developer_guide.md` with workflows.
- [X] Update `docs/mcp_test_flow.md` for RAG query changes.
- [X] Update plan doc (this file) with progress.
- [X] Create new documentation for enhanced context capture system.
- [X] Update `auto_log_chat.md` with new code snippet extraction and tool sequence tracking functionality.
- [X] Create API documentation for the context.py module.
- [X] Prepare developer guide for effective use of confidence scores and context extraction.

*Next Immediate Tasks:*

1. [X] Create the skeleton for `src/chroma_mcp_client/context.py` with key function signatures and docstrings
2. [X] Implement the first key function: code snippet extraction
3. [X] Add comprehensive unit tests for context capture logic
4. [X] Begin integrating with auto_log_chat rule once core functionality is stable
5. [X] Implement bidirectional linking between code and chat history
6. [X] Enhance chunking with semantic boundaries
7. [X] **Create `docs/usage/enhanced_context_capture.md` explaining the enriched chat logging system and bi-directional linking.**
8. [X] **Update the review-and-promote workflow to leverage the enhanced context data**
9. [X] **Fix ChromaDB client interaction in auto_log_chat implementation to use proper collection.add() method**
10. [X] **Update tests to correctly mock and verify the ChromaDB client interactions**
11. [ ] **Enhance `analyze_chat_history.sh` to leverage new metadata:**
    - [ ] Prioritize entries with higher confidence scores for analysis
    - [ ] Use already-captured code context instead of regenerating git diffs
    - [ ] Leverage tool sequence data for better correlation
    - [ ] Use bidirectional linking information already present
12. [ ] **Improve `promote_learning.sh` to utilize enhanced context:**
    - [ ] Add support for including code context and diffs from source chat entry
    - [ ] Use confidence scores to inform default confidence of promoted learnings
    - [ ] Include references to original modification type and tool sequences
13. [ ] **Enhance `review_and_promote.sh` interface:**
    - [ ] Show rich context (code diffs, tool sequences) during review
    - [ ] Sort/prioritize entries by confidence score
    - [ ] Add option to filter by modification type (refactor/bugfix/feature/documentation)
    - [ ] Display linked code chunks via bidirectional linking
14. [ ] **General enhancement task for CLI tools:**
    - [ ] Create a shared module for context rendering to ensure consistent formatting across tools
    - [ ] Implement color coding for diff display in terminal output
    - [ ] Add a "context richness" metric to help prioritize entries with more complete metadata
    - [ ] Create a visual indicator for bidirectional links in CLI interfaces
