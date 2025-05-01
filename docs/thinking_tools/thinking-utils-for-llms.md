# Using Chroma MCP Thinking Utilities with Large Language Models

This guide demonstrates how to use Chroma MCP Thinking Utilities to capture, organize, and retrieve thought chains from Large Language Models (LLMs).

## Why Use Thinking Utilities with LLMs?

LLMs often generate complex reasoning chains when solving problems. The Thinking Utilities provide:

1. **Structured Storage**: Capture multi-step reasoning in an organized format
2. **Semantic Retrieval**: Find similar reasoning patterns using semantic search
3. **Branching Logic**: Track alternative approaches to problem-solving
4. **Progressive Refinement**: Record step-by-step evolution of thoughts

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

### LLM Agents with Thinking Utilities

For LLM-based agents that need to track their reasoning:

```python
class ReasoningAgent:
    def __init__(self, llm_client, topic, mcp_client):
        self.llm_client = llm_client
        self.topic = topic
        self.mcp_client = mcp_client
        self.thinking_session = ThinkingSession(client=self.mcp_client)
        self.thought_count = 0
        
    def think(self, query, max_steps=5):
        """Generate and record a multi-step reasoning process."""
        thought = query
        self.thought_count = 0
        
        while self.thought_count < max_steps:
            self.thought_count += 1
            is_last_step = self.thought_count == max_steps
            
            # Get next reasoning step from LLM
            response = self.llm_client.generate(
                prompt=f"Previous thinking: {thought}\nContinue reasoning about {self.topic}. {'Provide final conclusion.' if is_last_step else 'Next step:'}"
            )
            
            # Record this step
            self.thinking_session.record_thought(
                thought=response,
                thought_number=self.thought_count,
                total_thoughts=max_steps,
                next_thought_needed=not is_last_step
            )
            
            thought = response
            
            # Check if LLM has reached a conclusion
            if "conclusion" in response.lower() or "final answer" in response.lower():
                break
                
        return self.thinking_session.get_session_summary()
```

## Best Practices for LLM Applications

1. **Atomic Thought Steps**: Encourage LLMs to produce clear, single-step thoughts rather than lengthy explanations
2. **Consistent Metadata**: Add model information, confidence scores, and task types in metadata
3. **Branch on Uncertainty**: Create branches when the LLM expresses uncertainty or offers alternative approaches
4. **Comparative Analysis**: Use similarity search to compare reasoning approaches across different models or problems
5. **Session Organization**: Group related reasoning chains in identifiable sessions for easier retrieval

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

# Analyze common reasoning patterns
for session in similar_sessions:
    print(f"Session ID: {session['metadata']['session_id']}")
    print(f"Model: {session['metadata'].get('llm_model', 'Unknown')}")
    print(f"Task: {session['metadata'].get('task', 'Unknown')}")
    print(f"Similarity Score: {session['distance']}")
    print("---")
```

By leveraging Chroma MCP Thinking Utilities, you can transform your LLM applications from black-box systems into transparent, analyzable reasoning engines with retrievable thought processes.
