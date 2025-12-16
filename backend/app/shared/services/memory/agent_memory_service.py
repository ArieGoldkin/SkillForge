"""Agent memory service for RAG-based context engineering.

Issue #245: Agent Memory Access (RAG)
Implements reactive and proactive recall patterns from Google ADK's Context Engineering.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.agent_memory import AgentMemory, MemoryType
from app.shared.services.embeddings.service import EmbeddingService

if TYPE_CHECKING:
    from app.core.types import EmbeddingVector

logger = get_logger(__name__)

# Relevance threshold for proactive injection (avoid noise)
DEFAULT_RELEVANCE_THRESHOLD = 0.7
DEFAULT_SEARCH_LIMIT = 5
DEFAULT_PROACTIVE_LIMIT = 3


@dataclass
class MemorySearchResult:
    """Result from memory search with relevance score."""

    memory: AgentMemory
    similarity: float

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.memory.id),
            "type": self.memory.memory_type,
            "content": self.memory.content,
            "similarity": round(self.similarity, 3),
            "metadata": self.memory.memory_metadata or {},
        }


@dataclass
class MemorySnippet:
    """Lightweight memory snippet for agent context injection."""

    content: str
    memory_type: str
    relevance: float
    source_id: str

    def to_context_string(self) -> str:
        """Format for injection into agent prompt."""
        return f"[{self.memory_type}] (relevance: {self.relevance:.2f}): {self.content}"


class AgentMemoryService:
    """Service for storing and retrieving agent memories.

    Implements two recall patterns:
    1. Reactive: Agent calls search_memory tool when it recognizes a knowledge gap
    2. Proactive: System pre-injects relevant context before agent invocation

    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        """Initialize memory service.

        Args:
            session: Database session for queries
            embedding_service: Optional embedding service (creates new if not provided)

        """
        self.session = session
        self._embedding_service = embedding_service

    @property
    def embedding_service(self) -> EmbeddingService:
        """Lazy-load embedding service."""
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    async def store(  # noqa: PLR0913
        self,
        content: str,
        memory_type: MemoryType,
        analysis_id: UUID | None = None,
        agent_type: str | None = None,
        metadata: dict | None = None,
        relevance_score: float = 1.0,
    ) -> AgentMemory:
        """Store a new memory with embedding.

        Args:
            content: The memory content to store
            memory_type: Type of memory (analysis_summary, vulnerability_pattern, etc.)
            analysis_id: Optional link to source analysis
            agent_type: Which agent created this memory
            metadata: Additional context as JSONB
            relevance_score: Quality/relevance score (0-1)

        Returns:
            The created AgentMemory record

        """
        # Generate embedding for the content
        embedding = await self.embedding_service.generate_embedding(content)

        memory = AgentMemory(
            id=uuid.uuid4(),
            analysis_id=analysis_id,
            memory_type=memory_type.value,
            agent_type=agent_type,
            content=content,
            embedding=embedding,
            relevance_score=relevance_score,
            memory_metadata=metadata or {},
        )

        self.session.add(memory)
        await self.session.commit()
        await self.session.refresh(memory)

        logger.info(
            "memory_stored",
            memory_id=str(memory.id),
            memory_type=memory_type.value,
            agent_type=agent_type,
            content_length=len(content),
        )

        return memory

    async def search(
        self,
        query: str,
        memory_type: MemoryType | None = None,
        limit: int = DEFAULT_SEARCH_LIMIT,
        threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    ) -> list[MemorySearchResult]:
        """Search memories by semantic similarity.

        Args:
            query: Search query text
            memory_type: Optional filter by memory type
            limit: Maximum results to return
            threshold: Minimum similarity threshold (0-1)

        Returns:
            List of MemorySearchResult sorted by similarity

        """
        # Generate embedding for query
        query_embedding = await self.embedding_service.generate_embedding(query)

        # Build similarity search query using pgvector
        results = await self._semantic_search(
            query_embedding=query_embedding,
            memory_type=memory_type,
            limit=limit,
            threshold=threshold,
        )

        logger.info(
            "memory_search_complete",
            query_length=len(query),
            memory_type=memory_type.value if memory_type else "all",
            results_count=len(results),
        )

        return results

    async def proactive_recall(
        self,
        content_summary: str,
        agent_type: str,
        limit: int = DEFAULT_PROACTIVE_LIMIT,
        threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    ) -> list[MemorySnippet]:
        """Proactively retrieve relevant memories for agent context.

        Called before agent invocation to inject relevant past knowledge.

        Args:
            content_summary: Summary of current content being analyzed
            agent_type: Type of agent being invoked (for filtering)
            limit: Maximum memories to inject
            threshold: Minimum relevance threshold

        Returns:
            List of MemorySnippet for context injection

        """
        # Map agent types to relevant memory types
        relevant_types = self._get_relevant_memory_types(agent_type)

        snippets: list[MemorySnippet] = []

        # Search for each relevant memory type
        for memory_type in relevant_types:
            results = await self.search(
                query=content_summary,
                memory_type=memory_type,
                limit=limit,
                threshold=threshold,
            )

            for result in results:
                snippets.append(
                    MemorySnippet(
                        content=str(result.memory.content),
                        memory_type=str(result.memory.memory_type),
                        relevance=result.similarity,
                        source_id=str(result.memory.id),
                    )
                )

        # Sort by relevance and limit
        snippets.sort(key=lambda x: x.relevance, reverse=True)
        snippets = snippets[:limit]

        logger.info(
            "proactive_recall_complete",
            agent_type=agent_type,
            content_length=len(content_summary),
            snippets_count=len(snippets),
        )

        return snippets

    async def _semantic_search(
        self,
        query_embedding: EmbeddingVector,
        memory_type: MemoryType | None,
        limit: int,
        threshold: float,
    ) -> list[MemorySearchResult]:
        """Execute semantic search using pgvector cosine similarity.

        Args:
            query_embedding: Query vector (1536 dimensions)
            memory_type: Optional filter
            limit: Max results
            threshold: Min similarity

        Returns:
            List of results with similarity scores

        """
        # Convert threshold to distance (cosine distance = 1 - similarity)
        max_distance = 1.0 - threshold

        # Build query with cosine distance
        # Note: pgvector <=> is cosine distance operator
        query = (
            select(
                AgentMemory,
                AgentMemory.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .where(AgentMemory.embedding.cosine_distance(query_embedding) <= max_distance)
            .order_by("distance")
            .limit(limit)
        )

        # Add memory type filter if specified
        if memory_type:
            query = query.where(AgentMemory.memory_type == memory_type.value)

        result = await self.session.execute(query)
        rows = result.all()

        return [
            MemorySearchResult(
                memory=row.AgentMemory,
                similarity=1.0 - row.distance,  # Convert distance back to similarity
            )
            for row in rows
        ]

    def _get_relevant_memory_types(self, agent_type: str) -> list[MemoryType]:
        """Map agent type to relevant memory types for proactive recall.

        Args:
            agent_type: The agent being invoked

        Returns:
            List of memory types relevant to this agent

        """
        # Agent-specific memory type mappings
        agent_memory_map: dict[str, list[MemoryType]] = {
            "security_auditor": [
                MemoryType.VULNERABILITY_PATTERN,
                MemoryType.BEST_PRACTICE,
            ],
            "tech_comparator": [
                MemoryType.ANALYSIS_SUMMARY,
                MemoryType.BEST_PRACTICE,
            ],
            "implementation_planner": [
                MemoryType.BEST_PRACTICE,
                MemoryType.ANALYSIS_SUMMARY,
            ],
            "code_reviewer": [
                MemoryType.VULNERABILITY_PATTERN,
                MemoryType.BEST_PRACTICE,
            ],
            "practical_applicator": [
                MemoryType.BEST_PRACTICE,
                MemoryType.ANALYSIS_SUMMARY,
            ],
        }

        # Default to all types if agent not in map
        return agent_memory_map.get(
            agent_type,
            [MemoryType.ANALYSIS_SUMMARY, MemoryType.BEST_PRACTICE],
        )

    async def store_agent_finding(
        self,
        analysis_id: UUID,
        agent_type: str,
        finding: str,
        metadata: dict | None = None,
    ) -> AgentMemory:
        """Store an agent's finding as a memory.

        Convenience method for storing findings after agent execution.

        Args:
            analysis_id: The analysis that produced this finding
            agent_type: Which agent produced the finding
            finding: The finding content
            metadata: Additional context

        Returns:
            The created memory

        """
        return await self.store(
            content=finding,
            memory_type=MemoryType.AGENT_FINDING,
            analysis_id=analysis_id,
            agent_type=agent_type,
            metadata=metadata,
        )
