# Chroma MCP Server - Test Flow Simulation

This document outlines a sequence of Model Context Protocol (MCP) tool calls to simulate a basic workflow and test the functionality of the `chroma-mcp-server`. This is useful for verifying that the server and its tools are operating correctly after setup or changes.

**Assumptions:**

- The `chroma-mcp-server` is running and accessible via the MCP client (e.g., through Cursor's `chroma_test` or `chroma` configuration).
- **Embedding Function:** The server uses an embedding function (configured via `--embedding-function` CLI arg or `CHROMA_EMBEDDING_FUNCTION` env var, defaulting to `all-MiniLM-L6-v2`). The specific function used can slightly affect the results of semantic searches (query/find_similar operations).
- We are using the `mcp_chroma_test_` prefix for the tools as exposed in this environment.
- **Recent Refactoring:** Document `add`, `update`, and `delete` tools now operate on **single documents** to improve compatibility with certain clients/models. Query and Get operations still support multiple items/results.

**Error Handling Note:**

- All tool implementations now raise `mcp.shared.exceptions.McpError` on failure (e.g., validation errors, collection not found, ChromaDB errors). Expect error responses to be structured accordingly, rather than returning `isError=True`.

**Client-Side/Framework Limitations Note (Important):**

- Testing has revealed that some MCP clients or the framework layer (particularly the test harness) might have limitations in correctly serializing or interpreting tool parameters, especially lists or values **explicitly provided** for parameters that were originally designed as optional.
- Specifically:
  - **Formerly Optional Parameters:** Providing values for parameters like `limit`, `offset`, `n_results`, `session_id`, `branch_id`, `threshold`, `increment_index` in a test tool call can lead to errors like `Parameter '...' must be of type undefined, got number/string`. The framework layer seems to misinterpret the argument *before* it reaches Python/Pydantic validation.
  - **List Parameters:** Required list parameters like `ids` or `query_texts` may be incorrectly serialized as strings by some clients (e.g., `'["id1", "id2"]'`) instead of proper JSON arrays, causing Pydantic validation errors on the server.
- **Workarounds (Mainly for Test Environment):**
  - **Omit formerly optional parameters** (`limit`, `offset`, `n_results`, `session_id`, `branch_id`, `threshold`, `increment_index`) in tool calls whenever possible, especially in the test harness. Rely on the default values defined in the implementation (e.g., `limit=0`, `offset=0`, `n_results=10`, `session_id=""`, `threshold=-1.0`, `increment_index=True`). The implementation code handles these defaults correctly.
  - For specifying included fields in `get` operations, use the dedicated tool variants (`chroma_get_documents_by_ids_embeddings`, `chroma_get_documents_by_ids_all`). Base tools now always use ChromaDB defaults.
  - **JSON String Parameters:** Ensure `metadata`, `where`, `where_document` are passed as valid **JSON strings** (e.g., `'{"key": "value"}'`). Do not pass Python dictionaries directly for these.
  - Required lists (`ids`, `query_texts`) remain potentially susceptible to client-side list serialization bugs, which might make tools requiring them unusable with certain clients.
- Single-item operations (add, update, delete) and simple *required* string/boolean parameters are generally unaffected by these issues.

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

### 2b. Create Collection with Metadata

Create a second collection, this time specifying metadata upfront.

```tool_code
print(default_api.mcp_chroma_test_chroma_create_collection_with_metadata(
    collection_name="mcp_flow_test_coll_meta",
    metadata='{"description": "Collection for metadata tests", "topic": "testing"}'
))
```

*Expected Outcome:* Confirmation of creation with the specified metadata.

### 2c. Rename Collection

Rename the second collection.

```tool_code
print(default_api.mcp_chroma_test_chroma_rename_collection(
    collection_name="mcp_flow_test_coll_meta",
    new_name="mcp_flow_test_coll_renamed"
))
```

*Expected Outcome:* Confirmation of rename.

### 3. List Collections

Verify the new collection appears in the list.

```tool_code
print(default_api.mcp_chroma_test_chroma_list_collections())
```

**Note:** Due to potential client limitations with optional parameters, `name_contains` is omitted. Verify manually if needed.

*Expected Outcome:* A list including `"mcp_flow_test_coll"` and `"mcp_flow_test_coll_renamed"`.

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

### 5d. Add Document (Basic)

Add a basic document without specifying ID or metadata to the first collection.

```tool_code
print(default_api.mcp_chroma_test_chroma_add_document(
    collection_name="mcp_flow_test_coll",
    document="This is a basic document with no extra info."
))
```

*Expected Outcome:* Confirmation that 1 document was added (response might include the generated ID).

### 6. Peek at Collection

Check the first few entries.

```tool_code
print(default_api.mcp_chroma_test_chroma_peek_collection(collection_name="mcp_flow_test_coll"))
```

**Note:** `limit` is omitted due to potential client issues.

*Expected Outcome:* A sample of documents (default limit is 10) including the ones we added (e.g., ID "test-doc-2", "test-doc-pangram", and one auto-generated ID).

### 6b. Get All Documents

Retrieve all documents from the first collection (respecting potential default limits).

```tool_code
print(default_api.mcp_chroma_test_chroma_get_all_documents(collection_name="mcp_flow_test_coll"))
```

*Expected Outcome:* A list containing all documents currently in `mcp_flow_test_coll`.

### 7. Query Documents

Perform a semantic search. We'll use the basic query tool.

**Note:** The quality and specific ranking of results depend on the chosen embedding function.

```tool_code
print(default_api.mcp_chroma_test_chroma_query_documents(
    collection_name="mcp_flow_test_coll",
    query_texts=["Tell me about test documents"], # Required list, should work
    # n_results is optional (defaults to 10), include is optional
))
```

**Note:** Optional parameters omitted due to potential client issues. Use specific variants for filtering if needed and if the client supports them.

*Expected Outcome (Client Limitation possible):* A list of results likely including relevant documents. May fail if client cannot handle `query_texts` list.

### 7b. Query with Metadata Filter (`where`)

Perform a query filtering by metadata.

```tool_code
print(default_api.mcp_chroma_test_chroma_query_documents_with_where_filter(
    collection_name="mcp_flow_test_coll",
    query_texts=["Tell me about pangrams"],
    where='{"topic": "pangram"}' # Filter for topic as JSON string
))
```

*Expected Outcome:* Results containing the "pangram" document.

### 7c. Query with Document Filter (`where_document`)

Perform a query filtering by document content.

```tool_code
print(default_api.mcp_chroma_test_chroma_query_documents_with_document_filter(
    collection_name="mcp_flow_test_coll",
    query_texts=["Tell me about general test documents"],
    where_document='{"$contains": "first test"}' # Filter for content as JSON string
))
```

*Expected Outcome:* Results containing the document with "first test" in its content.

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

### 8b. Get Documents with Metadata Filter (`where`)

Retrieve documents filtering by metadata.

```tool_code
print(default_api.mcp_chroma_test_chroma_get_documents_with_where_filter(
    collection_name="mcp_flow_test_coll",
    where='{"source": "test_flow"}' # Filter for source as JSON string
))
```

*Expected Outcome:* Documents matching the `source` metadata.

### 8c. Get Documents with Document Filter (`where_document`)

Retrieve documents filtering by content.

```tool_code
print(default_api.mcp_chroma_test_chroma_get_documents_with_document_filter(
    collection_name="mcp_flow_test_coll",
    where_document='{"$contains": "basic document"}' # Filter for content as JSON string
))
```

*Expected Outcome:* Documents containing "basic document".

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

### 9b. Update Document Metadata

Update the metadata of a document.

```tool_code
print(default_api.mcp_chroma_test_chroma_update_document_metadata(
    collection_name="mcp_flow_test_coll",
    id="test-doc-pangram",
    metadata='{"source": "test_flow_updated", "topic": "pangram", "status": "updated"}' # New metadata as JSON string
))
```

*Expected Outcome:* Confirmation of metadata update request.

### 10. Verify Update with Get (All Data)

Retrieve the updated documents using their IDs and the "all" variant tool to see the changes. **Required `ids` list might still fail with affected clients.**

```tool_code
# Use the same IDs used in Step 9/9b.
print(default_api.mcp_chroma_test_chroma_get_documents_by_ids_all(
    collection_name="mcp_flow_test_coll",
    ids=["test-doc-2", "test-doc-pangram"] # Required list
))
```

*Expected Outcome (in affected clients):* Likely failure due to client list handling.
*Expected Outcome (if successful):* JSON containing `ids`, `documents`, `metadatas`, `embeddings` for the requested documents, showing the updated content for `test-doc-2` and updated metadata for `test-doc-pangram`. May raise an `McpError` with code `INVALID_PARAMS` if the collection doesn't support loading URIs/data.

### 11. Delete Document by ID

Remove a specific document using its ID. Use the single-item delete tool.

```tool_code
# Use one of the known IDs.
print(default_api.mcp_chroma_test_chroma_delete_document_by_id(
    collection_name="mcp_flow_test_coll",
    id="test-doc-2" # Single ID
))
```

**Note:** Use filter variants (`delete_documents_by_where_filter`, `delete_documents_by_document_filter`) for bulk deletion based on criteria.

*Expected Outcome:* Confirmation of delete request for 1 document.

### 12. Verify Deletion with Get

Attempt to retrieve the deleted document. **This step might fail with affected clients due to list handling.**

```tool_code
# Use the same ID used in Step 11.
print(default_api.mcp_chroma_test_chroma_get_documents_by_ids(
    collection_name="mcp_flow_test_coll",
    ids=["test-doc-2"] # Required list
))
```

*Expected Outcome (in affected clients):* Likely failure due to client list handling.
*Expected Outcome (if successful):* JSON response indicating the document with ID "test-doc-2" was not found (e.g., empty result or specific error).

### 12b. Attempt Get on Non-Existent Document

Attempt to retrieve a document ID that never existed. **This step might fail with affected clients due to list handling.**

```tool_code
print(default_api.mcp_chroma_test_chroma_get_documents_by_ids(
    collection_name="mcp_flow_test_coll",
    ids=["this-id-never-existed"] # Required list
))
```

*Expected Outcome (in affected clients):* Likely failure due to client list handling.
*Expected Outcome (if successful):* JSON response indicating document not found.

### 13. Delete Remaining Documents (`test-doc-pangram`, generated IDs)

Delete the other known documents from the first collection.

```tool_code
# First, delete the pangram doc
print(default_api.mcp_chroma_test_chroma_delete_document_by_id(
    collection_name="mcp_flow_test_coll",
    id="test-doc-pangram" # Single ID
))

# Need to retrieve IDs of auto-generated docs to delete them
# For this example, we'll assume we know one from a peek/get_all result
# Replace 'generated-doc-id-1' with an actual ID obtained from Step 6b
# print(default_api.mcp_chroma_test_chroma_delete_document_by_id(
#     collection_name="mcp_flow_test_coll",
#     id="generated-doc-id-1"
# ))
# print(default_api.mcp_chroma_test_chroma_delete_document_by_id(
#     collection_name="mcp_flow_test_coll",
#     id="generated-doc-id-2"
# ))
```

*Expected Outcome:* Confirmation of delete requests. *Note: Manual step needed to get generated IDs for full cleanup in a real run.*

### 14. Delete First Collection (`mcp_flow_test_coll`)

Clean up by deleting the first test collection.

```tool_code
print(default_api.mcp_chroma_test_chroma_delete_collection(collection_name="mcp_flow_test_coll"))
```

*Expected Outcome:* Confirmation of deletion. If it doesn't exist, an `McpError` is raised.

### 14b. Delete Second Collection (`mcp_flow_test_coll_renamed`)

Clean up by deleting the second (renamed) test collection.

```tool_code
print(default_api.mcp_chroma_test_chroma_delete_collection(collection_name="mcp_flow_test_coll_renamed"))
```

*Expected Outcome:* Confirmation of deletion.

### 15. Verify Collection Deletion

Attempt to list collections (should be empty or only contain non-test collections).

```tool_code
print(default_api.mcp_chroma_test_chroma_list_collections())
```

**Note:** `name_contains` omitted. Verify manually.

*Expected Outcome:* A list of collection names that does not include `mcp_flow_test_coll` or `mcp_flow_test_coll_renamed`.

---

## Advanced: Thinking Tools (Example Flow)

This section demonstrates a more realistic workflow using the sequential thinking tools, simulating debugging and feature planning. These tools operate independently and use their own internal storage mechanisms.

**Note:** A `session_id` is generated on the first call for a new sequence and should be reused for subsequent thoughts in that sequence.

### T1. Start Session 1: Debugging Login

Record the first thought in a new session about a login issue.

```tool_code
print(default_api.mcp_chroma_test_chroma_sequential_thinking(
    thought="User reports login fails frequently after recent deployment. Need to check server logs for errors.",
    thought_number=1,
    total_thoughts=3
    # session_id is omitted, will be generated for session 1
))
```

*Expected Outcome:* Confirmation, including the generated `session_id` (let's call it `session_id_1`).

### T2. Continue Session 1: Identify Error

Record the second thought, using `session_id_1`.

```tool_code
# Replace 'session_id_1' with the actual ID from T1's output
print(default_api.mcp_chroma_test_chroma_sequential_thinking(
    session_id="session_id_1",
    thought="Logs show intermittent 'InvalidCredentialsError'. Suspect password hashing or comparison logic in auth_utils.py.",
    thought_number=2,
    total_thoughts=3
))
```

*Expected Outcome:* Confirmation.

### T3. Continue Session 1: Found Bug

Record the final thought for the debugging session.

```tool_code
# Replace 'session_id_1' with the actual ID from T1's output
print(default_api.mcp_chroma_test_chroma_sequential_thinking(
    session_id="session_id_1",
    thought="Found the bug! Salt generation during registration used a non-deterministic source. Fixing auth_utils.py.",
    thought_number=3,
    total_thoughts=3
))
```

*Expected Outcome:* Confirmation.

### T4. Start Session 2: Planning MFA

Start a new session for planning a new feature.

```tool_code
print(default_api.mcp_chroma_test_chroma_sequential_thinking(
    thought="Product requirement: Add multi-factor authentication (MFA) for enhanced security.",
    thought_number=1,
    total_thoughts=3
    # session_id is omitted, will be generated for session 2
))
```

*Expected Outcome:* Confirmation, including a *new* generated `session_id` (let's call it `session_id_2`).

### T5. Continue Session 2: Research Options

Record the second thought for the MFA planning.

```tool_code
# Replace 'session_id_2' with the actual ID from T4's output
print(default_api.mcp_chroma_test_chroma_sequential_thinking(
    session_id="session_id_2",
    thought="Researching MFA options. TOTP (like Google Authenticator) seems the best balance of security and user experience vs SMS/Email codes. Will investigate the 'pyotp' library.",
    thought_number=2,
    total_thoughts=3
))
```

*Expected Outcome:* Confirmation.

### T5a. Continue Session 2: Implementation Plan

Record the final thought outlining the implementation plan.

```tool_code
# Replace 'session_id_2' with the actual ID from T4's output
print(default_api.mcp_chroma_test_chroma_sequential_thinking(
    session_id="session_id_2",
    thought="MFA Implementation Plan: 1. Update User model (add TOTP secret field). 2. Integrate 'pyotp' library. 3. Create QR code setup flow in user profile page. 4. Modify login view/API to check for TOTP code after password validation.",
    thought_number=3,
    total_thoughts=3
))
```

*Expected Outcome:* Confirmation.

### T5b. Ensure Sessions Collection Exists

Ensure the internal collection used by `find_similar_sessions` exists. This might normally be handled by server initialization, but we include it here for test robustness.

```tool_code
# This command remains the same
print(default_api.mcp_chroma_test_chroma_create_collection(collection_name="thinking_sessions"))
```

*Expected Outcome:* Confirmation of creation or an McpError indicating it already exists (which is also acceptable for the test).

### T6. Find Similar Sessions

Search for entire sessions similar to a query related to the new examples. We will test with different thresholds.

**Note:** Session similarity scores depend on the chosen embedding function.

```tool_code
# Query relevant to both Session 1 (login issue) and Session 2 (MFA involves auth)
print(default_api.mcp_chroma_test_chroma_find_similar_sessions(
    query="frequent login failures after deployment",
    # We will vary the threshold in the actual test runs (e.g., 0.5, 0.75)
    threshold=0.5 # Placeholder value, will be changed in execution
))
```

*Expected Outcome:* A list of session IDs and summaries that are semantically similar to the query, depending on the threshold used during execution.

---

This flow covers the primary CRUD operations, filter/query variations, and provides a more detailed example of the thinking tools. Client limitations with list parameters may still affect query/get operations.
