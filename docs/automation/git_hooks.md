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
3. **`.env` Configuration:** Your project needs a `.env` file at the root, configured for `chroma-mcp-client` to connect to your ChromaDB instance (persistent or http/cloud). See the [chroma-client documentation](../scripts/chroma-client.md) for `.env` setup details.
4. **Git Repository:** This setup assumes you are working within a Git repository.

## Setup Steps

1. **Navigate to your project's hooks directory:**

    ```bash
    cd your-project-root/.git/hooks
    ```

2. **Create the `post-commit` file:** Create a new file named `post-commit` (no extension) in this directory.
3. **Paste the script content:** Open the `post-commit` file in a text editor and paste the following script:

    ```bash
    #!/bin/sh
    # .git/hooks/post-commit

    echo "Running post-commit hook: Indexing changed files..."

    # Ensure we are in the project root
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    cd "$PROJECT_ROOT" || exit 1

    # Get list of changed/added Python files in the last commit
    # Use --diff-filter=AM to only get Added or Modified files
    FILES=$(git diff-tree --no-commit-id --name-only -r HEAD --diff-filter=AM -- "*.py" "*.md" "*.txt")

    if [ -z "$FILES" ]; then
      echo "No relevant files changed in this commit."
      exit 0
    fi

    echo "Files to index:"
    echo "$FILES"

    # Run the indexer using hatch (adjust log level as needed)
    # Use the full path to the file list to avoid issues
    # Convert FILES to an argument list
    FILES_ARGS=$(echo "$FILES" | tr '\n' ' ')

    # Run the client - use -vv for DEBUG level
    hatch run python -m chroma_mcp_client.cli -vv index $FILES_ARGS

    if [ $? -ne 0 ]; then
      echo "Error running chroma-client indexer!"
      exit 1
    fi

    echo "Post-commit indexing complete."
    exit 0
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
