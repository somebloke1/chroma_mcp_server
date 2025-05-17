# Code Quality Check Logging Script

This script simplifies the process of logging code quality metrics for validation evidence.

## Overview

Code quality improvements are an important form of validation evidence, demonstrating that changes enhance maintainability and reduce issues. The `log_quality_check.sh` script wraps the `chroma-mcp-client log-quality-check` command, making it easy to:

- Record metrics from code quality tools
- Compare before/after results to quantify improvements
- Calculate percentage improvements in quality metrics
- Add quality evidence to the validation system

## Usage

```bash
./scripts/log_quality_check.sh --after pylint-results-after.txt
```

### Required Parameters

- `-a, --after`: Path to the quality tool output file after changes

### Optional Parameters

- `-b, --before`: Path to the quality tool output file before changes
- `-t, --tool`: Quality tool name (default: "pylint", options: "ruff", "flake8", "pylint", "coverage")
- `-m, --metric`: Metric type (default: "error_count", options: "linting", "complexity", "coverage", "maintainability")
- `-c, --collection`: Name of the collection to store quality checks (default: validation_evidence_v1)
- `-v, --verbose`: Enable verbose output

## Examples

### Basic quality check logging

```bash
./scripts/log_quality_check.sh --after pylint-output.txt
```

### Comparing before/after quality metrics

```bash
./scripts/log_quality_check.sh \
  --before pylint-before.txt \
  --after pylint-after.txt
```

### Specifying a different tool and metric type

```bash
./scripts/log_quality_check.sh \
  --tool coverage \
  --metric coverage \
  --before coverage-before.txt \
  --after coverage-after.txt
```

## Integration with Code Quality Workflow

This script is designed to be integrated into your code quality workflow:

1. Run quality tools on your codebase to capture baseline metrics
2. Make code improvements to address quality issues
3. Run quality tools again to measure improvements
4. Use this script to log the before/after comparison
5. Use the output with `validate-evidence.sh` to qualify the improvements

When comparing before/after outputs, the script calculates a percentage improvement score, which can contribute to the overall validation score for a learning.

## See Also

- [validate-evidence](validate-evidence.md) - For validating evidence for promotion
- [log-error](log-error.md) - For logging runtime errors
- [log-test-results](log-test-results.md) - For logging test results
- [promote-learning](promote-learning.md) - For promoting validated learnings
