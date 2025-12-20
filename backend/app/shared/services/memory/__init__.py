"""Memory services for agent context engineering.

Issue #245: Agent Memory Access (RAG)
"""

from app.shared.services.memory.agent_memory_service import (
    AgentMemoryService,
    MemorySearchResult,
    MemorySnippet,
)
from app.shared.services.memory.proactive_recall import (
    build_proactive_prompt,
    fetch_proactive_context,
    format_memory_context,
    inject_proactive_context,
)

__all__ = [
    "AgentMemoryService",
    "MemorySearchResult",
    "MemorySnippet",
    "build_proactive_prompt",
    "fetch_proactive_context",
    "format_memory_context",
    "inject_proactive_context",
]
