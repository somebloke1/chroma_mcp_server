# MCP Tool Development Guidelines (Python SDK)

This document outlines best practices and conventions for developing MCP tools within a Python server environment, aiming for strict adherence to the official Model Context Protocol (MCP) specification and Python SDK examples (v1.x, circa March 2024/2025). Following these guidelines is intended to maximize compatibility with various MCP clients (like IDE integrations), leverage the SDK's intended patterns, and prevent common issues.

**Note:** Different MCP clients support varying levels of protocol features (Tools, Resources, Prompts). Adhering to the standard ensures broader compatibility. See [Client Feature Matrix](https://modelcontextprotocol.io/clients) for details.

**References:**

* [MCP Tools Concept](https://modelcontextprotocol.io/docs/concepts/tools)
* [MCP Debugging Guide](https://modelcontextprotocol.io/docs/tools/debugging)

## 1. Tool Definition and Registration

Tools are exposed to clients via the `tools/list` mechanism. The server needs to define the tool's metadata.

**DO:**

* **Define Tool Metadata:** Ensure each tool has a clear `name`, a helpful `description`, and a precise JSON Schema (`inputSchema`) defining its parameters. The description should guide the LLM on how and when to use the tool.

* Example `types.Tool` structure:

    ```python
    from mcp import types # Assuming types are imported from the SDK root

    example_tool = types.Tool(
        name="calculate_sum",
        description="Add two numbers together. Use this when needing to compute the sum of two numeric values.",
        inputSchema={
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "The first number"},
                "b": {"type": "number", "description": "The second number"}
            },
            "required": ["a", "b"]
        }
    )
    ```

* **Register Tools:** Use the appropriate mechanism provided by the SDK/framework (e.g., `@app.list_tools()` or equivalent in `FastMCP`) to make the defined tools discoverable.
* **Use Specific Schema Types:** Define parameters in `inputSchema` using standard JSON Schema types (`string`, `number`, `integer`, `boolean`, `array`, `object`) and constraints (`required`, `enum`, `description`).

**DON'T:**

* **DON'T Provide Vague Descriptions:** Tool descriptions are crucial for LLM usage; make them explicit.
* **DON'T Use Non-Standard Schema:** Stick to valid JSON Schema for `inputSchema`.

## 2. Tool Implementation (`call_tool`)

The core logic executes when a client invokes a tool via `tools/call`.

**DO:**

* **Implement Central Handler (if using low-level SDK):** The base SDK examples often show a single handler (like `@app.call_tool()`) that receives the `name` and `arguments` (dict). Your logic would dispatch based on the `name`. (Note: Frameworks like `FastMCP` might abstract this with decorators like `@mcp.tool`, mapping signatures directly, but the underlying principle of handling arguments based on the schema applies).
* **Expect Arguments Dictionary:** If using a central handler, expect the arguments as a dictionary matching the structure defined in the `inputSchema`. Access parameters via dictionary keys (e.g., `arguments["a"]`).
* **Perform Logic:** Execute the core functionality of the tool.

**DON'T:**

* **DON'T Assume Argument Types Blindly:** While the schema defines types, perform necessary checks or conversions if the framework doesn't guarantee type safety based on the schema before passing arguments to internal functions.

## 3. Return Values (Success Results)

Tools **must** return results in the specific format expected by the MCP `tools/call` response, using SDK types.

**DO:**

* **Return `types.CallToolResult`:** The standard successful return should be an instance of `mcp.types.CallToolResult`.
* **Populate `content` List:** The `content` field of the result must be a *list* containing objects representing the output, using MCP content types.
* **Use Specific `types.Content` Objects:** Use appropriate content types from the SDK, such as:

* `mcp.types.TextContent(type="text", text="Your string result")` for textual output.
* `mcp.types.ImageContent(...)` for images.
* `mcp.types.EmbeddedResource(...)` for embedding resources.
* Ensure the `type` field matches the object type (e.g., `"text"` for `TextContent`).
* Example Success Return:

    ```python
    from mcp import types

    result_value = a + b
    return types.CallToolResult(
        content=[
            types.TextContent(type="text", text=f"The sum is: {result_value}")
        ]
        # isError defaults to False or is omitted
    )
    ```

* **Ensure JSON Serializable Content:** The data *within* the content objects (e.g., the `text` in `TextContent`) must be JSON serializable if it's not a primitive type already.

**DON'T:**

* **DON'T Return Plain Dictionaries:** Avoid returning generic Python dictionaries like `{"result": "some_value"}`. Use the specific `types.CallToolResult` and `types.Content` structures.
* **DON'T Return `None`:** Return a `types.CallToolResult` with potentially an empty `content` list if appropriate, but not `None`.
* **DON'T Return Bare Strings/Numbers:** Wrap primitive results in the appropriate `types.Content` object (e.g., `types.TextContent`).

## 4. Error Handling (Tool Execution Errors)

Errors occurring *during the execution of the tool's logic* should be reported back to the client *within* the standard tool result structure, allowing the LLM to potentially see and react to the error. **This differs significantly from raising protocol-level errors.**

**DO:**

* **Catch Tool-Specific Exceptions:** Use `try...except` blocks within your tool's execution logic to catch expected errors (e.g., invalid tool inputs processed *by the tool*, API call failures, file not found).
* **Return `types.CallToolResult` with `isError=True`:** On catching an exception, **return** (do not raise) an instance of `mcp.types.CallToolResult` with the `isError` flag set to `True`.
* **Provide Error Details in `content`:** Include a `types.TextContent` object (or other appropriate content type) in the `content` list describing the error clearly and concisely.
* **Log Full Error Server-Side:** When returning `isError=True`, ensure the *full* exception details (including stack trace) are logged on the server for debugging (see Logging section).

* Example Error Return:

    ```python
    from mcp import types

    try:
        # Tool operation that might fail
        if arguments["divisor"] == 0:
            raise ValueError("Division by zero is not allowed.")
        result = arguments["dividend"] / arguments["divisor"]
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=str(result))]
        )
    except Exception as error:
        # Log the full error server-side (see Logging section)
        # logger.error(f"Tool execution failed: {error}", exc_info=True)
        return types.CallToolResult(
            isError=True,
            content=[
                types.TextContent(type="text", text=f"Tool Error: {str(error)}") # User-friendly error
            ]
        )
    ```

**DON'T:**

* **DON'T `raise McpError` for Tool Execution Failures:** Do not raise `McpError` (or let internal exceptions leak) for errors *within* the tool's normal operational scope (like invalid input handled by the tool, or failed API calls). Return the `isError=True` result structure instead.
* **DON'T Expose Sensitive Details in Error Content:** The error message in the *returned* `content` should be safe for the client/LLM to see. Log detailed stack traces or sensitive context only on the server.

## 5. Protocol-Level Error Handling

Protocol-level errors occur *outside* the successful execution of a tool's core logic.

**DO:**

* **Let Framework Handle (or Raise `McpError`):** Errors like malformed requests, invalid JSON, failed authentication, or the framework being unable to find the requested tool (`METHOD_NOT_FOUND`) should generally result in standard JSON-RPC error responses. Frameworks like `FastMCP` likely handle this by raising or converting errors to `McpError` with appropriate codes (`-32700`, `-32600`, `-32601`, `-32602`, `-32603`).
* **Use `INVALID_PARAMS` (`-32602`) for Schema Validation:** If the *framework* (like `FastMCP`) fails to validate incoming arguments against the `inputSchema` *before* calling your tool logic, it's appropriate for it to raise `McpError` with code `-32602`.
* **Use `INTERNAL_ERROR` (`-32603`) for Unexpected Server Failures:** If a truly unexpected error occurs *outside* your specific tool's `try...except` block (e.g., database connection lost, unhandled exception in framework code), raising `McpError` with `-32603` might be necessary.

**DON'T:**

* **DON'T Confuse Tool Errors with Protocol Errors:** Maintain the distinction: Tool execution failures return `isError=True`; Protocol/Framework failures raise `McpError`.

## 6. Logging

Server-side logging remains crucial for debugging.

**DO:**

* **Use Server Logger:** Obtain and use the server's configured logger (e.g., `from ..server import get_logger; logger = get_logger("tools.mytool")`).
* **Log to `stderr` (for Stdio Transport):** When using the standard stdio transport (common for local servers launched by clients like Claude Desktop), log messages should be written to `stderr`. The host application will typically capture these logs. **Do not** log regular messages to `stdout` as it interferes with the protocol.
* **Log Tool Calls:** Log the start and end of tool calls, including the tool name and received arguments (mask sensitive data).
* **Log Success Results:** Log the structure of successful results being returned.
* **Log Tool Errors in Detail:** When catching an exception within a tool's logic (before returning `isError=True`), log the *full* error details, including stack trace (`exc_info=True`), on the server side for debugging.
* **Log Protocol Errors:** Ensure the framework logs protocol-level errors adequately.
* **(Optional) Send Log Notifications:** The SDK provides `session.send_log_message(...)` to send logs directly to the client if needed, but standard `stderr` logging is often sufficient for server diagnostics.

**DON'T:**

* **DON'T Log to `stdout` (for Stdio Transport):** This will break the MCP communication.
* **DON'T Rely Solely on Returned Errors:** The error returned to the client is often brief; detailed logs are essential for diagnosis.
* **DON'T Use `print()`:** Use the structured logger (`stderr` or `session.send_log_message`).

## 7. Input Validation

Validation is essential for robustness and security.

**DO:**

* **Define Schema Accurately:** The primary validation should leverage the `inputSchema`.
* **Validate in Tool Logic (if needed):** Perform *business logic* validation (e.g., checking if a user ID exists, if a value is within a semantic range) within your tool's `try...except` block.
* **Return `isError=True` for Validation Failures:** If *your tool's logic* determines an input is invalid (beyond simple type checking covered by the schema), return the `CallToolResult(isError=True, ...)` structure with a clear validation message.

**DON'T:**

* **DON'T Bypass Schema Validation:** Rely on the framework to perform initial type/structure validation based on the schema.

## 8. Debugging and Troubleshooting

Reference: [MCP Debugging Guide](https://modelcontextprotocol.io/docs/tools/debugging)

**DO:**

* **Check Server Logs:** Regularly inspect server logs (often captured by the host application like Claude Desktop, potentially in `~/Library/Logs/Claude/mcp*.log` on macOS, or wherever your server directs `stderr`).
* **Use the MCP Inspector:** For direct testing and iteration during development without a full client, use the `npx @modelcontextprotocol/inspector <server_command>` tool.
* **Verify Working Directory:** Be aware that servers launched by host applications might have an unexpected working directory (e.g., `/` on macOS). Use absolute paths for file access within tools or ensure paths are relative to a known, configured location.
* **Manage Environment Variables:** Servers launched by hosts may inherit only a limited set of environment variables (`USER`, `HOME`, `PATH`). If your tools rely on specific environment variables (`API_KEY`s, etc.), ensure they are explicitly passed or configured for the server process (e.g., via host config like `claude_desktop_config.json` or systemd unit files).
* **Test Standalone:** If issues occur, try running the server script directly from the command line to isolate problems from the host application environment.
* **Restart Server/Client:** Remember to restart the server after code changes and potentially the client application after configuration changes.

**DON'T:**

* **DON'T Assume CWD:** Avoid relying on the current working directory being the project root when the server is launched by a host.
* **DON'T Assume Full Environment Inheritance:** Explicitly manage required environment variables.

## Summary

Adhering strictly to the MCP SDK's patterns, especially using `mcp.types` for return values and adopting the `isError=True` mechanism for reporting tool execution errors, is key for building compliant and compatible MCP tools. Leveraging server-side logging and understanding common debugging pitfalls will further improve development efficiency and tool robustness. This may require refactoring existing code that uses custom error handling or generic return types.
