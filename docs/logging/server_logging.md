# MCP Server Logging

This document explains how the Chroma MCP Server handles logging to ensure clean JSON communication and proper timestamp management.

## Logging Configuration

### Log Directory

Logs are stored in the directory specified by the `CHROMA_LOG_DIR` environment variable. If not set, this defaults to the `./logs/` directory in the project root.

```bash
# Example setting in .env
CHROMA_LOG_DIR=./custom_logs
```

### Log Retention

The server automatically cleans up old log files based on the retention period specified by the `LOG_RETENTION_DAYS` environment variable. If not set, this defaults to 7 days.

```bash
# Example setting in .env
LOG_RETENTION_DAYS=14  # Keep logs for 14 days
```

Log cleanup happens during server startup, removing log files older than the specified retention period.

### Log Levels

Multiple environment variables control logging levels:

- `LOG_LEVEL`: Sets the default logging level for server components and the client CLI
- `MCP_LOG_LEVEL`: Controls logging level specifically for MCP framework components
- `MCP_SERVER_LOG_LEVEL`: Controls logging level for stdio mode (default: INFO)

Valid values for all log level settings: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## Stdio Mode Improvements

### Per-Execution Log Files

When operating in stdio mode (the default for MCP integrations like Cursor), Python logging output is now redirected to dedicated log files to prevent contamination of the JSON communication stream. These log files have timestamp-based filenames:

```bash
logs/chroma_mcp_stdio_<timestamp>.log
```

For example: `logs/chroma_mcp_stdio_1747049137.log`

This ensures:

1. Clean, pure JSON communication between MCP client and server
2. No logging messages mixing with JSON output, which previously caused parsing errors
3. All logs remain accessible for debugging, just in a separate file

### Implementation

The implementation in `app.py` includes:

1. **Root Logger Configuration**: A comprehensive setup that redirects all Python logging to a file
2. **Null Handler**: Added to prevent any uncaught logs from appearing in stdout/stderr
3. **Timestamp-based Filenames**: Each server execution gets its own log file
4. **Formatter**: Consistent log format with timestamps, logger name, and message

## Timestamp Enforcement

### Server-Side Timestamp Generation

The server automatically enforces the use of system-generated timestamps for all documents stored in ChromaDB collections. This prevents inconsistencies that can occur when AI models use their knowledge cutoff dates instead of the current system time.

### Affected Operations

The timestamp enforcement applies to these components:

1. **Document Tools**: When adding or updating documents in any collection
2. **Collection Tools**: When creating collections with metadata
3. **Thinking Tools**: For sequential thinking and session management

### Benefits

This implementation ensures:

1. Consistent timestamps across all collections
2. Accurate representation of when actions actually occurred
3. Prevention of date-related bugs in temporal analysis
4. Correct chronological ordering of documents regardless of AI model behavior

## Troubleshooting

If you encounter JSON parsing errors in MCP clients:

1. Verify the server is running with the latest version that includes these logging improvements
2. Check if any custom code is writing to stdout/stderr in stdio mode
3. Examine the dedicated log file in `CHROMA_LOG_DIR` for detailed error information

If timestamps appear incorrect:

1. Confirm you're using the latest server version with timestamp enforcement
2. Verify the server's system clock is set correctly
3. For existing collections with incorrect timestamps, consider reindexing or updating the metadata
