"""Search service for semantic, keyword, and hybrid content retrieval.

This service provides the main search functionality for the SkillForge platform,
supporting three search modes:

- SEMANTIC: Vector similarity search using embeddings (kNN with cosine similarity)
- KEYWORD: Full-text search using PostgreSQL tsvector
- HYBRID: Combined semantic + keyword search with Reciprocal Rank Fusion (RRF)

The service coordinates between the EmbeddingService for query vectorization
and the ChunkRepository for database queries, transforming results into
SearchResult schemas with highlighted snippets.

Architecture:
- Query embedding generation via EmbeddingService (OpenAI text-embedding-3-small)
- L2 normalized vectors for cosine similarity search
- RRF fusion with k=60 for hybrid search
- Snippet generation with <mark> tags for highlighting
- Metrics collection via MetricsService for observability

Example:
    >>> service = SearchService(session, embedding_service)
    >>> results = await service.search(
    ...     query="FastAPI authentication", mode=SearchMode.HYBRID, top_k=10
    ... )

"""

import re
import time
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SEARCH_TOP_K_MAX, SEARCH_TOP_K_MIN
from app.core.logging import get_logger
from app.models.analysis_chunk import AnalysisChunk
from app.schemas.search import (
    ChunkMetadata,
    ReRankConfig,
    SearchFilters,
    SearchMode,
    SearchResult,
)
from app.services.embeddings.service import EmbeddingService
from app.services.metrics import get_metrics_service
from app.services.search.reranker import ReRanker

if TYPE_CHECKING:
    from app.db.repositories.chunk_repository import ChunkRepository

logger = get_logger(__name__)


