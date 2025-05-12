# Using Chroma MCP Thinking Utilities with Large Language Models

This guide demonstrates how to use Chroma MCP Thinking Utilities to capture, organize, and retrieve thought chains from Large Language Models (LLMs).

## Why Use Thinking Utilities with LLMs?

LLMs often generate complex reasoning chains when solving problems. The Thinking Utilities provide:

1. **Structured Storage**: Capture multi-step reasoning in an organized format
2. **Semantic Retrieval**: Find similar reasoning patterns using semantic search
3. **Branching Logic**: Track alternative approaches to problem-solving
4. **Progressive Refinement**: Record step-by-step evolution of thoughts
5. **Context-Rich Reasoning**: Leverage enhanced context from chat history and code changes
6. **Bidirectional Linking**: Connect thoughts to related artifacts for comprehensive context

## Common LLM Use Cases

### Chain-of-Thought Reasoning

Record the step-by-step reasoning process of an LLM:

```python
from chroma_mcp_thinking.utils import record_thought_chain
from mcp import ClientSession

# LLM-generated reasoning steps
reasoning_steps = [
    "To solve this math problem, I'll start by identifying the variables.",
    "The equation can be rewritten as a quadratic formula: ax² + bx + c = 0",
    "Using the quadratic formula: x = (-b ± √(b² - 4ac)) / 2a",
    "Substituting the values: a=2, b=-5, c=3",
    "Computing the discriminant: b² - 4ac = (-5)² - 4(2)(3) = 25 - 24 = 1",
    "Therefore, x = (-(-5) ± √1) / 2(2) = 5 ± 1 / 4",
    "The solutions are: x = 1.5 or x = 0.5"
]

# Assume mcp_client is already initialized
mcp_client = ClientSession()

# Record the complete chain with metadata
result = record_thought_chain(
    thoughts=reasoning_steps,
    metadata={
        "task": "math_problem",
        "problem_type": "quadratic_equation",
        "llm_model": "gpt-4",
        "confidence": "high"
    },
    client=mcp_client
)

session_id = result["session_id"]
```

### Exploring Alternative Approaches

Record an alternative solution path using branching:

```python
from chroma_mcp_thinking.utils import create_thought_branch
from mcp import ClientSession

# Assume mcp_client is already initialized
mcp_client = ClientSession()

# Alternative approach using factoring instead of quadratic formula
factoring_approach = [
    "Instead of using the quadratic formula, I'll try factoring the equation.",
    "Rewriting 2x² - 5x + 3 = 0 in the form (px + q)(rx + s) = 0",
    "Finding factors of 2×3=6 that sum to -5: -2 and -3",
    "Therefore, 2x² - 5x + 3 = 0 can be written as (2x - 3)(x - 1) = 0",
    "Setting each factor to zero: 2x - 3 = 0 or x - 1 = 0",
    "Solving: x = 3/2 or x = 1"
]

# Create a branch from thought #2 (after identifying the quadratic equation)
branch_result = create_thought_branch(
    parent_session_id=session_id,
    parent_thought_number=2,  # Branch from the 2nd thought
    branch_thoughts=factoring_approach,
    branch_id="factoring-method",
    client=mcp_client
)
```

### Finding Similar Reasoning Patterns

Search for similar reasoning approaches across previous sessions:

```python
from chroma_mcp_thinking.utils import find_thoughts_across_sessions
from mcp import ClientSession

# Assume mcp_client is already initialized
mcp_client = ClientSession()

# Search for similar reasoning about quadratic equations
similar_thoughts = find_thoughts_across_sessions(
    query="solving quadratic equations by factoring",
    n_results=5,
    client=mcp_client
)

for thought in similar_thoughts:
    print(f"Session: {thought['metadata']['session_id']}")
    print(f"Thought: {thought['document']}")
    print(f"Similarity: {thought['distance']}")
    print()
```

### Context-Aware Reasoning with Enhanced Context

Help LLMs reason with richer context from previous chats and code changes:

