# Chroma MCP Memory Rules

Chroma MCP Memory Rules define how to consistently capture, structure, and retrieve semantic knowledge within your project. Following these guidelines ensures atomicity, clarity, and context‑awareness, turning your codebase into a living knowledge hub.

## 1. Capture Atomic Knowledge

- Create focused snippets (1–3 sentences) representing a single concept: bug fix, design decision, performance tip, etc.
- Always include metadata:
  - `type`: e.g. `bugfix`, `design`, `optimization`, `security`
  - `module`: file path or component (e.g. `models/user.py`)
  - `tags`: comma‑separated keywords (e.g. `pydantic,validation`)
  - `date`: ISO 8601 format (e.g. `2025-04-22`)
  - `author`: your Git username or alias

- Use the CLI for quick capture:

  ```bash
  mcp capture \
    --type bugfix \
    --module models/user.py \
    --tags pydantic,validation \
    "Fixed ValueError by validating input length."
  ```

## 2. Structure & Formatting

- Write content in Markdown or plain text; wrap code examples in fenced blocks with language specifier.
- Keep lines under 120 characters and avoid trailing spaces.
- Use 2-space indentation for nested lists.
- End each snippet with a single newline.

## 3. Tagging & Organization

- Standardize tags in your project README to ensure consistency.
- Group snippets by module or feature for easier filtering.
- Review and retire obsolete tags during sprint retrospectives.

## 4. Querying & Retrieval

- Perform semantic searches by meaning, not keyword only:

  ```bash
  mcp query "ValueError Pydantic"
  ```

- Filter by metadata:

  ```bash
  mcp query \
    --type bugfix \
    --module models \
    "authentication error"
  ```

- Combine tags and query text to narrow results.

## 5. Integration Points

- **Editor Plugins:** Enable in VSCode, JetBrains IDEs, or Vim for in‑place capture and retrieval.
- **CI Hooks:** Automate snippet capture after test failures or on merge events.
- **Automation Scripts:** Integrate with post-commit or post-build scripts to ensure continuous memory growth.

## 6. Continuous Improvement

- Analyze snippet usage trends to uncover recurring challenges and guide technical debt reduction.
- Merge related snippets to avoid duplication and maintain a lean knowledge base.
- Archive or archive stale entries monthly to keep content relevant.

---

Follow these rules to unlock the full potential of your project's living memory with Chroma MCP Server.
