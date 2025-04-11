# Chroma MCP Server API Reference

This document provides detailed information about the tools available in the Chroma MCP Server.

> **Note**: The Chroma MCP Server has been optimized with minimal dependencies. For full functionality including embedding models, install with `pip install chroma-mcp-server[full]`.

## Tool Categories

The Chroma MCP Server provides 26 tools across three categories:

1. [Collection Management Tools](#collection-management-tools)
2. [Document Operation Tools](#document-operation-tools)
3. [Sequential Thinking Tools](#sequential-thinking-tools)

---

## Collection Management Tools

### `chroma_create_collection`

Creates a new ChromaDB collection. It is **strongly recommended** to set all desired metadata, including custom keys, description, and specific HNSW parameters, using the `metadata` argument during this initial call, as modifying metadata after creation (especially settings) might be limited or impossible depending on the ChromaDB backend implementation.

#### Parameters for chroma_create_collection

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the collection to create |
| `metadata` | object | No | Dictionary containing initial collection metadata (including custom keys, description, and HNSW settings) |

#### Returns from chroma_create_collection

A JSON object containing basic collection information:

- `name`: Collection name
- `id`: Collection ID
- `metadata`: Initial collection metadata (containing default settings)

#### Example for chroma_create_collection

```json
{
  "collection_name": "my_documents",
  "metadata": {
    "description": "Documents related to project Alpha.",
    "settings": {
      "hnsw:space": "cosine",
      "hnsw:construction_ef": 128,
      "hnsw:search_ef": 64
    }
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

- `name`: Collection name
- `id`: Collection ID
- `metadata`: Current collection metadata (including description, settings, and custom keys)
- `count`: Number of documents in the collection
- `sample_entries`: Sample documents from the collection (result of `peek()`)

#### Example for chroma_get_collection

```json
{
  "collection_name": "my_documents"
}
```

### `chroma_rename_collection`

Renames an existing collection.

#### Parameters for chroma_rename_collection

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Current name of the collection |
| `new_name` | string | Yes | New name for the collection |

#### Returns from chroma_rename_collection

A JSON object containing the updated collection information (same as `chroma_get_collection` result, but under the new name).

#### Example for chroma_rename_collection

```json
{
  "collection_name": "my_documents",
  "new_name": "project_alpha_docs"
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

A JSON object containing the peek results:

- `peek_result`: The direct result from ChromaDB's `peek()` method (structure may vary).

#### Example for chroma_peek_collection

```json
{
  "collection_name": "my_documents",
  "limit": 5
}
```

---

## Document Operation Tools

### `chroma_add_document`

Add a document to a collection (auto-generates ID, no metadata).

#### Parameters for chroma_add_document

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the collection to add the document to. |
| `document` | string | Yes | The document content (string). |
| `increment_index` | boolean | No | Whether to immediately index the added document (default: False). |

#### Returns from chroma_add_document

A JSON object confirming the addition, potentially including the auto-generated ID.

```json
{
  "status": "success",
  "documents_added": 1
}
```

#### Example for chroma_add_document

```json
{
  "collection_name": "my_documents",
  "document": "This is a new document added via single-item tool."
}
```

### `chroma_add_document_with_id`

Add a document with a specified ID to a collection (no metadata).

#### Parameters for chroma_add_document_with_id

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the collection to add the document to. |
| `document` | string | Yes | The document content (string). |
| `id` | string | Yes | The unique ID for the document. |
| `increment_index` | boolean | No | Whether to immediately index the added document (default: False). |

#### Returns from chroma_add_document_with_id

A JSON object confirming the addition.

```json
{
  "status": "success",
  "documents_added": 1
}
```

#### Example for chroma_add_document_with_id

```json
{
  "collection_name": "my_documents",
  "document": "This document has a specific ID.",
  "id": "doc-manual-id-001"
}
```

### `chroma_add_document_with_metadata`

Add a document with specified metadata to a collection (auto-generates ID).

#### Parameters for chroma_add_document_with_metadata

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the collection to add the document to. |
| `document` | string | Yes | The document content (string). |
| `metadata` | string | Yes | Metadata JSON string for the document (e.g., '{"key": "value"}'). |
| `increment_index` | boolean | No | Whether to immediately index the added document (default: False). |

#### Returns from chroma_add_document_with_metadata

A JSON object confirming the addition, potentially including the auto-generated ID.

```json
{
  "status": "success",
  "documents_added": 1
}
```

#### Example for chroma_add_document_with_metadata

```json
{
  "collection_name": "my_documents",
  "document": "This document includes metadata.",
  "metadata": "{\"source\": \"api_ref\", \"status\": \"new\"}"
}
```

### `chroma_add_document_with_id_and_metadata`

Add a document with specified ID and metadata to a collection.

#### Parameters for chroma_add_document_with_id_and_metadata

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the collection to add the document to. |
| `document` | string | Yes | The document content (string). |
| `id` | string | Yes | The unique ID for the document. |
| `metadata` | string | Yes | Metadata JSON string for the document. |
| `increment_index` | boolean | No | Whether to immediately index the added document (default: False). |

#### Returns from chroma_add_document_with_id_and_metadata

A JSON object confirming the addition.

```json
{
  "status": "success",
  "documents_added": 1
}
```

#### Example for chroma_add_document_with_id_and_metadata

```json
{
  "collection_name": "my_documents",
  "document": "This document has ID and metadata.",
  "id": "doc-manual-id-002",
  "metadata": "{\"source\": \"api_ref\", \"status\": \"complete\"}"
}
```

### `chroma_query_documents`

Queries documents by semantic similarity.

**Client Limitation Note:** Some MCP clients may incorrectly serialize list parameters (`query_texts`, `include`) or optional parameters (`where`, `where_document`). If encountering validation errors, ensure lists are correctly formatted or try omitting optional parameters.

#### Parameters for chroma_query_documents

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the target collection |
| `query_texts` | array of strings | Yes | Query text strings |
| `n_results` | integer | No | Number of results per query (default: 10) |
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
  "where": {"source": "technical"},
  "include": ["documents", "metadatas", "distances"]
}
```

### `chroma_get_documents_by_ids`

Gets documents from a ChromaDB collection by specific IDs.

**Client Limitation Note:** Some MCP clients may incorrectly serialize list parameters (`ids`, `include`). If encountering validation errors, ensure lists are correctly formatted JSON arrays.

#### Parameters for chroma_get_documents_by_ids

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the collection |
| `ids` | array (string) | Yes | List of document IDs to retrieve |
| `include` | array (string) | No | Fields to include (e.g., `["documents", "metadatas"]`) |

#### Returns from chroma_get_documents_by_ids

A JSON object containing the matching documents and their data (or an empty list if not found).

#### Example for chroma_get_documents_by_ids

```json
{
  "collection_name": "my_documents",
  "ids": ["doc-manual-id-001", "doc-manual-id-002"],
  "include": ["documents", "metadatas"]
}
```

### `chroma_get_documents_with_where_filter`

Gets documents from a ChromaDB collection using a metadata filter.

**Client Limitation Note:** Some MCP clients may incorrectly serialize optional list parameters (`include`, `limit`, `offset`). If encountering validation errors, try omitting them.

#### Parameters for chroma_get_documents_with_where_filter

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the collection |
| `where` | object | Yes | Metadata filter (e.g., `{"source": "pdf"}`) |
| `limit` | integer | No | Maximum number of documents |
| `offset` | integer | No | Number of documents to skip |
| `include` | array (string) | No | Fields to include |

#### Returns from chroma_get_documents_with_where_filter

A JSON object containing the matching documents.

#### Example for chroma_get_documents_with_where_filter

```json
{
  "collection_name": "my_documents",
  "where": {"source": "api_ref"},
  "limit": 10,
  "include": ["documents", "metadatas"]
}
```

### `chroma_get_documents_with_document_filter`

Gets documents from a ChromaDB collection using a document content filter.

**Client Limitation Note:** Some MCP clients may incorrectly serialize optional list parameters (`include`, `limit`, `offset`). If encountering validation errors, try omitting them.

#### Parameters for chroma_get_documents_with_document_filter

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the collection |
| `where_document` | object | Yes | Document content filter (e.g., `{"$contains": "metadata"}`) |
| `limit` | integer | No | Maximum number of documents |
| `offset` | integer | No | Number of documents to skip |
| `include` | array (string) | No | Fields to include |

#### Returns from chroma_get_documents_with_document_filter

A JSON object containing the matching documents.

#### Example for chroma_get_documents_with_document_filter

```json
{
  "collection_name": "my_documents",
  "where_document": {"$contains": "specific ID"},
  "limit": 5,
  "include": ["documents"]
}
```

### `chroma_get_all_documents`

Gets all documents from a ChromaDB collection (use with caution on large collections).

**Client Limitation Note:** Some MCP clients may incorrectly serialize optional list parameters (`include`, `limit`, `offset`). If encountering validation errors, try omitting them.

#### Parameters for chroma_get_all_documents

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the collection |
| `limit` | integer | No | Maximum number of documents |
| `offset` | integer | No | Number of documents to skip |
| `include` | array (string) | No | Fields to include |

#### Returns from chroma_get_all_documents

A JSON object containing all documents (up to the limit).

#### Example for chroma_get_all_documents

```json
{
  "collection_name": "my_documents",
  "limit": 100,
  "include": ["ids", "metadatas"]
}
```

### `chroma_update_document_content`

Updates the content of an existing document by ID.

#### Parameters for chroma_update_document_content

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the collection containing the document. |
| `id` | string | Yes | The document ID to update. |
| `document` | string | Yes | The new document content. |

#### Returns from chroma_update_document_content

A JSON object confirming the update request.

```json
{
  "status": "success",
  "documents_updated_request": 1
}
```

#### Example for chroma_update_document_content

```json
{
  "collection_name": "my_documents",
  "id": "doc-manual-id-001",
  "document": "Updated content for this specific document."
}
```

### `chroma_update_document_metadata`

Updates the metadata of an existing document by ID.

#### Parameters for chroma_update_document_metadata

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the collection containing the document. |
| `id` | string | Yes | The document ID to update. |
| `metadata` | object | Yes | The new metadata dictionary (replaces existing metadata). |

#### Returns from chroma_update_document_metadata

A JSON object confirming the update request.

```json
{
  "status": "success",
  "documents_updated_request": 1
}
```

#### Example for chroma_update_document_metadata

```json
{
  "collection_name": "my_documents",
  "id": "doc-manual-id-002",
  "metadata": {
    "source": "api_ref",
    "status": "updated",
    "reviewed": true
  }
}
```

### `chroma_delete_document_by_id`

Delete a document from a collection by its specific ID.

#### Parameters for chroma_delete_document_by_id

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the collection to delete the document from. |
| `id` | string | Yes | The document ID to delete. |

#### Returns from chroma_delete_document_by_id

A JSON object confirming the delete request.

```json
{
  "status": "success",
  "documents_deleted_request": 1
}
```

#### Example for chroma_delete_document_by_id

```json
{
  "collection_name": "my_documents",
  "id": "doc-manual-id-001"
}
```

### `chroma_delete_documents_by_where_filter`

Deletes documents from a ChromaDB collection using a metadata filter.

#### Parameters for chroma_delete_documents_by_where_filter

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the collection |
| `where` | object | Yes | Metadata filter to select documents for deletion |

#### Returns from chroma_delete_documents_by_where_filter

A JSON object confirming the request and the filter used.

```json
{
  "status": "success",
  "filter_used": {"source": "obsolete"}
}
```

#### Example for chroma_delete_documents_by_where_filter

```json
{
  "collection_name": "my_documents",
  "where": {"status": "archived"}
}
```

### `chroma_delete_documents_by_document_filter`

Deletes documents from a ChromaDB collection using a document content filter.

#### Parameters for chroma_delete_documents_by_document_filter

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `collection_name` | string | Yes | Name of the collection |
| `where_document` | object | Yes | Document content filter for deletion |

#### Returns from chroma_delete_documents_by_document_filter

A JSON object confirming the request and the filter used.

```json
{
  "status": "success",
  "filter_used": {"$contains": "temporary"}
}
```

#### Example for chroma_delete_documents_by_document_filter

```json
{
  "collection_name": "my_documents",
  "where_document": {"$contains": "old project data"}
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
