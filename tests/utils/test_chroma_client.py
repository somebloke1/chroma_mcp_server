# tests/utils/test_chroma_client.py
import pytest
import os
from unittest.mock import patch, MagicMock

# Assuming your project structure allows this import path
from chroma_mcp.utils.chroma_client import (
    get_embedding_function,
    KNOWN_EMBEDDING_FUNCTIONS,
    GeminiEmbeddingFunction,
    get_api_key,
)
from chroma_mcp.utils.errors import EmbeddingError, INVALID_PARAMS, ErrorData
from mcp.shared.exceptions import McpError
from chromadb.utils import embedding_functions as ef

# Mock dependencies if they are not available in the test environment
try:
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
except ImportError:
    SentenceTransformerEmbeddingFunction = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# --- ADD Mock for onnxruntime ---
try:
    import onnxruntime
except ImportError:
    onnxruntime = None  # type: ignore


# --- Fixtures ---


@pytest.fixture(autouse=True)
def mock_logger():
    """Auto-mock the logger used within the utility functions."""
    with patch("chroma_mcp.utils.chroma_client.get_logger") as mock_get_logger:
        mock_log_instance = MagicMock()
        mock_get_logger.return_value = mock_log_instance
        yield mock_log_instance


@pytest.fixture
def mock_ef_dependencies():
    """Mock external embedding function dependencies and onnxruntime."""
    # Mock base classes/functions from chromadb.utils.embedding_functions
    mocks = {
        "ef.DefaultEmbeddingFunction": MagicMock(spec=ef.DefaultEmbeddingFunction),
        "ef.ONNXMiniLM_L6_V2": MagicMock(spec=ef.ONNXMiniLM_L6_V2),
        "ef.OpenAIEmbeddingFunction": MagicMock(spec=ef.OpenAIEmbeddingFunction),
        "ef.CohereEmbeddingFunction": MagicMock(spec=ef.CohereEmbeddingFunction),
        "ef.HuggingFaceEmbeddingFunction": MagicMock(spec=ef.HuggingFaceEmbeddingFunction),
        "ef.JinaEmbeddingFunction": MagicMock(spec=ef.JinaEmbeddingFunction),
        "ef.VoyageAIEmbeddingFunction": MagicMock(spec=ef.VoyageAIEmbeddingFunction),
    }
    # Conditionally mock SentenceTransformerEmbeddingFunction
    if SentenceTransformerEmbeddingFunction:
        mocks["SentenceTransformerEmbeddingFunction"] = MagicMock(spec=SentenceTransformerEmbeddingFunction)
    else:
        # If not installed, ensure the test using it is skipped or handles the None case
        mocks["SentenceTransformerEmbeddingFunction"] = None

    # Mock google.generativeai if needed for Gemini tests
    if genai:
        mocks["genai"] = MagicMock(spec=genai)
        # Mock configure and embed_content specifically if used directly
        mocks["genai"].configure = MagicMock()
        mocks["genai"].embed_content = MagicMock(return_value={"embedding": [[0.1, 0.2]]})  # Example return
    else:
        mocks["genai"] = None

    # --- ADD Mock for onnxruntime ---
    mock_onnxruntime = MagicMock(spec=onnxruntime) if onnxruntime else None
    if mock_onnxruntime:
        # Default mock providers
        mock_onnxruntime.get_available_providers.return_value = ["CPUExecutionProvider"]
        mocks["onnxruntime"] = mock_onnxruntime
    else:
        mocks["onnxruntime"] = None
    # <------------------------------

    # Apply patches using context managers
    with patch.multiple("chroma_mcp.utils.chroma_client", **mocks, create=True):
        # Patch the actual classes/modules where they are used if necessary
        # e.g., if KNOWN_EMBEDDING_FUNCTIONS references them directly
        # Put the patch.dict block back
        with patch.dict(
            "chroma_mcp.utils.chroma_client.KNOWN_EMBEDDING_FUNCTIONS",
            {
                "default": lambda: mocks["ef.ONNXMiniLM_L6_V2"](),
                "fast": lambda: mocks["ef.ONNXMiniLM_L6_V2"](),
                "accurate": (
                    lambda: mocks["SentenceTransformerEmbeddingFunction"]()
                    if mocks["SentenceTransformerEmbeddingFunction"]
                    else None
                ),
                "openai": lambda: mocks["ef.OpenAIEmbeddingFunction"](),
                "cohere": lambda: mocks["ef.CohereEmbeddingFunction"](),
                "huggingface": lambda: mocks["ef.HuggingFaceEmbeddingFunction"](),
                "jina": lambda: mocks["ef.JinaEmbeddingFunction"](),
                "voyageai": lambda: mocks["ef.VoyageAIEmbeddingFunction"](),
                "gemini": (
                    lambda: GeminiEmbeddingFunction() if mocks["genai"] else None
                ),  # Use real Gemini if genai mock exists
            },
            clear=True,  # Replace the dict entirely for the test
        ):
            yield mocks  # Yield from the nested patch.dict context


