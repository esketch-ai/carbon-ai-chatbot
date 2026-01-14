"""Setup script for react-agent package."""
from setuptools import setup, find_packages

setup(
    name="react-agent",
    version="0.0.1",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "python-dotenv>=1.0.1",
        "langgraph>=0.6.10",
        "langchain-anthropic>=0.3.0",
        "langchain-tavily>=0.2.12",
        "langchain>=0.3.27",
        "langchain-community>=0.3.0",
        "langchain-text-splitters>=0.3.0",
        "langchain-core>=0.3.0",
        "chromadb>=0.4.0",
        "sentence-transformers>=2.2.0",
        "pypdf>=3.17.0",
        "python-docx>=1.0.0",
        "httpx>=0.27.0",
        "nest-asyncio>=1.5.0",
    ],
    python_requires=">=3.11,<4.0",
)
