# Chroma MCP Server API Reference

This document provides detailed information about the tools available in the Chroma MCP Server.

> **Note**: The Chroma MCP Server has been optimized with minimal dependencies. For full functionality including embedding models, install with `pip install chroma-mcp-server[full]`.

## Tool Categories

The Chroma MCP Server provides 15 tools across three categories:

1. [Collection Management Tools](#collection-management-tools)
2. [Document Operation Tools](#document-operation-tools)
3. [Sequential Thinking Tools](#sequential-thinking-tools)

---

## Collection Management Tools

### `chroma_create_collection`

Creates a new ChromaDB collection with specified parameters.

#### Parameters for chroma_create_collection

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the collection to create |
| `description` | string | No | Optional description of the collection |
| `metadata` | object | No | Additional metadata for the collection |
| `hnsw_space` | string | No | Distance function for HNSW index (e.g., 'cosine', 'l2', 'ip') |
| `hnsw_construction_ef` | integer | No | HNSW construction parameter |
| `hnsw_search_ef` | integer | No | HNSW search parameter |
| `hnsw_M` | integer | No | HNSW M parameter |

#### Returns from chroma_create_collection

A JSON object containing:

- `id`: Collection ID
- `name`: Collection name
- `metadata`: Collection metadata
- `created_at`: Creation timestamp

#### Example for chroma_create_collection

```json
{
  "collection_name": "my_documents",
  "description": "Collection for storing document embeddings",
  "metadata": {
    "project": "semantic_search",
    "version": "1.0.0"
  }
}
```

### `chroma_list_collections`

Lists all available collections with optional filtering and pagination.

#### Parameters for chroma_list_collections

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `limit` | integer | No | Maximum number of collections to return |
| `offset` | integer | No | Number of collections to skip |
| `name_contains` | string | No | Filter collections by name substring |

#### Returns from chroma_list_collections

A JSON object containing:

- `collections`: Array of collection objects
- `total_count`: Total number of collections matching criteria
- `limit`: Applied limit (if specified)
- `offset`: Applied offset (if specified)

#### Example for chroma_list_collections

```json
{
  "limit": 10,
  "offset": 0,
  "name_contains": "doc"
}
```

### `chroma_get_collection`

Gets detailed information about a specific collection.

#### Parameters for chroma_get_collection

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the collection |

#### Returns from chroma_get_collection

A JSON object containing collection details:

- `id`: Collection ID
- `name`: Collection name
- `metadata`: Collection metadata
- `count`: Number of documents in the collection
- `created_at`: Creation timestamp

#### Example for chroma_get_collection

```json
{
  "collection_name": "my_documents"
}
```

### `chroma_modify_collection`

Updates a collection's name or metadata.

#### Parameters for chroma_modify_collection

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Current collection name |
| `new_name` | string | No | New name for the collection |
| `new_metadata` | object | No | Updated metadata (will be merged with existing) |

#### Returns from chroma_modify_collection

A JSON object containing the updated collection details.

#### Example for chroma_modify_collection

```json
{
  "collection_name": "my_documents",
  "new_name": "important_documents",
  "new_metadata": {
    "status": "active",
    "last_updated": "2025-03-29"
  }
}
```

### `chroma_delete_collection`

Deletes a collection and all its documents.

#### Parameters for chroma_delete_collection

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the collection to delete |

#### Returns from chroma_delete_collection

A JSON object with the deletion status.

#### Example for chroma_delete_collection

```json
{
  "collection_name": "my_documents"
}
```

### `chroma_peek_collection`

Gets a sample of documents from a collection.

#### Parameters for chroma_peek_collection

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the collection |
| `limit` | integer | No | Maximum number of documents to return (default: 10) |

#### Returns from chroma_peek_collection

A JSON object containing sample documents and their metadata.

#### Example for chroma_peek_collection

```json
{
  "collection_name": "my_documents",
  "limit": 5
}
```

---

## Document Operation Tools

### `chroma_add_documents`

Adds documents to a collection, with optional metadata and IDs.

#### Parameters for chroma_add_documents

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the target collection |
| `documents` | array of strings | Yes | Document contents to add |
| `ids` | array of strings | No | Document IDs (auto-generated if not provided) |
| `metadatas` | array of objects | No | Metadata for each document |
| `increment_index` | boolean | No | Whether to increment index for auto-generated IDs (default: true) |

#### Returns from chroma_add_documents

A JSON object with operation status and IDs of the added documents.

#### Example for chroma_add_documents

```json
{
  "collection_name": "my_documents",
  "documents": [
    "This is the first document.",
    "This is the second document."
  ],
  "metadatas": [
    {"source": "user", "category": "notes"},
    {"source": "user", "category": "email"}
  ]
}
```

### `chroma_query_documents`

Queries documents by semantic similarity.

#### Parameters for chroma_query_documents

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the target collection |
| `query_texts` | array of strings | Yes | Query text strings |
| `n_results` | integer | No | Number of results per query (default: 5) |
| `where` | object | No | Metadata filters using Chroma's query operators |
| `where_document` | object | No | Document content filters |
| `include` | array of strings | No | What to include in response (e.g., "documents", "embeddings", "metadatas", "distances") |

#### Returns from chroma_query_documents

A JSON object containing query results organized by the query text.

#### Example for chroma_query_documents

```json
{
  "collection_name": "my_documents",
  "query_texts": ["How does vector search work?"],
  "n_results": 3,
  "where": {"category": "technical"},
  "include": ["documents", "metadatas", "distances"]
}
```

### `chroma_get_documents`

Gets documents from a collection with optional filtering.

#### Parameters for chroma_get_documents

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the target collection |
| `ids` | array of strings | No | Document IDs to retrieve |
| `where` | object | No | Metadata filters using Chroma's query operators |
| `where_document` | object | No | Document content filters |
| `limit` | integer | No | Maximum number of documents to return |
| `offset` | integer | No | Number of documents to skip |
| `include` | array of strings | No | What to include in response |

#### Returns from chroma_get_documents

A JSON object containing the matching documents and their metadata.

#### Example for chroma_get_documents

```json
{
  "collection_name": "my_documents",
  "where": {"category": "technical"},
  "limit": 10,
  "include": ["documents", "metadatas"]
}
```

### `chroma_update_documents`

Updates existing documents in a collection.

#### Parameters for chroma_update_documents

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the target collection |
| `ids` | array of strings | Yes | Document IDs to update |
| `documents` | array of strings | No | New document contents |
| `metadatas` | array of objects | No | New metadata dictionaries |

#### Returns from chroma_update_documents

A JSON object with update status.

#### Example for chroma_update_documents

```json
{
  "collection_name": "my_documents",
  "ids": ["doc1", "doc2"],
  "documents": ["Updated content 1", "Updated content 2"],
  "metadatas": [
    {"status": "updated", "timestamp": "2025-03-29"},
    {"status": "updated", "timestamp": "2025-03-29"}
  ]
}
```

### `chroma_delete_documents`

Deletes documents from a collection.

#### Parameters for chroma_delete_documents

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the target collection |
| `ids` | array of strings | Yes | Document IDs to delete |
| `where` | object | No | Metadata filters for deletion |
| `where_document` | object | No | Document content filters for deletion |

#### Returns from chroma_delete_documents

A JSON object with deletion status.

#### Example for chroma_delete_documents

```json
{
  "collection_name": "my_documents",
  "ids": ["doc1", "doc2", "doc3"]
}
```

---

## Sequential Thinking Tools

### `chroma_sequential_thinking`

Records a thought in a sequential thinking process.

#### Parameters for chroma_sequential_thinking

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `thought` | string | Yes | The current thought content |
| `thought_number` | integer | Yes | Position in the thought sequence (1-based) |
| `total_thoughts` | integer | Yes | Total expected thoughts in the sequence |
| `session_id` | string | No | Session identifier (generated if not provided) |
| `branch_from_thought` | integer | No | Thought number this branches from |
| `branch_id` | string | No | Branch identifier for parallel thought paths |
| `next_thought_needed` | boolean | No | Whether another thought is needed (default: false) |
| `custom_data` | object | No | Additional metadata |

#### Returns from chroma_sequential_thinking

A JSON object containing thought information and context.

#### Example for chroma_sequential_thinking

```json
{
  "thought": "The similarity search should use cosine distance for text embeddings",
  "thought_number": 2,
  "total_thoughts": 5,
  "session_id": "problem-solving-123",
  "custom_data": {
    "domain": "vector_search",
    "confidence": 0.85
  }
}
```

### `chroma_find_similar_thoughts`

Finds similar thoughts across all or specific thinking sessions.

#### Parameters for chroma_find_similar_thoughts

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `query` | string | Yes | The thought or concept to search for |
| `n_results` | integer | No | Number of similar thoughts to return (default: 5) |
| `threshold` | number | No | Similarity threshold (0-1, default: 0.75) |
| `session_id` | string | No | Optional session ID to limit search scope |
| `include_branches` | boolean | No | Whether to include thoughts from branch paths (default: true) |

#### Returns from chroma_find_similar_thoughts

A JSON object containing similar thoughts and their metadata.

#### Example for chroma_find_similar_thoughts

```json
{
  "query": "vector database optimization techniques",
  "n_results": 3,
  "threshold": 0.8
}
```

### `chroma_get_session_summary`

Gets a summary of all thoughts in a thinking session.

#### Parameters for chroma_get_session_summary

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `session_id` | string | Yes | The session identifier |
| `include_branches` | boolean | No | Whether to include branching thought paths (default: true) |

#### Returns from chroma_get_session_summary

A JSON object containing session thoughts and metadata.

#### Example for chroma_get_session_summary

```json
{
  "session_id": "problem-solving-123",
  "include_branches": true
}
```

### `chroma_find_similar_sessions`

Finds thinking sessions with similar content or patterns.

#### Parameters for chroma_find_similar_sessions

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `query` | string | Yes | The concept or pattern to search for |
| `n_results` | integer | No | Number of similar sessions to return (default: 3) |
| `threshold` | number | No | Similarity threshold (0-1, default: 0.75) |

#### Returns from chroma_find_similar_sessions

A JSON object containing similar sessions and their summaries.

#### Example for chroma_find_similar_sessions

```json
{
  "query": "problem solving for vector search optimization",
  "n_results": 5,
  "threshold": 0.7
}
```

---

## Error Handling

All tools follow a consistent error handling pattern. Errors will be returned with:

- An error code
- A descriptive message
- Additional details when available

Common error types:

| Error | Description |
|-------|-------------|
| `ValidationError` | Input validation failures |
| `CollectionNotFoundError` | Requested collection doesn't exist |
| `DocumentNotFoundError` | Requested document doesn't exist |
| `ChromaDBError` | Errors from the underlying ChromaDB |
| `McpError` | General MCP-related errors |
