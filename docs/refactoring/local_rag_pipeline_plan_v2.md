# ✅ Action Plan v2: Local RAG Pipeline (Hybrid Approach)

**Goal:** Implement a local RAG pipeline using **direct ChromaDB access for automation (indexing, CI)** via installable client commands and the **`chroma-mcp-server` for interactive AI tasks (feedback, working memory)**, focusing on practicality, cost-efficiency, and quality improvement.

**Architecture:**

- **Automation (Git Hooks, CI, Scripts):** Use dedicated Python client modules (`src/chroma_mcp_client/`) exposed via installable console scripts (e.g., `chroma-client`) that connect *directly* to the ChromaDB backend based on `.env` config. Wrapper scripts (`scripts/`) can be used for internal repo tasks like git hooks.
- **Interaction (IDE - Cursor, Windsurf, etc.):** Use the `chroma-mcp-server` running via the IDE's MCP integration for feedback loops and sequential thinking tools.

---

## Phase 1: Setup & Configuration (Common Components)

- [ ] **1.1 Install Prerequisites:**
  - [ ] Verify Python ≥ 3.10 (`python --version`)
  - [ ] Verify Docker & Docker Compose (Needed *only* if running ChromaDB backend via HTTP/Docker, *not* required for persistent local DB or direct client usage) - *Consider removing Docker mentions if fully committed to non-Docker.*
  - [ ] Verify Git (`git --version`)
  - [ ] Install `chroma-mcp-server` (provides both server and reusable utils):
        ```bash
        # Installs server + core libs + embedding functions + client dependencies
        # Use the [client] extra for the command-line tools
        pip install "chroma-mcp-server[full,client]"
        ```
  - [ ] Install any additional tools if needed (`jq`, `mkcert`, etc.).

- [ ] **1.2 Prepare Shared Configuration (`.env`):**
  - [ ] Create data/log directories (e.g., `./chroma_data`, `./logs`).
  - [ ] Create `.env` in project root (used by *both* MCP server and direct client):
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
  - [ ] **Cost Optimization:** Start with a local embedding function (`default`, `accurate`).
  - [ ] **Security:** Add `.env` to `.gitignore`. Use secrets management for API keys/tokens in CI/shared environments.

