# Smithery Integration Guide for Chroma MCP Server

This document outlines how to integrate the Chroma MCP Server with Smithery after completing the Hatch migration. **Crucially, this guide focuses on making the server discoverable and runnable *locally* on a user's machine via the Smithery CLI and `stdio` communication.** It does **not** cover deploying or hosting the server online via Smithery Deployments.

## Scope: Local Execution Only (No Online Hosting)

This integration enables AI clients (like Claude Desktop or VSCode extensions using the Smithery CLI) to find, install (via `pip`), and run your `chroma-mcp-server` package **locally**. All execution and data handling occur on the user's machine.

**Online hosting via Smithery Deployments is intentionally not supported by this server.** This is because the server, especially when using the `persistent` client type, may interact with local file systems and potentially sensitive user data. To maintain data privacy and security, execution must remain local, and data should not be processed by external hosting services like Smithery Deployments.

Online hosting would also require providing a `Dockerfile` for building the server image and potentially supporting WebSocket communication, which is beyond the scope of this Python package designed for local execution.

## What is Smithery?

Smithery is a package management system and registry designed specifically for MCP servers, allowing AI clients to easily discover and use tools. By integrating our Chroma MCP Server with Smithery **for local execution**, we make it available through the Smithery ecosystem, enabling seamless discovery and local installation.

## Prerequisites

- Completed Hatch migration (see `hatch_migration_plan.md`)
- A working, Hatch-packaged Chroma MCP Server (runnable via `chroma-mcp-server` script)
- Published package (or ready-to-publish) on PyPI

## Creating a Smithery Configuration

### Step 1: Add a `smithery.yaml` File

Create a `smithery.yaml` file in the root of your project (ensure it reflects the updated configuration using environment variables and the `chroma-mcp-server` command as discussed previously):

```yaml
# Smithery configuration file: https://smithery.ai/docs/config#smitheryyaml
# This config enables LOCAL EXECUTION via Smithery CLI over stdio.

startCommand:
  type: stdio
  configSchema:
    # JSON Schema matching cli.py arguments (using camelCase)
    # Example (ensure this matches your actual updated smithery.yaml):
    type: object
    properties:
      clientType:
        type: string
        enum: ["ephemeral", "persistent", "http", "cloud"]
        description: "Type of Chroma client to use (ephemeral, persistent, http, cloud)"
        default: "ephemeral"
      dataDir:
        type: string
        description: "Path to data directory for persistent client"
      # ... other properties corresponding to cli.py args ...
      embeddingFunctionName:
        type: string
        description: "Name of the embedding function to use"
        default: "default"
    required: []
  commandFunction:
    # JS function setting environment variables and calling the script entry point
    # Example (ensure this matches your actual updated smithery.yaml):
    |-
    (config) => {
      const env = {};
      if (config.clientType !== undefined) env.CHROMA_CLIENT_TYPE = config.clientType;
      if (config.dataDir !== undefined) env.CHROMA_DATA_DIR = config.dataDir;
      // ... set other env vars based on config ...
      if (config.embeddingFunctionName !== undefined) env.CHROMA_EMBEDDING_FUNCTION = config.embeddingFunctionName;

      return {
        command: 'chroma-mcp-server', // Matches pyproject.toml [project.scripts]
        args: [],
        env: env
      };
    }
  exampleConfig:
    clientType: "persistent"
    dataDir: "./local_chroma_data"
    # ... other example settings ...
```

*(**Note:** Ensure the YAML content above reflects the actual, updated `smithery.yaml` configuration in your project.)*

### Step 2: Update Your Package Metadata

Ensure your `pyproject.toml` includes Smithery-specific metadata:

```toml
# ... other project settings ...

[project.scripts]
chroma-mcp-server = "chroma_mcp.cli:main"

# Entry point for Smithery ecosystem integration (may aid discovery)
[project.entry-points."smithery.mcps"]
chroma = "chroma_mcp.cli:main"

[project.urls]
Homepage = "https://github.com/your-username/chroma-mcp-server"
Documentation = "https://github.com/your-username/chroma-mcp-server#readme"
Repository = "https://github.com/your-username/chroma-mcp-server.git"
# Optional: Add a link if you register the package on Smithery website
# Smithery = "https://smithery.ai/packages/your-package-name"

# ... rest of pyproject.toml ...
```

