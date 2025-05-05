# tests/utils/test_chroma_client.py
import pytest
import os
from unittest.mock import patch, MagicMock
import numpy as np
from numpy.testing import assert_array_equal

# Assuming your project structure allows this import path
from src.chroma_mcp.utils.chroma_client import (
    get_embedding_function,
    KNOWN_EMBEDDING_FUNCTIONS,
    get_api_key,
    ONNXRUNTIME_AVAILABLE,
    SENTENCE_TRANSFORMER_AVAILABLE,
    OPENAI_AVAILABLE,
    COHERE_AVAILABLE,
    HF_API_AVAILABLE,
    VOYAGEAI_AVAILABLE,
    GENAI_AVAILABLE,
    BEDROCK_AVAILABLE,
    OLLAMA_AVAILABLE,
)
from src.chroma_mcp.utils.errors import EmbeddingError, INVALID_PARAMS, ErrorData, INTERNAL_ERROR
from mcp.shared.exceptions import McpError
from chromadb.utils import embedding_functions as ef
from src.chroma_mcp.utils import chroma_client  # Import the module itself

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
    with patch("src.chroma_mcp.utils.chroma_client.get_logger") as mock_get_logger:
        mock_log_instance = MagicMock()
        mock_get_logger.return_value = mock_log_instance
        yield mock_log_instance


