# Smithery Integration Guide for Chroma MCP Server

This document outlines how to integrate the Chroma MCP Server with Smithery after completing the Hatch migration, making it distributable through the Smithery package ecosystem.

## What is Smithery?

Smithery is a package management system designed specifically for MCP servers, allowing AI clients like Claude to easily discover and use tools. By integrating our Chroma MCP Server with Smithery, we make it available through the Smithery ecosystem, enabling seamless discovery and installation.

## Prerequisites

- Completed Hatch migration (see `hatch_migration_plan.md`)
- A working, Hatch-packaged Chroma MCP Server
- Published package (or ready-to-publish) on PyPI

## Creating a Smithery Configuration

### Step 1: Add a `smithery.yaml` File

Create a `smithery.yaml` file in the root of your project:

```yaml
# Smithery configuration file: https://smithery.ai/docs/config#smitheryyaml

startCommand:
  type: stdio
  configSchema:
    # JSON Schema defining the configuration options for the MCP.
    type: object
    properties:
      client_type:
        type: string
        enum: ["ephemeral", "persistent", "http", "cloud"]
        description: "Type of Chroma client to use"
        default: "ephemeral"
      data_dir:
        type: string
        description: "Path to data directory for persistent client"
      host:
        type: string
        description: "Host address for HTTP client"
      port:
        type: string
        description: "Port for HTTP client"
      ssl:
        type: boolean
        description: "Whether to use SSL for HTTP client"
        default: false
      tenant:
        type: string
        description: "Tenant ID for Cloud client"
      database:
        type: string
        description: "Database name for Cloud client"
      api_key:
        type: string
        description: "API key for Cloud client"
    required: []
  commandFunction:
    # A JS function that produces the CLI command based on the given config to start the MCP on stdio.
    |-
    (config) => {
      const args = ['chroma-mcp-server'];
      
      if (config.client_type) {
        args.push('--client-type', config.client_type);
      }
      
      if (config.data_dir) {
        args.push('--data-dir', config.data_dir);
      }
      
      if (config.host) {
        args.push('--host', config.host);
      }
      
      if (config.port) {
        args.push('--port', config.port);
      }
      
      if (config.ssl) {
        args.push('--ssl', 'true');
      }
      
      if (config.tenant) {
        args.push('--tenant', config.tenant);
      }
      
      if (config.database) {
        args.push('--database', config.database);
      }
      
      return { command: 'python', args: ['-m', ...args] };
    }
  exampleConfig:
    client_type: "ephemeral"
```

### Step 2: Update Your Package Metadata

Ensure your `pyproject.toml` includes Smithery-specific metadata:

```toml
[project.urls]
Homepage = "https://github.com/your-username/chroma-mcp-server"
Documentation = "https://github.com/your-username/chroma-mcp-server#readme"
Repository = "https://github.com/your-username/chroma-mcp-server.git"
Smithery = "https://smithery.ai/packages/chroma-mcp-server"

[project.entry-points."smithery.mcps"]
chroma = "chroma_mcp.server:main"
```

### Step 3: Adapt Your Server Module for Smithery

Ensure your server module can be invoked both as a command-line tool and from Smithery:

```python
def main():
    """Entry point for both command-line and Smithery invocation."""
    # Your existing server startup code...
    
if __name__ == "__main__":
    main()
```

## Publishing to Smithery

### Step 1: Register with Smithery (if needed)

```bash
npx -y @smithery/cli login
```

### Step 2: Publish Your Package

If your package is already on PyPI, you can register it with Smithery:

```bash
npx -y @smithery/cli publish
```

Or publish it directly to both PyPI and Smithery:

```bash
hatch build
hatch publish
npx -y @smithery/cli publish
```

## Testing Smithery Integration

### Test with Smithery CLI

```bash
npx -y @smithery/cli install chroma-mcp-server --client claude
```

### Test with Claude Desktop

1. Add the following to your Claude Desktop configuration:

    ```json
    {
    "mcpServers": {
        "chroma": {
        "command": "npx",
        "args": ["-y", "@smithery/cli", "run", "chroma-mcp-server"],
        "env": {
            "CHROMA_CLIENT_TYPE": "persistent",
            "CHROMA_DATA_DIR": "/path/to/data"
        }
        }
    }
    }
    ```

2. Restart Claude Desktop and test by having Claude create, query, and manage Chroma collections.

## Integration with Other MCP Clients

### VSCode Cline Extension

```json
{
  "mcpServers": {
    "chroma": {
      "command": "npx",
      "args": ["-y", "@smithery/cli", "run", "chroma-mcp-server"],
      "env": {
        "CHROMA_CLIENT_TYPE": "persistent",
        "CHROMA_DATA_DIR": "/path/to/data"
      }
    }
  }
}
```

### GoMCP

```yaml
mcps:
  chroma:
    command: npx
    args:
      - -y
      - "@smithery/cli"
      - run
      - chroma-mcp-server
    env:
      CHROMA_CLIENT_TYPE: persistent
      CHROMA_DATA_DIR: /path/to/data
```

## Troubleshooting

### Common Issues and Solutions

1. **Package Not Found by Smithery**
   - Ensure your package is correctly published to PyPI
   - Check that smithery.yaml is in the root of your package
   - Verify your entry point is correctly defined in pyproject.toml

2. **Command Not Running Correctly**
   - Test your command manually: `npx -y @smithery/cli run chroma-mcp-server`
   - Check if all required environment variables are set
   - Review logs for any startup errors

3. **Integration Issues with Claude**
   - Verify Claude Desktop configuration
   - Check if Claude can access the MCP server
   - Look for any network or permission issues

## Best Practices

1. **Version Management**
   - Keep smithery.yaml and pyproject.toml versions in sync
   - Document breaking changes clearly when updating versions

2. **Configuration**
   - Provide sensible defaults for all options
   - Validate all user-provided configuration values
   - Use environment variables as a fallback for configuration

3. **Documentation**
   - Include clear examples for different client types
   - Document all available configuration options
   - Provide troubleshooting guides for common issues

## Next Steps

- [ ] Implement automatic testing for Smithery integration
- [ ] Create example notebooks showing Claude using the Chroma MCP Server
- [ ] Develop CI/CD pipeline for automatic publishing to Smithery

## References

- [Smithery Documentation](https://smithery.ai/docs)
- [Claude Desktop Configuration Guide](https://docs.anthropic.com/claude/docs/claude-desktop-configuration)
- [MCP Protocol Specification](https://github.com/anthropics/anthropic-model-context-protocol)
