# Refactoring Plan V2: MCP SDK Compliance with Pydantic Input Validation

**Goal:** Refactor the `chroma-mcp-server` tools (`collection_tools.py`, `document_tools.py`, `thinking_tools.py`) to strictly adhere to the official MCP Python SDK patterns outlined in `docs/mcp-reference.md`. This version focuses on:

1. **Integrating Pydantic** for robust input schema definition and validation.
2. **Removing unnecessary `Optional` types** in tool inputs where parameters are logically required.
3. Ensuring **strict standard MCP SDK patterns** are used (no `FastMCP`).
4. Maintaining the **`McpError` exception pattern** for tool-level errors, letting the server framework handle the conversion to error results.
5. **Simplifying Document Operations:** Modifying document `add`, `update`, and `delete` tools to handle **single documents** only. This is necessary to improve compatibility with consuming models (LLMs) that struggle with complex list-based inputs for modification operations. Query and get operations will retain their ability to handle multiple items/results.

**Reference:** `docs/mcp-reference.md` (Updated version incorporating Pydantic examples)

---

## Phase 0: Standardize Server Entry Point & Initialization

**Goal:** Ensure the server startup mechanism follows the recommended pattern for logging, argument parsing, and asyncio execution.

- [x] **Identify Entry Point(s):** Locate the primary script(s) responsible for starting the server (e.g., `src/chroma_mcp/__main__.py`, `src/chroma_mcp/server.py`, `src/chroma_mcp/cli.py`, `src/chroma_mcp/__init__.py`).
- [x] **Review/Refactor `main` Function:**
  - [x] Ensure a synchronous `main` function exists (or is created) as the primary entry point.
  - [x] Implement/verify argument parsing (e.g., using `click` or `argparse`) for configurations like verbosity.
  - [x] Implement/verify logging configuration:
  - [x] Set logging level based on verbosity arguments.
  - [x] Configure `logging.basicConfig` (or equivalent) to output to `sys.stderr`.
  - [x] Include a clear log format (e.g., timestamp, logger name, level, message).
  - [x] Ensure the main async server setup/run function (e.g., `serve()`) is called using `asyncio.run()`.
  - [x] Include top-level `try...except` block around `asyncio.run()` to catch and log critical startup errors.
- [x] **Verify `if __name__ == "__main__":`:** Ensure the entry point script correctly calls the `main` function when executed directly.

---

## Phase 1: Define Pydantic Input Models for Simplified/Variant Tools

**Goal:** Create specific Pydantic models for each tool, simplifying `add`/`update`/`delete` operations to single items and using variants where necessary for `query`/`get`.

- [x] **Identify Tools for Refactoring:** Primarily `document_tools.py` for single-item simplification, and other tools for variant creation if needed to avoid complex optionals.
- [x] **Define Simplified/Variant Models:**
  - [ ] `collection_tools.py` variants (e.g., `CreateCollectionInput`, `CreateCollectionWithMetadataInput`).
  - [x] `document_tools.py`:
    - **Single-Item Models:** Define models for single-item operations (e.g., `AddDocumentInput`, `AddDocumentWithIdInput`, `AddDocumentWithMetadataInput`, `AddDocumentWithIdAndMetadataInput`, `UpdateDocumentContentInput`, `UpdateDocumentMetadataInput`, `DeleteDocumentByIdInput`). These models will have fields like `document: str`, `id: str`, `metadata: str` or `metadata: Dict` instead of lists.
    - **List-Based Query/Get Variants:** Define specific variants for query and get operations that still need lists (e.g., `QueryDocumentsInput`, `QueryDocumentsWithWhereFilterInput`, `GetDocumentsByIdsInput`, `GetAllDocumentsInput`). These models will use `query_texts: List[str]`, `ids: List[str]`, etc.
  - [x] `thinking_tools.py` variants (e.g., `SequentialThinkingInput`, `SequentialThinkingWithDataInput`).
- [x] **Define Fields:**
  - [x] Use precise Python types (`str`, `int`, `float`, `List`, `Dict`, `bool`).
  - [x] **Simplify Add/Update/Delete:** Ensure models for these operations use singular types (`str`, `Dict`) instead of `List`.
  - [x] **Eliminate Complex Optionals:** Avoid `Optional[Dict[...]]` or `Optional[List[...]]` in *all* models, using specific required fields or variants instead. Simple `Optional`s (`Optional[str]`) are acceptable if needed.
  - [x] Use `pydantic.Field` for descriptions/constraints.

---

## Phase 2: Update Tool Registration (`list_tools`)

**Goal:** Register the simplified single-item tools and necessary variants, removing original list-based modification tools.

- [x] **Import New Models:** Ensure the new Pydantic models (single-item and variant) are imported into `src/chroma_mcp/server.py`.
- [x] **Update `Tool` Definitions:** Modify the list of `mcp.types.Tool` objects in the `list_tools` function:
  - [x] **Remove Original List-Based Tools:** Comment out or delete registrations for original tools being replaced (e.g., the original list-based `chroma_add_documents`, `chroma_update_documents`, `chroma_delete_documents`).
  - [x] **Register Simplified/Variant Tools:** Add new `mcp.types.Tool` registration entries for each simplified single-item tool and each required variant defined in Phase 1.
  - Set the `name` (e.g., `chroma_add_document_with_id`, `chroma_query_documents_with_where_filter`).
  - Set the `description` clearly indicating the specific action (single item or variant).
  - Set the `inputSchema` using the corresponding Pydantic model.
- [x] **Update `TOOL_NAMES`, `INPUT_MODELS`, `IMPL_FUNCTIONS` Mappings:** Add entries for all new tools and remove entries for the replaced original tools in `src/chroma_mcp/server.py`.

