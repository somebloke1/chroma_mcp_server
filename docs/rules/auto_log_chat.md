# Rule: Auto-Log Chat Summaries

**Description:** Automatically logs a summary of the user prompt and AI response to the `chat_history_v1` ChromaDB collection after each AI response generation.

**Instructions for AI Assistant:**

1. **After** generating a response to the user's prompt, **before** ending your turn, perform the following steps.
2. **Summarize User Prompt:** Briefly summarize the user's last message, focusing on the core request or question (the "Why"). Store this as `prompt_summary`. Ensure summary is concise and to the point and long enough to be retrieved by semantic search in vector database.
3. **Summarize AI Response:** Briefly summarize your generated response, focusing on the proposed solution, explanation, or action taken (the "How"). Store this as `response_summary`. Ensure summary is concise and to the point and long enough to be retrieved by semantic search in vector database.
4. **Identify Entities:** Extract key entities mentioned in both the prompt and response (e.g., file paths, function names, specific concepts discussed). Store these as a comma-separated string in `involved_entities`.
5. **Prepare Metadata:** Construct a JSON metadata object including:
    * `session_id`: A unique identifier for the current interaction session (if available/applicable, otherwise generate or omit).
    * `timestamp`: The current time in ISO 8601 format.
    * `prompt_summary`: The summary from step 2.
    * `response_summary`: The summary from step 3.
    * `involved_entities`: A comma-separated string of the entities from step 4, since metadata values must be primitive types.
    * `status`: Set to `"captured"`.
6. **Log to ChromaDB:**
    * Determine the main content (`document`) to be stored. Use a concatenation of the summaries: `f"Prompt: {prompt_summary}\nResponse: {response_summary}"`
    * Call the `#chroma_add_document_with_metadata` tool.
    * Provide the following arguments:
        * `collection_name`: `"chat_history_v1"`
        * `document`: The concatenated summary string.
        * `metadata`: The JSON metadata object constructed in step 5.
        * `increment_index`: Set to `True`.
7. **Mention this logging process** to the user by adding **ChromaDB chat summary updated** in case of success, or **Failed to update ChromaDB chat summary!** in case of errors to ensure we have all chats summarized and logged. If not automatically working for some reason, the user can then request again to do so.
