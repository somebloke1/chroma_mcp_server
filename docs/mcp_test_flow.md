# Chroma MCP Server - Test Flow Simulation

This document outlines a sequence of Model Context Protocol (MCP) tool calls to simulate a basic workflow and test the functionality of the `chroma-mcp-server`. This is useful for verifying that the server and its tools are operating correctly after setup or changes.

**Assumptions:**

- The `chroma-mcp-server` is running and accessible via the MCP client (e.g., through Cursor's `chroma_test` or `chroma` configuration).
- We are using the `mcp_chroma_test_` prefix for the tools as exposed in this environment.

**Error Handling Note:**

- All tool implementations now raise `mcp.shared.exceptions.McpError` on failure (e.g., validation errors, collection not found, ChromaDB errors). Expect error responses to be structured accordingly, rather than returning `isError=True`.

**Client-Side Limitations Note (Important):**

- Testing has revealed that some MCP clients (including the one used in Cursor/VS Code during recent tests) have **limitations in correctly serializing *optional* list parameters** (e.g., `ids`, `metadatas` in `add_documents`; `limit` in `peek_collection`; `ids`, `limit`, `offset`, `include` in `get_documents`; `documents`, `metadatas` in `update_documents`; `ids` in `delete_documents`).
- Providing values for these optional lists through such clients may result in a **string representation** being sent to the server (e.g., `'["id1", "id2"]'`) instead of a proper JSON array, leading to server-side **Pydantic validation errors (`type=list_type, input_type=str`)**.
- Required list parameters (like `query_texts` in `query_documents`) seem to be handled correctly by these clients.
- **Workaround:** When using affected clients, **omit the optional list parameters** and rely on default behaviors (e.g., auto-generated IDs, default limits) or alternative filtering methods (like `where` clauses if applicable).
- Steps in this flow that rely heavily on optional list parameters (Steps 8-12b) were likely **skipped** during recent testing due to these client limitations.

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

*Expected Outcome:* Confirmation of creation with collection name, ID, and default metadata/settings. If the collection already exists, an `McpError` indicating this will be raised.

### 3. List Collections

Verify the new collection appears in the list.

```tool_code
print(default_api.mcp_chroma_test_chroma_list_collections())
```

**Note for Cursor Testing:** Due to potential limitations in Cursor's MCP client handling of optional parameters for this tool, you might need to omit the `name_contains` parameter when running this step. The call should be `print(default_api.mcp_chroma_test_chroma_list_collections())`. You will need to manually verify the collection exists in the full list returned.

*Expected Outcome:* A list including `"mcp_flow_test_coll"`.

### 4. Get Collection Details

Retrieve information about the newly created collection.

```tool_code
print(default_api.mcp_chroma_test_chroma_get_collection(collection_name="mcp_flow_test_coll"))
```

*Expected Outcome:* Details including name, ID, metadata, count (should be 0 initially), and sample entries (should be empty initially). If the collection doesn't exist, an `McpError` will be raised.

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
    metadatas=[ # Optional: Provide metadata
        {"source": "test_flow", "topic": "general"},
        {"source": "test_flow", "topic": "specific"},
        {"source": "test_flow", "topic": "pangram"}
    ]
))
```

**Note on Optional Parameters:** Due to the client-side limitations mentioned above, it's recommended to **omit `ids` and `metadatas`** when using affected clients. ChromaDB will auto-generate IDs. Subsequent steps relying on specific IDs (`doc1`, `doc2`, `doc3`) will need adjustment or may be skipped.

*Expected Outcome:* Confirmation that documents were added. If `ids` were omitted, the response will include the auto-generated UUIDs.

### 6. Peek at Collection

Check the first few entries.

```tool_code
print(default_api.mcp_chroma_test_chroma_peek_collection(collection_name="mcp_flow_test_coll"))
```

**Note on Optional Parameters:** Due to client-side limitations, the `limit` parameter is omitted here to rely on the default. Previous issues involving NumPy array evaluation in the response processing for this tool have been resolved (as of v0.1.57+), requiring a server restart to load the fix if encountered.

*Expected Outcome:* A sample of documents (default limit) and their data. If the collection is empty or doesn't exist, the result might be empty or an `McpError` respectively.

### 7. Query Documents

Perform a semantic search.

```tool_code
print(default_api.mcp_chroma_test_chroma_query_documents(
    collection_name="mcp_flow_test_coll",
    query_texts=["Tell me about test documents"] # Required list, should work
))
```

**Note on Optional Parameters:** Due to client-side limitations, optional parameters like `n_results`, `where`, `where_document`, `include` are omitted here.

*Expected Outcome:* A list of results (default number), likely including documents similar to the query text, with distances/similarities.

### 8. Get Specific Documents by ID

Retrieve documents using their IDs.

```tool_code
# Adjust IDs if they were auto-generated in step 5
print(default_api.mcp_chroma_test_chroma_get_documents(
    collection_name="mcp_flow_test_coll"
))
```

*Expected Outcome (if run without `ids` or filters):* An `McpError` due to missing required filter (`ids`, `where`, or `where_document`).
*Expected Outcome (in affected clients):* This step is likely **skipped** as providing the optional `ids` list leads to validation errors.

### 9. Update Documents

Modify the content and metadata of an existing document.

```tool_code
# Adjust ID if it was auto-generated in step 5
print(default_api.mcp_chroma_test_chroma_update_documents(
    collection_name="mcp_flow_test_coll",
    ids=["some-auto-generated-id"] # Required list, but 'documents' and 'metadatas' are optional lists
))
```

*Expected Outcome (in affected clients):* This step is likely **skipped** or run without providing optional `documents`/`metadatas` due to client-side limitations with optional lists. If run only with `ids`, it might effectively do nothing if no other parameters are provided.

### 10. Verify Update with Get

Retrieve the updated document to confirm changes.

```tool_code
# Adjust ID if it was auto-generated in step 5
print(default_api.mcp_chroma_test_chroma_get_documents(
    collection_name="mcp_flow_test_coll"
))
```

*Expected Outcome (in affected clients):* This step is likely **skipped** due to the same reasons as Step 8.

### 11. Delete Documents by ID

Remove specific documents.

```tool_code
# Adjust IDs if they were auto-generated in step 5
print(default_api.mcp_chroma_test_chroma_delete_documents(
    collection_name="mcp_flow_test_coll"
))
```

*Expected Outcome (in affected clients):* This step is likely **skipped** as providing the optional `ids` list leads to validation errors. Deletion might be tested using `where` or `where_document` filters instead, or by deleting the whole collection (Step 13).

### 12. Verify Deletion with Get

Attempt to retrieve deleted documents (should fail or return empty).

```tool_code
# Adjust IDs if they were auto-generated in step 5
print(default_api.mcp_chroma_test_chroma_get_documents(
    collection_name="mcp_flow_test_coll"
))
```

*Expected Outcome (in affected clients):* This step is likely **skipped** due to the same reasons as Step 8.

### 12b. Attempt Get on Non-Existent Document

Attempt to retrieve a document ID that never existed.

```tool_code
print(default_api.mcp_chroma_test_chroma_get_documents(
    collection_name="mcp_flow_test_coll"
))
```

*Expected Outcome (in affected clients):* This step is likely **skipped** due to the same reasons as Step 8.

### 13. Delete Collection

Clean up by deleting the test collection.

```tool_code
print(default_api.mcp_chroma_test_chroma_delete_collection(collection_name="mcp_flow_test_coll"))
```

*Expected Outcome:* Confirmation that the collection was deleted. If it doesn't exist, an `McpError` will be raised.

### 14. Verify Collection Deletion

Attempt to list the collection (should not be found).

```tool_code
print(default_api.mcp_chroma_test_chroma_list_collections()) # Omit name_contains due to potential client issues
```

**Note on Optional Parameters:** See note in step 3 regarding potential need to omit `name_contains`. Verify manually that `mcp_flow_test_coll` is absent from the full list.

*Expected Outcome:* A list of collection names that does not include `mcp_flow_test_coll`.

---

This flow covers the primary CRUD (Create, Read, Update, Delete) operations for both collections and documents. However, due to observed client-side limitations with optional list parameters, exercising Update and Delete operations on specific document IDs may require workarounds or different client environments.