- [ ] **1.3 Setup Direct Client Modules (`src/chroma_mcp_client/`, etc.):**
  - [ ] Create `src/chroma_mcp_client/`, `src/chroma_mcp_feedback/`, `src/chroma_mcp_thinking/` directories.
  - [ ] Move/Develop the core Python logic for indexing, querying, feedback, and thinking into these modules.
  - [ ] Ensure each logical component has a clear CLI entry point function (e.g., `main()` in `cli.py` modules within each directory).

        ```python
        # Example: src/chroma_mcp_client/connection.py
        import chromadb
        import os
        import sys
        from pathlib import Path
        # Import utils safely, assuming installed package or correct path setup
        try:
            from chroma_mcp_server.utils import (
                get_chroma_client_config,
                create_chroma_client,
                get_embedding_function
            )
            from chroma_mcp_server.config import load_config_from_env
            from chroma_mcp_server.types import ChromaClientConfig
        except ImportError:
             # Add project root to path if running as script (less ideal now)
             project_root = Path(__file__).resolve().parents[2] # Adjust based on nesting
             src_path = str(project_root / 'src')
             if src_path not in sys.path:
                 sys.path.insert(0, src_path)
             from chroma_mcp_server.utils import (
                 get_chroma_client_config,
                 create_chroma_client,
                 get_embedding_function
             )
             from chroma_mcp_server.config import load_config_from_env
             from chroma_mcp_server.types import ChromaClientConfig

        _direct_client = None
        _embedding_function = None
        _config_args = None

        def get_client_and_ef():
            """Initializes and returns direct client and embedding function based on .env"""
            global _direct_client, _embedding_function, _config_args
            if _direct_client is None:
                _config_args = load_config_from_env() # Loads from .env
                client_config = get_chroma_client_config(_config_args)
                _direct_client = create_chroma_client(client_config)
                _embedding_function = get_embedding_function(_config_args.embedding_function_name)
                print(f"Direct client initialized (Type: {client_config.client_type}, EF: {_config_args.embedding_function_name})", file=sys.stderr) # Log to stderr
            return _direct_client, _embedding_function
        ```
        ```python
        # Example: src/chroma_mcp_client/indexing.py
        import time
        import sys
        import hashlib
        import subprocess # Needed for git ls-files
        from pathlib import Path
        from .connection import get_client_and_ef # Relative import

        SUPPORTED_SUFFIXES = {".py", ".ts", ".js", ".go", ".java", ".md", ".txt", ".sh", ".yaml", ".json", ".h", ".c", ".cpp", ".cs", ".rb", ".php"}

        def index_file(file_path: Path, repo_root: Path):
            """Reads, embeds, and upserts a single file into ChromaDB."""
            client, embedding_func = get_client_and_ef()
            collection_name = "codebase_v1" # Or get from config

            if not file_path.exists() or file_path.is_dir():
                 print(f"Skipping non-existent or directory: {file_path}", file=sys.stderr)
                 return

            if file_path.suffix not in SUPPORTED_SUFFIXES:
                 print(f"Skipping unsupported file type: {file_path.suffix}", file=sys.stderr)
                 return

            try:
                content = file_path.read_text(errors='ignore')
                if not content.strip():
                     print(f"Skipping empty file: {file_path}", file=sys.stderr)
                     return

                embeddings = embedding_func([content]) # Batch size 1 for simplicity
                relative_path = str(file_path.relative_to(repo_root))
                doc_id = hashlib.sha1(relative_path.encode()).hexdigest()
                metadata = {"path": relative_path, "last_indexed": time.time()}

                collection = client.get_or_create_collection(name=collection_name)
                collection.upsert(
                    ids=[doc_id],
                    embeddings=embeddings,
                    metadatas=[metadata],
                    documents=[content]
                )
                # Use stderr for operational messages
                print(f"Indexed [Direct]: {relative_path}", file=sys.stderr)
            except Exception as e:
                print(f"Error indexing {file_path}: {e}", file=sys.stderr)

        def index_git_files(repo_root: Path):
             """Indexes all tracked git files."""
             print(f"Indexing all tracked files in {repo_root}...", file=sys.stderr)
             try:
                 # Use git ls-files to get all tracked files
                 cmd = ["git", "ls-files"]
                 result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=True)
                 files_to_index = [repo_root / f for f in result.stdout.splitlines()]
                 print(f"Found {len(files_to_index)} files to index.", file=sys.stderr)
                 for file_path in files_to_index:
                     index_file(file_path, repo_root)
             except Exception as e:
                 print(f"Error running git ls-files or indexing: {e}", file=sys.stderr)
                 # Decide if script should exit here or continue (e.g., exit(1))
        ```
        ```python
        # Example: src/chroma_mcp_client/querying.py
        import sys
        import json
        from .connection import get_client_and_ef

        def query_codebase(query: str, n_results: int = 5):
            """Performs a query against the codebase collection and prints JSON results."""
            client, _ = get_client_and_ef()
            collection_name = "codebase_v1"
            try:
                collection = client.get_collection(name=collection_name)
                results = collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    include=["metadatas", "documents", "distances"]
                )
                # Output results as JSON to stdout for the wrapper script/caller
                print(json.dumps(results, indent=2))
            except Exception as e:
                print(f"Error querying {collection_name}: {e}", file=sys.stderr)
                # Optionally return a JSON error structure to stdout
                print(json.dumps({"error": str(e)}))
                exit(1) # Indicate error

        def get_collection_count(collection_name: str):
             """Gets the count of items in a collection and prints it as JSON."""
             client, _ = get_client_and_ef()
             try:
                 collection = client.get_collection(name=collection_name)
                 count = collection.count()
                 # Output count as JSON to stdout
                 print(json.dumps({"collection": collection_name, "count": count}))
             except Exception as e:
                 print(f"Error getting count for {collection_name}: {e}", file=sys.stderr)
                 print(json.dumps({"error": str(e)}))
                 exit(1) # Indicate error
        ```
        ```python
        # Example: src/chroma_mcp_client/cli.py (Entry point for console script)
        import argparse
        import os
        import sys
        from pathlib import Path
        from .indexing import index_file, index_git_files
        from .querying import query_codebase, get_collection_count

        def main():
            parser = argparse.ArgumentParser(description="Direct ChromaDB Client CLI (via chroma-client command)")
            subparsers = parser.add_subparsers(dest="command", required=True)

            # Index Subparser
            index_parser = subparsers.add_parser("index", help="Index specific files or all git files")
            index_parser.add_argument("files", nargs='*', help="Paths to specific files to index (optional)")
            index_parser.add_argument("--repo-root", default=os.getcwd(), help="Repo root path")
            index_parser.add_argument("--all", action="store_true", help="Index all tracked files in the repo")

            # Query Subparser
            query_parser = subparsers.add_parser("query", help="Query the codebase")
            query_parser.add_argument("query_text", help="Text to search for")
            query_parser.add_argument("-n", "--n-results", type=int, default=5, help="Number of results")

            # Count Subparser
            count_parser = subparsers.add_parser("count", help="Count items in a collection")
            count_parser.add_argument("collection_name", default="codebase_v1", nargs='?', help="Name of the collection")

            args = parser.parse_args()
            repo_root_path = Path(args.repo_root).resolve()

            # Setup client/EF early (initializes connection based on .env)
            try:
                # Importing from connection implicitly calls get_client_and_ef if not already called
                from .connection import get_client_and_ef
                get_client_and_ef()
            except Exception as e:
                print(f"Error initializing ChromaDB client: {e}", file=sys.stderr)
                sys.exit(1)

            if args.command == "index":
                if args.files:
                    files_to_index = [Path(f).resolve() for f in args.files]
                    for file_path in files_to_index:
                        index_file(file_path, repo_root_path)
                elif args.all:
                    index_git_files(repo_root_path)
                else:
                     print("Error: No files specified for indexing and --all not used.", file=sys.stderr)
                     parser.print_help(sys.stderr)
                     exit(1)

            elif args.command == "query":
                query_codebase(args.query_text, args.n_results)

            elif args.command == "count":
                 get_collection_count(args.collection_name)

        if __name__ == "__main__":
             main()
        ```
  - [ ] Add `__init__.py` files to necessary directories.

