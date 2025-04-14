"""
ChromaDB client utility module for managing client instances and configuration.
"""

import os
import platform
from typing import Optional, Union, Any, Dict, Callable
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings
from chromadb import EmbeddingFunction, Documents, Embeddings
from chromadb.utils import embedding_functions as ef

# Import sentence-transformers if available
try:
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    # No assert needed, import success is sufficient
    SENTENCE_TRANSFORMER_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMER_AVAILABLE = False

# Import google generativeai if available
try:
    import google.generativeai as genai

    # No assert needed, only check library import for custom class
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# Import OpenAI if available
try:
    import openai  # type: ignore

    # Verify if the specific class exists within chromadb utils
    assert hasattr(ef, "OpenAIEmbeddingFunction")
    OPENAI_AVAILABLE = True
except (ImportError, AssertionError):
    OPENAI_AVAILABLE = False

# Import Cohere if available
try:
    import cohere  # type: ignore

    assert hasattr(ef, "CohereEmbeddingFunction")
    COHERE_AVAILABLE = True
except (ImportError, AssertionError):
    COHERE_AVAILABLE = False

# Import Jina if available (check for client library)
try:
    import jina  # type: ignore

    assert hasattr(ef, "JinaEmbeddingFunction")
    JINA_AVAILABLE = True
except (ImportError, AssertionError):
    JINA_AVAILABLE = False

# Import VoyageAI if available
try:
    import voyageai  # type: ignore

    assert hasattr(ef, "VoyageAIEmbeddingFunction")
    VOYAGEAI_AVAILABLE = True
except (ImportError, AssertionError):
    VOYAGEAI_AVAILABLE = False

# Import HuggingFace API Embedding Function (check existence)
try:
    import huggingface_hub  # type: ignore

    assert hasattr(ef, "HuggingFaceEmbeddingFunction")
    HF_API_AVAILABLE = True
except AssertionError:
    HF_API_AVAILABLE = False

from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS

# Local application imports
# Import ChromaClientConfig from types
from ..types import ChromaClientConfig

# Import errors from siblings
from .errors import EmbeddingError, ConfigurationError

# Import loggers/config getters directly from parent utils package (__init__.py)
from . import get_logger, get_server_config

# --- Constants ---

# --- ADD ONNX Runtime Import --- >
try:
    import onnxruntime  # type: ignore

    ONNXRUNTIME_AVAILABLE = True
except ImportError:
    ONNXRUNTIME_AVAILABLE = False
# <--------------------------------

# --- Embedding Function Helper ---

# Module-level cache for the client ONLY
_chroma_client: Optional[Union[chromadb.PersistentClient, chromadb.HttpClient, chromadb.EphemeralClient]] = None

# --- Custom Embedding Functions ---


# Google Gemini Embedding Function
class GeminiEmbeddingFunction(EmbeddingFunction):
    """Custom Embedding Function for Google Gemini."""

    # Example: models/embedding-001
    # Models: textembedding-gecko@001, textembedding-gecko-multilingual@001, embedding-001
    # Task Types: RETRIEVAL_QUERY, RETRIEVAL_DOCUMENT, SEMANTIC_SIMILARITY, CLASSIFICATION, CLUSTERING
    def __init__(
        self, api_key: Optional[str] = None, model_name: str = "models/embedding-001", task_type="RETRIEVAL_DOCUMENT"
    ):
        if genai is None:
            raise ImportError("google.generativeai is not installed. Please install `pip install google-generativeai`")

        self._model_name = model_name
        self._task_type = task_type
        resolved_api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not resolved_api_key:
            raise ValueError(
                "Google API Key not provided via api_key parameter or GOOGLE_API_KEY environment variable."
            )
        genai.configure(api_key=resolved_api_key)

    def __call__(self, input: Documents) -> Embeddings:
        logger = get_logger("GeminiEmbeddingFunction")
        try:
            # Ensure the task type is valid before making the call
            valid_task_types = {
                "RETRIEVAL_QUERY",
                "RETRIEVAL_DOCUMENT",
                "SEMANTIC_SIMILARITY",
                "CLASSIFICATION",
                "CLUSTERING",
            }
            if self._task_type not in valid_task_types:
                logger.warning(
                    f"Invalid task_type '{self._task_type}', defaulting to 'RETRIEVAL_DOCUMENT'. Valid types: {valid_task_types}"
                )
                self._task_type = "RETRIEVAL_DOCUMENT"

            # Google AI API for embeddings
            # Handle potential batching limits if necessary, though the API might handle it.
            # For simplicity, embedding documents one by one if needed, but batch is preferred.
            # The current genai.embed_content seems to handle lists directly.
            logger.debug(
                f"Embedding {len(input)} documents using model {self._model_name} with task type {self._task_type}"
            )
            result = genai.embed_content(
                model=self._model_name, content=input, task_type=self._task_type
            )  # type: ignore
            embeddings = result["embedding"]
            logger.debug(f"Successfully received {len(embeddings)} embeddings.")
            return embeddings  # type: ignore
        except Exception as e:
            logger.error(f"Error calling Google Gemini embed_content API: {e}", exc_info=True)
            # Re-raise as a standard exception or a specific embedding error
            raise EmbeddingError(f"Google Gemini API error: {e}") from e


