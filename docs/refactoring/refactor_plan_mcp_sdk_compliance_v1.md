# Refactoring Plan: MCP SDK Compliance

**Goal:** Refactor the `chroma-mcp-server` tools (`collection_tools.py`, `document_tools.py`, `thinking_tools.py`) to strictly adhere to the official MCP Python SDK patterns outlined in `docs/mcp-reference.md`, primarily focusing on tool return values and error handling for improved client compatibility.

**Reference:** `docs/mcp-reference.md`

---

## Phase 1: Preparation

- [x] **Import MCP Types:** Ensure necessary types are imported where needed, primarily:

    ```python
    from mcp import types # Or specific types like CallToolResult, TextContent
    from mcp.shared.exceptions import McpError # For protocol-level errors
    from mcp.types import ErrorData, INVALID_PARAMS, INTERNAL_ERROR # Standard error codes
    ```

  - [x] Add imports to `src/chroma_mcp/tools/collection_tools.py`.
  - [x] Add imports to `src/chroma_mcp/tools/document_tools.py`.
  - [x] Add imports to `src/chroma_mcp/tools/thinking_tools.py`.
  - [x] Add imports to `src/chroma_mcp/utils/errors.py` (if needed).

---

## Phase 2: Refactor Tool Implementation (`_impl` functions)

This is the core phase, modifying how each `_impl` function returns results and handles errors.

**General Approach Checklist for each `_impl` function:**

- [x] Update Return Type Hint (`-> types.CallToolResult`).
- [x] Refactor Success Path (Return `types.CallToolResult(content=[...])` with `types.Content` objects).
- [x] Refactor Error Handling Path:
  - [x] Modify `try...except` blocks.
  - [x] Catch specific expected operational errors.
  - [x] Log full error details server-side for expected errors.
  - [x] **Return** `types.CallToolResult(isError=True, ...)` for expected errors.
  - [x] Catch generic `Exception` as a last resort.
  - [x] Log full error details server-side for unexpected errors.
  - [x] **Return** `types.CallToolResult(isError=True, ...)` for unexpected errors.

**Specific Tool Modules:**

1. **`src/chroma_mcp/tools/collection_tools.py`:**
    - [x] Apply general approach to `_create_collection_impl`.
    - [x] Apply general approach to `_list_collections_impl`.
    - [x] Apply general approach to `_get_collection_impl`.
    - [x] Apply general approach to `_rename_collection_impl`.
    - [x] Apply general approach to `_delete_collection_impl`.
    - [x] Apply general approach to `_peek_collection_impl`.

2. **`src/chroma_mcp/tools/document_tools.py`:**
    - [x] Apply general approach to `_add_documents_impl`.
    - [x] Apply general approach to `_query_documents_impl`.
    - [x] Apply general approach to `_get_documents_impl`.
    - [x] Apply general approach to `_update_documents_impl`.
    - [x] Apply general approach to `_delete_documents_impl`.

3. **`src/chroma_mcp/tools/thinking_tools.py`:**
    - [x] Apply general approach to `_sequential_thinking_impl`.
    - [x] Apply general approach to `_find_similar_thoughts_impl`.
    - [x] Apply general approach to `_get_session_summary_impl`.
    - [x] Apply general approach to `_find_similar_sessions_impl`.

---

## Phase 3: Refactor Utility Functions

- [x] **`src/chroma_mcp/utils/errors.py`:**
  - [x] Review and simplify/repurpose `handle_chroma_error` (focus on unexpected exceptions -> `McpError(INTERNAL_ERROR)`).
  - [x] Remove mappings now handled by returning `isError=True` in `_impl`.
  - [x] Review `raise_validation_error` (still okay for internal use, caught by `except ValidationError` in `_impl`).

---

## Phase 4: Update Tests

**General Approach Checklist for Tests:**

- [x] Assert return type is `types.CallToolResult`.
- [x] Success Cases: Assert `isError` is False/absent, check `content` list.
- [x] Expected Error Cases: Assert `isError` is True, check error message in `content`.
- [x] Expected Error Cases: Remove `pytest.raises(McpError, ...)` where `isError=True` is now returned.
- [x] Unexpected Error Cases: Check for `isError=True` and error message in `content`.

**Specific Test Modules:**

- [x] **`tests/tools/test_collection_tools.py`:** Update all tests according to the general approach.
- [x] **`tests/tools/test_document_tools.py`:** Update all tests according to the general approach.
- [x] **`tests/tools/test_thinking_tools.py`:** Update all tests according to the general approach.

---

## Phase 5: Review and Verification

- [ ] **Code Review:** Perform a thorough review of all changes.
- [x] **Run Tests:** Execute the test suite using `hatch run test` (All tests passed!).
- [x] **Manual Testing (MCP Inspector):** Test successful calls and expected errors.
- [x] **Manual Testing (Integrated Clients):** Test with Copilot, Cursor, etc.
  - [x] Verify successful calls.
  - [x] Verify expected errors (how does client display `isError=True` result?).
  - [x] Verify unexpected server errors (protocol-level errors).
- [x] **Server Log Verification:** Check log output for clarity and detail.
- [x] **Linting/Formatting:** Run tools (`hatch run lint`). (Passed!).

---

This plan provides a structured approach with checklists to track progress in aligning the codebase with MCP standards. Each `_impl` function and its corresponding tests will need careful modification.
