"""Repository for agent example CRUD operations.

Provides async database operations for few-shot example management.
Used by SemanticExampleSelector for retrieving relevant examples.
"""

import uuid
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.agent_example import AgentExample

logger = get_logger(__name__)

# Embedding dimensions (OpenAI text-embedding-3-small)
EMBEDDING_DIMENSIONS = 1536


class IExampleRepository(Protocol):
    """Protocol interface for example repository operations."""

    async def get_by_id(self, example_id: uuid.UUID) -> AgentExample | None:
        """Get a single example by ID."""
        ...

    async def get_by_agent_type(
        self,
        agent_type: str,
        min_quality: float = 0.8,
        limit: int = 10,
    ) -> list[AgentExample]:
        """Get high-quality examples for an agent type."""
        ...

    async def get_similar_examples(
        self,
        embedding: list[float],
        agent_type: str,
        content_type: str | None = None,
        min_quality: float = 0.8,
        limit: int = 5,
    ) -> list[tuple[AgentExample, float]]:
        """Get semantically similar examples using vector search."""
        ...


class ExampleRepository:
    """Repository for few-shot example operations.

    Provides async database operations for agent examples, including:
    - CRUD operations
    - Semantic similarity search using PGVector
    - Quality-based filtering
    - Bulk operations for seeding

    Example:
        >>> repo = ExampleRepository(session)
        >>> examples = await repo.get_similar_examples(
        ...     embedding=[0.1] * 1536,
        ...     agent_type="tech_comparator",
        ...     min_quality=0.8,
        ...     limit=5,
        ... )

    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async SQLAlchemy database session

        """
        self.session = session

    async def get_by_id(self, example_id: uuid.UUID) -> AgentExample | None:
        """Get example by ID.

        Args:
            example_id: Example UUID

        Returns:
            AgentExample if found, None otherwise

        """
        result = await self.session.execute(
            select(AgentExample).where(AgentExample.id == example_id)
        )
        return result.scalar_one_or_none()

    async def get_by_agent_type(
        self,
        agent_type: str,
        min_quality: float = 0.8,
        limit: int = 10,
    ) -> list[AgentExample]:
        """Get high-quality examples for an agent type.

        Returns examples ordered by quality score (descending).

        Args:
            agent_type: Agent type (e.g., 'tech_comparator')
            min_quality: Minimum quality score threshold (default: 0.8)
            limit: Maximum number of examples to return (default: 10)

        Returns:
            List of AgentExample objects

        """
        stmt = (
            select(AgentExample)
            .where(AgentExample.agent_type == agent_type)
            .where(AgentExample.quality_score >= min_quality)
            .order_by(AgentExample.quality_score.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_similar_examples(
        self,
        embedding: list[float],
        agent_type: str,
        content_type: str | None = None,
        min_quality: float = 0.8,
        limit: int = 5,
    ) -> list[tuple[AgentExample, float]]:
        """Get semantically similar examples using vector search.

        Uses PGVector cosine distance to find examples similar to the query.
        Returns examples ordered by similarity (lower distance = more similar).

        Args:
            embedding: Query embedding vector (1536 dimensions)
            agent_type: Agent type filter
            content_type: Optional content type filter (article, video, repo)
            min_quality: Minimum quality score threshold (default: 0.8)
            limit: Maximum number of examples to return (default: 5)

        Returns:
            List of (example, distance) tuples sorted by similarity

        Example:
            >>> repo = ExampleRepository(session)
            >>> results = await repo.get_similar_examples(
            ...     embedding=[0.1] * 1536,
            ...     agent_type="tech_comparator",
            ...     limit=3,
            ... )
            >>> for example, distance in results:
            ...     print(f"Quality: {example.quality_score}, Distance: {distance}")

        """
        if not embedding:
            logger.warning("get_similar_examples_empty_embedding")
            return []

        if len(embedding) != EMBEDDING_DIMENSIONS:
            logger.error(
                "get_similar_examples_invalid_dimensions",
                expected=EMBEDDING_DIMENSIONS,
                actual=len(embedding),
            )
            return []

        # Build query with vector similarity using cosine distance
        stmt = (
            select(
                AgentExample,
                AgentExample.embedding.cosine_distance(embedding).label("distance"),
            )
            .where(AgentExample.agent_type == agent_type)
            .where(AgentExample.quality_score >= min_quality)
            .where(AgentExample.embedding.isnot(None))
        )

        # Optional content type filter
        if content_type:
            stmt = stmt.where(AgentExample.content_type == content_type)

        # Order by similarity (smaller distance = more similar)
        stmt = stmt.order_by("distance").limit(limit)

        result = await self.session.execute(stmt)
        examples = [(row.AgentExample, row.distance) for row in result]

        logger.info(
            "get_similar_examples_complete",
            agent_type=agent_type,
            content_type=content_type,
            min_quality=min_quality,
            limit=limit,
            results_count=len(examples),
        )

        return examples

    async def create(self, example: AgentExample) -> AgentExample:
        """Create a new example.

        Args:
            example: AgentExample object to create

        Returns:
            Created AgentExample with ID populated

        """
        self.session.add(example)
        await self.session.commit()
        await self.session.refresh(example)

        logger.info(
            "example_created",
            example_id=example.id,
            agent_type=example.agent_type,
            quality_score=example.quality_score,
        )

        return example

    async def bulk_create(self, examples: list[AgentExample]) -> list[AgentExample]:
        """Create multiple examples in bulk.

        Useful for seeding the database with golden dataset examples.

        Args:
            examples: List of AgentExample objects to create

        Returns:
            List of created examples with IDs populated

        """
        self.session.add_all(examples)
        await self.session.commit()

        logger.info(
            "examples_bulk_created",
            count=len(examples),
        )

        return examples

    async def count_by_agent_type(self) -> dict[str, int]:
        """Get count of examples per agent type.

        Returns:
            Dictionary mapping agent_type to count

        Example:
            >>> counts = await repo.count_by_agent_type()
            >>> counts
            {'tech_comparator': 15, 'security_auditor': 12, ...}

        """
        stmt = select(AgentExample.agent_type, func.count(AgentExample.id)).group_by(
            AgentExample.agent_type
        )

        result = await self.session.execute(stmt)
        counts = {row[0]: row[1] for row in result}

        logger.info(
            "examples_counted_by_type",
            agent_types=len(counts),
            total_examples=sum(counts.values()),
        )

        return counts
