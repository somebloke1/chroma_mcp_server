# Validation System

The validation system provides a framework for objectively measuring the quality and impact of code changes. This is particularly valuable for:

1. Ensuring changes successfully address issues
2. Qualifying learning promotions with evidence
3. Establishing a feedback loop for improvement
4. Building a repository of validated best practices

## Key Concepts

The validation system is built around several key concepts:

### Evidence Types

The system supports three main types of validation evidence:

1. **Test Transitions**: Tests that change from failing to passing, demonstrating a fix works
2. **Runtime Error Resolutions**: Runtime errors that are detected, fixed, and verified
3. **Code Quality Improvements**: Measurable improvements in code quality metrics

### Validation Score

Each piece of evidence contributes to an overall validation score, which is used to determine if a learning meets the promotion threshold. The score is calculated based on:

- Number and significance of test transitions
- Complexity and impact of error resolutions
- Percentage improvements in code quality metrics

### Promotion Threshold

A configurable threshold (default: 0.7 or 70%) that evidence must meet to qualify for promotion. This ensures only well-validated learnings are promoted.

## Using the Validation System

### Setting Up

1. Ensure required collections exist:

   ```bash
   chroma-client setup-collections
   ```

2. Configure any custom thresholds or settings as needed (defaults work well for most cases)

### Workflow Overview

The typical validation workflow consists of these steps:

1. **Identify Issue**: Document a bug, error, or quality problem
2. **Initial Logging**: Log the error or failing test
3. **Implement Fix**: Make code changes to address the issue
4. **Verify Fix**: Run tests or tools to verify the fix works
5. **Log Evidence**: Record the improvements as validation evidence
6. **Validate Changes**: Calculate validation score from evidence
7. **Promote Learning**: Use validated evidence to promote learning

### Logging Validation Evidence

#### Runtime Errors

Use the `log-error` command to record runtime errors:

```bash
# Log an error that was encountered
./scripts/log_error.sh \
  --error-type "TypeError" \
  --message "Cannot read property 'value' of undefined" \
  --stacktrace "Error at line 42 in utils.js" \
  --files "src/utils.js,src/components/form.js"

# After fixing, update with resolution
./scripts/log_error.sh \
  --error-type "TypeError" \
  --message "Cannot read property 'value' of undefined" \
  --files "src/utils.js,src/components/form.js" \
  --resolution "Added null checks before accessing properties" \
  --verified
```

#### Test Results

Use the `log-test-results` command to record test results:

```bash
# Basic test logging
./scripts/log_test_results.sh --xml test-results.xml

# Compare before/after to identify transitions
./scripts/log_test_results.sh \
  --xml after-fix.xml \
  --before-xml before-fix.xml \
  --commit-before abc12345 \
  --commit-after def67890
```

#### Code Quality

Use the `log-quality-check` command to record code quality metrics:

```bash
# Log current quality metrics
./scripts/log_quality_check.sh --after pylint-output.txt

# Compare before/after to measure improvements
./scripts/log_quality_check.sh \
  --tool pylint \
  --metric error_count \
  --before before-refactor.txt \
  --after after-refactor.txt
```

### Validating Evidence

Use the `validate-evidence` command to calculate validation scores:

```bash
# Validate from a single source
./scripts/validate_evidence.sh --file evidence.json

# Combine evidence from multiple sources
./scripts/validate_evidence.sh \
  --test-ids test-transition-123,test-transition-456 \
  --runtime-ids error-789 \
  --quality-ids quality-check-012

# Save validation results to a file
./scripts/validate_evidence.sh \
  --test-ids test-transition-123 \
  --quality-ids quality-check-012 \
  --output validation-report.json
```

### Promoting Validated Learnings

Use the validation evidence when promoting learnings:

```bash
# Promote learning with validation evidence
chroma-client promote-learning \
  --description "Always check for null/undefined before accessing object properties" \
  --pattern "if (obj && obj.property)" \
  --code-ref "src/utils.js:abc123:42" \
  --tags "javascript,error-handling,null-safety" \
  --confidence 0.95 \
  --require-validation \
  --validation-evidence-id evidence-123

# Promote learning with manual validation score
chroma-client promote-learning \
  --description "Use try/catch blocks around JSON.parse" \
  --pattern "try { JSON.parse(str) } catch (e) { /* handle error */ }" \
  --code-ref "src/data.js:def456:78" \
  --tags "javascript,error-handling,json" \
  --confidence 0.9 \
  --require-validation \
  --validation-score 0.85
```

## Evidence Scoring

The validation system calculates scores based on these factors:

### Test Transitions

- **Weight**: 0.5 (50% of total score)
- **Factors**: Number of transitions, test importance, coverage of affected code

### Runtime Error Resolutions

- **Weight**: 0.3 (30% of total score)
- **Factors**: Error severity, verification status, impact scope

### Code Quality Improvements

- **Weight**: 0.2 (20% of total score)
- **Factors**: Percentage improvement, metric type, affected code size

The final score is a weighted average of these components, normalized to a 0-1 range.

## Best Practices

- Log evidence as close to the time of implementation as possible
- Capture "before" data before making changes
- Be specific about affected files and components
- Verify resolutions before marking them as verified
- Combine multiple types of evidence for stronger validation
- Use consistent naming and tagging conventions

## Reference

See the CLI command reference for detailed parameter information:

- [log-error](../scripts/log-error.md)
- [log-test-results](../scripts/log-test-results.md)
- [log-quality-check](../scripts/log-quality-check.md)
- [validate-evidence](../scripts/validate-evidence.md)
- [promote-learning](../scripts/promote-learning.md)