- [ ] **1.4 Configure Packaging (`pyproject.toml`):**
  - [ ] Define `[project.optional-dependencies]` including a `client` extra for any client-specific dependencies.
        ```toml
        # pyproject.toml
        [project.optional-dependencies]
        client = [
            # Add any client-specific dependencies here, e.g.:
            # "requests",
        ]
        # ... other extras ...
        ```
  - [ ] Define `[project.scripts]` to create console script entry points for the client tools.
        ```toml
        # pyproject.toml
        [project.scripts]
        chroma-client = "chroma_mcp_client.cli:main"
        record-feedback = "chroma_mcp_feedback.cli:main" # Assumes cli:main exists
        record-thought = "chroma_mcp_thinking.cli:main" # Assumes cli:main exists
        ```
  - [ ] *(Optional)* Configure `[tool.hatch.build.targets.wheel.shared-data]` if the shell wrapper scripts (`scripts/`) should be included in the package distribution (primarily for internal use).
        ```toml
        # pyproject.toml
        [tool.hatch.build.targets.wheel.shared-data]
        "scripts" = "scripts"
        ```
  - [ ] Ensure build process (`hatch build`) picks up this configuration.

- [ ] **1.5 Create Wrapper Scripts (`scripts/*.sh` - for Internal Use):**
  - [ ] Create/maintain shell scripts (`scripts/chroma_client.sh`, `scripts/record_feedback.sh`, `scripts/record_thought.sh`) that invoke the Python client CLI modules (e.g., `python -m chroma_mcp_client.cli ...`).
  - [ ] **Note:** These wrappers are primarily for convenience *within this repository* (e.g., git hooks) and are *not* the primary public interface for external users (who should use the console scripts like `chroma-client`).
        ```bash
        #!/bin/bash
        # scripts/chroma_client.sh - Internal wrapper
        # ... (setup as before) ...
        # Execute the Python CLI module
        "${PYTHON_EXECUTABLE:-python}" -m chroma_mcp_client.cli "$@"
        ```
  - [ ] Make scripts executable.
  - [ ] Test the wrapper scripts for internal tasks.

