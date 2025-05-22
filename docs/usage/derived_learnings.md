# Curating and Using Derived Learnings (`derived_learnings_v1`)

## Introduction

"Derived learnings" are high-quality, validated insights, patterns, or solutions that are manually curated from development activities. They represent proven knowledge that can be explicitly captured and reused to improve consistency, efficiency, and the performance of your AI assistant.

The `derived_learnings_v1` ChromaDB collection serves as the central repository for this curated knowledge. When integrated into the Retrieval Augmented Generation (RAG) system, these learnings augment the context retrieved from the raw `codebase_v1`, providing the AI assistant with access to proven best practices and solutions.

## The `derived_learnings_v1` Collection Schema

The `derived_learnings_v1` collection is designed to store structured information about each learning:

- **`learning_id` (str, UUID):** A unique identifier for the learning entry.
- **`source_chat_id` (str, optional):** If the learning originated from an AI interaction, this field links to the corresponding entry ID in the `chat_history_v1` collection.
- **`description` (str):** The core content of the learning. This is a textual explanation of the pattern, solution, or insight. This is the primary document content for semantic search.
- **`pattern` (str):** A concise representation of the learning, often a short phrase, code signature, or keyword that encapsulates the essence of the pattern or solution.
- **`example_code_reference` (str, optional):** A reference to an exemplary code implementation. This could be a `chunk_id` from the `codebase_v1` collection, a permalink to a specific commit/file, or a direct code snippet.
- **`tags` (str, comma-separated):** Keywords or categories for organizing, filtering, and searching learnings (e.g., "python,error-handling,api-design").
- **`confidence` (float):** A human-assigned score (0.0-1.0) reflecting the curator's confidence in the utility, correctness, and general applicability of the learning.
- **`validation_evidence_id` (str, optional):** Links to an entry in `validation_evidence_v1` if the learning is backed by structured validation (e.g., a test transition).
- **`validation_score` (float, optional):** The score from the linked validation evidence.

## Workflow for Creating Derived Learnings (Promotion)

Derived learnings are typically created by "promoting" insights identified from various sources:

### 1. Source Identification

Potential learnings can be identified from:

- **Analyzed Chat History:** Interactions in `chat_history_v1` (often with status `analyzed` or those having high confidence scores, significant diffs, or positive test outcomes linked via validation evidence) are prime candidates.
- **Validated Test Transitions:** Successful test fixes captured in `validation_evidence_v1` (often identified by `chroma-mcp-client check-test-transitions`) demonstrate effective problem-solving.
- **Direct Developer Insights:** Experienced developers might identify valuable patterns or best practices from their work or external sources that are worth capturing.

### 2. The `chroma-mcp-client review-and-promote` Command

This interactive CLI command is the primary tool for curating and promoting learnings:

- **Interactive Review:** It allows developers to browse candidate interactions from `chat_history_v1` (often filtered by status, confidence, or other metadata) or directly input information for a new learning.
- **Contextual Information:** For chat-derived learnings, it can display the rich context (summaries, code diffs, tool sequences) associated with the original interaction.
- **Guided Curation:** The command guides the user through formulating the:
  - `description`: A clear explanation of the learning.
  - `pattern`: A concise summary or keyword.
  - `tags`: Relevant tags for discoverability.
  - `example_code_reference`: Users can search the codebase or paste snippets.
  - `confidence`: Assigning a confidence score.
  - `validation_evidence_id`: Links to an entry in `validation_evidence_v1` if the learning is backed by structured validation (e.g., a test transition).
  - `validation_score`: The score from the linked validation evidence.
- **Linking Validation Evidence:** If promoting based on a test transition or other validation, the user can link the corresponding `validation_evidence_id`.
- **Status Update:** Upon successful promotion, if the source was a `chat_history_v1` entry, its status is typically updated to `promoted_to_learning`.

### 3. The `chroma-mcp-client promote-learning` Command

While `review-and-promote` offers an interactive experience, `promote-learning` might be used for more direct, non-interactive promotion if all details are already known or scripted. It generally expects all necessary fields (description, pattern, etc.) as direct arguments.

## Using Derived Learnings in RAG

The primary goal of `derived_learnings_v1` is to enhance the RAG capabilities of your AI assistant:

- **Augmented Context Retrieval:** The `chroma_query_documents` MCP tool (used by the AI assistant) should be configured to query *both* the `codebase_v1` (for raw code context) and the `derived_learnings_v1` collections.
- **Prioritized Solutions:** Results from `derived_learnings_v1` represent validated or curated knowledge. The RAG system can potentially prioritize these results or blend them intelligently with code search results.
- **Improved AI Performance:** By providing the AI with access to these high-quality, human-vetted solutions and patterns, its responses can become more accurate, consistent, and aligned with best practices.

## Maintaining Derived Learnings

As your codebase and development practices evolve, derived learnings should also be maintained:

- **Review:** Periodically review existing learnings for relevance and accuracy.
- **Update:** Modify learnings if the underlying code or best practice changes.
- **Retire:** Remove learnings that are no longer applicable or have been superseded.

## Benefits of Derived Learnings

- **Knowledge Retention & Sharing:** Captures valuable, often tacit, knowledge within the team.
- **Improved RAG Quality:** Provides the AI assistant with a curated set of high-signal examples and patterns.
- **Enhanced AI Assistant Performance:** Leads to more relevant, accurate, and consistent AI-generated code and suggestions.
- **Consistency in Development:** Promotes the application of established best practices and patterns across the team.
- **Accelerated Onboarding:** New team members can learn from this curated knowledge base.
