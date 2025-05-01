# Automating Codebase Indexing with Git Hooks

This guide explains how to set up a Git `post-commit` hook to automatically index changed files into your ChromaDB collection whenever you make a commit. This keeps your codebase index up-to-date for RAG (Retrieval-Augmented Generation) tasks.

This approach uses the `chroma-mcp-client` CLI, run via `hatch` to ensure the correct Python environment and dependencies are used.

## Prerequisites

1. **`chroma-mcp-server` Installation:** You need the client tools installed:

    ```bash
    pip install "chroma-mcp-server[client]"
    # or if managing with hatch in the project
    # hatch add "chroma-mcp-server[client]"
    ```

2. **`hatch`:** The script relies on `hatch run` to execute the client CLI in the correct environment. Ensure `hatch` is installed and available in your terminal.
3. **`.env` Configuration:** Your project needs a `.env` file at the root, configured for `chroma-mcp-client` to connect to your ChromaDB instance (persistent or http/cloud). See the main documentation for `.env` setup details.
4. **Git Repository:** This setup assumes you are working within a Git repository.

## Setup Steps

1. **Navigate to your project's hooks directory:**

    ```bash
    cd your-project-root/.git/hooks
    ```

2. **Create the `post-commit` file:** Create a new file named `post-commit` (no extension) in this directory.
3. **Paste the script content:** Open the `post-commit` file in a text editor and paste the following script:

    ```bash
    #!/usr/bin/env bash
    set -euo pipefail
    
    REPO_ROOT=$(git rev-parse --show-toplevel)
    
    # Cross-platform MD5 - macOS uses md5, Linux uses md5sum
    calculate_md5() {
        if command -v md5sum >/dev/null 2>&1; then
            echo "$1" | md5sum | cut -d' ' -f1
        elif command -v md5 >/dev/null 2>&1; then
            echo "$1" | md5 | cut -d'=' -f2 | tr -d ' '
        else
            # Fallback to simple hash
            echo "$1" | cksum | cut -d' ' -f1
        fi
    }
    
    # Portable locking mechanism to prevent multiple hooks running simultaneously
    LOCKFILE="/tmp/chroma_index.lock.$(calculate_md5 "$REPO_ROOT")"
    
    # Try to create the lockfile as an atomic operation
    if ! mkdir "$LOCKFILE" 2>/dev/null; then
        echo "Indexer already running, skipping commit hook index." >&2
        exit 0 # Exit successfully if lock held
    fi
    
    # Register trap to remove the lockfile on exit (including errors)
    trap 'rm -rf "$LOCKFILE"' EXIT
    
    # --- Configuration --- 
    # Default collection name - change if needed
    COLLECTION_NAME="codebase_v1" 
    # -------------------

    # Get list of changed files (Added or Modified) in the last commit
    # Use -z and mapfile/readarray for safer filename handling
    changed_files=()
    while IFS= read -r -d $'\0' file; do
        # Only add files that actually exist (handles edge cases)
        if [ -f "$REPO_ROOT/$file" ]; then
             changed_files+=("$file")
        fi
    done < <(git diff-tree --no-commit-id --name-only --diff-filter=d -r -z HEAD)
    
    # Exit if no tracked files were changed/added
    if [ ${#changed_files[@]} -eq 0 ]; then
        echo "No files added/modified in this commit. Skipping indexing." >&2
        exit 0
    fi
    
    echo "Running post-commit indexing for ${#changed_files[@]} changed files via hatch..." >&2
    # Construct the command with the changed files as arguments
    # Ensure we are in the project root for hatch and for relative paths
    cd "$REPO_ROOT"
    
    # Execute the client CLI using hatch run
    hatch run python -m chroma_mcp_client.cli index \
        --repo-root "$REPO_ROOT" \
        --collection-name "$COLLECTION_NAME" \
        -- "${changed_files[@]}" # Pass files as positional arguments after --
    
    echo "Post-commit indexing finished." >&2
    ```

4. **Make the script executable:**

    ```bash
    chmod +x post-commit
    ```

## How it Works

- **Trigger:** Runs automatically after every successful `git commit`.
- **Locking:** Creates a temporary lock file to prevent multiple instances from running if commits happen very quickly.
- **File Detection:** Uses `git diff-tree` to find files added (`A`) or modified (`M`) in the specific commit just made. It ignores deleted files (`D`).
- **Execution:** Executes the `chroma-mcp-client`'s index command using `hatch run python -m chroma_mcp_client.cli index`.
- **Environment:** `hatch run` ensures the command uses the Python environment managed by `hatch` for your project, guaranteeing the correct versions of `chroma-mcp-server`, `chromadb`, and other dependencies are used.
- **Targeting:** Only the changed files are passed to the `index` command, making it efficient.

Now, every time you commit changes to tracked files in your repository, the hook will automatically update your specified ChromaDB collection.