- [ ] **1.6 Test Console Scripts (Public Interface):**
  - [ ] After installing the package locally (`pip install .[client]` or `hatch shell`), test the console scripts directly:
        ```bash
        # Test console scripts (assuming venv is active)
        chroma-client --help
        chroma-client index README.md --repo-root .
        chroma-client query "installation guide"
        chroma-client count codebase_v1
        record-feedback --help # etc.
        record-thought --help # etc.
        ```

- [ ] **1.7 Launch & Test MCP Server (for Interaction):**
  - [ ] Run `chroma-mcp-server` normally (via IDE integration / `.cursor/mcp.json`).
        ```bash
        # Example command if running manually (uses .env)
        chroma-mcp-server
        ```
  - [ ] Verify connection via MCP client (e.g., Cursor Tool window):
        ```tool_code
        print(default_api.mcp_chroma_dev_chroma_get_server_version(random_string="check"))
        ```

- [ ] **1.8 Verify Direct Client Connection (HTTP/Cloud via Console Script):**
  - [ ] Use the console script to test connection to remote backends:
        ```bash
        # Assumes .env configured and package installed
        chroma-client query "test connection" -n 1
        ```
  - [ ] Ensure no connection errors are reported (check stderr).

- [ ] **1.9 Security & Secrets Checklist:**
  - [ ] Ensure `.env` is git-ignored (`echo ".env" >> .gitignore`).
  - [ ] Use secrets management for API keys/tokens in CI/shared environments.
  - [ ] Store `CHROMA_API_KEY` / header tokens securely, inject at runtime.
  - [ ] *(Optional)* Configure TLS for HTTP mode if exposed.

- [ ] **1.10 Add Unit Tests for Client Logic (`tests/client/`, etc.):**
  - [ ] Create `tests/client/`, `tests/feedback/`, `tests/thinking/` directories.
  - [ ] Implement unit tests using `pytest` for `src/chroma_mcp_client/`, `src/chroma_mcp_feedback/`, `src/chroma_mcp_thinking/` modules.
  - [ ] Mock `chromadb` interactions to isolate client logic.
  - [ ] Test argument parsing, file handling, ID generation, JSON output.
  - [ ] Aim for >= 80% code coverage.
  - [ ] Run tests: `hatch run test`

- [ ] **1.11 Document Client Usage (`docs/usage/client_commands.md`):**
  - [ ] Create/update documentation explaining how to install (`pip install chroma-mcp-server[client]`) and use the `chroma-client`, `record-feedback`, `record-thought` console commands.
  - [ ] Document commands, options, and configuration via `.env`.
  - [ ] Clarify that these console scripts are the primary public interface.

---

## Phase 2: Codebase Indexing (Using Direct Client Wrapper/Command)

- [ ] **2.1 Ensure Codebase Collection Exists (via Console Script):**
  - [ ] Use the console script (implicitly handles via `get_or_create_collection`):

        ```bash
        # Running index via console script ensures collection exists
        chroma-client index README.md --repo-root .
        # Or verify count
        chroma-client count codebase_v1
        ```

