# Test Artifacts Organization Plan

## Rationale

This document outlines the plan to reorganize test artifacts (XML reports, coverage data, workflow tracking files) from the project root to a dedicated `logs/tests/` directory for better organization and to implement automatic cleanup after successful processing.

Currently, test artifacts are generated in the project root, leading to clutter and potential confusion. These files include:

- `test-results.xml`: JUnit XML test results
- `failed_tests_*.xml`: Saved failing test results for comparison
- `test_workflow_*.json`: Workflow tracking files
- `coverage.xml`: Coverage report in XML format
- `coverage_output.txt`: Coverage summary for quality checks

## Implementation Plan

### Phase 1: Directory Structure Setup

- [x] **Create logs/tests/ Directory Structure:**
  - [x] Create logs/tests/ directory if it doesn't exist
  - [x] Add necessary subdirectories: junit/, coverage/, workflows/
  - [x] Update .gitignore to exclude these directories

### Phase 2: Test Script Updates

- [x] **Update scripts/test.sh:**
  - [x] Modify output paths for all test artifacts to use logs/tests/ directory structure
  - [x] Ensure references between files are updated to use the new paths
  - [x] Update file handling to ensure proper directory creation if not exists

### Phase 3: Update GitHub Actions Workflow

- [x] **Update .github/workflows/tests.yml:**
  - [x] Update file paths in GitHub Actions workflow to reference the new locations
  - [x] Adjust codecov upload to point to the new coverage.xml location

### Phase 4: Update Client Code References

- [x] **Update Test Workflow Manager:**
  - [x] Update the `TestWorkflowManager` to look for files in the new location
  - [x] Update file path handling in any related modules
  - [x] Modify git hooks to reference the new locations

### Phase 5: Auto-Cleanup Implementation

- [x] **Implement Automatic Cleanup Logic:**
  - [x] Add cleanup function to the test workflow manager
  - [x] Trigger cleanup after successful processing of test transitions
  - [x] Only remove files that have been successfully processed
  - [x] Add safety checks to prevent accidental removal of important data

## Detailed Implementation

### Directory Structure

```bash
logs/
  └── tests/
      ├── junit/
      │   ├── test-results.xml                  # Current test results
      │   └── failed_tests_TIMESTAMP.xml        # Failed test results for comparison
      ├── coverage/
      │   ├── coverage.xml                      # Coverage XML report
      │   └── coverage_output.txt               # Coverage text summary
      └── workflows/
          ├── test_workflow_TIMESTAMP.json      # Workflow tracking
          └── test_workflow_complete_TIMESTAMP.json  # Completed workflow
```

### File Path Updates

Update the following path references in scripts/test.sh:

```bash
# From:
XML_OUTPUT_PATH="test-results.xml"
# To:
TEST_LOGS_DIR="logs/tests"
JUNIT_DIR="${TEST_LOGS_DIR}/junit"
COVERAGE_DIR="${TEST_LOGS_DIR}/coverage"
WORKFLOW_DIR="${TEST_LOGS_DIR}/workflows"

# Create directories if they don't exist
mkdir -p "${JUNIT_DIR}" "${COVERAGE_DIR}" "${WORKFLOW_DIR}"

XML_OUTPUT_PATH="${JUNIT_DIR}/test-results.xml"
```

### Auto-Cleanup Logic

```python
def cleanup_processed_artifacts(self, workflow_file: str):
    """
    Clean up test artifacts after successful processing.
    
    Args:
        workflow_file: Path to the workflow file that was processed
    """
    try:
        # Read workflow file to get associated artifact paths
        with open(workflow_file, 'r') as f:
            workflow_data = json.load(f)
        
        # Get paths to artifacts
        before_xml = workflow_data.get('before_xml')
        after_xml = workflow_data.get('after_xml')
        
        # Only remove files if they exist and evidence was successfully created
        if before_xml and os.path.exists(before_xml):
            logger.info(f"Removing processed artifact: {before_xml}")
            os.remove(before_xml)
            
            # Also remove commit file if it exists
            commit_file = f"{before_xml}.commit"
            if os.path.exists(commit_file):
                os.remove(commit_file)
        
        # Only remove the workflow file itself after processing
        logger.info(f"Removing processed workflow file: {workflow_file}")
        os.remove(workflow_file)
            
    except Exception as e:
        logger.warning(f"Error cleaning up artifacts: {e}")
```

### GitHub Actions Updates

```yaml
- name: Generate coverage XML report
  run: |
    mkdir -p logs/tests/coverage
    hatch run coverage xml -o logs/tests/coverage/coverage.xml

- name: Upload coverage reports to Codecov
  uses: codecov/codecov-action@v3
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
    file: ./logs/tests/coverage/coverage.xml
    fail_ci_if_error: true
```

## Migration Strategy

1. **Backward Compatibility:** Initially maintain backward compatibility by checking both old and new locations
2. **Gradual Implementation:** Roll out changes in phases to avoid disrupting existing workflows
3. **Documentation:** Update documentation to reference new file locations

## Implementation Status

All changes have been implemented:

1. ✅ Test script updated to use the new directory structure
2. ✅ GitHub Actions workflow updated to use the new locations
3. ✅ Auto-cleanup functionality added to remove artifacts after successful processing
4. ✅ Backward compatibility maintained for a smooth transition

## References and Related Documents

- [Automated Test Workflow Guide](../usage/automated_test_workflow.md)
- [Test-Driven Learning Documentation](../thinking_tools/test_driven_learning.md)