# --- Embedding Function Registry & Helpers ---


def get_api_key(service_name: str) -> Optional[str]:
    """Retrieve API key for a service from environment variables."""
    env_var_name = f"{service_name.upper()}_API_KEY"
    key = os.getenv(env_var_name)
    logger = get_logger("utils.chroma_client")
    if key:
        logger.debug(f"Found API key for {service_name} in env var {env_var_name}")
    else:
        logger.debug(f"API key for {service_name} not found in env var {env_var_name}")
    return key


# Registry mapping names to factory functions/classes
KNOWN_EMBEDDING_FUNCTIONS: Dict[str, Callable[[], EmbeddingFunction]] = {
    # --- Local CPU Options ---
    # Use ONNX Runtime providers for default/fast
    "default": lambda: ef.ONNXMiniLM_L6_V2(
        preferred_providers=(
            onnxruntime.get_available_providers()
            if ONNXRUNTIME_AVAILABLE and onnxruntime.get_available_providers()
            else ["CPUExecutionProvider"]  # Fallback if no providers or onnxruntime missing
        )
    ),
    "fast": lambda: ef.ONNXMiniLM_L6_V2(
        preferred_providers=(
            onnxruntime.get_available_providers()
            if ONNXRUNTIME_AVAILABLE and onnxruntime.get_available_providers()
            else ["CPUExecutionProvider"]  # Fallback if no providers or onnxruntime missing
        )
    ),
    # Accurate uses SentenceTransformer, relies on its internal device auto-detection (CUDA/MPS/CPU)
    **(
        {"accurate": lambda: SentenceTransformerEmbeddingFunction(model_name="all-mpnet-base-v2")}
        if SENTENCE_TRANSFORMER_AVAILABLE
        else {}
    ),
    # --- API-based Options ---
    # Conditionally add API-based providers
    **({"openai": lambda: ef.OpenAIEmbeddingFunction(api_key=get_api_key("openai"))} if OPENAI_AVAILABLE else {}),
    **({"cohere": lambda: ef.CohereEmbeddingFunction(api_key=get_api_key("cohere"))} if COHERE_AVAILABLE else {}),
    **(
        {
            "huggingface": lambda: ef.HuggingFaceEmbeddingFunction(  # Requires api_key and model_name
                api_key=get_api_key("huggingface"), model_name="sentence-transformers/all-MiniLM-L6-v2"  # Example model
            )
        }
        if HF_API_AVAILABLE
        else {}
    ),
    **({"jina": lambda: ef.JinaEmbeddingFunction(api_key=get_api_key("jina"))} if JINA_AVAILABLE else {}),
    **(
        {"voyageai": lambda: ef.VoyageAIEmbeddingFunction(api_key=get_api_key("voyageai"))}
        if VOYAGEAI_AVAILABLE
        else {}
    ),
    **({"gemini": lambda: GeminiEmbeddingFunction(api_key=get_api_key("google"))} if GENAI_AVAILABLE else {}),
}


