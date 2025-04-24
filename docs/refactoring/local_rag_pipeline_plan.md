# ✅ Action Plan: Local RAG Pipeline with Chroma MCP Server

**Goal:** Implement a local RAG pipeline using `chroma-mcp-server` for enhanced code generation, testing, and knowledge retrieval in development environments (Cursor, Windsurf, etc.), incorporating a feedback loop and focusing on cost-efficiency and quality improvement.

---

## Phase 1: Setup & Configuration

- [x] **1.1 Install Prerequisites:**
  - [x] Verify Python ≥ 3.10 (`python --version`)
  - [x] Verify Docker & Docker Compose (`docker --version`, `docker compose version`) (Docker needed for alternative server setup or external ChromaDB)
  - [x] Verify Git (`git --version`)
  - [x] Install `chroma-mcp-server` with necessary extras (e.g., for local embedding models):

    ```bash
    pip install "chroma-mcp-server[full]" # Or specific extras as needed
    ```

  - [x] Install any additional tools if needed (`jq` for release script, etc.).

- [x] **1.2 Prepare Server Configuration:**
  - [x] Create a data directory for persistent storage (e.g., `./chroma_data`).
  - [x] Create a log directory (e.g., `./logs`).
  - [x] Create or update a `.env` file in the project root or server working directory:

    ```dotenv
    # .env
    CHROMA_CLIENT_TYPE=persistent
    CHROMA_DATA_DIR=./chroma_data # Use the path created above
    CHROMA_LOG_DIR=./logs         # Use the path created above
    LOG_LEVEL=INFO
    MCP_LOG_LEVEL=INFO
    # Choose a cost-effective local embedding function initially
    CHROMA_EMBEDDING_FUNCTION=default # e.g., 'default'/'fast' (ONNX MiniLM)
    # Add API keys here ONLY if using API-based embedding functions later
    # OPENAI_API_KEY=...
    # GOOGLE_API_KEY=...
    ```

  - [x] For chromadb backend HTTP mode, update your `.env` with:

    ```dotenv
    CHROMA_CLIENT_TYPE=http
    CHROMA_HOST=localhost
    CHROMA_PORT=8000
    CHROMA_SSL=false
    # (Optional) CHROMA_HEADERS='{"Authorization":"Bearer <token>"}'
    ```

  - [x] For chromadb backend cloud mode, update your `.env` with:

    ```dotenv
    CHROMA_CLIENT_TYPE=cloud
    CHROMA_HOST=api.trychroma.com
    CHROMA_TENANT=<your-tenant>
    CHROMA_DATABASE=<your-database>
    CHROMA_API_KEY=<your-api-key>
    ```

  - [x] **Cost Optimization:** Select a local embedding function (`default`, `accurate`) initially to minimize embedding costs.

- [x] **1.3 Launch Chroma MCP Server:**
  - [x] Run the server using the configured `.env` file (recommended method):

    ```bash
    # Ensure .env is in the current directory or specify --dotenv-path
    chroma-mcp-server
    ```

  - [x] **Alternative (Docker):** If running `chroma-mcp-server` within Docker is preferred (requires creating a suitable Dockerfile): *Adapt the concept below, replacing `chromadb/chroma` with your `chroma-mcp-server` image and adjusting command/environment variables.* The key is mounting volumes and passing config.

    ```yaml
    # Conceptual docker-compose.yml for chroma-mcp-server
    services:
      chroma-mcp:
        image: your-chroma-mcp-server-image:latest # Replace with your image
        # command: ["chroma-mcp-server", "--args..."] # If needed
        ports:
          - "8000:8000" # Expose port if using networked MCP tools (not default)
        volumes:
          - ./chroma_data:/app/chroma_data # Mount persistent data dir
          - ./logs:/app/logs             # Mount log dir
          - ./.env:/app/.env             # Mount config file
        environment:
          # Env vars can also be set here instead of .env
          CHROMA_CLIENT_TYPE: "persistent"
          CHROMA_DATA_DIR: "/app/chroma_data"
          CHROMA_LOG_DIR: "/app/logs"
          # ... other env vars ...
    ```

  - [x] Verify server startup: Check logs for successful initialization and MCP endpoint availability (typically `stdio` for direct execution). If using Docker, check `docker logs <container_name>`.

