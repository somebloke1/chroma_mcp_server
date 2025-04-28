import time
import sys
import hashlib
import subprocess
import logging
from pathlib import Path
from typing import Set

from .connection import get_client_and_ef

# Configure logging for this module
logger = logging.getLogger(__name__)

# Define supported file types (can be extended)
DEFAULT_SUPPORTED_SUFFIXES: Set[str] = {
    ".py", ".ts", ".js", ".go", ".java", ".md", ".txt", ".sh",
    ".yaml", ".json", ".h", ".c", ".cpp", ".cs", ".rb", ".php", ".toml",
    ".ini", ".cfg", ".sql", ".dockerfile", "Dockerfile", ".env"
}

# Default collection name (consider making this configurable)
DEFAULT_COLLECTION_NAME = "codebase_v1"

def index_file(
    file_path: Path,
    repo_root: Path,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    supported_suffixes: Set[str] = DEFAULT_SUPPORTED_SUFFIXES,
) -> bool:
    """Reads, embeds, and upserts a single file into the specified ChromaDB collection.

    Args:
        file_path: Absolute path to the file.
        repo_root: Absolute path to the repository root (for relative path metadata).
        collection_name: Name of the ChromaDB collection.
        supported_suffixes: Set of file extensions to index.

    Returns:
        True if the file was indexed successfully, False otherwise.
    """
    client, embedding_func = get_client_and_ef() # Gets client/EF from connection module

    if not file_path.exists() or file_path.is_dir():
        logger.debug(f"Skipping non-existent or directory: {file_path}")
        return False

    # Check suffix case-insensitively
    if file_path.suffix.lower() not in supported_suffixes:
        logger.debug(f"Skipping unsupported file type: {file_path.suffix}")
        return False

    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        if not content.strip():
            logger.info(f"Skipping empty file: {file_path}")
            return False

        # Use relative path for ID generation and metadata
        relative_path = str(file_path.relative_to(repo_root))
        # Generate a stable ID based on the relative path
        doc_id = hashlib.sha1(relative_path.encode('utf-8')).hexdigest()
        metadata = {
            "path": relative_path,
            "last_indexed_utc": time.time(), # Store as UTC timestamp
            "filename": file_path.name,
        }

        # Get or create the collection
        # Note: get_or_create_collection might be expensive if called repeatedly
        # Consider getting it once outside the loop if indexing many files.
        collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_func # Pass EF if not default
        )

        # Upsert the document (adds or updates)
        # Note: ChromaDB handles embedding generation internally if EF is set on collection
        collection.upsert(
            ids=[doc_id],
            metadatas=[metadata],
            documents=[content] # Provide document content
        )
        logger.info(f"Indexed: {relative_path}")
        return True

    except Exception as e:
        logger.error(f"Error indexing {file_path}: {e}", exc_info=True)
        return False

def index_git_files(
    repo_root: Path,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    supported_suffixes: Set[str] = DEFAULT_SUPPORTED_SUFFIXES,
) -> int:
    """Indexes all files tracked by Git within the repository root.

    Args:
        repo_root: Absolute path to the repository root.
        collection_name: Name of the ChromaDB collection.
        supported_suffixes: Set of file extensions to index.

    Returns:
        The number of files successfully indexed.
    """
    logger.info(f"Indexing all tracked git files in {repo_root}...")
    indexed_count = 0
    try:
        # Use 'git ls-files -z' for safer handling of filenames with spaces/special chars
        cmd = ["git", "-C", str(repo_root), "ls-files", "-z"]
        result = subprocess.run(cmd, capture_output=True, check=True, encoding='utf-8')

        # Split by null character
        files_to_index = [repo_root / f for f in result.stdout.strip('\0').split('\0') if f]
        logger.info(f"Found {len(files_to_index)} files tracked by git.")

        # Consider getting the collection once before the loop for efficiency
        # client, _ = get_client_and_ef()
        # collection = client.get_or_create_collection(name=collection_name, ...)

        for file_path in files_to_index:
            if index_file(file_path, repo_root, collection_name, supported_suffixes):
                indexed_count += 1

        logger.info(f"Successfully indexed {indexed_count} out of {len(files_to_index)} tracked files.")
        return indexed_count

    except FileNotFoundError:
        logger.error(f"'git' command not found. Ensure Git is installed and in PATH.")
        return 0
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running 'git ls-files' in {repo_root}: {e}")
        logger.error(f"Git stderr: {e.stderr}")
        return 0
    except Exception as e:
        logger.error(f"An unexpected error occurred during git file indexing: {e}", exc_info=True)
        return 0