@pytest.fixture
def mock_ef_dependencies():
    """Mock external embedding function dependencies."""
    # Mock base classes/functions from chromadb.utils.embedding_functions
    mocks = {
        "ef.DefaultEmbeddingFunction": MagicMock(spec=ef.DefaultEmbeddingFunction, autospec=True),
        "ef.ONNXMiniLM_L6_V2": MagicMock(spec=ef.ONNXMiniLM_L6_V2, autospec=True),
        "ef.OpenAIEmbeddingFunction": MagicMock(spec=ef.OpenAIEmbeddingFunction, autospec=True),
        "ef.CohereEmbeddingFunction": MagicMock(spec=ef.CohereEmbeddingFunction, autospec=True),
        "ef.HuggingFaceEmbeddingFunction": MagicMock(spec=ef.HuggingFaceEmbeddingFunction, autospec=True),
        "ef.VoyageAIEmbeddingFunction": MagicMock(spec=ef.VoyageAIEmbeddingFunction, autospec=True),
        "ef.GoogleGenerativeAiEmbeddingFunction": MagicMock(spec=ef.GoogleGenerativeAiEmbeddingFunction, autospec=True),
        "ef.AmazonBedrockEmbeddingFunction": MagicMock(spec=ef.AmazonBedrockEmbeddingFunction, autospec=True),
        "ef.OllamaEmbeddingFunction": MagicMock(spec=ef.OllamaEmbeddingFunction, autospec=True),
    }
    # Conditionally mock SentenceTransformerEmbeddingFunction
    if SentenceTransformerEmbeddingFunction:
        mocks["SentenceTransformerEmbeddingFunction"] = MagicMock(
            spec=SentenceTransformerEmbeddingFunction, autospec=True
        )
    else:
        # If not installed, ensure the test using it is skipped or handles the None case
        mocks["SentenceTransformerEmbeddingFunction"] = None

    # Mock google.generativeai if needed for Gemini tests
    if genai:
        mocks["genai"] = MagicMock(spec=genai)
        mocks["genai"].configure = MagicMock()
        mocks["genai"].embed_content = MagicMock(return_value={"embedding": [[0.1, 0.2]]})  # Example return
    else:
        mocks["genai"] = None

    # Create mock lambdas referencing the mocked classes
    mock_lambdas = {
        "default": lambda: mocks["ef.ONNXMiniLM_L6_V2"](),
        "fast": lambda: mocks["ef.ONNXMiniLM_L6_V2"](),
        "openai": lambda: mocks["ef.OpenAIEmbeddingFunction"](),
        "cohere": lambda: mocks["ef.CohereEmbeddingFunction"](),
        "huggingface": lambda: mocks["ef.HuggingFaceEmbeddingFunction"](),
        "voyageai": lambda: mocks["ef.VoyageAIEmbeddingFunction"](),
        "google": lambda: mocks["ef.GoogleGenerativeAiEmbeddingFunction"](),
        "bedrock": lambda: mocks["ef.AmazonBedrockEmbeddingFunction"](),
        "ollama": lambda: mocks["ef.OllamaEmbeddingFunction"](),
    }
    if mocks["SentenceTransformerEmbeddingFunction"]:
        mock_lambdas["accurate"] = lambda: mocks["SentenceTransformerEmbeddingFunction"]()

    # Apply patches
    # Patch the imported availability flags to True by default for fixture users
    # Tests checking False flags will patch them manually
    availability_patches = {
        "ONNXRUNTIME_AVAILABLE": True,
        "SENTENCE_TRANSFORMER_AVAILABLE": bool(SentenceTransformerEmbeddingFunction),
        "OPENAI_AVAILABLE": True,
        "COHERE_AVAILABLE": True,
        "HF_API_AVAILABLE": True,
        "VOYAGEAI_AVAILABLE": True,
        "GENAI_AVAILABLE": bool(genai),
        "BEDROCK_AVAILABLE": True,  # Assume available for tests using fixture
        "OLLAMA_AVAILABLE": True,  # Assume available for tests using fixture
    }

    # Patch the actual classes where they are imported/used
    # This is crucial if the availability flags somehow fail
    class_patches = {
        "ef": ef,  # Patch the module alias
        "SentenceTransformerEmbeddingFunction": mocks["SentenceTransformerEmbeddingFunction"],
        "genai": mocks["genai"],
        # Patch the classes directly within the chroma_client module context
        "ef.ONNXMiniLM_L6_V2": mocks["ef.ONNXMiniLM_L6_V2"],
        "ef.OpenAIEmbeddingFunction": mocks["ef.OpenAIEmbeddingFunction"],
        "ef.CohereEmbeddingFunction": mocks["ef.CohereEmbeddingFunction"],
        "ef.HuggingFaceEmbeddingFunction": mocks["ef.HuggingFaceEmbeddingFunction"],
        "ef.VoyageAIEmbeddingFunction": mocks["ef.VoyageAIEmbeddingFunction"],
        "ef.GoogleGenerativeAiEmbeddingFunction": mocks["ef.GoogleGenerativeAiEmbeddingFunction"],
        "ef.AmazonBedrockEmbeddingFunction": mocks["ef.AmazonBedrockEmbeddingFunction"],
        "ef.OllamaEmbeddingFunction": mocks["ef.OllamaEmbeddingFunction"],
    }

    with (
        patch.multiple("src.chroma_mcp.utils.chroma_client", **availability_patches, **class_patches, create=True),
        patch.dict("src.chroma_mcp.utils.chroma_client.KNOWN_EMBEDDING_FUNCTIONS", mock_lambdas, clear=True),
    ):
        yield mocks  # Yield the original class mocks for assertion checks


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
        ("voyageai", "ef.VoyageAIEmbeddingFunction"),
        pytest.param(
            "google",
            "ef.GoogleGenerativeAiEmbeddingFunction",
            marks=pytest.mark.skipif(not genai, reason="google-generativeai not installed"),
        ),
        pytest.param("bedrock", "ef.AmazonBedrockEmbeddingFunction"),
        pytest.param("ollama", "ef.OllamaEmbeddingFunction"),
    ],
)
def test_get_embedding_function_success(name, expected_type_mock_key, mock_ef_dependencies, mock_logger):
    """Test successful instantiation of known embedding functions when dependencies and keys are available."""
    mock_logger.reset_mock()
    instance_mock = mock_ef_dependencies[expected_type_mock_key]
    instance_mock.reset_mock()  # Reset call count etc. for the lambda's underlying mock

    # Mock API key retrieval to pass the pre-emptive check in get_embedding_function
    # Also mock Ollama URL getter for the 'ollama' case
    with (
        patch("src.chroma_mcp.utils.chroma_client.get_api_key", return_value="dummy_key") as mock_get_key,
        patch(
            "src.chroma_mcp.utils.chroma_client.get_ollama_base_url", return_value="http://mock-ollama:11434"
        ) as mock_get_ollama,
    ):
        embedding_function = get_embedding_function(name)

        # Assert the pre-emptive key check was called (or ollama url getter)
        if name in ["openai", "cohere", "huggingface", "voyageai", "google"]:
            mock_get_key.assert_called_with(name)
        elif name == "ollama":
            mock_get_ollama.assert_called_once()
        # Bedrock doesn't have an explicit check in get_embedding_function

        # Assert the correct mock lambda was called, returning the mocked instance
        assert embedding_function is instance_mock.return_value
        instance_mock.assert_called_once()  # Check the underlying class mock was instantiated via the lambda

        # Check logs
        mock_logger.info.assert_any_call(f"Instantiating embedding function: '{name.lower()}'")
        mock_logger.info.assert_any_call(f"Successfully instantiated embedding function: '{name.lower()}'")


