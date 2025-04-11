# Refactoring Plan V2: MCP SDK Compliance with Pydantic Input Validation

**Goal:** Refactor the `chroma-mcp-server` tools (`collection_tools.py`, `document_tools.py`, `thinking_tools.py`) to strictly adhere to the official MCP Python SDK patterns outlined in `docs/mcp-reference.md`. This version focuses on:

1. **Integrating Pydantic** for robust input schema definition and validation.
2. **Removing unnecessary `Optional` types** in tool inputs where parameters are logically required.
3. Ensuring **strict standard MCP SDK patterns** are used (no `FastMCP`).
4. Maintaining the **`isError=True` return pattern** for tool-level errors (established in V1 refactor).

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

## Phase 1: Define Pydantic Input Models

**Goal:** Create specific Pydantic models for each tool's input arguments.

- [x] **Review Tool Parameters:** For each tool, identify required vs. truly optional parameters based on ChromaDB's API and the tool's logic.
- [x] **Create Models:** In a logical location (e.g., within each `tools/` file or a dedicated `schemas.py`), define a Pydantic `BaseModel` for *each* tool.
  - [x] `collection_tools.py` models (e.g., `CreateCollectionInput`, `ListCollectionsInput`, ...)
  - [x] `document_tools.py` models (e.g., `AddDocumentsInput`, `QueryDocumentsInput`, ...)
  - [x] `thinking_tools.py` models (e.g., `SequentialThinkingInput`, `FindSimilarThoughtsInput`, ...)
- [x] **Define Fields:**
  - [x] Use precise Python types (`str`, `int`, `float`, `list`, `dict`, `bool`).
  - [x] **Minimize `Optional`:** Only use `Optional[T]` (or `T | None`) if the parameter is *truly optional* for the tool's operation. If a parameter is required by the logic or Chroma, make it non-optional in the model. Pydantic validation will enforce its presence.
  - [x] Use `pydantic.Field` to add descriptions, default values (for optional fields), and constraints if applicable.

---

## Phase 2: Update Tool Registration (`list_tools`)

**Goal:** Use the new Pydantic models to generate the `inputSchema` for tool registration.

- [x] **Import Models:** Ensure Pydantic models are imported into the file where tools are registered (likely `src/chroma_mcp/server.py` or similar).
- [x] **Update `Tool` Definitions:** Modify the list of `mcp.types.Tool` objects:
  - [x] For each tool, set `inputSchema=YourCorrespondingInputModel.model_json_schema()` (assuming Pydantic v2+).
  - [x] Verify tool `name` and `description` remain accurate.

---

## Phase 3: Refactor Tool Implementation (Dispatch/Handler)

**Goal:** Implement Pydantic validation at the entry point of tool execution and pass validated data to core logic.

- [x] **Identify Handler:** Locate the central function that receives the `tool_name` and `arguments: dict` (e.g., the function decorated with `@server.call_tool()` in `src/chroma_mcp/server.py`).
- [x] **Implement Validation Logic:** Within this handler, *before* calling the core logic for each tool:
  - [x] Use a `try...except pydantic.ValidationError` block.
  - [x] Inside the `try`, instantiate the appropriate Pydantic input model: `input_data = ToolInputModel(**arguments)`.
  - [x] If validation fails (`except ValidationError as e`):
  - [x] Log the validation error (e.g., `logger.warning(f"Input validation failed for {tool_name}: {e}")`).
  - [x] **Return** `types.CallToolResult(isError=True, content=[types.TextContent(type="text", text=f"Input Error: {str(e)}")])`.
- [x] **Pass Validated Data:** Modify the call to the core logic function to pass the `input_data` (the Pydantic model instance) instead of the raw `arguments` dict.
- [x] **Handle Execution Errors:** Keep the *outer* `try...except Exception` block (established in V1 refactor) around the validation *and* core logic call to catch errors *after* validation, returning `CallToolResult(isError=True, ...)` for these execution failures.

**Example Snippet (Conceptual):**

```python
# Inside the @mcp.server.call_tool() decorated function
async def call_tool(name: str, arguments: dict) -> types.CallToolResult:
    try:
        # --- Pydantic Validation --- >
        validated_input = None
        if name == "create_collection":
            InputModel = CreateCollectionInput
        elif name == "add_documents":
            InputModel = AddDocumentsInput
        # ... other tools
        else:
            # Handle unknown tool name early
            logger.error(f"Attempted to call unknown tool: {name}")
            return types.CallToolResult(
                isError=True,
                content=[types.TextContent(type="text", text=f"Tool Error: Unknown tool name '{name}'")]
            )

        try:
            validated_input = InputModel(**arguments)
        except ValidationError as e:
            logger.warning(f"Input validation failed for {name}: {e}")
            # Return validation error details to the client
            return types.CallToolResult(
                isError=True,
                content=[types.TextContent(type="text", text=f"Input Error: {str(e)}")]
            )
        # <--- Pydantic Validation Done ---

        # --- Call Core Logic --- >
        # Find and call the corresponding implementation function
        # (These functions now expect the Pydantic model instance)
        if name == "create_collection":
            result = await _create_collection_impl(validated_input)
        elif name == "add_documents":
            result = await _add_documents_impl(validated_input)
        # ... etc.

        # Return the result from the _impl function (already a CallToolResult)
        return result

    except Exception as error:
        # Catch errors during core logic execution (post-validation)
        logger.error(f"Execution failed for tool {name}: {error}", exc_info=True)
        return types.CallToolResult(
            isError=True,
            content=[types.TextContent(type="text", text=f"Tool Execution Error: {str(error)}")]
        )
```