*(**Note:** Replace `your-username` and potentially the Smithery URL)*

### Step 3: Adapt Your Server Module for Smithery

Your `chroma_mcp.cli:main` function already serves as the entry point that reads arguments (defaulting from environment variables set by Smithery). Ensure it handles the configuration correctly. No specific structural changes should be needed beyond what's required for standard command-line execution using `argparse` and `os.getenv`.

```python
# Example structure in chroma_mcp/cli.py
import os
import argparse

def parse_args():
    parser = argparse.ArgumentParser(...)
    # Arguments should read defaults from os.getenv, matching smithery.yaml env vars
    parser.add_argument("--client-type", default=os.getenv("CHROMA_CLIENT_TYPE", "ephemeral"), ...)
    # ... other arguments ...
    return parser.parse_args()

def main():
    args = parse_args()
    # ... configure and run server using args ...

# Ensure this file is the target of the 'chroma-mcp-server' script
```

## Registering with Smithery

Registering makes your server *discoverable* via the Smithery registry and configures how clients should interact with it (e.g., local execution vs. online hosting). This process is done via the Smithery website after your package is available on PyPI.

**Steps:**

1. **Publish to PyPI:** Ensure the desired version of `chroma-mcp-server` is published on PyPI.

2. **Visit Smithery Website:** Go to [https://smithery.ai/](https://smithery.ai/) and log in (typically with GitHub).

3. **Add/Claim Server:**
    - Look for an option to "Add Server" or similar.
    - If Smithery might have already discovered your package from PyPI or GitHub, you might need to "Claim" it.

4. **Connect GitHub Repository:**
    - Configure the server entry to point to your GitHub repository (`djm81/chroma_mcp_server`).
    - Grant necessary permissions if requested.

5. **Configure Server Settings:**
    - Smithery should detect the `smithery.yaml` file in your repository root.
    - Review the detected configuration.
    - **Set Execution Mode:** Find the settings related to deployment or execution. Ensure you configure it for **local execution only**. Disable any options related to "Smithery Deployments" or online hosting.
    - Specify the base directory if your `smithery.yaml` is not in the repo root (though it should be in this project).

Once saved, your server should be listed on Smithery and configured such that the `@smithery/cli` tool will facilitate local installation (`install` command using `pip`) and local execution (`run` command interpreting your `smithery.yaml`).

## Testing Smithery Integration

### Test Local Execution via Smithery CLI

After registering on the Smithery website and publishing to PyPI, test the end-to-end local flow:

```bash
# Install (fetches from PyPI via pip)
npx -y @smithery/cli install chroma-mcp-server

# Run with default config (ephemeral)
npx -y @smithery/cli run chroma-mcp-server

# Run with specific config (persistent)
npx -y @smithery/cli run chroma-mcp-server --config '{ "clientType": "persistent", "dataDir": "./test-chroma-data" }'
```

### Test with MCP Inspector

Use the official MCP Inspector tool for visual testing of the MCP communication:

```bash
# Install the inspector if you haven't already
# npm install -g @modelcontextprotocol/inspector

# Run the inspector, telling it how to start your server
# Example using the script directly (requires environment to be set up):
# npx @modelcontextprotocol/inspector chroma-mcp-server -- --client-type persistent --data-dir ./test-data

# Example using Smithery CLI to launch (recommended):
npx @modelcontextprotocol/inspector npx -y @smithery/cli run chroma-mcp-server --config '{ "clientType": "persistent", "dataDir": "./test-chroma-data" }'

# Example using default ephemeral client:
npx @modelcontextprotocol/inspector npx -y @smithery/cli run chroma-mcp-server
```

The inspector will launch your server locally and provide a UI to send MCP requests and view responses.

### Test with Client Integrations (e.g., Claude Desktop)

1. Add the following to your Claude Desktop configuration (or similar for other clients), adjusting the `env` as needed:

    ```json
    {
      "mcpServers": {
        "chroma": {
          "command": "npx",
          "args": ["-y", "@smithery/cli", "run", "chroma-mcp-server"],
          "env": {
              "clientType": "persistent",
              "dataDir": "/path/to/your/local/data"
          }
        }
      }
    }
    ```

    *(Note: The `env` here provides the configuration *object* that the `commandFunction` in `smithery.yaml` receives)*

2. Restart Claude Desktop and test by having Claude interact with the Chroma tools (create collections, add documents, query, etc.).

## Integration with Other MCP Clients

Similar configuration patterns apply to other clients that support launching MCP servers via commands.

### VSCode Cline Extension

```json
{
  "mcpServers": {
    "chroma": {
      "command": "npx",
      "args": ["-y", "@smithery/cli", "run", "chroma-mcp-server"],
      "env": { // Config object passed to smithery.yaml commandFunction
        "clientType": "persistent",
        "dataDir": "/path/to/local/data"
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
    # GoMCP might require passing config differently, check its docs.
    # If it uses env vars directly, you might bypass smithery run
    # or configure it to pass the config object if supported.
    # The example below assumes direct env var setting, bypassing smithery.yaml's config handling:
    # env:
    #   CHROMA_CLIENT_TYPE: persistent
    #   CHROMA_DATA_DIR: /path/to/data
    # Check GoMCP documentation for the correct way to pass config when using 'npx ... run'.
```

## Troubleshooting

### Common Issues and Solutions

1. **Package Not Found by Smithery (`install` or `publish`)**
    - Ensure your package is successfully published and available on PyPI.
    - Check the package name used (`chroma-mcp-server`) matches PyPI exactly.
    - Verify `smithery.yaml` is correctly placed (usually project root for non-monorepos).

2. **Command Not Running Correctly (`npx ... run`)**
    - Test your script entry point directly: `chroma-mcp-server -- --help` (ensure environment is activated or package installed globally).
    - Verify the `commandFunction` in `smithery.yaml` correctly sets environment variables and calls `chroma-mcp-server`.
    - Check server logs (`--log-dir`) for startup errors. Ensure necessary environment variables (like API keys for specific embedding functions) are available in the execution environment where `npx ... run` is called.

3. **Integration Issues with Claude / Other Clients**
    - Verify the client configuration (command, args, env/config object).
    - Ensure the client can execute the `npx` command.
    - Check client logs for errors related to launching or communicating with the MCP server.
    - Confirm the server starts correctly and listens on `stdio` when launched via the client's configured command.

## Best Practices

1. **Version Management**
    - Keep `pyproject.toml` version up-to-date.
    - Document breaking changes clearly.

2. **Configuration (`smithery.yaml` & `cli.py`)**
    - Ensure `smithery.yaml` `configSchema` accurately reflects options in `cli.py`.
    - Use environment variables (`os.getenv`) in `cli.py` to read defaults provided by `smithery.yaml` `commandFunction`.
    - Provide clear descriptions in `smithery.yaml` and help text in `cli.py`.

3. **Documentation**
    - Maintain clear documentation (`README.md`, etc.) explaining setup, configuration (especially environment variables needed for different embedding functions/client types), and usage.
    - Include examples for different client types and common configurations.

## Next Steps

- [ ] Implement automatic testing for Smithery integration (e.g., running `npx @smithery/cli run ...` in CI).
- [ ] Create example notebooks or scripts showing clients using the Chroma MCP Server locally.
- [ ] Develop CI/CD pipeline for automatic publishing to PyPI upon tagging releases.

## References

- [Smithery Documentation](https://smithery.ai/docs)
- [Claude Desktop Configuration Guide](https://docs.anthropic.com/claude/docs/claude-desktop-configuration)
- [MCP Protocol Specification](https://github.com/anthropics/anthropic-model-context-protocol)
- [MCP Inspector Tool](https://github.com/modelcontextprotocol/inspector)
