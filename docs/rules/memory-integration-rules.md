# Memory Integration Rule

## Objective

Integrate the Chroma MCP thinking tools (working memory) into the RAG pipeline for context retrieval.

## Instructions for AI Assistant

- When the user asks to recall previous context, decisions, related ideas, or specific 'thoughts' that might have been recorded, **actively consider using the `chroma_find_similar_thoughts` tool**.
- Formulate a concise query based on the user's request to search the recorded thoughts.
- Use the results from `chroma_find_similar_thoughts` (even if potentially limited by the current embedding model) to inform and enrich your response, combining it with your general knowledge.
- Mention briefly if you are using retrieved thoughts to provide context. Example: "Based on similar thoughts recorded earlier..."

## After Applying This Rule

After this rule has been applied, confirm in chat with **Working Memory Lookup Performed.**