---

## Phase 4: Refactor Core Logic Functions (`_impl`)

**Goal:** Simplify core logic functions by having them accept the validated Pydantic model.

- [x] **Update Signatures:** Change the signature of each `_impl` function (or equivalent) to accept the specific Pydantic input model instance instead of `arguments: dict`.
  - [x] `collection_tools.py` `_impl` functions.
  - [x] `document_tools.py` `_impl` functions.
  - [x] `thinking_tools.py` `_impl` functions.
- [x] **Update Parameter Access:** Replace dictionary access (e.g., `arguments.get("param")`, `arguments["param"]`) with direct attribute access on the input model instance (e.g., `input_data.param`).
- [x] **Remove Redundant Checks:** Remove checks for `None` or key existence for parameters that are now non-optional in the Pydantic model, as validation guarantees their presence and type.
- [x] **Maintain `isError=True` Returns:** Ensure these functions still return `CallToolResult` and handle their *own* execution errors (e.g., Chroma API errors) by catching them and returning `CallToolResult(isError=True, ...)`, as established in V1.

---

## Phase 5: Refactor Utility Functions

**Goal:** Review and potentially simplify error utility functions.

- [x] **`src/chroma_mcp/utils/errors.py`:**
  - [x] Review `handle_chroma_error`: This might still be useful within `_impl` functions to specifically catch ChromaDB exceptions and format them into the `isError=True` `CallToolResult`, but it should *not* be raising `McpError` for expected operational errors.
  - [x] Review `raise_validation_error`: This function is likely **obsolete** if all input validation is handled by Pydantic models in the dispatcher (Phase 3). Consider removing it. (Removed `validate_input` function which served this purpose)

---

## Phase 6: Update Tests

**Goal:** Align tests with Pydantic validation and the refactored function signatures.

**General Approach Checklist for Tests:**

- [x] **Update Fixtures/Inputs:** Ensure test inputs match the Pydantic models (provide required fields, use correct types, remove `None` for non-optional fields).
- [x] **Add Validation Failure Tests:** Create new tests specifically designed to fail Pydantic validation (e.g., missing required args, incorrect types) and assert that the handler correctly returns `CallToolResult(isError=True, ...)` with an appropriate validation error message.
- [x] **Update Existing Error Tests:** Tests previously checking for `McpError` on bad input should be updated to check for `CallToolResult(isError=True, ...)` resulting from `ValidationError`.
- [x] **Update Core Logic Tests:** If testing `_impl` functions directly, update mocks/inputs to pass the Pydantic model instance instead of a dictionary.
- [x] **Maintain Execution Error Tests:** Keep tests that verify `CallToolResult(isError=True, ...)` is returned for errors *after* successful validation (e.g., mocking a Chroma API error).
- [x] **Maintain Success Case Tests:** Ensure success cases still pass, checking the `content` of the returned `CallToolResult`.

**Specific Test Modules:**

- [x] **`tests/tools/test_collection_tools.py`:** Update all tests.
- [x] **`tests/tools/test_document_tools.py`:** Update all tests.
- [x] **`tests/tools/test_thinking_tools.py`:** Update all tests.

---

## Phase 7: Review and Verification

**Goal:** Ensure the refactoring is complete, correct, and improves compatibility.

- [x] **Code Review:** Perform a thorough review focusing on Pydantic usage, removal of Optionals, error handling consistency, and adherence to `mcp-reference.md`. (Reviewed `list_tools` and `call_tool`)
- [x] **Run Tests:** Execute the full test suite (`hatch run test`). Address any failures. (Test suite successfully executed via `./scripts/test.sh`, all tests passed or skipped as expected).
- [ ] **Manual Testing (MCP Inspector):**
  - [x] Test valid inputs for all tools.
  - [x] Test invalid inputs (missing required fields, wrong types) and verify clear `Input Error:` messages are returned via `isError=True`.
  - [ ] Test scenarios causing execution errors (e.g., deleting a non-existent collection) and verify `Tool Execution Error:` messages via `isError=True`.
- [ ] **Manual Testing (Integrated Clients - Cursor, etc.):**
  - [x] Verify successful tool calls work as expected.
  - [x] Observe how clients handle the `isError=True` results for both validation and execution errors. Does the feedback help the user/LLM?
  - [ ] Test scenarios where optional parameters are omitted and provided.
- [x] **Server Log Verification:** Check logs for clarity, especially for validation failures vs. execution errors.
- [x] **Linting/Formatting:** Run tools (`hatch run lint`). (`black` successful, `pylint` skipped)