class SearchService:
    """Service for executing search queries across content chunks.

    Provides semantic, keyword, and hybrid search capabilities with
    result ranking, snippet generation, filtering, and optional re-ranking.

    Attributes:
        session: AsyncSession for database operations
        embedding_service: Service for generating query embeddings
        chunk_repo: Repository for chunk database operations
        reranker: Optional re-ranker for improving result relevance

    """

    chunk_repo: "ChunkRepository"

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: EmbeddingService,
        reranker: ReRanker | None = None,
    ) -> None:
        """Initialize SearchService with dependencies.

        Args:
            session: AsyncSession for database queries
            embedding_service: Service for generating embeddings
            reranker: Optional re-ranker for LLM-based relevance scoring

        """
        self.session = session
        self.embedding_service = embedding_service
        self.reranker = reranker or ReRanker()
        self._metrics = get_metrics_service()

        # Import here to avoid circular dependency
        from app.db.repositories.chunk_repository import ChunkRepository

        self.chunk_repo = ChunkRepository(session)

        logger.info(
            "search_service_initialized",
            embedding_model=embedding_service.model,
            embedding_dimensions=embedding_service.expected_dimensions,
        )

    async def search(
        self,
        query: str,
        mode: SearchMode,
        top_k: int = 10,
        filters: SearchFilters | None = None,
        rerank: ReRankConfig | None = None,
    ) -> list[SearchResult]:
        """Execute search query using specified mode with optional re-ranking.

        Main entry point for search operations. Routes to appropriate
        search method based on mode and returns unified SearchResult format.
        Optionally applies LLM-based re-ranking for improved relevance.

        Args:
            query: Search query string (max 1000 characters)
            mode: Search strategy (SEMANTIC, KEYWORD, or HYBRID)
            top_k: Maximum number of results to return (1-100)
            filters: Optional filters for content_type, date_range, etc.
            rerank: Optional re-ranking configuration for LLM-based scoring

        Returns:
            List of SearchResult objects sorted by relevance score (descending)

        Raises:
            ValueError: If query is empty or top_k is invalid
            EmbeddingError: If embedding generation fails (semantic/hybrid modes)

        Example:
            >>> results = await service.search(
            ...     query="How to implement OAuth2?",
            ...     mode=SearchMode.HYBRID,
            ...     top_k=5,
            ...     filters=SearchFilters(content_type="article"),
            ...     rerank=ReRankConfig(enabled=True, final_count=5),
            ... )

        """
        if not query or not query.strip():
            msg = "Search query cannot be empty"
            logger.error("search_empty_query")
            raise ValueError(msg)

        if top_k < SEARCH_TOP_K_MIN or top_k > SEARCH_TOP_K_MAX:
            msg = f"top_k must be between {SEARCH_TOP_K_MIN} and {SEARCH_TOP_K_MAX}, got {top_k}"
            logger.error("search_invalid_top_k", top_k=top_k)
            raise ValueError(msg)

        # Determine how many results to fetch from DB
        # If re-ranking is enabled, fetch more candidates than final_count
        fetch_k = top_k
        if rerank and rerank.enabled:
            fetch_k = rerank.candidate_count

        logger.info(
            "search_started",
            query=query[:100],  # Truncate for logging
            mode=mode.value,
            top_k=top_k,
            fetch_k=fetch_k,
            filters=filters.model_dump() if filters else None,
            rerank_enabled=rerank.enabled if rerank else False,
        )

        # Track timing for metrics
        start_time = time.perf_counter()
        reranked = False

        # Route to appropriate search method
        if mode == SearchMode.SEMANTIC:
            results = await self._semantic_search(query, fetch_k, filters)
        elif mode == SearchMode.KEYWORD:
            results = await self._keyword_search(query, fetch_k, filters)
        else:  # SearchMode.HYBRID
            results = await self._hybrid_search(query, fetch_k, filters)

        # Apply re-ranking if enabled
        if rerank and rerank.enabled:
            results = await self.reranker.rerank(
                query=query,
                results=results,
                config=rerank,
            )
            reranked = True
        else:
            # Truncate to top_k if not re-ranking
            results = results[:top_k]

        # Calculate latency and record metrics
        latency_ms = (time.perf_counter() - start_time) * 1000
        self._metrics.record_search_request(
            mode=mode.value,
            reranked=reranked,
            latency_ms=latency_ms,
            results_count=len(results),
        )

        logger.info(
            "search_completed",
            query=query[:100],
            mode=mode.value,
            results_count=len(results),
            top_score=results[0].score if results else None,
            reranked=reranked,
            latency_ms=latency_ms,
        )

        return results

    async def _semantic_search(
        self,
        query: str,
        top_k: int,
        filters: SearchFilters | None,
    ) -> list[SearchResult]:
        """Execute semantic search using vector similarity.

        Generates embedding for query and performs kNN search using
        cosine similarity (via L2 distance on normalized vectors).

        Args:
            query: Search query string
            top_k: Maximum number of results
            filters: Optional search filters

        Returns:
            List of SearchResult with similarity scores (0.0-1.0)

        """
        logger.info("semantic_search_started", query_length=len(query))

        # Generate normalized query embedding
        query_embedding = await self.embedding_service.generate_embedding(
            text=query,
            normalize=True,
        )

        logger.debug(
            "query_embedding_generated",
            embedding_dimensions=len(query_embedding),
            first_values=query_embedding[:3],
        )

        # Convert SearchFilters to dict format expected by repository
        filter_dict = self._filters_to_dict(filters) if filters else None

        # Execute semantic search via repository
        # Returns tuples of (chunk, similarity_score)
        chunks_with_scores = await self.chunk_repo.semantic_search(
            query_embedding=query_embedding,
            limit=top_k,
            filters=filter_dict,
        )

        logger.info(
            "semantic_search_completed",
            chunks_found=len(chunks_with_scores),
        )

        # Convert to SearchResult - scores already in 0.0-1.0 range
        return [self._chunk_to_result(chunk, score, query) for chunk, score in chunks_with_scores]

    async def _keyword_search(
        self,
        query: str,
        top_k: int,
        filters: SearchFilters | None,
    ) -> list[SearchResult]:
        """Execute keyword search using PostgreSQL full-text search.

        Uses tsvector and tsquery for full-text search with ranking.

        Args:
            query: Search query string
            top_k: Maximum number of results
            filters: Optional search filters

        Returns:
            List of SearchResult with relevance scores

        """
        logger.info("keyword_search_started", query=query[:100])

        # Convert SearchFilters to dict format expected by repository
        filter_dict = self._filters_to_dict(filters) if filters else None

        # Execute keyword search via repository
        chunks_with_scores = await self.chunk_repo.keyword_search(
            query_text=query,
            limit=top_k,
            filters=filter_dict,
        )

        logger.info(
            "keyword_search_completed",
            chunks_found=len(chunks_with_scores),
        )

        # Normalize scores to 0.0-1.0 range
        # ts_rank_cd scores are typically between 0 and ~1, but can be higher
        max_score = max((score for _, score in chunks_with_scores), default=1.0)
        normalized_results = [
            (chunk, min(score / max_score, 1.0) if max_score > 0 else 0.0)
            for chunk, score in chunks_with_scores
        ]

        # Convert to SearchResult with highlighted snippets
        return [self._chunk_to_result(chunk, score, query) for chunk, score in normalized_results]

    async def _hybrid_search(
        self,
        query: str,
        top_k: int,
        filters: SearchFilters | None,
    ) -> list[SearchResult]:
        """Execute hybrid search combining semantic and keyword search.

        Performs both semantic and keyword searches in parallel, then
        combines results using Reciprocal Rank Fusion (RRF).

        RRF formula: score(item) = Σ 1/(k + rank(item))
        where k=60 is the standard constant.

        Args:
            query: Search query string
            top_k: Maximum number of results
            filters: Optional search filters

        Returns:
            List of SearchResult sorted by RRF score

        """
        logger.info("hybrid_search_started", query=query[:100])

        # Generate query embedding for semantic component
        query_embedding = await self.embedding_service.generate_embedding(
            text=query,
            normalize=True,
        )

        # Convert SearchFilters to dict format expected by repository
        filter_dict = self._filters_to_dict(filters) if filters else None

        # Execute hybrid search via repository
        # Repository handles both semantic and keyword search + RRF fusion
        chunks_with_scores = await self.chunk_repo.hybrid_search(
            query_embedding=query_embedding,
            query_text=query,
            limit=top_k,
            filters=filter_dict,
        )

        logger.info(
            "hybrid_search_completed",
            chunks_found=len(chunks_with_scores),
        )

        # Normalize RRF scores to 0.0-1.0 range
        # RRF scores are typically small positive values
        max_score = max((score for _, score in chunks_with_scores), default=1.0)
        normalized_results = [
            (chunk, score / max_score if max_score > 0 else 0.0)
            for chunk, score in chunks_with_scores
        ]

        # Convert to SearchResult
        return [self._chunk_to_result(chunk, score, query) for chunk, score in normalized_results]

    def _generate_snippet(
        self,
        content: str,
        query: str,
        max_length: int = 200,
    ) -> str:
        """Generate highlighted snippet from content.

        Finds query terms in content and extracts surrounding context
        with <mark> tags for highlighting matched terms.

        Args:
            content: Full chunk content
            query: Search query for term matching
            max_length: Maximum snippet length in characters

        Returns:
            Snippet with <mark>highlighted</mark> query terms

        Example:
            >>> snippet = service._generate_snippet(
            ...     "FastAPI provides built-in OAuth2 support...", "OAuth2", max_length=100
            ... )
            >>> "<mark>OAuth2</mark>" in snippet
            True

        """
        if len(content) <= max_length:
            # Content is short enough, highlight and return
            return self._highlight_terms(content, query)

        # Extract query terms (split on whitespace and punctuation)
        query_terms = re.findall(r"\b\w+\b", query.lower())

        # Find first occurrence of any query term
        content_lower = content.lower()
        first_match_pos = len(content)

        for term in query_terms:
            pos = content_lower.find(term)
            if pos != -1 and pos < first_match_pos:
                first_match_pos = pos

        # If no matches found, return beginning of content
        if first_match_pos == len(content):
            snippet = content[:max_length]
            return snippet + "..." if len(content) > max_length else snippet

        # Calculate snippet window around first match
        # Try to center the match, but ensure we don't go negative
        half_length = max_length // 2
        start_pos = max(0, first_match_pos - half_length)
        end_pos = min(len(content), start_pos + max_length)

        # Adjust start if we're at the end of content
        if end_pos == len(content) and end_pos - start_pos < max_length:
            start_pos = max(0, end_pos - max_length)

        # Extract snippet
        snippet = content[start_pos:end_pos]

        # Add ellipsis if truncated
        prefix = "..." if start_pos > 0 else ""
        suffix = "..." if end_pos < len(content) else ""

        snippet = prefix + snippet + suffix

        # Highlight query terms
        return self._highlight_terms(snippet, query)

    def _highlight_terms(self, text: str, query: str) -> str:
        """Highlight query terms in text with <mark> tags.

        Args:
            text: Text to highlight
            query: Query containing terms to highlight

        Returns:
            Text with <mark>term</mark> tags around matches

        """
        # Extract query terms
        query_terms = re.findall(r"\b\w+\b", query.lower())

        # Build regex pattern for all terms (case-insensitive, word boundaries)
        if not query_terms:
            return text

        pattern = r"\b(" + "|".join(re.escape(term) for term in query_terms) + r")\b"

        # Replace matches with highlighted version
        highlighted = re.sub(
            pattern,
            r"<mark>\1</mark>",
            text,
            flags=re.IGNORECASE,
        )

        return highlighted

    def _chunk_to_result(
        self,
        chunk: AnalysisChunk,
        score: float,
        query: str,
    ) -> SearchResult:
        """Convert AnalysisChunk model to SearchResult schema.

        Args:
            chunk: Database chunk model
            score: Relevance score from search
            query: Original query for snippet generation

        Returns:
            SearchResult with snippet and metadata

        """
        # Extract metadata from chunk property (builds dict from individual fields)
        chunk_metadata: dict = chunk.chunk_metadata or {}

        # Get string values from chunk (handle potential None)
        # The content property returns snippet, chunk_type returns granularity
        content_str: str = chunk.content or ""
        chunk_type_str: str = chunk.chunk_type or "unknown"

        # Generate snippet with highlighted terms
        snippet = (
            self._generate_snippet(
                content=content_str,
                query=query,
                max_length=200,
            )
            if content_str
            else ""
        )

        # Build result metadata - using all available fields
        metadata = ChunkMetadata(
            section=chunk_metadata.get("section"),  # Maps to section_title
            path=chunk_metadata.get("path"),  # JSONB array from database
            content_type=chunk_metadata.get("content_type"),
            chunk_type=chunk_type_str,  # Maps to granularity
            language=chunk_metadata.get("language"),
            chunk_idx=chunk_metadata.get("chunk_idx"),
            chunk_total=chunk_metadata.get("chunk_total"),
        )

        # Create SearchResult
        result = SearchResult(
            chunk_id=str(chunk.id),
            analysis_id=str(chunk.analysis_id),
            content=content_str,
            snippet=snippet,
            score=float(score),  # Ensure float type
            metadata=metadata,
            created_at=chunk.created_at,  # type: ignore[arg-type]
        )

        return result

    def _filters_to_dict(self, filters: SearchFilters) -> dict[str, str]:
        """Convert SearchFilters Pydantic model to dict for repository.

        Transforms the typed SearchFilters object into a flat dictionary
        that can be used for JSONB filtering in the repository layer.

        Args:
            filters: SearchFilters with content_type, analysis_id, etc.

        Returns:
            Dict of filter key-value pairs for JSONB filtering

        Note:
            Currently supports content_type and analysis_id filters.
            Date range and tags filters require additional repository support.

        """
        result: dict[str, str] = {}

        if filters.content_type:
            result["content_type"] = filters.content_type

        if filters.analysis_id:
            result["analysis_id"] = filters.analysis_id

        # Note: date_range and tags filters require additional repository support
        # and can be added in a future iteration

        return result