- [ ] **2.2 Implement Incremental Indexing (Git Hook using Wrapper Script):**
  - [ ] Update the `.git/hooks/post-commit` hook to use the *internal wrapper script* (`scripts/chroma_client.sh`), as it runs within the repo context.

        ```bash
        #!/usr/bin/env bash
        set -euo pipefail

        REPO_ROOT=$(git rev-parse --show-toplevel)
        # Use internal wrapper script from repo
        WRAPPER_SCRIPT="${REPO_ROOT}/scripts/chroma_client.sh"

        # Check if wrapper script exists
        if [ ! -f "$WRAPPER_SCRIPT" ]; then
            echo "Error: Wrapper script not found at $WRAPPER_SCRIPT" >&2
            exit 1
        fi

        # Concurrency lock (remains the same)
        LOCKFILE="/tmp/chroma_index.lock.$(echo $REPO_ROOT | md5sum | cut -d' ' -f1)" # Repo-specific lock
        exec 200>"$LOCKFILE"
        flock -n 200 || {
            echo "Indexer already running, skipping commit hook index." >&2
            exit 0 # Exit successfully if lock held
        }

        echo "Running post-commit indexing via wrapper..." >&2
        git diff --name-only --diff-filter=ACMRT HEAD~1 HEAD | grep -E '\.(py|ts|js|go|java|md|txt|sh|yaml|json|h|c|cpp|cs|rb|php)$' | while read -r file; do
            if [ -f "$REPO_ROOT/$file" ]; then
                # Call the internal wrapper script
                "$WRAPPER_SCRIPT" index "$REPO_ROOT/$file" --repo-root "$REPO_ROOT"
            else
                 echo "Skipping deleted/moved file: $file" >&2
            fi
        done
        echo "Post-commit indexing finished." >&2
        # Lock automatically released on script exit
        ```
  - [ ] Make the hook executable.
  - [ ] **Key Points:**
        - Git hook uses the internal wrapper script for convenience within the repo.
        - Relies on the Python environment being correctly set up for the wrapper.

- [ ] **2.3 Initial Codebase Indexing (via Console Script):**
  - [ ] Trigger indexing for all relevant *tracked* files using the public console script:
        ```bash
        chroma-client index --all --repo-root .
        ```
  - [ ] Monitor script stderr output.
  - [ ] Verify collection count using the console script:
        ```bash
        chroma-client count codebase_v1
        ```

---

## Phase 3: IDE Integration (Interactive RAG via MCP)

- [ ] **3.1 Identify Interactive Tool:**
  - [ ] The tool for *interactive* RAG is `chroma_query_documents` (from the running `chroma-mcp-server`).

- [ ] **3.2 Configure IDE (Cursor, Windsurf, etc.):**
  - [ ] Ensure the IDE connects to the running `chroma-mcp-server` (via `.cursor/mcp.json`, etc.).
  - [ ] Configure auth headers (`CHROMA_HEADERS`) in IDE env if needed.

- [ ] **3.3 Test Interactive Retrieval (via MCP):**
  - [ ] In the IDE, manually invoke `chroma_query_documents`:

        ```tool_code
        print(default_api.mcp_chroma_dev_chroma_query_documents(...))
        ```
  - [ ] Verify results.
  - [ ] *(Optional)* Compare with direct client console script query:

        ```bash
        chroma-client query "..."
        ```

---

## Phase 4: Feedback Loop & Reinforcement (via MCP)

- [ ] **4.1 Create Feedback Collection (via MCP):**
  - [ ] Use MCP client:

        ```tool_code
        print(default_api.mcp_chroma_dev_chroma_create_collection(collection_name="rag_feedback_v1"))
        ```

