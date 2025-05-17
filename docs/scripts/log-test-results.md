# Test Results Logging Script

This script simplifies the process of logging test results for validation evidence and tracking test transitions.

## Overview

Test results provide a critical form of validation evidence for measuring the impact of code changes. The `log_test_results.sh` script provides a convenient wrapper around the `chroma-mcp-client log-test-results` command, making it easy to:

- Log JUnit XML test results
- Compare before/after test results to identify transitions (failing → passing)
- Associate results with specific git commits
- Calculate validation scores based on test improvements

## Usage

```bash
./scripts/log_test_results.sh --xml test-results.xml
```

### Required Parameters

- `-x, --xml`: Path to the JUnit XML test results file

### Optional Parameters

- `-b, --before-xml`: Path to a previous JUnit XML file for comparison
- `--commit-before`: Git commit hash for the "before" state
- `--commit-after`: Git commit hash for the "after" state
- `-c, --collection`: Name of the collection to store results (default: test_results_v1)
- `-v, --verbose`: Enable verbose output

## Examples

### Basic test results logging

```bash
./scripts/log_test_results.sh --xml test-results.xml
```

### Logging test transitions (before/after comparison)

```bash
./scripts/log_test_results.sh \
  --xml test-results-after.xml \
  --before-xml test-results-before.xml
```

### Associating with git commits

```bash
./scripts/log_test_results.sh \
  --xml test-results.xml \
  --before-xml baseline-results.xml \
  --commit-before abc12345 \
  --commit-after def67890
```

## Integration with Test Workflow

This script is designed to be integrated into your testing workflow, especially after implementing changes that should improve or fix tests. Typical usage would be:

1. Run tests before making code changes to capture baseline results
2. Make code changes to fix bugs or improve functionality
3. Run tests again to capture improved results
4. Use this script to log the results and transitions
5. Use the generated evidence ID with `validate-evidence.sh` to qualify the changes

When a test transition is detected (failed → passed), it provides strong validation evidence that a change successfully addressed an issue.

## See Also

- [validate-evidence](validate-evidence.md) - For validating evidence for promotion
- [log-error](log-error.md) - For logging runtime errors
- [log-quality-check](log-quality-check.md) - For logging code quality metrics
- [promote-learning](promote-learning.md) - For promoting validated learnings
