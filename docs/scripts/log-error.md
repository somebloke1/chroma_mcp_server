# Runtime Error Logging Script

This script simplifies the process of logging runtime errors for validation evidence and future promotion.

## Overview

When errors occur in a system, logging them with detailed information is valuable for validation and learning. The `log_error.sh` script provides a convenient wrapper around the `chroma-mcp-client log-error` command, making it easy to record:

- Error types and messages
- Stacktraces
- Affected files
- Resolutions
- Verification status

## Usage

```bash
./scripts/log_error.sh --error-type "TypeError" --message "Cannot read property of undefined"
```

### Required Parameters

- `-t, --error-type`: Type of error (e.g., ValueError, TypeError)
- `-m, --message`: Error message content

### Optional Parameters

- `-s, --stacktrace`: Full stacktrace of the error
- `-f, --files`: Comma-separated list of affected file paths
- `-r, --resolution`: Description of how the error was resolved
- `--verified`: Flag indicating the resolution has been verified
- `-c, --collection`: Name of the collection to store errors (default: validation_evidence_v1)
- `-v, --verbose`: Enable verbose output

## Examples

### Basic error logging

```bash
./scripts/log_error.sh --error-type "TypeError" --message "Cannot read property of undefined"
```

### Including stacktrace and affected files

```bash
./scripts/log_error.sh \
  --error-type "ValueError" \
  --message "Invalid input value" \
  --stacktrace "File 'main.py', line 42
ValueError: Invalid input value" \
  --files "src/main.py,src/validation.py"
```

### Logging a resolved error

```bash
./scripts/log_error.sh \
  --error-type "ImportError" \
  --message "Module not found" \
  --files "src/app.py" \
  --resolution "Added missing dependency in requirements.txt" \
  --verified
```

## Integration with Validation Workflow

Runtime errors captured with this script become part of the validation evidence system and can be used to validate learning promotions. When an error is logged, it is stored in the ChromaDB collection and assigned a unique ID that can be referenced in validation evidence.

The evidence can then be used with the `promote-learning` command to validate that a learning has been properly tested and fixed known issues.

## See Also

- [validate-evidence](validate-evidence.md) - For validating evidence for promotion
- [log-test-results](log-test-results.md) - For logging test results
- [log-quality-check](log-quality-check.md) - For logging code quality metrics
- [promote-learning](promote-learning.md) - For promoting validated learnings
