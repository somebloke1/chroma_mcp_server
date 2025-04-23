# Dockerfile for Chroma MCP Server
FROM python:3.11-slim

# Create and set working directory
WORKDIR /app

# Copy application code
COPY . /app

# Install package with all extras
RUN pip install --no-cache-dir .[full]

# Expose default MCP port
EXPOSE 8000

# Default command
ENTRYPOINT ["chroma-mcp-server"]
