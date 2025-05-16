# Learning Validation Workflow

## The Current Learning Promotion Problem

Our current approach for promoting learnings to `derived_learnings_v1` has a fundamental flaw: **we promote code changes without evidence that they represent valuable learning moments**. This leads to:

1. A collection filled with routine code changes rather than meaningful insights
2. Difficulty measuring the true ROI of our RAG system
3. Reduced effectiveness when these "learnings" are used in future RAG queries

## A New Validation-Based Workflow

This document outlines a revised workflow that prioritizes **evidence-based validation** of learnings before promotion.

## Core Principle: No Promotion Without Validation

The central principle of the new workflow is simple: **A code change or discussion should only be promoted to `derived_learnings_v1` if there is concrete evidence of its learning value**.

## Types of Validation Evidence

### 1. Error Resolution Evidence

- **Test Failure → Success Transitions**: Code changes that fix failing tests
- **Runtime Error → Resolution**: Changes that eliminate runtime errors
- **Bug Fix Verification**: Commits linked to bug reports with verification of resolution

### 2. Quality Improvement Evidence

- **Measurable Code Quality Improvements**: Changes that significantly improve complexity, maintainability, or performance metrics
- **Security Vulnerability Mitigation**: Changes that address security issues
- **Performance Optimization Proof**: Benchmark results showing meaningful performance improvements

### 3. Knowledge Gap Evidence

- **Misunderstanding Correction**: Clear evidence that a change corrected a significant misunderstanding or misconception
- **Edge Case Handling**: Changes that address overlooked edge cases with potential for broader application
- **Pattern Establishment**: Introduction of a pattern that enables consistency across the codebase

## Validation Scoring System

Each potential learning should be scored based on validation evidence:

| Evidence Type | Weight | Examples |
|---------------|--------|----------|
| Test Transition | High | Failing test → Passing test |
| Runtime Error Fix | High | Logged error → No error |
| Bug Resolution | High | Verified bug fix |
| Code Quality | Medium | >20% complexity reduction |
| Performance | Medium | >10% speed improvement |
| Security | High | Elimination of vulnerability |
| Knowledge Gap | Medium | Correction of documented misconception |
| Edge Case | Medium | Handling previously unhandled condition |

Only candidates scoring above a threshold should be promoted.

## Revised Promotion Workflow

### 1. Identification Phase

- Analyze `chat_history_v1` entries as before
- Identify code changes linked to those entries
- **New:** Check for validation evidence (test results, error logs, metrics)
- **New:** Calculate a validation score

### 2. Validation Phase

- **New:** For entries with insufficient validation, create validation tasks:
  - Run tests before and after the change
  - Check for error logs before and after
  - Measure quality metrics before and after
- Record all validation results in metadata

### 3. Review Phase

- Present candidates with validation evidence and scores
- Allow reviewer to see the validation data
- Enable filtering by validation type and score
- **New:** Allow additional validation to be performed during review

### 4. Promotion Phase

- Only promote entries that meet validation criteria
- Include validation evidence in the learning metadata
- Tag learnings with validation types for future filtering

## Implementation Plan

### Phase 1: Add Validation Fields

1. Update `derived_learnings_v1` schema:

   ```python
   validation_evidence = {
       "type": ["test_transition", "error_resolution", "quality_improvement", "knowledge_gap"],
       "score": 0.85,  # 0.0 to 1.0
       "evidence_details": {
           "test_ids": ["test-123", "test-456"],
           "before_status": "fail",
           "after_status": "pass",
           "metrics_before": {"complexity": 12, "maintainability": 65},
           "metrics_after": {"complexity": 8, "maintainability": 78}
       }
   }
   ```

2. Modify promotion process to require validation metadata

### Phase 2: Enhance Validation Collection

1. Integrate with test result collection
2. Add code quality metric calculation
3. Implement runtime error logging
4. Create validation scoring algorithm

### Phase 3: Update User Interface

1. Modify `review-and-promote` to display validation evidence
2. Add validation filters and sorting
3. Implement on-demand validation during review

## Example: Test-Based Validation

```python
def assess_learning_candidate(chat_id, code_changes):
    """Assess if a chat interaction produced validated learning."""
    # Find test results before and after the change
    test_results_before = get_test_results_before_change(code_changes["files"])
    test_results_after = get_test_results_after_change(code_changes["files"])
    
    # Check for fail → pass transitions
    validation_score = 0.0
    validation_evidence = {}
    
    for test_id in test_results_before:
        if test_id in test_results_after:
            if test_results_before[test_id] == "fail" and test_results_after[test_id] == "pass":
                # Found a validation point!
                validation_score += 0.25  # Accumulate score based on validations
                if "test_transitions" not in validation_evidence:
                    validation_evidence["test_transitions"] = []
                validation_evidence["test_transitions"].append({
                    "test_id": test_id,
                    "before": "fail",
                    "after": "pass"
                })
    
    # Only return candidates that meet threshold
    if validation_score >= PROMOTION_THRESHOLD:
        return {
            "chat_id": chat_id,
            "validation_score": min(1.0, validation_score),
            "validation_evidence": validation_evidence,
            "recommendation": "promote"
        }
    else:
        return {
            "chat_id": chat_id,
            "validation_score": validation_score,
            "recommendation": "insufficient_evidence"
        }
```

## Benefits of Validation-Based Promotion

1. **Higher Quality Learnings**: Only truly valuable insights get promoted
2. **Measurable ROI**: Clear evidence of the system's impact
3. **More Effective RAG**: Queries return validated solutions rather than routine changes
4. **Targeted Improvements**: Focus on areas where errors actually occur
5. **Continuous Refinement**: System naturally adapts to focus on high-value solutions

## Next Steps

1. Implement test result collection as described in `local_rag_pipeline_plan_v4.md`
2. Create the validation scoring system
3. Update the promotion workflow to incorporate validation
4. Develop better visualization of validation evidence
5. Establish thresholds and criteria for different types of validation