def test_get_embedding_function_unknown_name(mock_logger):
    """Test requesting an unknown embedding function name."""
    unknown_name = "non_existent_ef"
    mock_logger.reset_mock()
    # Update expected message: Availability check fails first for unknown names
    expected_error_msg_part = (
        f"Dependency potentially missing for embedding function '{unknown_name}"  # Expect INTERNAL_ERROR message
    )

    with pytest.raises(McpError) as excinfo:
        # Assume availability flags don't include the unknown name
        get_embedding_function(unknown_name)

    # Check the specific error for unknown name (should be INTERNAL_ERROR from availability check)
    # Revert to checking the string representation
    assert expected_error_msg_part in str(excinfo.value)

    # Check logger was called before raising (should be the error from availability check)
    mock_logger.error.assert_any_call(
        f"Dependency potentially missing for embedding function '{unknown_name}'. Please ensure the required library is installed."
    )
    # This log won't happen now:
    # mock_logger.error.assert_any_call(f"Unknown embedding function name requested: '{unknown_name}' (Not found in registry even if available)")


# REMOVED @pytest.mark.usefixtures("mock_ef_dependencies") - Test API key failure directly
def test_get_embedding_function_instantiation_error_api_key(mock_logger):
    """Test McpError(INVALID_PARAMS) when API key is missing (pre-emptive check)."""
    ef_name = "openai"
    mock_logger.reset_mock()
    expected_error_msg_part = (
        f"Configuration error for embedding function '{ef_name}': API key for '{ef_name}' not found"
    )

    # Mock the registry to ensure the key exists, regardless of actual library install
    mock_registry = {"openai": MagicMock(name="MockOpenAIInstantiator")}

    # Ensure the availability flag is True, so the check proceeds
    with (
        patch.object(chroma_client, "OPENAI_AVAILABLE", True),
        patch.object(chroma_client, "KNOWN_EMBEDDING_FUNCTIONS", mock_registry),
        patch.object(chroma_client, "get_api_key", return_value=None) as mock_get_key,
    ):
        with pytest.raises(McpError) as excinfo:
            get_embedding_function(ef_name)

        # Assert get_api_key was called
        mock_get_key.assert_called_with(ef_name)

        # Assert the correct McpError is raised due to missing key
        # Revert to checking the string representation
        assert expected_error_msg_part in str(excinfo.value)

        # Check logger (get_embedding_function logs error before raising)
        # REMOVE check for the warning log inside the mocked get_api_key:
        # mock_logger.warning.assert_any_call(f"API key for {ef_name} not found in env var {ef_name.upper()}_API_KEY")
        mock_logger.error.assert_any_call(
            f"Configuration error instantiating '{ef_name}': API key for '{ef_name}' not found in environment variable.",
            exc_info=True,  # Check if exc_info is logged
        )


