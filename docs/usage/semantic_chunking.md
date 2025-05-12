# Semantic Code Chunking

This document describes the semantic chunking feature implemented in the codebase indexing process.

## Overview

Traditional chunking methods divide text into fixed-size segments with overlap, which can break logical structures in code. Semantic chunking improves this by attempting to preserve the logical structure of code, such as functions, classes, and modules when creating chunks for vector embeddings.

## How It Works

The semantic chunking algorithm in `chroma_mcp_client/indexing.py` implements the following approach:

1. **Boundary Detection**: The algorithm identifies semantic boundaries in code files:
   - Class definitions
   - Function/method definitions
   - Module-level constructs

2. **Language-Specific Rules**: Different programming languages have different patterns for defining boundaries:
   - Python: `def function_name(...):`, `class ClassName:`, etc.
   - JavaScript/TypeScript: Function expressions, arrow functions, class methods
   - Other languages: Based on common patterns (Java, Go, C++, etc.)

3. **Fallback Mechanism**: If semantic boundaries don't produce suitable chunks (e.g., in very large functions or unstructured text), the algorithm falls back to traditional line-based chunking.

4. **Size Control**: Extremely large semantic chunks (e.g., a very long function) are further subdivided to avoid token limits and ensure optimal embedding.

## Benefits

Semantic chunking offers several advantages over traditional fixed-size chunking:

1. **Improved Relevance**: Queries are more likely to match complete logical units (whole functions or classes) rather than fragments.

2. **Better Context**: When retrieving chunks, you get complete methods or classes, making the context more understandable.

3. **Enhanced Bi-directional Linking**: Links between chat discussions and code changes are more meaningful when they reference complete logical units rather than arbitrary sections.

4. **More Effective RAG**: The RAG system provides better context when using chunks that follow logical boundaries.

## Implementation Details

The semantic chunking is primarily implemented through two functions:

1. **`chunk_file_content_semantic`**: The main entry point that attempts semantic chunking first before falling back to line-based chunking.

2. **`_chunk_code_semantic`**: The core implementation that analyzes code structure and identifies semantic boundaries.

These functions use regex patterns to identify:

- Python functions (with or without async, decorators)
- JavaScript/TypeScript functions and methods
- Class and interface definitions
- Other logical boundaries

## Example

Given a Python file with several functions:

```python
def function_one(a, b):
    """Docstring for function one."""
    return a + b

class MyClass:
    def method_one(self):
        return "Hello"
        
    def method_two(self, param):
        # Complex method with many lines
        result = 0
        for i in range(param):
            result += i
        return result

def function_two():
    return "Another function"
```

Traditional chunking might break this into fixed-size segments (e.g., 10 lines per chunk with 2 lines overlap):

```toolcall
Chunk 1: def function_one() through part of method_one()
Chunk 2: part of method_one() through part of method_two()
Chunk 3: part of method_two() through function_two()
```

With semantic chunking, it would be chunked as:

```toolcall
Chunk 1: def function_one() (complete function)
Chunk 2: class MyClass: with method_one() and method_two() (complete class)
Chunk 3: def function_two() (complete function)
```

## Usage

The semantic chunking is automatically applied when using the indexing features:

```bash
# Index all files in the repo with semantic chunking
chroma-client index --all

# Index specific files with semantic chunking 
chroma-client index path/to/file.py path/to/file.js

# Post-commit hook also uses semantic chunking automatically
```

No special configuration is needed as semantic chunking is now the default behavior.

## Customization

The chunking behavior can be modified by editing the constants in `src/chroma_mcp_client/indexing.py`:

- `DEFAULT_SUPPORTED_SUFFIXES`: File extensions recognized for indexing
- Regex patterns in `_chunk_code_semantic`: Language-specific patterns for boundary detection
- `MAX_LINES_PER_SEMANTIC_CHUNK`: Maximum size for a semantic chunk before further splitting