```python
import openai
from chroma_mcp_thinking.thinking_session import ThinkingSession
from chroma_mcp_client import ChromaMcpClient

client = openai.OpenAI(api_key="your-api-key")
chroma_client = ChromaMcpClient()

# First, query for relevant previous discussions and code
chat_entries = chroma_client.query_documents(
    collection_name="chat_history_v1",
    query_texts=["authentication implementation JWT"],
    n_results=2
)

code_chunks = chroma_client.query_documents(
    collection_name="codebase_v1",
    query_texts=["authentication implementation JWT"],
    n_results=2
)

# Extract enhanced context
context_info = []
for entry in chat_entries:
    context_info.append(f"Previous discussion: {entry['document']}")
    if 'diff_summary' in entry['metadata']:
        context_info.append(f"Code changes: {entry['metadata']['diff_summary']}")
    if 'tool_sequence' in entry['metadata']:
        context_info.append(f"Implementation approach: {entry['metadata']['tool_sequence']}")
        
for chunk in code_chunks:
    context_info.append(f"Relevant code: {chunk['document']}")

# Provide this rich context to the LLM for reasoning
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are an expert software architect. Reason step-by-step with the context provided."},
        {"role": "user", "content": f"Based on the following context, identify the best approach to extend our authentication system:\n\n{chr(10).join(context_info)}"}
    ]
)

reasoning = response.choices[0].message.content

# Record this context-informed reasoning
thinking_session = ThinkingSession(client=chroma_client)
thinking_session.record_thought(
    thought=reasoning,
    thought_number=1,
    total_thoughts=1,
    metadata={
        "related_chat_ids": [entry['metadata'].get('chat_id') for entry in chat_entries],
        "related_code_chunks": [chunk['metadata'].get('file_path') for chunk in code_chunks],
        "confidence": 0.9,
        "modification_type": "enhancement"
    }
)
```

## Integration with LLM Applications

### Using with OpenAI API

```python
import openai
from chroma_mcp_thinking.thinking_session import ThinkingSession
from mcp import ClientSession

client = openai.OpenAI(api_key="your-api-key")
mcp_client = ClientSession()
thinking_session = ThinkingSession(client=mcp_client)

# Define a multi-step reasoning problem
problem = "Solve the equation: 3x² + 7x - 10 = 0"

# Step 1: Initial approach
response1 = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a math tutor. Explain your first step in solving this problem."},
        {"role": "user", "content": problem}
    ]
)
step1 = response1.choices[0].message.content

# Record the first thought
thinking_session.record_thought(
    thought=step1,
    thought_number=1,
    total_thoughts=3,
    next_thought_needed=True
)

# Step 2: Continue reasoning
response2 = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "Continue solving the problem. Show your work."},
        {"role": "user", "content": problem},
        {"role": "assistant", "content": step1}
    ]
)
step2 = response2.choices[0].message.content

# Record the second thought
thinking_session.record_thought(
    thought=step2,
    thought_number=2,
    total_thoughts=3,
    next_thought_needed=True
)

# Step 3: Final solution
response3 = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "Provide the final answer and verify it."},
        {"role": "user", "content": problem},
        {"role": "assistant", "content": step1 + "\n" + step2}
    ]
)
step3 = response3.choices[0].message.content

# Record the final thought
thinking_session.record_thought(
    thought=step3,
    thought_number=3,
    total_thoughts=3,
    next_thought_needed=False
)

# Get the complete reasoning chain
summary = thinking_session.get_session_summary()
```

### LLM Agents with Thinking Utilities and Enhanced Context

For LLM-based agents that need to track their reasoning with rich context:

```python
class EnhancedReasoningAgent:
    def __init__(self, llm_client, chroma_client, topic):
        self.llm_client = llm_client
        self.chroma_client = chroma_client
        self.topic = topic
        self.thinking_session = ThinkingSession(client=self.chroma_client)
        self.thought_count = 0
        self.context_data = {
            "chat_entries": [],
            "code_chunks": [],
            "related_ids": {"chats": [], "code": []}
        }
        
    def gather_context(self, query):
        """Gather relevant context from chat history and codebase"""
        # Query chat history
        chat_entries = self.chroma_client.query_documents(
            collection_name="chat_history_v1",
            query_texts=[query],
            n_results=3
        )
        
        # Query codebase
        code_chunks = self.chroma_client.query_documents(
            collection_name="codebase_v1",
            query_texts=[query],
            n_results=3
        )
        
        # Store results
        self.context_data["chat_entries"] = chat_entries
        self.context_data["code_chunks"] = code_chunks
        self.context_data["related_ids"]["chats"] = [
            entry['metadata'].get('chat_id') for entry in chat_entries
        ]
        self.context_data["related_ids"]["code"] = [
            chunk['metadata'].get('file_path') for chunk in code_chunks
        ]
        
        # Format context for LLM consumption
        formatted_context = []
        for entry in chat_entries:
            formatted_context.append(f"Previous chat: {entry['document']}")
            if 'diff_summary' in entry['metadata']:
                formatted_context.append(f"Code changes: {entry['metadata']['diff_summary']}")
        
        for chunk in code_chunks:
            formatted_context.append(f"Code: {chunk['document']}")
            
        return "\n".join(formatted_context)
        
    def think(self, query, max_steps=5):
        """Generate and record a multi-step reasoning process with rich context"""
        self.thought_count = 0
        
        # Get context first
        context = self.gather_context(query)
        thought = f"Query: {query}\n\nContext:\n{context}"
        
        while self.thought_count < max_steps:
            self.thought_count += 1
            is_last_step = self.thought_count == max_steps
            
            # Get next reasoning step from LLM with context
            response = self.llm_client.generate(
                prompt=f"Previous thinking: {thought}\nContinue reasoning about {self.topic} using the provided context. {'Provide final conclusion.' if is_last_step else 'Next step:'}"
            )
            
            # Record this step with bidirectional links
            self.thinking_session.record_thought(
                thought=response,
                thought_number=self.thought_count,
                total_thoughts=max_steps,
                next_thought_needed=not is_last_step,
                metadata={
                    "related_chat_ids": self.context_data["related_ids"]["chats"],
                    "related_code_chunks": self.context_data["related_ids"]["code"],
                    "confidence": 0.8,  # Could be improved by LLM self-assessment
                    "modification_type": "analysis"
                }
            )
            
            thought = response
            
            # Check if LLM has reached a conclusion
            if "conclusion" in response.lower() or "final answer" in response.lower():
                break
                
        return self.thinking_session.get_session_summary()
```

## Best Practices for LLM Applications with Enhanced Context

1. **Atomic Thought Steps**: Encourage LLMs to produce clear, single-step thoughts rather than lengthy explanations
2. **Consistent Metadata**: Add model information, confidence scores, and task types in metadata
3. **Branch on Uncertainty**: Create branches when the LLM expresses uncertainty or offers alternative approaches
4. **Comparative Analysis**: Use similarity search to compare reasoning approaches across different models or problems
5. **Session Organization**: Group related reasoning chains in identifiable sessions for easier retrieval
6. **Prioritize Recent Context**: When integrating with chat history, prioritize recent and high-confidence entries
7. **Provide Code Diffs**: When reasoning about code changes, include diff summaries for clearer context
8. **Leverage Tool Sequences**: Reference successful tool sequences from chat history to inform LLM reasoning
9. **Use Confidence Scores**: Filter context by confidence score to prioritize high-quality information
10. **Bidirectional Linking**: Establish clear links between thoughts, chats, and code for a comprehensive view

## Analyzing LLM Reasoning Patterns

Over time, as you collect LLM reasoning chains, you can analyze patterns:

```python
from chroma_mcp_thinking.thinking_session import ThinkingSession
from mcp import ClientSession

# Find sessions where the LLM used a specific technique
similar_sessions = ThinkingSession.find_similar_sessions(
    query="solving problems using the divide and conquer approach",
    n_results=10,
    client=mcp_client
)

# Find LLM reasoning that leverages specific code patterns
code_related_thoughts = find_thoughts_across_sessions(
    query="reasoning about authentication middleware",
    n_results=5,
    client=client
)

# Find which thoughts have the highest confidence scores
high_confidence_thoughts = []
for thought in code_related_thoughts:
    if thought["metadata"].get("confidence", 0) > 0.8:
        high_confidence_thoughts.append(thought)

# Extract code related to high-confidence thoughts
for thought in high_confidence_thoughts:
    if "related_code_chunks" in thought["metadata"]:
        for code_path in thought["metadata"]["related_code_chunks"]:
            # Query code chunks
            code = client.query_documents(
                collection_name="codebase_v1",
                query_texts=[""],
                where={"file_path": code_path}
            )
            # This code represents patterns the LLM was highly confident about
```

By leveraging Chroma MCP Thinking Utilities, you can transform your LLM applications from black-box systems into transparent, analyzable reasoning engines with retrievable thought processes.
