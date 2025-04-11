# Chroma MCP Server - Test Flow Simulation

This document outlines a sequence of Model Context Protocol (MCP) tool calls to simulate a basic workflow and test the functionality of the `chroma-mcp-server`. This is useful for verifying that the server and its tools are operating correctly after setup or changes.

**Assumptions:**

- The `chroma-mcp-server` is running and accessible via the MCP client (e.g., through Cursor's `chroma_test` or `chroma` configuration).
- We are using the `mcp_chroma_test_` prefix for the tools as exposed in this environment.
- **Recent Refactoring:** Document `add`, `update`, and `delete` tools now operate on **single documents** to improve compatibility with certain clients/models. Query and Get operations still support multiple items/results.

**Error Handling Note:**

- All tool implementations now raise `mcp.shared.exceptions.McpError` on failure (e.g., validation errors, collection not found, ChromaDB errors). Expect error responses to be structured accordingly, rather than returning `isError=True`.

**Client-Side Limitations Note (Updated):**

- Testing has revealed that some MCP clients (including the one used in Cursor/VS Code during recent tests) may have **limitations in correctly serializing list parameters**, especially optional ones. This can also affect required list parameters used in **query and get** tool variants.
- Providing values for these lists through such clients may result in a **string representation** being sent to the server (e.g., `'["id1", "id2"]'`) instead of a proper JSON array, leading to server-side **Pydantic validation errors (`type=list_type, input_type=str`)**.
- **Workaround:** When using affected clients for **query/get** operations:
  - For *optional* lists, omit them and rely on defaults or alternative methods.
  - For *required* lists (e.g., `ids` in `get_documents_by_ids`), this workaround might not be possible, and these specific tool variants may be unusable with that client.
- **Single-item operations** (add, update, delete) should not be affected by this list issue.
- Steps in this flow relying on list parameters for *query/get* (Steps 7, 8, 10, 12, 12b) might fail or need skipping with affected clients.

## Test Sequence

### 1. Check Server Version

Verify the server is responding and get its version.

```tool_code
print(default_api.mcp_chroma_test_chroma_get_server_version(random_string="check"))
```

*Expected Outcome:* A JSON response containing the package name and installed version.

### 2. Create a New Collection

Let's create a collection to store test data using the basic tool.

```tool_code
print(default_api.mcp_chroma_test_chroma_create_collection(collection_name="mcp_flow_test_coll"))
```

*Expected Outcome:* Confirmation of creation with collection name, ID, and default metadata/settings. If the collection already exists, an `McpError` indicating this will be raised.

### 3. List Collections

Verify the new collection appears in the list.

```tool_code
print(default_api.mcp_chroma_test_chroma_list_collections())
```

**Note:** Due to potential client limitations with optional parameters, `name_contains` is omitted. Verify manually if needed.

*Expected Outcome:* A list including `"mcp_flow_test_coll"`.

### 4. Get Collection Details

Retrieve information about the newly created collection.

```tool_code
print(default_api.mcp_chroma_test_chroma_get_collection(collection_name="mcp_flow_test_coll"))
```

*Expected Outcome:* Details including name, ID, metadata, count (should be 0 initially), and sample entries (should be empty initially).

### 5. Add a Document (with Metadata as JSON String)

Add a sample document using the single-item tool that expects metadata as a JSON string.

```tool_code
print(default_api.mcp_chroma_test_chroma_add_document_with_metadata(
    collection_name="mcp_flow_test_coll",
    document="This is the first test document.",
    metadata='{"source": "test_flow", "topic": "general"}' # Single JSON string
    # increment_index is optional, defaults to False for single items
))
```

*Expected Outcome:* Confirmation that 1 document was added. The response might include the auto-generated ID if the tool implementation returns it (design choice). Let's assume we don't know the ID for now.

### 5b. Add Another Document (with ID)

Add another document, this time specifying an ID.

```tool_code
print(default_api.mcp_chroma_test_chroma_add_document_with_id(
    collection_name="mcp_flow_test_coll",
    document="Here is another document for testing purposes.",
    id="test-doc-2" # Parameter remains singular 'id' as per schema
))
```

*Expected Outcome:* Confirmation that 1 document was added with the specified ID.

### 5c. Add Third Document (with ID and Metadata)

Add a third document with both ID and metadata.

```tool_code
print(default_api.mcp_chroma_test_chroma_add_document_with_id_and_metadata(
    collection_name="mcp_flow_test_coll",
    document="The quick brown fox jumps over the lazy dog.",
    id="test-doc-pangram",
    metadata='{"source": "test_flow", "topic": "pangram"}'
))
```

*Expected Outcome:* Confirmation that 1 document was added with the specified ID and metadata.

### 6. Peek at Collection

Check the first few entries.

```tool_code
print(default_api.mcp_chroma_test_chroma_peek_collection(collection_name="mcp_flow_test_coll"))
```

**Note:** `limit` is omitted due to potential client issues.

*Expected Outcome:* A sample of documents (default limit is 10) including the ones we added (e.g., ID "test-doc-2", "test-doc-pangram", and one auto-generated ID).

### 7. Query Documents

Perform a semantic search. We'll use the basic query tool.

```tool_code
print(default_api.mcp_chroma_test_chroma_query_documents(
    collection_name="mcp_flow_test_coll",
    query_texts=["Tell me about test documents"], # Required list, should work
    # n_results is optional (defaults to 10), include is optional
))
```

**Note:** Optional parameters omitted due to potential client issues. Use specific variants for filtering if needed and if the client supports them.

*Expected Outcome (Client Limitation possible):* A list of results likely including relevant documents. May fail if client cannot handle `query_texts` list.

### 8. Get Specific Documents by ID

Retrieve documents using their known IDs. Use the specific `_by_ids` variant. **This step might fail with affected clients due to list handling.**

```tool_code
# Use the IDs we specified earlier.
print(default_api.mcp_chroma_test_chroma_get_documents_by_ids(
    collection_name="mcp_flow_test_coll",
    ids=["test-doc-2", "test-doc-pangram"] # Required list
    # include is optional
))
```

*Expected Outcome (in affected clients):* Likely failure due to client list handling.
*Expected Outcome (if successful):* JSON containing the requested documents "test-doc-2" and "test-doc-pangram".

### 9. Update Document Content

Modify a document's content using its ID. Use the single-item update tool.

```tool_code
# Use one of the known IDs.
print(default_api.mcp_chroma_test_chroma_update_document_content(
    collection_name="mcp_flow_test_coll",
    id="test-doc-2", # Single ID
    document="This document content has been updated." # Single document content
))
```

**Note:** To update metadata, use `mcp_chroma_test_chroma_update_document_metadata` (takes single `id` and `metadata` dict/JSON string).

*Expected Outcome:* Confirmation of update request for 1 document.

### 10. Verify Update with Get

Retrieve the updated document using its ID. **This step might fail with affected clients due to list handling.**

```tool_code
# Use the same ID used in Step 9.
print(default_api.mcp_chroma_test_chroma_get_documents_by_ids(
    collection_name="mcp_flow_test_coll",
    ids=["test-doc-2"] # Required list
))
```

*Expected Outcome (in affected clients):* Likely failure due to client list handling.
*Expected Outcome (if successful):* JSON containing the document with ID "test-doc-2" showing the updated content.

### 11. Delete Document by ID

Remove a specific document using its ID. Use the single-item delete tool.

```tool_code
# Use one of the known IDs.
print(default_api.mcp_chroma_test_chroma_delete_document_by_id(
    collection_name="mcp_flow_test_coll",
    id="test-doc-2" # Single ID
))
```

**Note:** Use filter variants (`