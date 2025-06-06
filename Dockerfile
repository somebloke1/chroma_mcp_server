FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install the package with full dependencies
RUN pip install --no-cache-dir -e ".[full]"

# Create data and logs directories
RUN mkdir -p /app/data /app/logs

# Expose MCP server port
EXPOSE 3033

# Set environment variables
ENV CHROMA_CLIENT_TYPE=persistent
ENV CHROMA_DATA_DIR=/app/data
ENV CHROMA_LOG_DIR=/app/logs
ENV LOG_LEVEL=INFO
ENV MCP_LOG_LEVEL=INFO
ENV MCP_SERVER_LOG_LEVEL=INFO

# Start the Chroma MCP server
CMD ["chroma-mcp-server", "--client-type", "persistent", "--data-dir", "/app/data"]