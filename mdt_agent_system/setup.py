from setuptools import setup, find_packages

setup(
    name="mdt_agent_system",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn>=0.23.2",
        "pydantic>=2.4.2",
        "python-multipart>=0.0.6",
        "python-dotenv>=1.0.0",
        "aiofiles>=23.2.1",
        "sse-starlette>=1.6.5",
        "google-generativeai>=0.3.1",
        "langchain>=0.1.0",
        "langchain-google-genai>=0.0.5",
        "langchain-core>=0.1.7",
        "pytest>=8.3.5",
        "pytest-asyncio>=0.26.0"
    ],
    python_requires=">=3.9",
) 