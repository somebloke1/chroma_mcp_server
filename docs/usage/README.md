# Usage Guides

This section contains detailed guides on how to use specific features and workflows within the `chroma-mcp-server` and its associated client tools. These documents aim to provide practical instructions and conceptual explanations to help you leverage the system effectively.

## Available Guides

- **[Daily Workflow Integration](./daily_workflow_integration.md)**
  - Explains how to integrate the `chroma-mcp-server` ecosystem into your daily development workflow.

- **[Automated Test Workflow](./automated_test_workflow.md)**
  - Explains the fully automated test-driven learning workflow, including setup, how it captures test failures and successes, and its integration with Git hooks and ChromaDB for validated learning promotion.

- **[Context Module](./context_module.md)**
  - Details the `context.py` module, which provides reusable logic for extracting and processing contextual information such as code snippets, diffs, and tool usage sequences.

- **[Enhanced Context Capture](./enhanced_context_capture.md)**
  - Describes the system for automatically extracting rich contextual information (code diffs, tool sequences, confidence scores) during AI interactions that modify code. Also covers the error-driven learning approach.

- **[ROI Measurement Framework](./roi_measurement.md)**
  - Outlines the framework and metrics for measuring the return on investment and effectiveness of the RAG (Retrieval Augmented Generation) implementation.

- **[Semantic Code Chunking](./semantic_chunking.md)**
  - Explains the strategy of preserving logical code structures (functions, classes) when indexing code, leading to more meaningful context retrieval.

- **[Test Result Integration](./test_result_integration.md)**
  - Details how test execution results are captured, stored, and integrated into the RAG workflow to measure code quality improvements and correlate them with development activities.

- **[Tool Usage Format Specification](./tool_usage_format.md)**
  - Specifies the JSON format expected for logging tool usage information, whether captured automatically or provided manually.

- **[Validation System](./validation_system.md)**
  - Describes the evidence-based validation system for promoting learnings, including different types of evidence and the scoring mechanism.