- [ ] **4.2 Implement Feedback Recording Logic (`src/chroma_mcp_feedback/`):**
  - [ ] Create `src/chroma_mcp_feedback/` directory.
  - [ ] Develop Python modules for recording feedback. **Challenge:** These modules need a reliable way to send MCP requests to the IDE-managed `chroma-mcp-server` instance. This might involve:
        - [ ] Using a library like `fastmcp.client` (if available and suitable).
        - [ ] Implementing custom logic to communicate over stdio or a network socket if the MCP server exposes one for tools:

        ```python
        # Example: src/chroma_mcp_feedback/recorder.py - Conceptual
        import json
        import uuid
        import time
        import sys
        # Import or implement your MCP client communication method here
        # This is the tricky part - how does this client find and talk to the
        # MCP server instance run by the IDE?
        # Placeholder:
        def send_mcp_request(tool_name, params):
            # This needs real implementation based on chosen communication method
            # (stdio wrapper, network socket, etc.)
            print(f"[MCP Client SIM] Calling {tool_name} with {params}", file=sys.stderr)
            # Simulate success for now
            return {"status": "simulated_success"}

        def record_feedback(snippet: str, source_query: str, source_file: str, accepted: bool):
            """Records feedback using MCP tools."""
            collection_name = "rag_feedback_v1"
            doc_id = f"feedback_{uuid.uuid4()}" # Use UUID for uniqueness
            metadata = {
                "source_query": source_query,
                "source_file": source_file,
                "accepted": accepted,
                "timestamp": time.time()
            }
            # Metadata needs to be a JSON string for the tool
            metadata_json = json.dumps(metadata)

            params = {
                "collection_name": collection_name,
                "document": snippet,
                "id": doc_id,
                "metadata": metadata_json,
                "increment_index": True # Index immediately
            }
            try:
                # Tool to add document with ID and metadata
                response = send_mcp_request(
                    # Adjust tool name prefix if needed based on mcp.json
                    "mcp_chroma_dev_chroma_add_document_with_id_and_metadata", params
                )
                print(f"Feedback Recorded (MCP): ID={doc_id} Accepted={accepted}", file=sys.stderr)
                # Handle response if needed
                return response # Return response for CLI
            except Exception as e:
                print(f"Error recording feedback via MCP: {e}", file=sys.stderr)
                # Re-raise or return error indicator
                raise
        ```
        ```python
        # Example: src/chroma_mcp_feedback/cli.py - Conceptual
        import argparse
        import sys
        import json
        from .recorder import record_feedback

        def main():
            parser = argparse.ArgumentParser(description="Record RAG feedback via MCP (record-feedback command)")
            parser.add_argument("--snippet", required=True, help="The code snippet acted upon")
            parser.add_argument("--query", required=True, help="The original query that produced the snippet")
            parser.add_argument("--source-file", required=True, help="Source file context if available")
            parser.add_argument("--accepted", action=argparse.BooleanOptionalAction, required=True, help="Whether the suggestion was accepted/useful")

            args = parser.parse_args()

            try:
                result = record_feedback(
                    snippet=args.snippet,
                    source_query=args.query,
                    source_file=args.source_file,
                    accepted=args.accepted
                )
                # Optionally print success/result JSON to stdout
                print(json.dumps({"status": "success", "result": result}))
            except Exception as e:
                print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
                sys.exit(1)

        if __name__ == "__main__":
             main()

        ```
- [ ] **4.3 Create Feedback Wrapper Script (`scripts/record_feedback.sh` - for Internal Use):**
  - [ ] Create/maintain a shell script (`scripts/record_feedback.sh`) to invoke the feedback Python CLI module (`python -m chroma_mcp_feedback.cli ...`).
  - [ ] **Note:** This is mainly for internal repo use or specific IDE integrations calling a script. External users should use the `record-feedback` console command.
        ```bash
        #!/bin/bash
        # scripts/record_feedback.sh - Internal wrapper
        # ... (setup as before) ...
        # Execute the Python CLI module
        "${PYTHON_EXECUTABLE:-python}" -m chroma_mcp_feedback.cli "$@"
        ```
  - [ ] Make executable.