def get_embedding_function(name: str) -> EmbeddingFunction:
    """
    Gets an instantiated embedding function by name from the registry.

    Args:
        name: The name of the embedding function (e.g., 'default', 'openai').

    Returns:
        An instance of the requested EmbeddingFunction.

    Raises:
        McpError: If the name is unknown or instantiation fails.
    """
    logger = get_logger("utils.chroma_client")
    normalized_name = name.lower()

    instantiator = KNOWN_EMBEDDING_FUNCTIONS.get(normalized_name)
    if not instantiator:
        logger.error(f"Unknown embedding function name requested: '{name}'")
        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Unknown embedding function: {name}"))

    try:
        logger.info(f"Instantiating embedding function: '{normalized_name}'")
        instance = instantiator()
        logger.info(f"Successfully instantiated embedding function: '{normalized_name}'")
        return instance
    except ImportError as e:
        logger.error(f"ImportError instantiating '{normalized_name}': {e}. Dependency likely missing.", exc_info=True)
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR, message=f"Dependency missing for embedding function '{normalized_name}': {e}"
            )
        ) from e
    except ValueError as e:
        # Catch ValueErrors often raised for missing API keys
        logger.error(f"Configuration error instantiating '{normalized_name}': {e}", exc_info=True)
        raise McpError(
            ErrorData(
                code=INVALID_PARAMS, message=f"Configuration error for embedding function '{normalized_name}': {e}"
            )
        ) from e
    except Exception as e:
        logger.error(f"Failed to instantiate embedding function '{normalized_name}': {e}", exc_info=True)
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message=f"Failed to create embedding function '{normalized_name}': {e}")
        ) from e


def get_chroma_client(
    config: Optional[ChromaClientConfig] = None,
) -> Union[chromadb.PersistentClient, chromadb.HttpClient, chromadb.EphemeralClient]:
    """Get or initialize the ChromaDB client based on configuration."""
    global _chroma_client

    # ADD logger assignment inside the function
    logger = get_logger("utils.chroma_client")

    # If client already exists, return it
    if _chroma_client is not None:
        return _chroma_client

    # If client doesn't exist, initialize it (should only happen once)
    if config is None:
        # Import getter locally within the function
        config = get_server_config()  # Get the config set during server startup

    # Ensure config is actually set (should be by server startup)
    if config is None:
        logger.critical("Chroma client configuration not found during initialization.")
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message="Chroma client configuration not found during initialization.")
        )

    # Create ChromaDB settings with telemetry disabled
    chroma_settings = Settings(
        # Opt out of telemetry (see https://docs.trychroma.com/docs/overview/telemetry)
        anonymized_telemetry=False,
        # Potentially add other settings here if needed, e.g., from config
    )

    # Validate configuration
    if config.client_type == "persistent" and not config.data_dir:
        raise ValueError("data_dir is required for persistent client")
    elif config.client_type == "http" and not config.host:
        raise ValueError("host is required for http client")

    try:
        logger.info(f"Initializing Chroma client (Type: {config.client_type})")
        if config.client_type == "persistent":
            _chroma_client = chromadb.PersistentClient(path=config.data_dir, settings=chroma_settings)
            logger.info(f"Persistent client initialized (Path: {config.data_dir})")
        elif config.client_type == "http":
            _chroma_client = chromadb.HttpClient(
                host=config.host,
                port=config.port,
                ssl=config.ssl,
                tenant=config.tenant,
                database=config.database,
                settings=chroma_settings
                # Note: API key might be handled separately or via headers
            )
            logger.info(f"HTTP client initialized (Host: {config.host}, Port: {config.port}, SSL: {config.ssl})")
        else:  # ephemeral
            _chroma_client = chromadb.EphemeralClient(settings=chroma_settings)
            logger.info("Ephemeral client initialized")

        return _chroma_client

    except Exception as e:
        error_msg = f"Failed to initialize ChromaDB client: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=error_msg))


def reset_client() -> None:
    """Reset the global client instance."""
    logger = get_logger("utils.chroma_client")
    logger.info("Resetting Chroma client instance.")
    global _chroma_client
    if _chroma_client is not None:
        try:
            _chroma_client.reset()
        except Exception as e:
            if "Resetting is not allowed" in str(e):
                logger.warning(f"Client reset failed gracefully (allow_reset=False): {e}")
            else:
                logger.error(f"Error resetting client: {e}")
        _chroma_client = None
        logger.info("Chroma client instance reset.")
    else:
        logger.info("No active Chroma client instance to reset.")
