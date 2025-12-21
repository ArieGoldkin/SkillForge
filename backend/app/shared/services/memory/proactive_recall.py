"""Proactive recall integration for agent context injection.

Issue #245: Agent Memory Access (RAG)
Implements proactive recall pattern from Google ADK's Context Engineering.

The proactive recall system pre-fetches relevant memories from past analyses
and injects them into the agent's context BEFORE the agent is invoked.
This differs from reactive recall where the agent explicitly calls search_memory.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.shared.services.memory.agent_memory_service import AgentMemoryService, MemorySnippet

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.shared.services.embeddings.service import EmbeddingService

logger = get_logger(__name__)

# Default configuration
DEFAULT_PROACTIVE_LIMIT = 3
DEFAULT_RELEVANCE_THRESHOLD = 0.7


async def fetch_proactive_context(  # noqa: PLR0913
    session: AsyncSession,
    content_summary: str,
    agent_type: str,
    limit: int = DEFAULT_PROACTIVE_LIMIT,
    threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    embedding_service: EmbeddingService | None = None,
) -> list[MemorySnippet]:
    """Fetch relevant memories for proactive injection.

    This is the main entry point for proactive recall. It creates an
    AgentMemoryService, queries for relevant memories, and returns
    formatted snippets ready for context injection.

    Args:
        session: Database session for queries
        content_summary: Summary of content being analyzed (used for similarity)
        agent_type: Type of agent being invoked (filters memory types)
        limit: Maximum memories to return
        threshold: Minimum relevance score (0-1)
        embedding_service: Optional embedding service (creates new if not provided)

    Returns:
        List of MemorySnippet objects sorted by relevance

    Example:
        >>> async with get_session_factory()() as session:
        ...     snippets = await fetch_proactive_context(
        ...         session=session,
        ...         content_summary="React hooks performance optimization",
        ...         agent_type="security_auditor",
        ...     )
        ...     context = format_memory_context(snippets)

    """
    service = AgentMemoryService(session, embedding_service)

    snippets = await service.proactive_recall(
        content_summary=content_summary,
        agent_type=agent_type,
        limit=limit,
        threshold=threshold,
    )

    logger.info(
        "proactive_context_fetched",
        agent_type=agent_type,
        snippets_count=len(snippets),
        content_summary_length=len(content_summary),
    )

    return snippets


def format_memory_context(snippets: list[MemorySnippet]) -> str:
    """Format memory snippets for injection into agent prompt.

    Creates a structured context block that can be prepended to the
    agent's user prompt. The format is designed to be clear and actionable.

    Args:
        snippets: List of MemorySnippet objects

    Returns:
        Formatted context string, or empty string if no snippets

    Example output:
        ## Relevant Context from Past Analyses

        The following information from past analyses may be relevant:

        1. [vulnerability_pattern] (relevance: 0.85):
           SQL injection patterns in ORM queries...

        2. [best_practice] (relevance: 0.78):
           Always use parameterized queries for database access...

        Use this context to inform your analysis where applicable.

    """
    if not snippets:
        return ""

    lines = [
        "## Relevant Context from Past Analyses",
        "",
        "The following information from past analyses may be relevant:",
        "",
    ]

    for i, snippet in enumerate(snippets, 1):
        lines.append(f"{i}. {snippet.to_context_string()}")
        lines.append("")

    lines.append("Use this context to inform your analysis where applicable.")
    lines.append("")

    return "\n".join(lines)


def inject_proactive_context(
    user_prompt: str,
    memory_context: str,
) -> str:
    """Inject proactive memory context into user prompt.

    Prepends the memory context to the existing user prompt with
    a clear separation.

    Args:
        user_prompt: Original user prompt for the agent
        memory_context: Formatted memory context (from format_memory_context)

    Returns:
        Enhanced user prompt with memory context prepended

    """
    if not memory_context:
        return user_prompt

    return f"{memory_context}\n---\n\n{user_prompt}"


async def build_proactive_prompt(  # noqa: PLR0913
    session: AsyncSession,
    user_prompt: str,
    content_summary: str,
    agent_type: str,
    limit: int = DEFAULT_PROACTIVE_LIMIT,
    threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    embedding_service: EmbeddingService | None = None,
) -> str:
    """Build user prompt with proactive memory injection.

    Convenience function that combines fetch, format, and inject steps.

    Args:
        session: Database session for queries
        user_prompt: Original user prompt
        content_summary: Summary for similarity search
        agent_type: Agent type for memory filtering
        limit: Maximum memories to inject
        threshold: Minimum relevance threshold
        embedding_service: Optional embedding service

    Returns:
        Enhanced user prompt with relevant memories prepended

    Example:
        >>> prompt = await build_proactive_prompt(
        ...     session=session,
        ...     user_prompt="Analyze this code for security issues...",
        ...     content_summary="React authentication flow with JWT",
        ...     agent_type="security_auditor",
        ... )

    """
    snippets = await fetch_proactive_context(
        session=session,
        content_summary=content_summary,
        agent_type=agent_type,
        limit=limit,
        threshold=threshold,
        embedding_service=embedding_service,
    )

    memory_context = format_memory_context(snippets)
    return inject_proactive_context(user_prompt, memory_context)
