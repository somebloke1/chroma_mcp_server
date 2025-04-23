# Dockerfile for Chroma MCP Server
FROM python:3.11-slim

# Create and set working directory
WORKDIR /app

# Copy application code
COPY . /app

# Install package with all extras (if required for GPU and API embeddings models)
# Note: This requires up to 10 GB of disk space for the image
#RUN pip install --no-cache-dir .[full]

# Install package without extras (for default/accurate CPU embeddings models)
# Note: This requires up to 1 GB of disk space for the image
RUN pip install --no-cache-dir .

# Expose default MCP port
EXPOSE 8000

# Default command
ENTRYPOINT ["chroma-mcp-server"]