- [ ] **4.4 Integrate Feedback Trigger (IDE -> Console Script / Wrapper -> Python -> MCP Server):**
  - [ ] Hook the feedback mechanism into the IDE workflow.
  - [ ] **Preferred Method:** IDE directly calls the `record-feedback` console command if possible.
  - [ ] **Alternative:** IDE calls the `scripts/record_feedback.sh` wrapper script.
  - [ ] Ensure the underlying Python code can reach the running MCP server.

- [ ] **4.5 Refine Interactive Retrieval using Feedback (Advanced):**
  - [ ] Modify interactive retrieval prompts (Phase 3) to query `rag_feedback_v1` via MCP server *before* or *alongside* `codebase_v1`.

- [ ] **4.6 Add Unit Tests for Feedback Logic (`tests/feedback/`):**
  - [ ] Create `tests/feedback/` directory.
  - [ ] Test feedback recording logic in `src/chroma_mcp_feedback/`.
  - [ ] Mock MCP communication (`send_mcp_request`).
  - [ ] Verify correct parameters are passed to the mock.
  - [ ] Aim for >= 80% coverage.

- [ ] **4.7 Document Feedback Mechanism (`docs/usage/client_commands.md`):**
  - [ ] Explain how the feedback loop works.
  - [ ] Document `record-feedback` console command usage.
  - [ ] Show how to integrate with IDEs (examples using console command preferably).

---

## Phase 5: Working Memory & Sequential Thinking (via MCP)

*This phase relies entirely on the interactive MCP server running via the IDE and requires MCP communication from Python clients.*

- [ ] **5.1 Create Thinking Sessions Collection (via MCP):**
  - [ ] Use MCP client:

        ```tool_code
        print(default_api.mcp_chroma_dev_chroma_create_collection(collection_name="thinking_sessions_v1"))
        ```

