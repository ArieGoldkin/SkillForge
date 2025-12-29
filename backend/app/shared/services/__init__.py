"""Shared services - Cross-domain infrastructure services.

This package contains services shared across multiple domains:
- embeddings/ - Embedding generation
- extraction/ - Content extraction
- chunking/ - Text chunking
- messaging/ - SSE and event broadcasting
- search/ - Semantic search
- persistence/ - Progress persistence
- backpressure/ - Rate limiting and backpressure
- cleanup/ - Data cleanup services
- mcp/ - MCP client integration
- memory/ - Agent memory services
- metrics/ - Metrics collection
- pii/ - PII detection
- utils/ - Utility functions
- llm/ - LLM provider abstraction (cloud/local)
"""

from app.shared.services import llm

__all__ = ["llm"]