# --- Test Cases for get_api_key ---


@pytest.mark.parametrize(
    "service_name, env_var, env_value, expected_key",
    [
        ("openai", "OPENAI_API_KEY", "sk-123", "sk-123"),
        ("google", "GOOGLE_API_KEY", "gk-456", "gk-456"),
        ("cohere", "COHERE_API_KEY", None, None),
        ("HUGGINGFACE", "HUGGINGFACE_API_KEY", "hf-789", "hf-789"),
    ],
)
def test_get_api_key(monkeypatch, service_name, env_var, env_value, expected_key):
    """Test retrieving API keys from environment variables."""
    if env_value:
        monkeypatch.setenv(env_var, env_value)
    else:
        monkeypatch.delenv(env_var, raising=False)

    assert get_api_key(service_name) == expected_key


# --- Test Cases for get_embedding_function ---


@pytest.mark.usefixtures("mock_ef_dependencies")
@pytest.mark.parametrize(
    "name, expected_type_mock_key",
    [
        ("default", "ef.ONNXMiniLM_L6_V2"),
        ("fast", "ef.ONNXMiniLM_L6_V2"),
        pytest.param(
            "accurate",
            "SentenceTransformerEmbeddingFunction",
            marks=pytest.mark.skipif(
                not SentenceTransformerEmbeddingFunction, reason="sentence-transformers not installed"
            ),
        ),
        ("openai", "ef.OpenAIEmbeddingFunction"),
        ("cohere", "ef.CohereEmbeddingFunction"),
        ("huggingface", "ef.HuggingFaceEmbeddingFunction"),
        ("jina", "ef.JinaEmbeddingFunction"),
        ("voyageai", "ef.VoyageAIEmbeddingFunction"),
        pytest.param(
            "gemini", "genai", marks=pytest.mark.skipif(not genai, reason="google-generativeai not installed")
        ),  # Check against genai mock existing
    ],
)
def test_get_embedding_function_success(name, expected_type_mock_key, mock_ef_dependencies, mock_logger):
    """Test successful instantiation of known embedding functions."""
    # Clear mocks associated with the specific type before calling
    if expected_type_mock_key != "genai":  # Gemini uses the real class with mocked genai module
        instance_mock = mock_ef_dependencies[expected_type_mock_key]
        instance_mock.reset_mock()  # Reset call count etc.

    # Mock API key retrieval for API-based functions
    with patch("chroma_mcp.utils.chroma_client.get_api_key", return_value="dummy_key"):
        # --- ADD specific mock for os.getenv for Gemini --- >
        if name == "gemini":
            with patch("os.getenv", return_value="dummy_google_key") as mock_getenv:
                embedding_function = get_embedding_function(name)
                mock_getenv.assert_called_with("GOOGLE_API_KEY")  # Verify it checks the env var
        else:
            # <--------------------------------------------------
            embedding_function = get_embedding_function(name)

        # Assert the correct mock was called (or the Gemini class was instantiated)
        if name == "gemini":
            assert isinstance(embedding_function, GeminiEmbeddingFunction)
            # Check if genai.configure was called by GeminiEmbeddingFunction's init
            mock_ef_dependencies["genai"].configure.assert_called_once()
        elif name == "accurate":
            if SentenceTransformerEmbeddingFunction:  # Only assert if it should exist
                instance_mock.assert_called_once()
                assert embedding_function is not None  # Should not be None if ST installed
            else:
                # If ST not installed, 'accurate' shouldn't be in KNOWN_EMBEDDING_FUNCTIONS for the test
                with pytest.raises(McpError) as excinfo:
                    get_embedding_function(name)
                assert "Unknown embedding function: accurate" in str(excinfo.value)

        else:
            instance_mock.assert_called_once()  # Check the factory lambda was called

        # Check logs
        mock_logger.info.assert_any_call(f"Instantiating embedding function: '{name.lower()}'")
        mock_logger.info.assert_any_call(f"Successfully instantiated embedding function: '{name.lower()}'")


def test_get_embedding_function_unknown_name(mock_logger):
    """Test requesting an unknown embedding function name."""
    unknown_name = "non_existent_ef"
    with pytest.raises(McpError) as excinfo:
        get_embedding_function(unknown_name)

    # Check the string representation of the exception for the message
    assert f"Unknown embedding function: {unknown_name}" in str(excinfo.value)
    mock_logger.error.assert_called_once_with(f"Unknown embedding function name requested: '{unknown_name}'")


