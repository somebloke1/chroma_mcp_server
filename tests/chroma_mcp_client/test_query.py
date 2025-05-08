import pytest
from unittest.mock import patch, MagicMock
import chromadb

# Module to test
from chroma_mcp_client.query import query_codebase, DEFAULT_CODEBASE_COLLECTION, DEFAULT_QUERY_N_RESULTS
from chromadb.api.models.Collection import Collection


# Mock Embedding Function
class MockEmbeddingFunction:
    def __call__(self, texts):
        # Dummy implementation, replace if needed
        return [[0.1] * len(texts)]


@pytest.fixture
def mock_chroma_client():
    client = MagicMock(spec=chromadb.ClientAPI)
    collection = MagicMock(spec=Collection)
    client.get_collection.return_value = collection
    return client, collection


def test_query_codebase_success(mock_chroma_client):
    """Test successful query to codebase collection."""
    client, collection = mock_chroma_client
    ef = MockEmbeddingFunction()
    query = ["find this code"]
    n_res = 3
    mock_results = {"ids": [["id1"]], "documents": [["doc1"]], "metadatas": [[{"path": "p"}]], "distances": [[0.1]]}
    collection.query.return_value = mock_results

    results = query_codebase(
        client=client, embedding_function=ef, query_texts=query, collection_name="test_code", n_results=n_res
    )

    client.get_collection.assert_called_once_with(name="test_code", embedding_function=ef)
    collection.query.assert_called_once_with(
        query_texts=query, n_results=n_res, include=["metadatas", "documents", "distances"]
    )
    assert results == mock_results


def test_query_codebase_defaults(mock_chroma_client):
    """Test query_codebase uses default collection name and n_results."""
    client, collection = mock_chroma_client
    ef = MockEmbeddingFunction()
    query = ["another query"]
    collection.query.return_value = {"ids": [[]]}  # Minimal valid return

    query_codebase(client=client, embedding_function=ef, query_texts=query)

    client.get_collection.assert_called_once_with(name=DEFAULT_CODEBASE_COLLECTION, embedding_function=ef)
    collection.query.assert_called_once_with(
        query_texts=query, n_results=DEFAULT_QUERY_N_RESULTS, include=["metadatas", "documents", "distances"]
    )


def test_query_codebase_get_collection_error(mock_chroma_client, caplog):
    """Test handling when get_collection fails."""
    client, _ = mock_chroma_client
    ef = MockEmbeddingFunction()
    query = ["query that fails"]
    client.get_collection.side_effect = Exception("Cannot connect")

    results = query_codebase(client=client, embedding_function=ef, query_texts=query)

    assert results is None
    assert "Failed to query collection" in caplog.text
    assert "Cannot connect" in caplog.text


def test_query_codebase_query_error(mock_chroma_client, caplog):
    """Test handling when collection.query fails."""
    client, collection = mock_chroma_client
    ef = MockEmbeddingFunction()
    query = ["query that fails query"]
    collection.query.side_effect = Exception("Query failed internally")

    results = query_codebase(client=client, embedding_function=ef, query_texts=query)

    assert results is None
    assert "Failed to query collection" in caplog.text
    assert "Query failed internally" in caplog.text