# This test needs the fixture to mock the lambda returning a faulty instance
@pytest.mark.usefixtures("mock_ef_dependencies")
def test_get_embedding_function_instantiation_error_value_error(mock_logger, mock_ef_dependencies):
    """Test McpError(INVALID_PARAMS) when the embedding function __init__ raises ValueError."""
    ef_name = "cohere"
    mock_logger.reset_mock()
    instance_mock = mock_ef_dependencies["ef.CohereEmbeddingFunction"]
    config_error_detail = "Invalid configuration in Cohere init"
    expected_error_msg_part = f"Configuration error for embedding function '{ef_name}': {config_error_detail}"

    # Mock the call to the mocked class instance to raise ValueError AFTER the API key check passes
    instance_mock.side_effect = ValueError(config_error_detail)

    # Patch get_api_key to return a dummy key so the pre-emptive check passes
    with patch("src.chroma_mcp.utils.chroma_client.get_api_key", return_value="dummy_key") as mock_get_key:
        with pytest.raises(McpError) as excinfo:
            # The fixture ensures COHERE_AVAILABLE=True and patches KNOWN_EMBEDDING_FUNCTIONS
            get_embedding_function(ef_name)

        # Check API key was checked
        mock_get_key.assert_called_with(ef_name)

        # Check the mocked class instantiation was attempted
        instance_mock.assert_called_once()

        # Assert the correct McpError is raised due to ValueError during instantiation
        # Revert to checking the string representation
        assert expected_error_msg_part in str(excinfo.value)

        # Check logger
        mock_logger.info.assert_any_call(f"Instantiating embedding function: '{ef_name}'")
        mock_logger.error.assert_any_call(
            f"Configuration error instantiating '{ef_name}': {config_error_detail}", exc_info=True
        )


# @pytest.mark.skipif(not SentenceTransformerEmbeddingFunction, reason="sentence-transformers not installed")
# Use fixture which handles skipif logic via parametrize/availability flags
@pytest.mark.usefixtures("mock_ef_dependencies")
def test_get_embedding_function_accurate_specifics(mock_ef_dependencies):
    """Test that 'accurate' uses SentenceTransformerEmbeddingFunction via the fixture."""
    if not SentenceTransformerEmbeddingFunction:
        pytest.skip("sentence-transformers not installed")

    # Reset mocks if needed (though fixture should handle setup)
    st_mock_instance = mock_ef_dependencies["SentenceTransformerEmbeddingFunction"]
    st_mock_instance.reset_mock()

    # Patch get_api_key just in case (though 'accurate' doesn't need one)
    with patch("src.chroma_mcp.utils.chroma_client.get_api_key", return_value="dummy_key"):
        ef_instance = get_embedding_function("accurate")

    # Assert the mock provided by the fixture was returned
    assert ef_instance is st_mock_instance.return_value
    # Assert the underlying mock class was called by the lambda
    st_mock_instance.assert_called_once()


# --- Specific Tests for ONNX Provider Logic ---


# REMOVED @pytest.mark.usefixtures("mock_ef_dependencies")
# Manually patch dependencies within the test
def test_get_embedding_function_onnx_gpu_available(mock_logger):
    """Test ONNX EF uses providers list when onnxruntime reports GPU."""
    mock_logger.reset_mock()
    # Patch the necessary components manually
    with (
        patch("src.chroma_mcp.utils.chroma_client.ef.ONNXMiniLM_L6_V2") as mock_onnx_class,
        patch("src.chroma_mcp.utils.chroma_client.onnxruntime") as mock_rt,
        patch("src.chroma_mcp.utils.chroma_client.ONNXRUNTIME_AVAILABLE", True),
    ):
        # Skip test if real onnxruntime is not installed (mock_rt will be None in patch)
        # This check might be redundant if ONNXRUNTIME_AVAILABLE is correctly False when not installed
        if mock_rt is None:
            pytest.skip("onnxruntime could not be patched, likely not installed")

        # Simulate GPU provider available
        gpu_providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        mock_rt.get_available_providers.return_value = gpu_providers

        # Call the function - the lambda inside KNOWN_EMBEDDING_FUNCTIONS will execute
        get_embedding_function("fast")  # or "default"

        # Assert the mocked CLASS was called with the correct providers by the lambda
        mock_onnx_class.assert_called_once_with(preferred_providers=gpu_providers)
        mock_logger.info.assert_any_call(f"Instantiating embedding function: 'fast'")
        mock_logger.info.assert_any_call(f"Successfully instantiated embedding function: 'fast'")


