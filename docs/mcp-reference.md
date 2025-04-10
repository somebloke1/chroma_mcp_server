# MCP Tool Development Guidelines (Python SDK)

This document outlines best practices and conventions for developing MCP tools within a Python server environment, aiming for strict adherence to the official Model Context Protocol (MCP) specification and Python SDK examples (v1.x, circa March 2024/2025). Following these guidelines is intended to maximize compatibility with various MCP clients (like IDE integrations), leverage the SDK's intended patterns, and prevent common issues.

**Note:** Different MCP clients support varying levels of protocol features (Tools, Resources, Prompts). Adhering to the standard ensures broader compatibility. See [Client Feature Matrix](https://modelcontextprotocol.io/clients) for details.

**References:**

* [MCP Tools Concept](https://modelcontextprotocol.io/docs/concepts/tools)
* [MCP Debugging Guide](https://modelcontextprotocol.io/docs/tools/debugging)
* [Pydantic Documentation](https://docs.pydantic.dev/)

## 1. Tool Definition and Registration

Tools are exposed to clients via the `tools/list` mechanism. The server needs to define the tool's metadata.

**DO:**

* **Define Tool Metadata with Pydantic:** Ensure each tool has a clear `name` and `description`. Define the input structure using a Pydantic `BaseModel`. Use the model's `.schema()` (or `.model_json_schema()` in Pydantic v2+) method to generate the `inputSchema`. Pydantic fields (`Field`) allow embedding descriptions and validation rules directly in the model.

* Example `types.Tool` structure using Pydantic:

    ```python
    from mcp import types
    from pydantic import BaseModel, Field
    import json # Needed for schema generation if not using built-in methods directly

    # Define the input structure using Pydantic
    class CalculateSumInput(BaseModel):
        a: float = Field(description="The first number")
        b: float = Field(description="The second number")

    # Create the Tool definition
    example_tool = types.Tool(
        name="calculate_sum",
        description="Add two numbers together. Use this when needing to compute the sum of two numeric values.",
        # Generate the JSON schema from the Pydantic model
        # For Pydantic V1: inputSchema=CalculateSumInput.schema()
        # For Pydantic V2: inputSchema=CalculateSumInput.model_json_schema()
        inputSchema=CalculateSumInput.model_json_schema() # Assuming Pydantic v2+
    )

    # Alternative: If using a Tool subclass (less common with base SDK)
    # class CalculateSumTool(types.Tool):
    #     name = "calculate_sum"
    #     description = "Add two numbers together. Use this when needing to compute the sum of two numeric values."
    #     inputSchema = CalculateSumInput.model_json_schema()
    # example_tool = CalculateSumTool()

    ```

* **Define Models for Each Tool:** For a server with multiple tools, define a separate Pydantic `BaseModel` for each tool's input arguments, as seen in `mcp_server_git/server.py`:

    ```python
    # From mcp_server_git/server.py
    from pydantic import BaseModel
    from enum import Enum

    class GitStatusInput(BaseModel):
        repo_path: str

    class GitAddInput(BaseModel):
        repo_path: str
        files: list[str]

    class GitCommitInput(BaseModel):
        repo_path: str
        message: str

    # ... other input models ...

    class GitTools(str, Enum):
        STATUS = "git_status"
        ADD = "git_add"
        COMMIT = "git_commit"
        # ... other tool names ...
    ```

* **Register Tools:** Use the appropriate mechanism provided by the SDK (e.g., passing a list of tool definitions to the server constructor or using a registration method) to make the defined tools discoverable. The `list_tools` function in `mcp_server_git/server.py` provides a clear example:

    ```python
    # From mcp_server_git/server.py
    from mcp import types

    # ... Assume Pydantic models (GitStatusInput, GitAddInput, etc.) and GitTools Enum are defined ...

    # Within the server class or using a decorator like @mcp.server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name=GitTools.STATUS,
                description="Shows the working tree status",
                inputSchema=GitStatusInput.model_json_schema(), # Pydantic v2+
            ),
            types.Tool(
                name=GitTools.ADD,
                description="Adds file contents to the staging area",
                inputSchema=GitAddInput.model_json_schema(),
            ),
            types.Tool(
                name=GitTools.COMMIT,
                description="Records changes to the repository",
                inputSchema=GitCommitInput.model_json_schema(),
            ),
            # ... registrations for other tools ...
        ]
    ```

* **Leverage Pydantic Features:** Use Pydantic's features like `Field` for descriptions, default values, validation constraints (e.g., `gt`, `le`, `pattern`) within your input models.

**DON'T:**

* **DON'T Manually Construct JSON Schemas:** Let Pydantic generate the `inputSchema` from your models to ensure consistency and reduce errors.

## 2. Tool Implementation (`call_tool`)

The core logic executes when a client invokes a tool via `tools/call`.

**DO:**

* **Implement Central Handler (if using low-level SDK):** The base SDK often uses a single handler (like `@app.call_tool()` or a method in a server class) that receives the `name` and `arguments` (dict). Your logic will dispatch based on the `name`. The `mcp_server_git/server.py` uses a `match` statement for this:

    ```python
    # Simplified structure from mcp_server_git/server.py
    from mcp import types
    from pathlib import Path
    import git # Assuming GitPython library is used
    # Assume Pydantic models and GitTools Enum are defined

    # Within the server class or using a decorator like @mcp.server.call_tool()
    async def call_tool(name: str, arguments: dict) -> types.CallToolResult: # Return type adjusted for guideline
        repo_path = Path(arguments["repo_path"]) # Common argument extraction

        # Example: Handle git init separately (doesn't need existing repo)
        if name == GitTools.INIT:
            # ... git_init logic ...
            result = git_init(str(repo_path))
            return types.CallToolResult(content=[types.TextContent(type="text", text=result)])

        # For other commands requiring a repo
        try:
            repo = git.Repo(repo_path)
        except git.InvalidGitRepositoryError as e:
            # Handle error if repo is invalid
            return types.CallToolResult(isError=True, content=[types.TextContent(type="text", text=f"Git Error: {e}")])

        # *** Guideline Recommendation: Perform Pydantic validation here ***
        # try:
        #     if name == GitTools.STATUS:
        #         input_data = GitStatusInput(**arguments)
        #     elif name == GitTools.ADD:
        #         input_data = GitAddInput(**arguments)
        #     # ... etc for other tools
        # except ValidationError as e:
        #     return types.CallToolResult(isError=True, content=[...])

        # Dispatch based on tool name (Git server example accesses dict directly)
        match name:
            case GitTools.STATUS:
                # Access arguments directly (as in Git server example)
                # status_input = GitStatusInput(**arguments) # Recommended validation
                status_result = git_status(repo)
                content = [types.TextContent(type="text", text=f"Repository status:\n{status_result}")]
            case GitTools.ADD:
                # files = arguments["files"] # Direct access from Git server example
                # add_input = GitAddInput(**arguments) # Recommended validation
                # files = add_input.files # Access via validated model
                add_result = git_add(repo, arguments["files"])
                content = [types.TextContent(type="text", text=add_result)]
            case GitTools.COMMIT:
                # message = arguments["message"] # Direct access
                # commit_input = GitCommitInput(**arguments) # Recommended
                # message = commit_input.message # Recommended
                commit_result = git_commit(repo, arguments["message"])
                content = [types.TextContent(type="text", text=commit_result)]
            # ... cases for other tools ...
            case _:
                return types.CallToolResult(
                    isError=True,
                    content=[types.TextContent(type="text", text=f"Unknown tool: {name}")]
                )
                # raise ValueError(f"Unknown tool: {name}") # Alternative: Raise internal error

        return types.CallToolResult(content=content)

        # Note: The actual git_server.py returns list[TextContent] directly
        #       which is slightly non-compliant. Returning CallToolResult is preferred.

    ```

* **Validate Input with Pydantic:** Inside your handler, *before* executing the core tool logic, instantiate the corresponding Pydantic input model using the received `arguments` dictionary. This performs validation and type coercion. Catch `pydantic.ValidationError`. **(Note: While the provided Git server example often accesses the `arguments` dictionary directly within the `match` cases, the recommended practice shown in the comments above is to validate first).**

* **Return `types.CallToolResult`:** The standard successful return should be an instance of `mcp.types.CallToolResult`. The `mcp_server_git/server.py` example often returns `list[TextContent]` directly, but wrapping it in `CallToolResult` is more compliant with the spec, especially for handling errors correctly.
* **Populate `content` List:** The `content` field of the result must be a *list* containing objects representing the output, using MCP content types.
* **Use Specific `types.Content` Objects:** Use appropriate content types from the SDK. The Git server primarily uses `TextContent`:

    ```python
    # Inside the call_tool match statement for GitTools.STATUS
    status_result = git_status(repo)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Repository status:\n{status_result}")]
    )
    ```

* **Ensure JSON Serializable Content:** The data *within* the content objects (e.g., the `text` in `TextContent`) must be JSON serializable if it's not a primitive type already.

**DON'T:**

* **DON'T Return Plain Dictionaries:** Avoid returning generic Python dictionaries like `{"result": "some_value"}`. Use the specific `types.CallToolResult` and `types.Content` structures.
* **DON'T Return `None`:** Return a `types.CallToolResult` with potentially an empty `content` list if appropriate, but not `None`.
* **DON'T Return Bare Strings/Numbers:** Wrap primitive results in the appropriate `types.Content` object (e.g., `types.TextContent`).

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

Errors occurring *during the execution of the tool's logic* (after successful Pydantic validation) should be reported back to the client using the standard `isError=True` result structure.

**DO:**

* **Catch Tool-Specific Exceptions:** Use `try...except` blocks *after* the Pydantic validation block to catch errors specific to the tool's operation (e.g., API call failures, file not found, division by zero, business logic failures).
* **Return `types.CallToolResult` with `isError=True`:** On catching an execution exception, return `CallToolResult(isError=True, ...)` as shown in the example above.
* **Distinguish Validation vs. Execution Errors:** Provide clear error messages in the `content` distinguishing between input validation failures (from `ValidationError`) and subsequent execution failures.

**DON'T:**

* **DON'T Let Pydantic `ValidationError` Leak:** Catch `ValidationError` specifically and return the `isError=True` structure. Do not let it propagate as an unhandled exception, which might incorrectly trigger a protocol-level error.

## 5. Protocol-Level Error Handling

Protocol-level errors occur *outside* the successful execution of a tool's core logic.

**DO:**

* **Let Server/SDK Handle:** Errors like malformed requests (invalid JSON), failed authentication, or the server being unable to find the requested tool (`METHOD_NOT_FOUND`) should generally result in standard JSON-RPC error responses raised by the server framework or base SDK. These typically use codes like `-32700`, `-32600`, `-32601`, `-32603`.
* **Distinguish `INVALID_PARAMS` (`-32602`):** This code is typically reserved for errors where the *request structure itself* is invalid before even attempting Pydantic validation (e.g., missing required `name` or `arguments` fields in the `tools/call` request). It should *not* generally be used for Pydantic validation failures, which are handled by returning `isError=True` within the tool result.

**DON'T:**

* **DON'T Raise `McpError` for Pydantic Validation Failures:** Catch `ValidationError` within your tool handler and return `CallToolResult(isError=True, ...)`. Raising `McpError` for this bypasses the mechanism allowing the LLM to potentially see and correct input errors.

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
* **Log Pydantic Validation Errors:** When a `ValidationError` is caught, log the specifics of the validation failure server-side (potentially at `WARNING` level, as it's an issue with the client input). The detailed `e.errors()` or `e.json()` from Pydantic can be useful here, but avoid logging excessively verbose data unless needed for debugging.
* **Log Tool Execution Errors in Detail:** When catching other exceptions *after* validation (before returning `isError=True`), log the *full* error details, including stack trace (`exc_info=True`), typically at `ERROR` level.

**DON'T:**

* **DON'T Log to `stdout` (for Stdio Transport):** This will break the MCP communication.
* **DON'T Rely Solely on Returned Errors:** The error returned to the client is often brief; detailed logs are essential for diagnosis.
* **DON'T Use `print()`:** Use the structured logger (`stderr` or `session.send_log_message`).

## 7. Input Validation

Validation is essential for robustness and security, primarily handled by Pydantic.

**DO:**

* **Define Schema Accurately with Pydantic:** The primary validation layer *is* the Pydantic model derived from the `inputSchema`. Use Pydantic's built-in validators (`Field` constraints, custom validators) effectively.
* **Handle `ValidationError`:** Explicitly catch `pydantic.ValidationError` during model instantiation in your tool handler and return `CallToolResult(isError=True, ...)` with a clear message derived from the validation error.
* **Perform Business Logic Validation:** After Pydantic validation passes, perform any additional *business logic* validation (e.g., checking if a user ID exists in a database, if a value is semantically valid in the current context) within the tool's `try...except` block. Raise custom exceptions (like `ValueError`) for these failures, which are then caught and returned as `isError=True`.

**DON'T:**

* **DON'T Re-implement Basic Type/Format Validation:** Rely on Pydantic for structural and type validation defined in the model. Focus tool-specific validation logic on semantics and business rules.

## 8. Debugging and Troubleshooting

Reference: [MCP Debugging Guide](https://modelcontextprotocol.io/docs/tools/debugging)

**DO:**

* **Check Server Logs:** Regularly inspect server logs (often captured by the host application like Claude Desktop, potentially in `~/Library/Logs/Claude/mcp*.log` on macOS, or wherever your server directs `stderr`).
* **Use the MCP Inspector:** For direct testing and iteration during development without a full client, use the `npx @modelcontextprotocol/inspector <server_command>` tool.
* **Verify Working Directory:** Be aware that servers launched by host applications might have an unexpected working directory (e.g., `/` on macOS). Use absolute paths for file access within tools or ensure paths are relative to a known, configured location.
* **Manage Environment Variables:** Servers launched by hosts may inherit only a limited set of environment variables (`USER`, `HOME`, `PATH`). If your tools rely on specific environment variables (`API_KEY`s, etc.), ensure they are explicitly passed or configured for the server process (e.g., via host config like `claude_desktop_config.json` or systemd unit files).
* **Test Standalone:** If issues occur, try running the server script directly from the command line to isolate problems from the host application environment.
* **Restart Server/Client:** Remember to restart the server after code changes and potentially the client application after configuration changes.
* **Inspect Validation Errors:** Check server logs specifically for `ValidationError` messages to understand why Pydantic rejected certain inputs.
* **Test with MCP Inspector:** Use the `npx @modelcontextprotocol/inspector` to send specific arguments and test both successful validation/execution and expected error handling (both validation errors and execution errors).

**DON'T:**

* **DON'T Assume CWD:** Avoid relying on the current working directory being the project root when the server is launched by a host.
* **DON'T Assume Full Environment Inheritance:** Explicitly manage required environment variables.

## 9. Server Entry Point and Initialization (Example)

While the MCP specification focuses on the protocol interactions, a typical Python MCP server needs an entry point to start, configure logging, and run the main asynchronous event loop.
The `mcp_server_git/__init__.py` provides a good example using `click` for argument parsing and standard `logging`:

```python
# Example structure based on mcp_server_git/__init__.py
import click
from pathlib import Path
import logging
import sys
import asyncio

# Assuming 'serve' is the main async function that sets up and runs the MCP Server
from .server import serve # Make sure to import your server logic

@click.command()
@click.option("--repository", "-r", type=Path, help="Optional path to a default resource (e.g., Git repository)")
@click.option("-v", "--verbose", count=True, help="Increase logging verbosity (-v for INFO, -vv for DEBUG)")
def main(repository: Path | None, verbose: int) -> None:
    """Main entry point for the MCP server."""

    # 1. Configure Logging Level based on verbosity
    logging_level = logging.WARN
    if verbose == 1:
        logging_level = logging.INFO
    elif verbose >= 2:
        logging_level = logging.DEBUG

    # 2. Setup standard Python logging, directing to stderr for MCP stdio transport
    logging.basicConfig(level=logging_level, stream=sys.stderr,
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger = logging.getLogger(__name__) # Get logger for the entry point
    logger.info(f"Starting server with log level {logging.getLevelName(logging_level)}")

    # 3. Run the main asynchronous server function
    try:
        # asyncio.run() starts the event loop and runs the async function
        asyncio.run(serve(repository)) # Pass necessary config/arguments to your server setup
    except Exception as e:
        # Log critical errors that might prevent the server from running
        logger.critical(f"Server exited with unexpected error: {e}", exc_info=True)
        sys.exit(1) # Exit with a non-zero code to indicate failure

if __name__ == "__main__":
    # This makes the script executable
    main()

```

**Key Points:**

* **Argument Parsing:** Using libraries like `click` or `argparse` allows for configurable server behavior (e.g., setting default paths, verbosity levels for logging).
* **Logging Setup:** Standard Python `logging` is configured early in the execution. Crucially, for servers using the `stdio` transport (common for local IDE integrations), logs **must** be directed to `sys.stderr` to avoid interfering with the JSON-RPC messages sent over `sys.stdout`.
* **Asyncio:** MCP servers built with the Python SDK are inherently asynchronous to handle concurrent requests efficiently. The core server logic (tool registration, request handling in `serve`) will be `async`. `asyncio.run()` is the standard way to start the event loop and run the main `async def serve(...)` function from the synchronous `main` entry point.
* **Error Handling:** A top-level `try...except` block in `main` is good practice to catch critical errors during server startup or unexpected failures in the main loop, ensuring they get logged before the process exits.

## Summary

Adhering strictly to the MCP SDK's patterns, especially using `mcp.types` for return values, is key. Integrating **Pydantic** for defining `inputSchema` and validating arguments within the `call_tool` handler provides robust type safety and input validation. Handling `pydantic.ValidationError` correctly by returning `CallToolResult(isError=True, ...)` allows clients/LLMs to potentially react to input issues. Distinguish these validation errors from subsequent tool execution errors, which should also be caught and returned using `isError=True`. Leveraging server-side logging (configured early and directed to `stderr`) and understanding common debugging pitfalls will further improve development efficiency and tool robustness. This robust approach enhances compatibility and stability compared to manual schema management or lighter frameworks.
