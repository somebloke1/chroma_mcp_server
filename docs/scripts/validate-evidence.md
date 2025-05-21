# Validation Evidence Script

**DEPRECATION NOTICE:** The `validate_evidence.sh` shell script is deprecated and will be removed in version 0.3.0. Please use the `chroma-mcp-client validate-evidence` console script installed via the Python package.

This script simplifies the process of validating evidence for learning promotions.

## Overview

Validation evidence provides objective metrics to qualify the impact and quality of code changes. The `validate_evidence.sh` script wraps the `chroma-mcp-client validate-evidence` command, making it easy to:

- Load validation evidence from files or IDs
- Calculate validation scores based on multiple evidence types
- Check if evidence meets promotion threshold
- Save validation reports to files

## Usage

**Recommended**: Use the console script directly:

```bash
chroma-mcp-client validate-evidence --file evidence.json
```

**Legacy wrapper script (deprecated)**:

```bash
./scripts/validate_evidence.sh --file evidence.json
```

### Required Parameters

At least one of these evidence sources must be provided:

- `-f, --file`: Path to a JSON file containing validation evidence
- `-t, --test-ids`: Comma-separated list of test transition evidence IDs
- `-r, --runtime-ids`: Comma-separated list of runtime error evidence IDs
- `-q, --quality-ids`: Comma-separated list of code quality evidence IDs

### Optional Parameters

- `--threshold`: Validation score threshold for promotion eligibility (default: 0.7)
- `-o, --output`: Path to save the validation results as JSON
- `-v, --verbose`: Enable verbose output

## Examples

### Validating evidence from a file

```bash
./scripts/validate_evidence.sh --file evidence.json
```

### Validating evidence from multiple sources

```bash
./scripts/validate_evidence.sh \
  --test-ids test-123,test-456 \
  --runtime-ids error-789 \
  --quality-ids quality-012
```

### Setting a custom threshold and saving results

```bash
./scripts/validate_evidence.sh \
  --file evidence.json \
  --threshold 0.8 \
  --output validation-report.json
```

## Integration with Promotion Workflow

This script plays a critical role in the promotion workflow:

1. Collect evidence using the various evidence logging scripts
2. Use this script to validate the collected evidence
3. If the evidence meets the threshold, use the validation report with the `promote-learning` command

The validation score is calculated based on:

- Test transitions (failing → passing)
- Runtime error resolutions
- Code quality improvements

Each evidence type contributes to the overall score, with weights defined by the validation system.

## See Also

- [log-error](log-error.md) - For logging runtime errors
- [log-test-results](log-test-results.md) - For logging test results
- [log-quality-check](log-quality-check.md) - For logging code quality metrics
- [promote-learning](promote-learning.md) - For promoting validated learnings