# REMOVED @pytest.mark.usefixtures("mock_ef_dependencies")
# Manually patch dependencies within the test
def test_get_embedding_function_onnx_cpu_only(mock_logger):
    """Test ONNX EF uses CPU provider when onnxruntime reports only CPU."""
    mock_logger.reset_mock()
    # Patch the necessary components manually
    with (
        patch("src.chroma_mcp.utils.chroma_client.ef.ONNXMiniLM_L6_V2") as mock_onnx_class,
        patch("src.chroma_mcp.utils.chroma_client.onnxruntime") as mock_rt,
        patch("src.chroma_mcp.utils.chroma_client.ONNXRUNTIME_AVAILABLE", True),
    ):
        if mock_rt is None:
            pytest.skip("onnxruntime could not be patched, likely not installed")

        # Simulate only CPU provider available
        cpu_providers = ["CPUExecutionProvider"]
        mock_rt.get_available_providers.return_value = cpu_providers

        # Call the function
        get_embedding_function("default")  # or "fast"

        # Assert the mocked CLASS was called with the correct providers by the lambda
        mock_onnx_class.assert_called_once_with(preferred_providers=cpu_providers)
        mock_logger.info.assert_any_call(f"Instantiating embedding function: 'default'")
        mock_logger.info.assert_any_call(f"Successfully instantiated embedding function: 'default'")


# REMOVED @pytest.mark.usefixtures("mock_ef_dependencies")
def test_get_embedding_function_onnx_runtime_missing(mock_logger):
    """Test McpError(INTERNAL_ERROR) when ONNXRUNTIME_AVAILABLE is False."""
    mock_logger.reset_mock()
    ef_name = "fast"  # or default
    expected_error_msg = f"Dependency potentially missing for embedding function '{ef_name}'. Please ensure the required library is installed."

    # Patch the flag directly
    # No need to patch the class as it shouldn't be called
    with patch("src.chroma_mcp.utils.chroma_client.ONNXRUNTIME_AVAILABLE", False):
        # Call the function and expect McpError due to availability check
        with pytest.raises(McpError) as excinfo:
            get_embedding_function(ef_name)

        # Assert the correct McpError is raised due to the flag being False
        # Revert to checking the string representation
        assert expected_error_msg in str(excinfo.value)

        # Check logger was called before raising
        mock_logger.error.assert_any_call(expected_error_msg)


# --- Tests for Missing Dependencies ---


# Use parametrize to test multiple unavailable functions
@pytest.mark.parametrize(
    "ef_name, availability_flag_path",
    [
        ("openai", "src.chroma_mcp.utils.chroma_client.OPENAI_AVAILABLE"),
        ("cohere", "src.chroma_mcp.utils.chroma_client.COHERE_AVAILABLE"),
        ("huggingface", "src.chroma_mcp.utils.chroma_client.HF_API_AVAILABLE"),
        ("voyageai", "src.chroma_mcp.utils.chroma_client.VOYAGEAI_AVAILABLE"),
        ("google", "src.chroma_mcp.utils.chroma_client.GENAI_AVAILABLE"),
        ("accurate", "src.chroma_mcp.utils.chroma_client.SENTENCE_TRANSFORMER_AVAILABLE"),
        ("bedrock", "src.chroma_mcp.utils.chroma_client.BEDROCK_AVAILABLE"),
        ("ollama", "src.chroma_mcp.utils.chroma_client.OLLAMA_AVAILABLE"),
        # ONNX/Default/Fast handled by ONNXRUNTIME_AVAILABLE flag
        ("default", "src.chroma_mcp.utils.chroma_client.ONNXRUNTIME_AVAILABLE"),
        ("fast", "src.chroma_mcp.utils.chroma_client.ONNXRUNTIME_AVAILABLE"),
    ],
)
def test_get_embedding_function_dependency_unavailable(mock_logger, ef_name, availability_flag_path):
    """Test McpError(INTERNAL_ERROR) when dependency availability flag is False."""
    # This test runs for each parameter set, so reset logger inside
    mock_logger.reset_mock()
    expected_error_msg = f"Dependency potentially missing for embedding function '{ef_name}'. Please ensure the required library is installed."

    # Patch the specific availability flag to False for this run
    with patch(availability_flag_path, False):
        # Call get_embedding_function and expect the pre-emptive check to fail
        with pytest.raises(McpError) as excinfo:
            get_embedding_function(ef_name)

    # Assert the correct McpError is raised due to the flag being False
    # Revert to checking the string representation
    assert expected_error_msg in str(excinfo.value)

    # Check logger was called before raising
    mock_logger.error.assert_any_call(expected_error_msg)


# --- End Tests ---
