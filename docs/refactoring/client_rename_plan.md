# Client Rename Plan: chroma-client → chroma-mcp-client

## Rationale

This document outlines the plan to rename the CLI executable from `chroma-client` to `chroma-mcp-client` for the following reasons:

1. **Naming Consistency:** The server is named `chroma-mcp-server`, so the client should follow the same naming pattern
2. **Disambiguation:** Avoids confusion with potential official Chroma client tools
3. **Product Identity:** Clearly associates the client with our specific MCP implementation

## Implementation Plan

### Phase 1: Setup Backward Compatibility

- [x] **Update Entry Points in pyproject.toml:**

  ```toml
  [project.scripts]
  # Keep the old entry point temporarily
  chroma-client = "chroma_mcp_client.deprecated_cli:main"
  # Add the new entry point
  chroma-mcp-client = "chroma_mcp_client.cli:main"
  ```

- [x] **Create Deprecated CLI Wrapper:**
  - [x] Create `src/chroma_mcp_client/deprecated_cli.py` with deprecation warning
  - [x] Implement a simple wrapper that calls the main CLI module with a warning
  - [x] Add unit test for the deprecated CLI wrapper

### Phase 2: Documentation Updates

- [x] **Update Key Documentation:**
  - [x] Update README.md with new command name
  - [x] Add deprecation notice to CHANGELOG.md
  - [x] Update docs where old cli is used

- [x] **Create Migration Guide:**
  - [x] Document in a dedicated migration.md or section in docs/usage/client_commands.md
  - [x] Include examples of replacing old commands with new ones

### Phase 3: Incremental Codebase Updates

- [x] **Update Internal Script References:**
  - [x] Modify scripts in `scripts/` directory that call `chroma-client`
  - [x] Update any tests that reference `chroma-client`

- [x] **Update Documentation References:**
  - [x] Scan and update references in `docs/` directory
  - [x] Update examples in documentation

- [x] **Update local_rag_pipeline_plan_v4.md:**
  - [x] Add references to client renaming
  - [x] Update examples that use the client command

### Phase 4: Testing

- [x] **Unit Tests:**
  - [x] Ensure all unit tests pass with both command names
  - [x] Add specific tests for the deprecated CLI module

- [x] **Integration Tests:**
  - [x] Verify both commands work with identical functionality
  - [x] Test that the deprecation warning appears

- [x] **Manual Testing:**
  - [x] Test both commands with common use cases

### Phase 5: Future Planning

- [x] **Plan for Removal of Backward Compatibility:**
  - [x] Document timeline for removing the old entry point (e.g., in version 0.3.0)
  - [x] Plan for announcement and communication

## Backward Compatibility Strategy

1. **Temporary Dual Entry Points:** Maintain both `chroma-client` and `chroma-mcp-client` in the 0.2.x releases
2. **Deprecation Warning:** Show deprecation warning when using `chroma-client`
3. **Removal Timeline:** Plan to remove `chroma-client` in the 0.3.0 release
4. **Documentation:** Clearly communicate the change in documentation and release notes

## Implementation Notes

### Deprecation Warning Example

```python
import sys
import warnings
from . import cli

def main():
    warnings.warn(
        "The 'chroma-client' command is deprecated and will be removed in version 0.3.0. "
        "Please use 'chroma-mcp-client' instead.", 
        DeprecationWarning, 
        stacklevel=2
    )
    return cli.main()

if __name__ == "__main__":
    sys.exit(main())
```

### Documentation Note Example

```markdown
**Note:** Starting from version 0.2.x, the `chroma-client` command is deprecated and will be removed in version 0.3.0. 
Please use `chroma-mcp-client` instead, which provides identical functionality with a more consistent naming scheme.
```

## References and Related Documents

- [Local RAG Pipeline Plan V4](./local_rag_pipeline_plan_v4.md)
- [MCP SDK Compliance V2](./refactor_plan_mcp_sdk_compliance_v2.md)
