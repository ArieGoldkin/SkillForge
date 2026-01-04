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

from app.core.config import settings
from app.core.constants import (
    DOCUMENT_PATH_BOOST_FACTOR,
    SEARCH_TOP_K_MAX,
    SEARCH_TOP_K_MIN,
    SECTION_TITLE_BOOST_FACTOR,
    TECHNICAL_KEYWORD_BOOST,
    TECHNICAL_TERMS,
)
from app.core.logging import get_logger
from app.db.models.analysis_chunk import AnalysisChunk
from app.schemas.search import (
    ChunkMetadata,
    ReRankConfig,
    SearchFilters,
    SearchMode,
    SearchResult,
)
from app.shared.services.embeddings import EmbeddingServiceProtocol
from app.shared.services.metrics import get_metrics_service
from app.shared.services.search.decomposer import QueryDecomposer
from app.shared.services.search.hyde import HyDEService
from app.shared.services.search.reranker import ReRanker

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
        embedding_service: EmbeddingServiceProtocol,
        reranker: ReRanker | None = None,
        hyde_service: HyDEService | None = None,
        evaluation_mode: bool = False,
    ) -> None:
        """Initialize SearchService with dependencies.

        Args:
            session: AsyncSession for database queries
            embedding_service: Service for generating embeddings
            reranker: Optional re-ranker for LLM-based relevance scoring
            hyde_service: Optional HyDE service for vocabulary mismatch resolution
            evaluation_mode: Skip HyDE for faster, raw retrieval testing (Issue #638)

        """
        self.session = session
        self.embedding_service = embedding_service
        self.reranker = reranker or ReRanker()
        self.evaluation_mode = evaluation_mode

        # Only create HyDE service if not in evaluation mode
        if evaluation_mode:
            self.hyde_service = None
        else:
            self.hyde_service = hyde_service or HyDEService(embedding_service)

        self._metrics = get_metrics_service()

        # Import here to avoid circular dependency
        from app.db.repositories.chunk_repository import ChunkRepository

        self.chunk_repo = ChunkRepository(session)

        logger.info(
            "search_service_initialized",
            embedding_model=embedding_service.model,
            embedding_dimensions=embedding_service.expected_dimensions,
            hyde_enabled=not evaluation_mode,
            evaluation_mode=evaluation_mode,
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

        # Execute search with optional query decomposition (Issue #601)
        results = await self._execute_search(query, mode, fetch_k, filters)

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

    async def _execute_search(
        self,
        query: str,
        mode: SearchMode,
        fetch_k: int,
        filters: SearchFilters | None,
    ) -> list[SearchResult]:
        """Execute search with optional query decomposition.

        This method handles the query decomposition logic for multi-concept queries
        and routes to appropriate search methods.

        Args:
            query: Search query string
            mode: Search strategy (SEMANTIC, KEYWORD, or HYBRID)
            fetch_k: Number of results to fetch
            filters: Optional search filters

        Returns:
            List of SearchResult objects

        """
        # Query Decomposition (Issue #601)
        # For multi-concept queries, decompose and search each concept in parallel
        if settings.QUERY_DECOMPOSITION_ENABLED:
            decomposer = QueryDecomposer(embedding_service=self.embedding_service)
            decomp_result = await decomposer.decompose(query)

            logger.info(
                "query_decomposition_result",
                query=query[:100],
                is_multi_concept=decomp_result.is_multi_concept,
                num_concepts=len(decomp_result.concepts),
                source=decomp_result.source.value,
                latency_ms=decomp_result.latency_ms,
            )

            if decomp_result.is_multi_concept:
                return await self._multi_concept_search(
                    query=query,
                    mode=mode,
                    fetch_k=fetch_k,
                    filters=filters,
                    concepts=decomp_result.concepts,
                )

        # Single-concept query or decomposition disabled - use standard search flow
        return await self._single_concept_search(query, mode, fetch_k, filters)

    async def _multi_concept_search(
        self,
        query: str,
        mode: SearchMode,
        fetch_k: int,
        filters: SearchFilters | None,
        concepts: list[str],
    ) -> list[SearchResult]:
        """Execute multi-concept search with parallel retrieval and RRF fusion.

        Args:
            query: Original query for snippet generation
            mode: Search strategy
            fetch_k: Number of results per concept
            filters: Optional search filters
            concepts: List of concept queries from decomposition

        Returns:
            List of SearchResult objects with fused scores

        """
        decomposer = QueryDecomposer(embedding_service=self.embedding_service)

        # Define concept search function for parallel retrieval
        async def concept_search(concept: str, concept_top_k: int) -> list[tuple[str, float]]:
            """Search a single concept and return (chunk_id, score) tuples."""
            concept_results = await self._single_concept_search(
                concept, mode, concept_top_k, filters
            )
            return [(result.chunk_id, result.score) for result in concept_results]

        # Execute parallel retrieval with RRF fusion
        fused_chunk_scores = await decomposer.parallel_retrieve(
            concepts=concepts,
            search_fn=concept_search,
            top_k_per_concept=fetch_k,
        )

        # Convert fused (chunk_id, score) tuples back to SearchResult objects
        results = await self._fused_scores_to_results(
            fused_chunk_scores=fused_chunk_scores,
            query=query,
            top_k=fetch_k,
        )

        logger.info(
            "multi_concept_search_completed",
            query=query[:100],
            num_concepts=len(concepts),
            fused_results_count=len(results),
        )

        return results

    async def _single_concept_search(
        self,
        query: str,
        mode: SearchMode,
        fetch_k: int,
        filters: SearchFilters | None,
    ) -> list[SearchResult]:
        """Execute single-concept search using the specified mode.

        Args:
            query: Search query string
            mode: Search strategy
            fetch_k: Number of results to fetch
            filters: Optional search filters

        Returns:
            List of SearchResult objects

        """
        if mode == SearchMode.SEMANTIC:
            return await self._semantic_search(query, fetch_k, filters)
        if mode == SearchMode.KEYWORD:
            return await self._keyword_search(query, fetch_k, filters)
        return await self._hybrid_search(query, fetch_k, filters)

    async def _semantic_search(
        self,
        query: str,
        top_k: int,
        filters: SearchFilters | None,
    ) -> list[SearchResult]:
        """Execute semantic search using vector similarity.

        Uses HyDE (Hypothetical Document Embeddings) to improve retrieval
        for queries with vocabulary mismatch. Generates a hypothetical
        document that would answer the query, then embeds that document.

        In evaluation_mode, skips HyDE for faster, raw retrieval testing.

        Args:
            query: Search query string
            top_k: Maximum number of results
            filters: Optional search filters

        Returns:
            List of SearchResult with similarity scores (0.0-1.0)

        """
        logger.info(
            "semantic_search_started",
            query_length=len(query),
            evaluation_mode=self.evaluation_mode,
        )

        # In evaluation mode, use direct embedding (skip HyDE LLM call)
        # This is faster for CI/CD testing of raw retrieval quality
        if self.evaluation_mode or self.hyde_service is None:
            query_embedding = await self.embedding_service.generate_embedding(query)
            logger.debug(
                "direct_embedding_generated",
                query=query[:50],
                embedding_dimensions=len(query_embedding),
            )
        else:
            # Use HyDE for improved semantic matching (Issue #602)
            # Generates hypothetical document, embeds it instead of raw query
            hyde_result = await self.hyde_service.generate(query)
            query_embedding = hyde_result.embedding
            logger.debug(
                "hyde_embedding_generated",
                query=query[:50],
                hypothetical_len=len(hyde_result.hypothetical_doc),
                source=hyde_result.source.value,
                latency_ms=hyde_result.latency_ms,
                embedding_dimensions=len(query_embedding),
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
        Uses HyDE for the semantic component to improve vocabulary matching.

        In evaluation_mode, skips HyDE for faster, raw retrieval testing.

        RRF formula: score(item) = Σ 1/(k + rank(item))
        where k=60 is the standard constant.

        Args:
            query: Search query string
            top_k: Maximum number of results
            filters: Optional search filters

        Returns:
            List of SearchResult sorted by RRF score

        """
        logger.info(
            "hybrid_search_started",
            query=query[:100],
            evaluation_mode=self.evaluation_mode,
        )

        # In evaluation mode, use direct embedding (skip HyDE LLM call)
        if self.evaluation_mode or self.hyde_service is None:
            query_embedding = await self.embedding_service.generate_embedding(query)
            logger.debug(
                "hybrid_direct_embedding_generated",
                query=query[:50],
                embedding_dimensions=len(query_embedding),
            )
        else:
            # Use HyDE for semantic component (Issue #602)
            hyde_result = await self.hyde_service.generate(query)
            query_embedding = hyde_result.embedding
            logger.debug(
                "hybrid_hyde_embedding_generated",
                query=query[:50],
                source=hyde_result.source.value,
                latency_ms=hyde_result.latency_ms,
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
        results = [
            self._chunk_to_result(chunk, score, query) for chunk, score in normalized_results
        ]

        # Apply metadata-based boosts for improved ranking
        # This boosts results where query terms match section titles or document paths
        return self._apply_metadata_boosts(results, query)

    async def _fused_scores_to_results(
        self,
        fused_chunk_scores: list[tuple[str, float]],
        query: str,
        top_k: int,
    ) -> list[SearchResult]:
        """Convert fused (chunk_id, score) tuples to SearchResult objects.

        This method takes the output of RRF fusion (chunk_id, score pairs) and
        fetches the full chunk data from the database to construct SearchResult
        objects with snippets and metadata.

        Args:
            fused_chunk_scores: List of (chunk_id, rrf_score) tuples from fusion
            query: Original query for snippet generation
            top_k: Maximum number of results to return

        Returns:
            List of SearchResult objects with full chunk data and snippets

        """
        if not fused_chunk_scores:
            return []

        # Limit to top_k
        fused_chunk_scores = fused_chunk_scores[:top_k]

        # Extract chunk IDs
        chunk_ids = [chunk_id for chunk_id, _ in fused_chunk_scores]

        # Fetch chunks from database
        chunks = await self.chunk_repo.get_by_ids(chunk_ids)

        # Create mapping from chunk_id to chunk for fast lookup
        chunk_map = {str(chunk.id): chunk for chunk in chunks}

        # Build SearchResult objects, preserving RRF score order
        results = []
        for chunk_id, rrf_score in fused_chunk_scores:
            chunk = chunk_map.get(chunk_id)
            if chunk:
                # Convert chunk to SearchResult with RRF score
                result = self._chunk_to_result(chunk, rrf_score, query)
                results.append(result)

        logger.debug(
            "fused_scores_converted",
            input_count=len(fused_chunk_scores),
            output_count=len(results),
            missing_chunks=len(fused_chunk_scores) - len(results),
        )

        return results

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
        return re.sub(
            pattern,
            r"<mark>\1</mark>",
            text,
            flags=re.IGNORECASE,
        )

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
        return SearchResult(
            chunk_id=str(chunk.id),
            analysis_id=str(chunk.analysis_id),
            content=content_str,
            snippet=snippet,
            score=float(score),  # Ensure float type
            metadata=metadata,
            created_at=chunk.created_at,
        )

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

    def _is_technical_query(self, query: str) -> bool:
        """Detect if query contains technical terms warranting keyword boost.

        Technical queries benefit from stronger keyword matching because
        technical terms (langgraph, kubernetes, oauth) have precise meanings
        that semantic search may conflate with similar concepts.

        Args:
            query: Search query string

        Returns:
            True if query contains any recognized technical terms

        """
        query_lower = query.lower()
        query_terms = set(re.findall(r"\b\w+\b", query_lower))
        return bool(query_terms & TECHNICAL_TERMS)

    def _apply_metadata_boosts(
        self,
        results: list[SearchResult],
        query: str,
    ) -> list[SearchResult]:
        """Apply metadata-based score boosts for improved ranking.

        Boosts are applied for:
        1. Section title matches - 1.5x when query terms appear in section title
        2. Document path matches - 1.15x when query terms appear in document path
        3. Technical queries - Additional keyword weight for technical terms

        Args:
            results: List of SearchResult from initial retrieval
            query: Original query for term matching

        Returns:
            Results with boosted scores, re-sorted by boosted score

        Note:
            Boosts are multiplicative and capped at reasonable limits to
            prevent score explosion while still meaningfully affecting rank.

        """
        if not results:
            return results

        query_terms = set(re.findall(r"\b\w+\b", query.lower()))
        is_technical = self._is_technical_query(query)

        boosted_results = []
        for result in results:
            boost_factor = 1.0

            # Section title boost (1.5x) - when query terms match section title
            section = result.metadata.section
            if section:
                section_terms = set(re.findall(r"\b\w+\b", section.lower()))
                if query_terms & section_terms:
                    boost_factor *= SECTION_TITLE_BOOST_FACTOR
                    logger.debug(
                        "section_title_boost_applied",
                        chunk_id=result.chunk_id,
                        section=section,
                        boost=SECTION_TITLE_BOOST_FACTOR,
                    )

            # Document path boost (1.15x) - when query terms match path components
            path = result.metadata.path
            if path:
                path_text = " ".join(path).lower()
                path_terms = set(re.findall(r"\b\w+\b", path_text))
                if query_terms & path_terms:
                    boost_factor *= DOCUMENT_PATH_BOOST_FACTOR
                    logger.debug(
                        "document_path_boost_applied",
                        chunk_id=result.chunk_id,
                        path=path,
                        boost=DOCUMENT_PATH_BOOST_FACTOR,
                    )

            # Technical keyword boost (1.2x) - for technical queries
            if is_technical and result.metadata.chunk_type == "code_block":
                boost_factor *= TECHNICAL_KEYWORD_BOOST
                logger.debug(
                    "technical_keyword_boost_applied",
                    chunk_id=result.chunk_id,
                    boost=TECHNICAL_KEYWORD_BOOST,
                )

            # Apply boost to score (capped at 1.0 for normalized scores)
            boosted_score = min(result.score * boost_factor, 1.0)

            # Create new result with boosted score
            boosted_result = SearchResult(
                chunk_id=result.chunk_id,
                analysis_id=result.analysis_id,
                content=result.content,
                snippet=result.snippet,
                score=boosted_score,
                metadata=result.metadata,
                created_at=result.created_at,
            )
            boosted_results.append(boosted_result)

        # Re-sort by boosted score
        boosted_results.sort(key=lambda r: r.score, reverse=True)

        if any(r.score != orig.score for r, orig in zip(boosted_results, results, strict=False)):
            logger.info(
                "metadata_boosts_applied",
                original_top_score=results[0].score if results else 0,
                boosted_top_score=boosted_results[0].score if boosted_results else 0,
                is_technical_query=is_technical,
            )

        return boosted_results