@pytest.mark.usefixtures("mock_ef_dependencies")
def test_get_embedding_function_instantiation_error(mock_logger):
    """Test handling of errors during embedding function instantiation (e.g., missing API key)."""
    # Simulate ValueError during instantiation (like missing API key)
    with patch.dict(
        "chroma_mcp.utils.chroma_client.KNOWN_EMBEDDING_FUNCTIONS",
        {"error_ef": lambda: ef.OpenAIEmbeddingFunction(api_key=None)},  # Simulate missing key error
        clear=True,
    ):
        # We need to patch the actual OpenAIEmbeddingFunction to raise the error
        with patch(
            "chromadb.utils.embedding_functions.OpenAIEmbeddingFunction.__init__",
            side_effect=ValueError("API key missing"),
        ):
            with pytest.raises(McpError) as excinfo:
                get_embedding_function("error_ef")

    # Revert to checking string representation
    assert "Configuration error for embedding function 'error_ef'" in str(excinfo.value)
    assert "API key missing" in str(excinfo.value)

    mock_logger.error.assert_called_with("Configuration error instantiating 'error_ef': API key missing", exc_info=True)


@pytest.mark.skipif(not SentenceTransformerEmbeddingFunction, reason="sentence-transformers not installed")
def test_get_embedding_function_accurate_specifics(mock_ef_dependencies):
    """Test that 'accurate' specifically calls SentenceTransformerEmbeddingFunction"""
    mock_st_ef = mock_ef_dependencies["SentenceTransformerEmbeddingFunction"]
    mock_st_ef.reset_mock()

    ef_instance = get_embedding_function("accurate")

    mock_st_ef.assert_called_once()
    # Check the model name passed during instantiation in the registry
    mock_st_ef.assert_called_with()  # The lambda calls it with default args
    # Check the actual instance returned is the mocked one
    assert ef_instance == mock_st_ef.return_value


# --- Specific Tests for ONNX Provider Logic ---


# REMOVE @pytest.mark.usefixtures("mock_ef_dependencies")
# Manually patch dependencies within the test
def test_get_embedding_function_onnx_gpu_available(mock_logger):
    """Test ONNX EF uses providers list when onnxruntime reports GPU."""

    # Patch the necessary components manually
    with patch("chroma_mcp.utils.chroma_client.ef.ONNXMiniLM_L6_V2") as mock_onnx_class, patch(
        "chroma_mcp.utils.chroma_client.onnxruntime"
    ) as mock_rt:
        # Skip test if real onnxruntime is not installed (mock_rt will be None)
        # This check might not be strictly necessary if the patch target exists, but good practice
        if mock_rt is None:
            pytest.skip("onnxruntime could not be patched, likely not installed")

        # Simulate GPU provider available
        gpu_providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        mock_rt.get_available_providers.return_value = gpu_providers

        # Call the function - this will use the original lambda from KNOWN_EMBEDDING_FUNCTIONS
        get_embedding_function("fast")

        # Assert the mocked CLASS was called with the correct args by the original lambda
        mock_onnx_class.assert_called_once_with(preferred_providers=gpu_providers)


# REMOVE @pytest.mark.usefixtures("mock_ef_dependencies")
# Manually patch dependencies within the test
def test_get_embedding_function_onnx_cpu_only(mock_logger):
    """Test ONNX EF uses CPU provider when onnxruntime reports only CPU."""

    # Patch the necessary components manually
    with patch("chroma_mcp.utils.chroma_client.ef.ONNXMiniLM_L6_V2") as mock_onnx_class, patch(
        "chroma_mcp.utils.chroma_client.onnxruntime"
    ) as mock_rt:
        # Skip test if real onnxruntime is not installed
        if mock_rt is None:
            pytest.skip("onnxruntime could not be patched, likely not installed")

        # Simulate only CPU provider available
        cpu_providers = ["CPUExecutionProvider"]
        mock_rt.get_available_providers.return_value = cpu_providers

        # Call the function - uses original lambda
        get_embedding_function("default")

        # Assert the mocked CLASS was called with the correct args by the original lambda
        mock_onnx_class.assert_called_once_with(preferred_providers=cpu_providers)


@pytest.mark.usefixtures("mock_ef_dependencies")
# This test checks the fallback when onnxruntime itself is missing, so it needs mock_ef_dependencies
def test_get_embedding_function_onnx_runtime_missing(mock_ef_dependencies, mock_logger):
    """Test ONNX EF falls back to CPU if onnxruntime is missing."""
    # mock_onnx = mock_ef_dependencies['ef.ONNXMiniLM_L6_V2']
    mock_rt = mock_ef_dependencies["onnxruntime"]
    if mock_rt:  # Skip if onnxruntime *is* available
        pytest.skip("onnxruntime is available, skipping missing test")

    # Test relies on ONNXRUNTIME_AVAILABLE being False in the source module
    # Patch __init__ directly for this test
    with patch("chroma_mcp.utils.chroma_client.ef.ONNXMiniLM_L6_V2.__init__", return_value=None) as mock_onnx_init:
        get_embedding_function("fast")

        # Assert the __init__ mock was called with the fallback CPU provider
        mock_onnx_init.assert_called_once_with(preferred_providers=["CPUExecutionProvider"])


# <------------------------------------------
