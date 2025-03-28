from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="chroma-mcp",
    version="0.1.0",
    author="Nold Coaching & Consulting",
    author_email="info@noldcoaching.de",
    description="A Model Context Protocol (MCP) server for ChromaDB operations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nold-ai/nold-ai-automation",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=[
        "chromadb>=0.4.0",
        "fastmcp>=0.1.0",  # Adjust version as needed
        "python-dotenv>=0.19.0",
        "pydantic>=2.0.0",
        "onnxruntime>=1.15.0",  # For ONNXMiniLM_L6_V2 embedding function
        "sentence-transformers>=2.2.0",  # For embedding functions
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "isort>=5.0.0",
            "mypy>=1.0.0",
            "pylint>=2.17.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "chroma-mcp=chroma_mcp.server:main",
        ],
    },
) 