- [ ] **1.4 Initial Server Check:**
  - [ ] Use an MCP client (like Cursor's MCP tool window) to connect and run a basic command:

    ```tool_code
    # Example using 'dev' prefix if configured in Cursor mcp.json
    print(default_api.mcp_chroma_dev_chroma_get_server_version(random_string="check"))
    ```

  - [ ] Ensure a successful response (e.g., server version) is received.

- [ ] **1.5 Remote-Mode Smoke Test:**
  - [ ] Verify HTTP client connection:

    ```bash
    chroma-mcp-server --client-type http --host "$CHROMA_HOST" --port "$CHROMA_PORT" --ssl "$CHROMA_SSL" && echo "HTTP client OK"
    ```

  - [ ] Verify Cloud client connection:

    ```bash
    chroma-mcp-server --client-type cloud --tenant "$CHROMA_TENANT" --database "$CHROMA_DATABASE" --api-key "$CHROMA_API_KEY" && echo "Cloud client OK"
    ```

- [ ] **1.6 Security & Secrets Checklist:**
  - [x] Ensure `.env` is **git-ignored** (`echo ".env" >> .gitignore`).
  - [ ] Use a secrets manager (GitHub Secrets, 1Password CLI, Vault) for CI workflows—never commit API keys.
  - [ ] For HTTP/Cloud modes, store `CHROMA_API_KEY` / header tokens in your secret store and inject at runtime (`--env-from` in Docker or GitHub Secrets action).
  - [ ] *(Optional)* Generate a self-signed cert for local HTTPS if exposing HTTP client:

    ```bash
    mkcert localhost 127.0.0.1 ::1
    # configure reverse-proxy (Caddy / nginx) to terminate TLS and forward to chroma-mcp on :8000
    ```

- [ ] **1.7 Build & Publish Dev Docker Image (optional but recommended):**
  - [ ] Create a `Dockerfile`:

    ```dockerfile
    FROM python:3.11-slim
    WORKDIR /app
    COPY . /app
    RUN pip install --no-cache-dir .[full]
    EXPOSE 8000
    ENTRYPOINT ["chroma-mcp-server"]
    ```

  - [ ] Build and tag:

    ```bash
    docker build -t myrepo/chroma-mcp-server:dev .
    ```

  - [ ] (Optional) Push in CI via GitHub Action:

    ```yaml
    # .github/workflows/docker.yml (excerpt)
    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v3
          - name: Build
            run: docker build -t ${{ secrets.DOCKER_USER }}/chroma-mcp:${{ github.sha }} .
          - name: Login and Push
            run: |
              echo ${{ secrets.DOCKER_TOKEN }} | docker login -u ${{ secrets.DOCKER_USER }} --password-stdin
              docker push ${{ secrets.DOCKER_USER }}/chroma-mcp:${{ github.sha }}
    ```

---

## Phase 2: Codebase Indexing

- [ ] **2.1 Create Codebase Collection:**
  - [ ] Use the MCP client to create a dedicated collection for codebase indexing:

    ```tool_code
    print(default_api.mcp_chroma_dev_chroma_create_collection(collection_name="codebase_v1"))
    ```

  - [ ] Verify successful creation message.

- [ ] **2.2 Implement Incremental Indexing (Git Hook):**
  - [ ] Adapt the *concept* from the original plan's Python script for `.git/hooks/post-commit`. **Direct `chromadb` client usage will not work.** The hook must interact with the running `chroma-mcp-server` via MCP.
  - [ ] **Original Script Concept (for reference, needs modification):**

    ```python
    # Original concept - DO NOT USE DIRECTLY - Needs MCP integration
    #!/usr/bin/env python3
    import subprocess, pathlib, hashlib, chromadb # Direct client import
    from sentence_transformers import SentenceTransformer

    repo   = pathlib.Path(
              subprocess.check_output(["git","rev-parse","--show-toplevel"]).strip().decode())
    files  = subprocess.check_output(["git","diff","--name-only","HEAD~1"]).decode().splitlines()

    # !! This needs to be replaced with MCP communication !!
    # client = chromadb.HttpClient(host="localhost", port=4000) # Example from original plan
    col    = client.get_or_create_collection("codebase") # Direct API call
    model  = SentenceTransformer("thenlper/gte-large") # Embedding done in hook

    for f in files:
        p = repo / f
        if p.suffix not in {".py",".ts",".go",".java",".md"} or not p.exists(): continue
        txt    = p.read_text(errors="ignore")
        # !! Embedding should ideally happen via MCP server tool if possible,
        # !! otherwise the hook needs the same embedding model as the server.
        emb    = model.encode(txt)
        doc_id = hashlib.sha1(p.as_posix().encode()).hexdigest()
        # !! This needs to be replaced with an MCP tool call !!
        # col.upsert(ids=[doc_id], embeddings=[emb], metadatas=[{"path":f}]) # Direct API call
    print("🔄 indexed", len(files), "files")
    ```

  - [ ] **MCP Integration Options:**
  - **Option A (Subprocess):** Create a simple CLI script that takes a file path, content, and ID, and uses an MCP client library (like `fastmcp` potentially, or manual requests) to call the `chroma_add_document_with_id_and_metadata` tool on the running server. The git hook then calls this script via `subprocess`.
  - **Option B (File Watcher/Periodic Script):** Implement indexing *outside* the git hook. A separate script watches for file changes or runs periodically, scans for modified files (using `git diff`), and then uses an MCP client to call the appropriate `add`/`update` tools on the `chroma-mcp-server`.
  - [ ] **Key Considerations for Adaptation:**
  - Decide where embedding happens: Ideally, pass raw text directly to the server's `add` tool so it uses the configured `CHROMA_EMBEDDING_FUNCTION`. If you must embed in the hook script, pin the exact same embedding function and model version (match `CHROMA_EMBEDDING_FUNCTION` and package versions) to guarantee vector consistency.
  - Use a consistent hashing method for document IDs (e.g., SHA1 of relative path).
  - **Cost Optimization:** The script must still only process diffs (`git diff --name-only HEAD~1`).
  - [ ] Make the hook/script executable (e.g., `chmod +x .git/hooks/post-commit`).

- [ ] **2.3 Initial Codebase Indexing:**
  - [ ] Trigger an initial indexing run (e.g., run the watcher/periodic script, or if using the hook, make an initial commit):

    ```bash
    # If using post-commit hook for triggering
    git commit --allow-empty -m "chore: Initial codebase indexing trigger"
    ```

  - [ ] Monitor the server logs and hook/script output to ensure files are processed and added to the `codebase_v1` collection.
  - [ ] Verify collection count increases using the MCP client:

    ```tool_code
    print(default_api.mcp_chroma_dev_chroma_get_collection(collection_name="codebase_v1"))
    ```

- [ ] **Concurrency Guard (multi-user):**
  - [ ] Add a simple `flock` wrapper to avoid simultaneous index-updates if several developers share the same instance:

    ```bash
    # inside post-commit hook
    exec 200>"$HOME/.mcp_index.lock"
    flock -n 200 || exit 0
    # …rest of script…
    ```

---

## Phase 3: IDE Integration

- [ ] **3.1 Identify Retrieval Tool:**
  - [ ] The primary tool for RAG is `chroma_query_documents` provided by `chroma-mcp-server`.
  - [ ] *(Note: The original plan mentioned a custom `project_search.yaml` tool spec. This is not needed when using `chroma-mcp-server` as the tools are built-in).*

- [ ] **3.2 Configure Cursor:**
  - [ ] Edit `.cursorconfig/settings.json` (or workspace settings):

    ```json
    // settings.json
    "[python]": { // Or other relevant languages
       "editor.codeActionsOnSave": {
            "source.organizeImports": "explicit"
       },
       "editor.defaultFormatter": "charliermarsh.ruff" // Example formatter
    },
    "cursor.codeLenses.relatedContext": true, // Optional: Show related context lenses
    // **Ensure Cursor is configured to use your chroma-mcp-server instance**
    // (Refer to Cursor docs for mcpServerCommand / mcpServerEnv if needed)
    ```

  - [ ] Use the specific tool name (`chroma_query_documents`) when calling it manually or potentially configuring Cursor's future RAG features.

- [ ] **3.3 Configure Windsurf / Other Tools:**
  - [ ] Follow specific configuration steps for other IDEs/tools to register and call the `chroma_query_documents` tool from your running `chroma-mcp-server` instance.
  - [ ] **Example Concept (VS Code Copilot Extension from original plan):** *(This demonstrates calling **any** MCP tool, adapt the tool name and server URL/port if using a networked setup).*

    ```typescript
    // Conceptual src/activate.ts for calling an MCP tool
    import { registerCopilotAgentTool } from "@github/copilot-tools";
    export function activate(ctx) {
      registerCopilotAgentTool(ctx, {
        // Use the actual tool name from chroma-mcp-server
        name: "chroma_query_documents",
        description: "Query Chroma vector store via MCP Server",
        // Define parameters expected by chroma_query_documents
        parameters: {
          collection_name: { type: "string", required: true },
          query_texts: { type: "array", items: { type: "string" }, required: true },
          n_results: { type: "number" }
          // Add other parameters as needed (where, where_document, include)
        },
        // Invoke needs to communicate with the MCP server (stdio or network)
        // This example assumes a hypothetical network endpoint - likely needs adjustment
        // for stdio communication or a proper MCP client library.
        invoke: async (params) => {
          const serverUrl = "http://localhost:8000"; // Adjust if networked
          const toolName = "chroma_query_documents";
          // Placeholder: Actual MCP communication logic needed here
          console.log(`Calling ${toolName} with:`, params);
          // Example: Simulate fetch to a hypothetical REST wrapper (replace with real MCP call)
          // const response = await fetch(`${serverUrl}/invoke/${toolName}`, {
          //   method: "POST",
          //   headers: { "Content-Type": "application/json" },
          //   body: JSON.stringify(params)
          // });
          // return await response.text();
          return JSON.stringify({ note: "MCP invocation logic needed" });
        }
      });
    }
    ```

- [ ] **3.4 Test Retrieval:**
  - [ ] In the IDE, manually invoke the retrieval tool with a relevant query:

    ```tool_code
    # Example using a configured 'chroma_dev' prefix
    print(default_api.mcp_chroma_dev_chroma_query_documents(
        collection_name="codebase_v1",
        query_texts=["function for http client authentication"],
        n_results=5
    ))
    ```

  - [ ] Verify relevant code snippets are returned.

---

## Phase 4: Feedback Loop & Reinforcement

- [ ] **4.1 Create Feedback Collection:**
  - [ ] Create a separate collection to store feedback data:

    ```tool_code
    print(default_api.mcp_chroma_dev_chroma_create_collection(collection_name="rag_feedback_v1"))
    ```

- [ ] **4.2 Implement Feedback Recording:**
  - [ ] Create a script or mechanism (`feedback.py` concept) using MCP tools.
  - [ ] **Conceptual `feedback.py` using MCP:**

    ```python
    # Conceptual feedback.py - Needs MCP client implementation
    import json
    import os
    import subprocess
    # Assume an MCP client/wrapper script exists: mcp_client_cli.py

    def call_mcp_tool(tool_name, params):
        # Placeholder: Implement actual MCP communication
        # Example using a hypothetical CLI wrapper via subprocess
        try:
            cmd = ["python", "mcp_client_cli.py", tool_name, json.dumps(params)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            # Parse result.stdout as needed
            print(f"MCP Call Success: {result.stdout}")
            return json.loads(result.stdout) # Assuming JSON output
        except Exception as e:
            print(f"MCP Call Error: {e}")
            print(f"Stderr: {getattr(e, 'stderr', 'N/A')}")
            return None

    def record_accept(snippet: str, source_query: str, source_file: str, accepted: bool):
        collection_name = "rag_feedback_v1"
        # Generate a unique ID, e.g., based on snippet hash or UUID
        doc_id = f"feedback_{hash(snippet)}_{accepted}" 
        metadata = {
            "source_query": source_query,
            "source_file": source_file,
            "accepted": accepted,
            # "timestamp": time.time() # Add timestamp if desired
        }
        params = {
            "collection_name": collection_name,
            "document": snippet,
            "id": doc_id,
            "metadata": json.dumps(metadata) # Metadata must be JSON string for the tool
        }
        
        # Use the appropriate add tool
        call_mcp_tool("chroma_add_document_with_id_and_metadata", params)
        print(f"Recorded feedback for snippet from {source_file}: Accepted={accepted}")

    # Example usage (replace with actual trigger logic):
    # record_accept("def example():\n  pass", "query about example", "src/utils.py", True)
    ```

  - [ ] Define metadata schema (see example above).

- [ ] **4.3 Integrate Feedback Trigger:**
  - [ ] Hook the feedback recording mechanism (e.g., calling the `record_accept` function) into the IDE/workflow (Cursor custom commands, Windsurf events, manual triggers).

- [ ] **4.4 Refine Retrieval using Feedback (Advanced):**
  - [ ] Modify retrieval logic/prompts to query `rag_feedback_v1` and use results (e.g., boosting snippets marked `accepted: True`) to improve `codebase_v1` query results.
  - [ ] **Quality Improvement Focus:** Prioritize useful, validated snippets.

- [ ] **4.5 CI Integration for Feedback:**
  - [ ] Adapt CI workflows (`.github/workflows/test.yml` concept) to call the feedback script.
  - [ ] **Conceptual CI Step:**

    ```yaml
    # .github/workflows/test.yml (Conceptual Step)
    - name: Log Test Outcome to Chroma Feedback
        # Run only if tests failed OR on success for main branch (example)
        if: failure() || (github.ref == 'refs/heads/main' && success())
        env:
            TEST_OUTCOME: ${{ job.status }}
        run: |
            ACCEPTED_FLAG=$( [ "$TEST_OUTCOME" == "success" ] && echo "true" || echo "false" )
            # Gather relevant snippet/log data (adjust based on test framework)
            SNIPPET_DATA="$(cat test_summary.log || echo 'Test log unavailable')"
            SOURCE_QUERY="CI Test Run - ${GITHUB_WORKFLOW}"
            SOURCE_FILE="ci_job_${GITHUB_RUN_ID}"    
            # Call the feedback script (assuming it's accessible and configured)
            python path/to/feedback.py \
                --snippet "$SNIPPET_DATA" \
                --query "$SOURCE_QUERY" \
                --file "$SOURCE_FILE" \
                --accepted $ACCEPTED_FLAG
    ```

  - [ ] **Avoid Repetitive Errors:** This helps the RAG avoid suggesting code patterns associated with past CI failures.

---

## Phase 5: Working Memory & Sequential Thinking

- [ ] **5.1 Create Thinking Sessions Collection:**
  - [ ] Create a dedicated collection for storing thinking sessions and sequential thoughts:
        ```tool_code
        print(default_api.mcp_chroma_dev_chroma_create_collection(collection_name="thinking_sessions_v1"))
        ```
  - [ ] Verify successful creation message.

- [ ] **5.2 Implement Sequential Thinking:**
  - [ ] Define a method to record structured thought sequences during development:

    ```python
    # thought_recorder.py concept
    import json
    import uuid

    def call_mcp_tool(tool_name, params):
        # Similar implementation as the feedback script
        # Uses your preferred MCP client approach
        pass

    class ThinkingSession:
        def __init__(self, session_id=None, branch_id="main"):
            """Initialize a thinking session with optional ID"""
            self.session_id = session_id or str(uuid.uuid4())
            self.branch_id = branch_id
            self.thought_count = 0
            self.total_thoughts = 0  # Will be updated when known
            
        def record_thought(self, thought_content, total_thoughts=None, next_needed=False):
            """Record a single thought in a sequence"""
            self.thought_count += 1
            if total_thoughts:
                self.total_thoughts = total_thoughts
            
            params = {
                "thought": thought_content,
                "thought_number": self.thought_count,
                "total_thoughts": self.total_thoughts or self.thought_count,
                "session_id": self.session_id,
                "branch_id": self.branch_id,
                "branch_from_thought": 0,  # No branching in this simple implementation
                "next_thought_needed": next_needed
            }
            
            result = call_mcp_tool("chroma_sequential_thinking", params)
            print(f"Recorded thought #{self.thought_count} in session {self.session_id}")
            return result
            
        def find_similar_thoughts(self, query, n_results=5):
            """Find thoughts similar to the query"""
            params = {
                "query": query,
                "session_id": "",  # Empty to search globally
                "n_results": n_results
            }
            return call_mcp_tool("chroma_find_similar_thoughts", params)
            
        def get_session_summary(self):
            """Get all thoughts in this session"""
            params = {
                "session_id": self.session_id,
                "include_branches": True
            }
            return call_mcp_tool("chroma_get_session_summary", params)
    
    # Example usage:
    # session = ThinkingSession()
    # session.record_thought("Initial design idea: Implement indexer using git hooks", 3)
    # session.record_thought("Problem encountered: Hook needs MCP client access", 3)
    # session.record_thought("Solution: Create lightweight CLI wrapper for the hook", 3)
    # summary = session.get_session_summary()
    ```

- [ ] **5.3 Integrate with Development Workflow:**
  - [ ] Define key checkpoints to record structured thoughts during development:
        - [ ] **Session Start:** Record initial tasks, goals, and context
        - [ ] **Design Decisions:** Record architecture choices with rationale
        - [ ] **Challenges:** Document problems encountered and solutions applied
        - [ ] **Session Conclusion:** Summarize outcomes and next steps
  - [ ] Create IDE shortcuts (macros or commands) to trigger thought recording at those checkpoints
        ```bash
        # Example shortcut/script
        python thought_recorder.py --checkpoint start --thought "Starting task: $1"
        ```

- [ ] **5.4 Connect with RAG Query Pipeline:**
  - [ ] Extend retrieval prompts to include relevant previous thinking from similar sessions:

    ```python
    # Conceptual integration in a retrieval wrapper
    def enhanced_retrieval(query, primary_collection="codebase_v1", thought_collection="thinking_sessions_v1"):
        # First, get code snippets
        code_results = call_mcp_tool("chroma_query_documents", {
            "collection_name": primary_collection,
            "query_texts": [query],
            "n_results": 3
        })
        
        # Then, find related thoughts from previous sessions
        thought_results = call_mcp_tool("chroma_find_similar_thoughts", {
            "query": query,
            "n_results": 2
        })
        
        # Combine results into enhanced context
        combined_context = {
            "code_snippets": code_results,
            "related_thoughts": thought_results
        }
        
        return combined_context
    ```

  - [ ] Create a utility to find similar past sessions for current task context
        ```python
        def find_similar_sessions(query, n_results=3):
            params = {
                "query": query,
                "n_results": n_results
            }
            return call_mcp_tool("chroma_find_similar_sessions", params)
        ```

- [ ] **5.5 Test Working Memory Integration:**
  - [ ] Create a test thinking session with a sequence of related thoughts
  - [ ] Verify retrieval of thoughts across sessions
  - [ ] Test how the working memory enhances RAG results by providing additional context

- [ ] **5.6 Provide a CLI Wrapper for Thought Recording:**
  - [ ] Add a small script `scripts/record_thought.sh`:

    ```bash
    #!/usr/bin/env bash
    set -euo pipefail
    THOUGHT="$*"
    python thought_recorder.py --checkpoint manual --thought "$THOUGHT"
    ```

  - [ ] Make it executable (`chmod +x scripts/record_thought.sh`) and wire as an IDE macro / shell alias.

---

## Phase 6: Optimization & Usage

- [ ] **6.1 Define Prompting Strategy:**
  - [ ] Establish clear rules (IDE snippets, custom prompts) for using the RAG tool (e.g., `chroma_query_documents`).
  - [ ] Inject retrieved snippets concisely into prompts.
  - [ ] Define rules for test generation based on retrieved context.

- [ ] **6.2 Performance & Cost Tuning:**
  - [ ] **Chunking:** Experiment with code chunking strategies if not indexing whole files.
  - [ ] **Embedding Model:** Evaluate local (`default`, `accurate`) vs. API models based on cost/quality needs.
  - [ ] **Hardware:** Ensure sufficient RAM for the server. Monitor resources.
  - [ ] **Quantization/Optimization:** Check ChromaDB/model docs for optimization options (e.g., INT8 quantization). *(Note: The original plan mentioned `persist(pq=True)`, which relates to older Chroma versions or specific configurations - verify current options)*.

- [ ] **6.3 Monitoring & Maintenance:**
  - [ ] Monitor server logs.
  - [ ] Periodically check retrieval relevance and feedback data.
  - [ ] Plan for re-indexing if models change.
  - [ ] Back up the persistent data directory (`CHROMA_DATA_DIR`).

- [ ] **6.4 HTTP Resilience & Retries:**
  - [ ] If using HTTP/Cloud mode, test and tune client timeouts and retry policies (via CLI flags or env vars if supported).
  - [ ] Consider exponential backoff wrappers to handle transient network issues.

- [ ] **6.5 Observability / Metrics Dashboard (optional):**
  - [ ] Expose FastAPI `/metrics` via Prometheus or run `prometheus_client` in middleware if not already exposed.
  - [ ] Spin up Prometheus + Grafana docker-compose stack and import a simple dashboard showing:
    - Query latency p95 / p99
    - Collection sizes
    - Error counts
  - [ ] Add Grafana alert rule for high latency (> 2 s) or error spikes.

- [ ] **6.6 Custom Embedding Functions (advanced):**
  - [ ] Create a Python module `custom_embeddings/my_retrieval.py` implementing the `EmbeddingFunction` interface.
  - [ ] Install it into the environment and reference with `--embedding-function my_retrieval` or set `CHROMA_EMBEDDING_FUNCTION=my_retrieval`.
  - [ ] Index a small sample and evaluate accuracy vs cost.

- [ ] **6.7 Automated Daily Backup Script:**
  - [ ] Add `scripts/backup_chroma.sh`:

    ```bash
    #!/usr/bin/env bash
    tar czf "chroma_backup_$(date +%Y%m%d_%H%M).tar.gz" -C "$CHROMA_DATA_DIR" .
    find . -name 'chroma_backup_*.tar.gz' -mtime +7 -delete  # keep 7 days
    ```

  - [ ] Schedule via cron or GitHub Action.

---

## Phase 7: Verification

- [ ] **7.1 End-to-End Test:** Simulate a development task, use RAG, apply snippet, trigger feedback, verify recording.
- [ ] **7.2 Cost Check:** Monitor API costs if applicable.
- [ ] **7.3 Quality Assessment:** Evaluate if RAG improves workflow speed and reduces errors.
- [ ] **7.4 Latency Benchmark:** Measure 95th‑percentile end‑to‑end query latency to ensure interactive performance.
- [ ] **7.5 Index Size & Storage Check:** Track collection size (vector count) and disk usage (`du -sh $CHROMA_DATA_DIR`) to plan for sharding or archiving as indexes grow.
- [ ] **7.6 Restore-from-Backup Test:**
  - [ ] Stop server, move current data dir aside, untar most recent backup, restart, and ensure collections & query results are intact.
- [ ] **7.7 Metrics & Alerts Test:**
  - [ ] Introduce artificial latency (e.g., `tc qdisc` or sleep) and verify Grafana alert fires.

---

**Outcome:** A functional local RAG pipeline integrated into the development workflow, learning from usage, optimized for cost, and aimed at improving code quality and consistency.