- [ ] **5.2 Implement Sequential Thinking Logic (`src/chroma_mcp_thinking/`):**
  - [ ] Create `src/chroma_mcp_thinking/` directory.
  - [ ] Develop Python modules for managing thinking sessions. **Challenge:** Similar to feedback, needs robust MCP communication logic.

        ```python
        # Example: src/chroma_mcp_thinking/session.py - Conceptual
        import json
        import uuid
        import sys
        # Import or implement your MCP client communication method here
        # Placeholder:
        def send_mcp_request(tool_name, params):
            print(f"[MCP Client SIM] Calling {tool_name} with {params}", file=sys.stderr)
            return {"status": "simulated_success", "session_id": params.get("session_id")}

        class ThinkingSession:
            def __init__(self, session_id=None, branch_id="main"):
                self.session_id = session_id or str(uuid.uuid4())
                self.branch_id = branch_id
                self.thought_count = 0
                self.total_thoughts = 0 # Estimate or update later

            def record_thought(self, thought_content, total_thoughts_estimate=0, next_needed=False):
                """Records a thought using the chroma_sequential_thinking MCP tool."""
                self.thought_count += 1
                if total_thoughts_estimate > self.total_thoughts:
                     self.total_thoughts = total_thoughts_estimate

                params = {
                    "thought": thought_content,
                    "thought_number": self.thought_count,
                    "total_thoughts": self.total_thoughts or self.thought_count, # Best guess
                    "session_id": self.session_id,
                    "branch_id": self.branch_id,
                    "branch_from_thought": 0, # Simple linear sequence for now
                    "next_thought_needed": next_needed,
                }
                try:
                     # Adjust tool name prefix if needed
                     response = send_mcp_request("mcp_chroma_dev_chroma_sequential_thinking", params)
                     print(f"Thought Recorded (MCP): Session={self.session_id}, Num={self.thought_count}", file=sys.stderr)
                     return response # Return response for CLI
                except Exception as e:
                     print(f"Error recording thought via MCP: {e}", file=sys.stderr)
                     raise

            # --- Add methods to find similar thoughts/sessions using MCP tools ---
            def find_similar_thoughts(self, query, n_results=3):
                 params = {"query": query, "n_results": n_results, "session_id": self.session_id}
                 try:
                      # Adjust tool name prefix if needed
                      response = send_mcp_request("mcp_chroma_dev_chroma_find_similar_thoughts", params)
                      return response
                 except Exception as e:
                      print(f"Error finding thoughts via MCP: {e}", file=sys.stderr)
                      raise

            def get_session_summary(self):
                 params = {"session_id": self.session_id, "include_branches": True}
                 try:
                      # Adjust tool name prefix if needed
                      response = send_mcp_request("mcp_chroma_dev_chroma_get_session_summary", params)
                      return response
                 except Exception as e:
                      print(f"Error getting session summary via MCP: {e}", file=sys.stderr)
                      raise

        ```
        ```python
        # Example: src/chroma_mcp_thinking/cli.py - Conceptual
        import argparse
        import sys
        import json
        from .session import ThinkingSession

        def main():
            parser = argparse.ArgumentParser(description="Record thoughts or query thinking sessions via MCP (record-thought command)")
            parser.add_argument("--session-id", help="Existing session ID (optional, defaults to new session)")
            parser.add_argument("--branch-id", default="main", help="Branch ID within the session")

            subparsers = parser.add_subparsers(dest="action", required=True)

            # Record thought action
            record_parser = subparsers.add_parser("record", help="Record a new thought")
            record_parser.add_argument("thought", help="The content of the thought")
            record_parser.add_argument("--total-estimate", type=int, default=0, help="Estimate of total thoughts in sequence")
            record_parser.add_argument("--next-needed", action="store_true", help="Flag if next thought is needed")

            # Query thoughts action
            query_parser = subparsers.add_parser("query", help="Find similar thoughts in the session")
            query_parser.add_argument("query_text", help="Text to search for")
            query_parser.add_argument("-n", "--n-results", type=int, default=3, help="Number of results")

            # Summarize session action
            summary_parser = subparsers.add_parser("summary", help="Get summary of the session")

            args = parser.parse_args()

            session = ThinkingSession(session_id=args.session_id, branch_id=args.branch_id)

            try:
                if args.action == "record":
                    result = session.record_thought(
                        thought_content=args.thought,
                        total_thoughts_estimate=args.total_estimate,
                        next_needed=args.next_needed
                    )
                    # Print session ID for potential chaining
                    print(json.dumps({"status": "success", "session_id": session.session_id, "result": result}))
                elif args.action == "query":
                    result = session.find_similar_thoughts(args.query_text, args.n_results)
                    print(json.dumps(result, indent=2))
                elif args.action == "summary":
                    result = session.get_session_summary()
                    print(json.dumps(result, indent=2))

            except Exception as e:
                print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
                sys.exit(1)

        if __name__ == "__main__":
            main()
        ```

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

- [ ] **5.7 Add Unit Tests for Thinking Logic (`tests/thinking/`):**
  - [ ] Create `tests/thinking/` directory.
  - [ ] Test session management and parameter construction in `src/chroma_mcp_thinking/`.
  - [ ] Mock MCP communication.
  - [ ] Aim for >= 80% coverage.

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
- [ ] **7.5 Run Unit Tests:** Execute `hatch run test` and check coverage report. Verify >= 80%.
- [ ] **7.6 Cost Check:** Monitor API costs.
- [ ] **7.7 Quality Assessment:** Evaluate workflow.
- [ ] **7.8 Latency Benchmark:** Measure interactive MCP query latency.
- [ ] **7.9 Index Size & Storage Check:** Monitor data dir size.
- [ ] **7.10 Restore-from-Backup Test:** Verify backup/restore.
- [ ] **7.11 Documentation Review:** Ensure console commands and overall workflow are clearly documented.

---

**Outcome:** A functional local RAG pipeline using a **hybrid architecture**: direct client access (via installable console commands) for robust automation (indexing, CI) and the `chroma-mcp-server` for interactive AI tasks (feedback, working memory), with improved structure, packaging, testing, and documentation for easier external use.
