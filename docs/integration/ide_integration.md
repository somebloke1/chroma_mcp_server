# IDE Integration for Thinking Utilities

This guide provides examples of how to integrate the `record-thought` console script into popular IDEs, making it easier to capture thoughts during your development workflow.

The goal is typically to create a command or keybinding that runs `record-thought` and passes the currently selected text (or prompts for input) as the thought content.

Refer to the [record-thought script documentation](../scripts/record-thought.md) for command-line options.

## Prerequisites

- `chroma-mcp-server` installed with thinking tools (`pip install "chroma-mcp-server"`).
- `hatch` installed and available in your terminal environment.
- The project must be managed by `hatch` so that `hatch run` can find the correct environment.
- The `record-thought` command (and its underlying module `chroma_mcp_thinking.thinking_cli`) must be runnable via `hatch run python -m ...`.
- The script will automatically start the required Chroma MCP server in stdio mode as a subprocess.

## VS Code / Cursor / Windsurf Integration

VS Code, Cursor and Windsurf allow defining custom tasks and keybindings.

### Method 1: Using Tasks (`.vscode/tasks.json`)

Define a task to run the `record-thought` command. You can trigger this task via the Command Palette (Cmd/Ctrl+Shift+P -> "Run Task").

1. Create or open the `.vscode/tasks.json` file in your project root.
2. Add the following task definition:

    ```json
    {
      "version": "2.0.0",
      "tasks": [
        {
          "label": "Record Selected Thought",
          "type": "shell",
          // Use hatch run to execute within the project environment
          // Using python -m ensures module resolution works correctly
          // Remember to escape quotes for the shell command
          "command": "hatch run python -m chroma_mcp_thinking.thinking_cli record --thought \"${selectedText}\"",
          "problemMatcher": [],
          "presentation": {
            "echo": true,
            "reveal": "silent", // Don't reveal terminal unless error
            "focus": false,
            "panel": "shared",
            "showReuseMessage": false,
            "clear": false
          },
          "detail": "Records the currently selected text as a thought using record-thought CLI via hatch."
        }
      ]
    }
    ```

3. **Usage:** Select text in your editor, open the Command Palette, type "Run Task", and choose "Record Selected Thought".

### Method 2: Using Keybindings (`keybindings.json`)

Bind a keyboard shortcut directly to the command for faster access.

1. Open Keyboard Shortcuts (Cmd/Ctrl+K Cmd/Ctrl+S or File > Preferences > Keyboard Shortcuts).
2. Click the `Open Keyboard Shortcuts (JSON)` icon in the top right.
3. Add the following entry to your `keybindings.json` file (choose an unbound key combination):

    ```json
    {
        "key": "ctrl+alt+t", // Example keybinding - change as needed
        "command": "workbench.action.terminal.sendSequence",
        "args": {
            // Ensure newline at the end to execute the command
            // Use hatch run and --thought option
            "text": "hatch run python -m chroma_mcp_thinking.thinking_cli record --thought \"${selectedText}\"\u000D"
        },
        "when": "editorHasSelection" // Only active when text is selected
    }
    ```

4. **Usage:** Select text in your editor and press your chosen keybinding (e.g., `Ctrl+Alt+T`). The command will run in the integrated terminal.

**Note:** Using `${selectedText}` directly passes the selected content. Be mindful of shell special characters within the selected text; complex selections might require more sophisticated scripting.

## JetBrains IDEs (PyCharm, IntelliJ IDEA, etc.) Integration

JetBrains IDEs allow configuring "External Tools".

1. Go to `File` > `Settings` (or `Preferences` on macOS).
2. Navigate to `Tools` > `External Tools`.
3. Click the `+` icon to add a new tool.
4. Configure the tool:
    - **Name:** `Record Thought (Hatch)`
    - **Program:** `hatch` (Assumes `hatch` is in your system PATH)
    - **Arguments:** `run python -m chroma_mcp_thinking.thinking_cli record "$SelectedText$"`
    - **Working directory:** `$ProjectFileDir$`
    - *(Optional)* Under `Advanced Options`, you might untick "Open console" if you don't need to see the output immediately.
5. Click `OK` to save.
6. **Usage:** Select text in your editor, right-click, go to `External Tools`, and select `Record Thought`. You can also assign a keyboard shortcut to this external tool via `Keymap` settings.

## Other IDEs

Most other programmable IDEs or text editors (e.g., Sublime Text, Neovim) offer ways to run external shell commands and bind them to shortcuts or commands, often involving configuration files or scripting. Consult your specific IDE's documentation for running shell commands and accessing selected text.

The core principle remains the same: execute `hatch run python -m chroma_mcp_thinking.thinking_cli record "<selected_text_or_input>"` from the project root directory.
