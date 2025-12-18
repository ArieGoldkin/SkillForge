"""Semantic example selector for Few-Shot Prompting.

Retrieves high-quality agent examples based on semantic similarity to input content.
Uses PGVector for efficient vector similarity search.

Architecture:
- Query PGVector using cosine distance for semantic similarity
- Filter by agent type and minimum quality score
- Return 3-6 examples ordered by relevance
- Performance target: < 100ms P95 latency

Example:
    >>> selector = SemanticExampleSelector(db_session, embedding_service)
    >>> result = await selector.select_examples(
    ...     content="Comparing React vs Vue",
    ...     agent_type="tech_comparator",
    ...     max_examples=5,
    ... )
    >>> len(result.examples) <= 5
    True

"""

import time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.shared.services.embeddings.service import EmbeddingService
from app.shared.services.examples.schemas import (
    AgentExample,
    ExampleSelectionResult,
)

logger = get_logger(__name__)

# Embedding dimensions (OpenAI text-embedding-3-small)
EMBEDDING_DIMENSIONS = 1536

# Maximum cosine distance for relevant examples (0.3 = 70% similarity)
MAX_SIMILARITY_DISTANCE = 0.3


class SemanticExampleSelector:
    """Select few-shot examples using semantic similarity.

    Uses PGVector cosine distance to find examples similar to the input content.
    Supports filtering by agent type, content type, and quality threshold.

    Performance: P95 < 100ms (target)

    Example:
        >>> async with get_db() as session:
        ...     selector = SemanticExampleSelector(session, embedding_service)
        ...     result = await selector.select_examples(
        ...         content="How to implement state management in React",
        ...         agent_type="implementation_planner",
        ...         max_examples=3,
        ...     )

    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: EmbeddingService,
    ) -> None:
        """Initialize selector with database session and embedding service.

        Args:
            session: Async SQLAlchemy database session
            embedding_service: Service for generating embeddings

        """
        self.session = session
        self.embedding_service = embedding_service

    async def select_examples(
        self,
        content: str,
        agent_type: str,
        max_examples: int = 5,
        min_quality_score: float = 0.7,
        content_type: str | None = None,
    ) -> ExampleSelectionResult:
        """Select examples using semantic similarity search.

        Strategy:
        1. Generate embedding for input content (first 2000 chars)
        2. Query PGVector for similar examples (cosine distance)
        3. Filter by agent type and quality threshold
        4. Optionally filter by content type
        5. Return top K examples ordered by similarity

        Args:
            content: Input content to find examples for
            agent_type: Agent type (e.g., 'tech_comparator')
            max_examples: Maximum number of examples to return (default: 5)
            min_quality_score: Minimum quality score filter (default: 0.7)
            content_type: Optional content type filter (article, video, repo)

        Returns:
            ExampleSelectionResult with selected examples and metadata

        Raises:
            ValueError: If content is empty or agent_type is invalid
            EmbeddingError: If embedding generation fails

        Example:
            >>> result = await selector.select_examples(
            ...     content="Compare FastAPI vs Flask performance",
            ...     agent_type="tech_comparator",
            ...     max_examples=3,
            ...     min_quality_score=0.8,
            ... )
            >>> len(result.examples) <= 3
            True

        """
        start_time = time.perf_counter()

        # Validate inputs
        if not content or not content.strip():
            msg = "Content cannot be empty"
            logger.error("example_selection_empty_content")
            raise ValueError(msg)

        if not agent_type or not agent_type.strip():
            msg = "Agent type cannot be empty"
            logger.error("example_selection_empty_agent_type")
            raise ValueError(msg)

        # Truncate content for embedding (first 2000 chars)
        content_preview = content[:2000]

        # Generate embedding for content
        try:
            query_embedding = await self.embedding_service.generate_embedding(
                content_preview, normalize=True
            )
        except Exception as e:
            logger.exception(
                "example_selection_embedding_failed",
                agent_type=agent_type,
                error=str(e),
            )
            # Return empty result on embedding failure
            return ExampleSelectionResult(
                examples=[],
                total_candidates=0,
                selection_strategy="semantic_similarity",
                avg_quality_score=None,
                avg_similarity_distance=None,
            )

        # Import AgentExample model (lazy import to avoid circular dependencies)
        from app.db.models.agent_example import AgentExample as AgentExampleModel

        # Build vector similarity query
        # Using cosine_distance for semantic similarity
        # Only include examples with high relevance (distance <= MAX_SIMILARITY_DISTANCE)
        query = (
            select(
                AgentExampleModel,
                AgentExampleModel.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .where(AgentExampleModel.agent_type == agent_type)
            .where(AgentExampleModel.quality_score >= min_quality_score)
            .where(AgentExampleModel.embedding.isnot(None))
            .where(
                AgentExampleModel.embedding.cosine_distance(query_embedding)
                <= MAX_SIMILARITY_DISTANCE
            )
        )

        # Optional content type filter
        if content_type:
            query = query.where(AgentExampleModel.content_type == content_type)

        # Order by similarity (lower distance = more similar) and limit
        query = query.order_by("distance").limit(max_examples)

        # Execute query
        try:
            result = await self.session.execute(query)
            rows = result.all()
        except Exception as e:
            logger.exception(
                "example_selection_query_failed",
                agent_type=agent_type,
                error=str(e),
            )
            # Return empty result on query failure
            return ExampleSelectionResult(
                examples=[],
                total_candidates=0,
                selection_strategy="semantic_similarity",
                avg_quality_score=None,
                avg_similarity_distance=None,
            )

        # Convert to Pydantic schemas
        examples = []
        for row in rows:
            example_model = row[0]
            distance = row[1]

            example = AgentExample(
                id=example_model.id,
                agent_type=example_model.agent_type,
                input_summary=example_model.input_summary,
                input_content_preview=example_model.input_content_preview,
                output_example=example_model.output_example,
                context_note=example_model.context_note,
                quality_score=example_model.quality_score,
                content_type=example_model.content_type,
                difficulty_level=example_model.difficulty_level,
                similarity_distance=distance,
            )
            examples.append(example)

        # Calculate statistics
        total_candidates = await self._count_candidates(agent_type, min_quality_score, content_type)
        avg_quality = sum(e.quality_score for e in examples) / len(examples) if examples else None
        avg_distance = (
            sum(e.similarity_distance for e in examples if e.similarity_distance) / len(examples)
            if examples
            else None
        )

        # Calculate latency
        latency_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "example_selection_complete",
            agent_type=agent_type,
            content_length=len(content),
            max_examples=max_examples,
            results_count=len(examples),
            total_candidates=total_candidates,
            avg_quality_score=avg_quality,
            avg_similarity_distance=avg_distance,
            latency_ms=latency_ms,
        )

        return ExampleSelectionResult(
            examples=examples,
            total_candidates=total_candidates,
            selection_strategy="semantic_similarity",
            avg_quality_score=avg_quality,
            avg_similarity_distance=avg_distance,
        )

    async def _count_candidates(
        self,
        agent_type: str,
        min_quality_score: float,
        content_type: str | None,
    ) -> int:
        """Count total available examples matching filters.

        Args:
            agent_type: Agent type filter
            min_quality_score: Quality threshold
            content_type: Optional content type filter

        Returns:
            Total count of matching examples

        """
        from app.db.models.agent_example import AgentExample as AgentExampleModel

        query = (
            select(func.count(AgentExampleModel.id))
            .where(AgentExampleModel.agent_type == agent_type)
            .where(AgentExampleModel.quality_score >= min_quality_score)
            .where(AgentExampleModel.embedding.isnot(None))
        )

        if content_type:
            query = query.where(AgentExampleModel.content_type == content_type)

        try:
            result = await self.session.execute(query)
            count = result.scalar_one()
            return count or 0
        except Exception:
            logger.exception(
                "example_selection_count_failed",
                agent_type=agent_type,
            )
            return 0