**Tools to Replace/Refactor:**

- `chroma_create_collection` -> Add `chroma_create_collection_with_metadata`
- `chroma_add_documents` -> Replace with **single-item** tools: `add_document`, `add_document_with_id`, `add_document_with_metadata`, `add_document_with_id_and_metadata`.
- `chroma_query_documents` -> Replace with **list-based variants**: `query_documents`, `query_documents_with_where_filter`, `query_documents_with_document_filter`.
- `chroma_get_documents` -> Replace with **list-based variants**: `get_documents_by_ids`, `get_documents_with_where_filter`, `get_documents_with_document_filter`, `get_all_documents`.
- `chroma_update_documents` -> Replace with **single-item** tools: `update_document_content`, `update_document_metadata`.
- `chroma_delete_documents` -> Replace with **single-item** tool `delete_document_by_id` and **filter-based variants** `delete_documents_by_where_filter`, `delete_documents_by_document_filter`.
- `chroma_sequential_thinking` -> Add `chroma_sequential_thinking_with_data`

---

## Phase 3: Refactor Tool Implementation (Dispatch/Handler)

**Goal:** Ensure the dispatcher correctly routes calls for the new simplified/variant tools to their implementations.

- [x] **Identify Handler:** Locate the central function decorated with `@server.call_tool()` (`call_tool` in `src/chroma_mcp/server.py`).
- [x] **Update Dispatch Logic:** The existing logic using `INPUT_MODELS` and `IMPL_FUNCTIONS` dictionaries should work correctly, provided these dictionaries are updated accurately in Phase 2.
- [x] **Error Handling:** The existing `try...except ValidationError` and the raising of `McpError` remain appropriate.

---

## Phase 4: Refactor Core Logic Functions (`_impl`)

**Goal:** Create or adapt `_impl` functions for each simplified single-item tool and list-based variant.

- [x] **Create/Adapt `_impl` Functions:** Define/modify implementation functions (e.g., `_add_document_with_id_impl`, `_query_documents_with_where_filter_impl`) for each tool registered in Phase 2.
- [x] **Update Signatures:** Ensure each `_impl` function accepts its specific Pydantic model (e.g., `input_data: AddDocumentWithIdInput`, `input_data: QueryDocumentsWithWhereFilterInput`) and returns `List[types.TextContent]`.
- [x] **Implement Logic:**
  - **Single-Item Tools:** Logic will take single inputs (e.g., `input_data.id`, `input_data.document`). When calling the underlying ChromaDB client method that expects lists, wrap the single item in a list (e.g., `collection.add(ids=[input_data.id], documents=[input_data.document], ...)`).
  - **List-Based Variants:** Logic will handle lists directly from the input model (e.g., `input_data.query_texts`).
  - Consider shared internal helpers where appropriate.
- [x] **Raise `McpError` on Failure:** Ensure functions catch operational errors and raise `McpError`.

---

## Phase 5: Refactor Utility Functions

**Goal:** Review utility functions in light of the new structure.

- [x] **`src/chroma_mcp/utils/errors.py`:** No changes likely needed beyond Phase V1/V2 adjustments. `handle_chroma_error` can still be used to convert Chroma errors to `McpError` within `_impl` functions.
- [ ] **Shared Logic Helpers:** Consider creating new utility functions if significant logic is shared between the new `_impl` variants (as mentioned in Phase 4).

---

## Phase 6: Update Tests

**Goal:** Align tests with the new single-item add/update/delete tools, list-based query/get tools, and `McpError` exception handling.

**General Approach Checklist for Tests:**

- [x] **Write Tests for New Tools:** Create new test functions for each specific tool (single-item or variant) added in Phase 2 (e.g., `test_add_document_with_id_success`, `test_query_documents_with_where_filter_success`).
  - Use inputs matching the tool's Pydantic model.
  - Test validation failures by providing incorrect input to `call_tool` and asserting `pytest.raises(McpError, code=INVALID_PARAMS)`.
  - Test execution failures by mocking errors and asserting `_impl` raises `McpError`.
  - Test success cases.
- [x] **Remove/Skip Tests for Replaced Tools:** Remove or skip tests for the original list-based tools that were replaced.

**Specific Test Modules:**

- [ ] **`tests/tools/test_collection_tools.py`:** Add tests for `create_collection_with_metadata`.
- [x] **`tests/tools/test_document_tools.py`:** Add tests for all **single-item** `add`, `update`, `delete` tools and **list-based** `query`, `get`, filter-delete variants. Skip/remove tests for original list-based modification tools.
- [x] **`tests/tools/test_thinking_tools.py`:** Add tests for `sequential_thinking_with_data`.

---

## Phase 7: Review and Verification

**Goal:** Ensure the refactoring is complete, correct, and improves client compatibility by using single-item modification tools.

- [x] **Code Review:** Perform a thorough review focusing on the single-item tools, list-based variants, Pydantic models, `_impl` logic (especially list wrapping for single-item calls), `McpError` usage, and test coverage.
- [x] **Run Tests:** Execute the full test suite (`hatch run test`). Address any failures.
- [ ] **Manual Testing (MCP Inspector / Client):**
  - [ ] Verify the *original list-based* add/update/delete tools no longer appear.
  - [ ] Verify the *new single-item* add/update/delete tools appear correctly.
  - [ ] Verify the *new list-based* query/get variants appear correctly.
  - [ ] Test valid inputs for all *new* tools.
  - [ ] Test invalid inputs for tools (e.g., missing required fields) and verify `McpError` (`INVALID_PARAMS`).
  - [ ] Test execution errors and verify `McpError`.
- [x] **Server Log Verification:** Check logs.
- [ ] **Linting/Formatting:** Run tools (`hatch run lint`).
