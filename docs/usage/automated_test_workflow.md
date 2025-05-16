# Automated Test-Driven Learning Workflow

This document explains how to use the automated test-driven learning workflow to capture, track, and learn from test failures and their resolutions.

## Overview

The automated test workflow provides a seamless way to:

1. Automatically capture test failures and their context
2. Track when tests transition from failing to passing after code changes
3. Create bidirectional links between test fixes, code changes, and chat history
4. Generate validation evidence from successful test transitions
5. Promote high-quality test fixes to derived learnings

Instead of manually tracking each step in the process, the automated workflow handles the entire lifecycle, requiring minimal developer intervention.

## Quick Start

To enable the automated workflow:

```bash
# Set up the workflow (creates git hooks)
chroma-client setup-test-workflow

# Run tests with automatic workflow capture
./scripts/test.sh -c -v --auto-capture-workflow
```

## How It Works

The automated workflow consists of several components that work together:

### 1. Test Execution with Automatic Capture

When you run tests with the `--auto-capture-workflow` flag, the system:

- Runs the tests normally
- If tests fail:
  - Saves the test results XML to a timestamped file
  - Records the git commit hash associated with the failure
  - Creates a workflow state file tracking the failure
  - Stores the failure in the `test_results_v1` collection
- If tests pass:
  - Checks for previous failures to detect transitions
  - If a previous failure is found, compares the results to identify fixes
  - Creates a validation record showing which tests were fixed
  - Correlates the fixes with code changes and chat history

### 2. Git Hooks Integration

The workflow installs two git hooks:

- `pre-push`: Runs tests with automatic workflow capture before pushing
- `post-commit`: Checks for test transitions after a commit

These hooks ensure test transitions are detected and captured even during normal development workflow.

### 3. Bidirectional Linking

When a test transitions from failing to passing, the system:

- Identifies which code files were changed between the failing and passing commits
- Searches the chat history for entries that modified those files
- Creates bidirectional links between the test results, code changes, and chat discussions
- Stores these links in the validation evidence

### 4. Auto-Promotion (Optional)

With the `--auto-promote` flag, the system can:

- Evaluate the quality of test fixes based on validation evidence
- Automatically promote high-confidence fixes to derived learnings
- Create comprehensive, reusable knowledge entries from successful fixes

## Configuration

### Setup Options

```bash
chroma-client setup-test-workflow [OPTIONS]

Options:
  --workspace-dir PATH   Root directory of the workspace (default: current directory)
  --force               Force overwrite of existing git hooks
```

### Test Execution Options

```bash
./scripts/test.sh [OPTIONS]

Options:
  --auto-capture-workflow   Enable automatic test workflow capture
  --log-results             Log test results to validation system
  --before-xml FILE         Path to JUnit XML from before changes for comparison
```

### Checking Test Transitions

```bash
chroma-client check-test-transitions [OPTIONS]

Options:
  --workspace-dir PATH       Root directory of the workspace
  --auto-promote             Automatically promote validated learnings
  --confidence-threshold N   Confidence threshold for auto-promotion (default: 0.8)
```

## Workflow Examples

### Example 1: Capturing a Test Failure and Fix

1. Run tests, which fail:

   ```bash
   ./scripts/test.sh -c -v --auto-capture-workflow
   # ❌ Tests failed - saved results for future comparison
   ```

2. Fix the code based on the test failure

3. Run tests again, which now pass:

   ```bash
   ./scripts/test.sh -c -v --auto-capture-workflow
   # ✅ Tests passed - found previous failure to compare with
   # 📊 Analyzing test transitions...
   ```

4. The system automatically detects the transition, creates validation evidence, and links it to the relevant chat history

### Example 2: Manual Check for Transitions

If you've been working without the `--auto-capture-workflow` flag, you can manually check for transitions:

```bash
chroma-client check-test-transitions
# Processed 2 test transitions
```

### Example 3: Auto-Promoting Learnings

To automatically promote high-confidence fixes to derived learnings:

```bash
chroma-client check-test-transitions --auto-promote
# Processed 2 test transitions
# Auto-promoted 1 learning to derived_learnings_v1
```

## Integration with Learning Ecosystem

The automated test workflow integrates with other components of the Second Brain ecosystem:

- **Chat History**: Test failures and fixes are linked to relevant chat history entries
- **Code Context**: Test results are associated with the code they cover
- **Derived Learnings**: High-quality fixes can be promoted to derived learnings
- **Validation Evidence**: Test transitions provide strong validation evidence

## Best Practices

1. **Always use `--auto-capture-workflow`** when running tests to ensure consistent tracking
2. **Commit frequently** to create clear transition points for test fixes
3. **Include detailed commit messages** to help correlate code changes with test fixes
4. **Review auto-promoted learnings** periodically to ensure quality
5. **Set up the workflow for CI systems** to capture test transitions in automated environments

## Troubleshooting

### Missing Test Transitions

If transitions aren't being detected:

- Ensure the workflow state files (`test_workflow_*.json`) exist in your workspace
- Check that the XML output paths in the state files point to valid files
- Verify that git hooks are properly installed in `.git/hooks/`

### Manual Recovery

If automatic detection fails, you can manually log test transitions:

```bash
# Find the failure XML file
ls -la failed_tests_*.xml

# Run a comparison with recent results
./scripts/test.sh -c -v --log-results --before-xml failed_tests_20250101_123456.xml
```

## Advanced Topics

### Custom Validation Settings

You can customize the validation evidence thresholds in `.env`:

```bash
VALIDATION_THRESHOLD=0.7
TEST_TRANSITION_WEIGHT=0.6
CODE_QUALITY_WEIGHT=0.3
RUNTIME_ERROR_WEIGHT=0.1
```

### Extending the Workflow

The workflow can be extended with custom plugins in the `src/chroma_mcp_client/validation/` directory. See the developer guide for more details on creating custom evidence collectors and validators.

## Setting Up the Workflow

The workflow setup process creates Git hooks that automate test failure capture and transition detection. To set up the workflow, run:

```bash
chroma-client setup-test-workflow
```

This creates:

- A `pre-push` hook that runs tests with the `--auto-capture-workflow` flag
- A `post-commit` hook that checks for test transitions

> **Note**: The setup process preserves any existing content in your post-commit hook, particularly codebase indexing functionality. If you already have a post-commit hook for indexing files (as described in [Automating Codebase Indexing with Git Hooks](../automation/git_hooks.md)), the test transition check will be appended rather than replacing your existing hook.

You can also specify a custom workspace directory:

```bash
chroma-client setup-test-workflow --workspace-dir /path/to/project
```

To replace existing hooks, use:

```bash
chroma-client setup-test-workflow --force
```
