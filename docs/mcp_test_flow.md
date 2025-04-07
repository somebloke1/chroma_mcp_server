# Chroma MCP Server - Test Flow Simulation

This document outlines a sequence of Model Context Protocol (MCP) tool calls to simulate a basic workflow and test the functionality of the `chroma-mcp-server`. This is useful for verifying that the server and its tools are operating correctly after setup or changes.

**Assumptions:**

* The `chroma-mcp-server` is running and accessible via the MCP client (e.g., through Cursor's `chroma_test` or `chroma` configuration).
* We are using the `mcp_chroma_test_` prefix for the tools as exposed in this environment.

## Test Sequence

### 1. Check Server Version

Verify the server is responding and get its version.

```tool_code
print(default_api.mcp_chroma_test_chroma_get_server_version(random_string="check"))
```

*Expected Outcome:* A JSON response containing the package name and installed version.

### 2. Create a New Collection

Let's create a collection to store test data.

```tool_code
print(default_api.mcp_chroma_test_chroma_create_collection(collection_name="mcp_flow_test_coll"))
```

*Expected Outcome:* Confirmation of creation with collection name, ID, and default metadata/settings.

### 3. List Collections

Verify the new collection appears in the list.

```tool_code
print(default_api.mcp_chroma_test_chroma_list_collections(name_contains="mcp_flow"))
```

*Expected Outcome:* A list including `"mcp_flow_test_coll"`.

### 4. Get Collection Details

Retrieve information about the newly created collection.

```tool_code
print(default_api.mcp_chroma_test_chroma_get_collection(collection_name="mcp_flow_test_coll"))
```

*Expected Outcome:* Details including name, ID, metadata, count (should be 0), and sample entries (should be empty).

### 5. Add Documents

Add some sample documents to the collection.

```tool_code
print(default_api.mcp_chroma_test_chroma_add_documents(
    collection_name="mcp_flow_test_coll",
    documents=[
        "This is the first test document.",
        "Here is another document for testing purposes.",
        "The quick brown fox jumps over the lazy dog."
    ],
    ids=["doc1", "doc2", "doc3"],
    metadatas=[
        {"source": "test_flow", "topic": "general"},
        {"source": "test_flow", "topic": "specific"},
        {"source": "test_flow", "topic": "pangram"}
    ]
))
```

*Expected Outcome:* Confirmation that 3 documents were added, along with their IDs.

### 6. Peek at Collection

Check the first few entries.

```tool_code
print(default_api.mcp_chroma_test_chroma_peek_collection(collection_name="mcp_flow_test_coll", limit=2))
```

*Expected Outcome:* The first 2 documents (`doc1`, `doc2`) and their data.

### 7. Query Documents

Perform a semantic search.

```tool_code
print(default_api.mcp_chroma_test_chroma_query_documents(
    collection_name="mcp_flow_test_coll",
    query_texts=["Tell me about test documents"],
    n_results=2
))
```

*Expected Outcome:* A list of results, likely including `doc1` and `doc2` with distances/similarities.

### 8. Get Specific Documents by ID

Retrieve documents using their IDs.

```tool_code
print(default_api.mcp_chroma_test_chroma_get_documents(
    collection_name="mcp_flow_test_coll",
    ids=["doc1", "doc3"]
))
```

*Expected Outcome:* Details for `doc1` and `doc3`.

### 9. Update Documents

Modify the content and metadata of an existing document.

```tool_code
print(default_api.mcp_chroma_test_chroma_update_documents(
    collection_name="mcp_flow_test_coll",
    ids=["doc2"],
    documents=["This is the updated second document."],
    metadatas=[{"source": "test_flow", "topic": "updated"}]
))
```

*Expected Outcome:* Confirmation that 1 document was updated.

### 10. Verify Update with Get

Retrieve the updated document to confirm changes.

```tool_code
print(default_api.mcp_chroma_test_chroma_get_documents(
    collection_name="mcp_flow_test_coll",
    ids=["doc2"]
))
```

*Expected Outcome:* Details for `doc2` showing the updated content and metadata.

### 11. Modify Collection Metadata

Add custom metadata to the collection itself.

```tool_code
print(default_api.mcp_chroma_test_chroma_update_collection_metadata(
    collection_name="mcp_flow_test_coll",
    metadata_update={"test_run": "flow_simulation", "status": "testing"}
))
```

*Expected Outcome:* Updated collection info showing the new metadata keys.

**Note:** This step will fail with a `ValidationError` if the collection was created with default immutable settings (e.g., `hnsw:` keys).

### 12. Set Collection Description

Add a description to the collection.

```tool_code
print(default_api.mcp_chroma_test_chroma_set_collection_description(
    collection_name="mcp_flow_test_coll",
    description="Collection used for the MCP test flow simulation."
))
```

*Expected Outcome:* Updated collection info showing the description in the metadata.

**Note:** This step will also fail with a `ValidationError` if the collection was created with default immutable settings.

### 13. Delete Documents by ID

Remove specific documents.

```tool_code
print(default_api.mcp_chroma_test_chroma_delete_documents(
    collection_name="mcp_flow_test_coll",
    ids=["doc1", "doc3"]
))
```

*Expected Outcome:* Confirmation that 2 documents were deleted, along with their IDs.

### 14. Verify Deletion with Get

Attempt to retrieve deleted documents (should fail or return empty).

```tool_code
print(default_api.mcp_chroma_test_chroma_get_documents(
    collection_name="mcp_flow_test_coll",
    ids=["doc1", "doc3"]
))
```

*Expected Outcome:* An empty list of documents.

### 15. Delete Collection

Clean up by deleting the test collection.

```tool_code
print(default_api.mcp_chroma_test_chroma_delete_collection(collection_name="mcp_flow_test_coll"))
```

*Expected Outcome:* Confirmation that the collection was deleted.

### 16. Verify Collection Deletion

Attempt to list the collection (should not be found).

```tool_code
print(default_api.mcp_chroma_test_chroma_list_collections(name_contains="mcp_flow_test_coll"))
```

*Expected Outcome:* An empty list of collection names.

---

This flow covers the primary CRUD (Create, Read, Update, Delete) operations for both collections and documents, providing a good baseline for testing the server's functionality.
