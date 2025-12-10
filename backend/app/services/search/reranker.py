"""Re-ranking service for improving search result relevance.

This module provides LLM-based re-ranking of search results using
a cost-effective model (GPT-4o-mini) for relevance scoring, combined with
structural priors from chunk metadata.

Architecture:
- Uses lightweight LLM for semantic relevance scoring
- Applies structural priors based on chunk position/path
- Gracefully falls back to base ranking on timeout/error
- Batch processes candidates for efficiency
- Records metrics via MetricsService for observability

Example:
    >>> from app.services.search.reranker import ReRanker
    >>> from app.schemas.search import ReRankConfig
    >>> reranker = ReRanker()
    >>> ranked = await reranker.rerank(
    ...     query="OAuth2 authentication",
    ...     results=search_results,
    ...     config=ReRankConfig(enabled=True),
    ... )

"""

import asyncio
import time
from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.constants import (
    RERANK_ALPHA,
    RERANK_BETA,
    RERANK_GAMMA,
    RERANK_MODEL,
)
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.schemas.search import ReRankConfig, SearchResult
from app.services.metrics import get_metrics_service
from app.services.search.structural_priors import StructuralPriorScorer

logger = get_logger(__name__)


@dataclass
class ReRankScore:
    """Score components for a re-ranked result.

    Attributes:
        chunk_id: Unique identifier for the chunk
        base_score: Original score from retrieval (0.0-1.0)
        llm_score: LLM relevance score (0.0-1.0)
        structural_score: Metadata-based prior score
        final_score: Combined weighted score

    """

    chunk_id: str
    base_score: float
    llm_score: float
    structural_score: float
    final_score: float


class ReRanker:
    """Service for re-ranking search results using LLM + structural priors.

    Uses a cost-effective LLM model for relevance scoring with fallback
    to base ranking on timeout or error. Combines LLM scores with
    structural priors from chunk metadata.

    Attributes:
        model: The LLM model used for scoring
        structural_scorer: Scorer for metadata-based priors

    Example:
        >>> reranker = ReRanker()
        >>> results = await reranker.rerank(
        ...     query="OAuth2 authentication",
        ...     results=search_results,
        ...     config=ReRankConfig(enabled=True, final_count=5),
        ... )

    """

    def __init__(self, model: BaseChatModel | None = None) -> None:
        """Initialize ReRanker with optional custom model.

        Args:
            model: Optional custom model. Defaults to RERANK_MODEL from constants.

        """
        self._model = model
        self._structural_scorer = StructuralPriorScorer()
        self._metrics = get_metrics_service()

    @property
    def model(self) -> BaseChatModel:
        """Lazy-load the LLM model on first access."""
        if self._model is None:
            self._model = get_chat_model({"configurable": {"model": RERANK_MODEL}})
        return self._model

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        config: ReRankConfig,
    ) -> list[SearchResult]:
        """Re-rank search results using LLM scoring + structural priors.

        Fetches top candidates, scores them with LLM and structural priors,
        combines scores with configurable weights, and returns top results.

        Args:
            query: Original search query
            results: List of SearchResult candidates to re-rank
            config: Re-ranking configuration

        Returns:
            Re-ranked list of SearchResult, truncated to config.final_count

        Note:
            On timeout or error, returns results sorted by base score
            (graceful fallback to preserve user experience).

        """
        if not config.enabled:
            return results[: config.final_count]

        # If we have fewer results than final_count, just return them
        if len(results) <= config.final_count:
            return results

        # Track timing for metrics
        start_time = time.perf_counter()

        try:
            async with asyncio.timeout(config.timeout_seconds):
                # Score all candidates
                scores = await self._score_candidates(query, results, config)

                # Sort by final_score descending, with chunk_id as tiebreaker for determinism
                scores.sort(key=lambda s: (-s.final_score, s.chunk_id))

                # Map back to SearchResult, updating scores
                chunk_to_score = {s.chunk_id: s for s in scores}
                reranked: list[SearchResult] = []

                for result in results:
                    if result.chunk_id in chunk_to_score:
                        score_data = chunk_to_score[result.chunk_id]
                        # Create new result with updated score
                        # Clamp final score to [0, 1] range
                        clamped_score = max(0.0, min(1.0, score_data.final_score))
                        updated = result.model_copy(update={"score": clamped_score})
                        reranked.append(updated)

                # Sort by new score (with tiebreaker) and truncate
                reranked.sort(key=lambda r: (-r.score, r.chunk_id))

                # Record success metrics
                latency_ms = (time.perf_counter() - start_time) * 1000
                output_count = min(len(reranked), config.final_count)
                self._metrics.record_rerank_request(
                    latency_ms=latency_ms,
                    input_count=len(results),
                    output_count=output_count,
                )

                logger.info(
                    "rerank_complete",
                    query_length=len(query),
                    input_count=len(results),
                    output_count=output_count,
                    latency_ms=latency_ms,
                )

                return reranked[: config.final_count]

        except TimeoutError:
            # Record timeout (still log latency)
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._metrics.record_rerank_request(
                latency_ms=latency_ms,
                input_count=len(results),
                output_count=config.final_count,
            )

            logger.warning(
                "rerank_timeout",
                query=query[:100],
                timeout=config.timeout_seconds,
                candidate_count=len(results),
                latency_ms=latency_ms,
            )
            return self._fallback_rank(results, config.final_count)

        except (ValueError, RuntimeError, ConnectionError, OSError) as e:
            # Record error
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._metrics.record_rerank_request(
                latency_ms=latency_ms,
                input_count=len(results),
                output_count=config.final_count,
            )

            logger.warning(
                "rerank_failed",
                query=query[:100],
                error=str(e),
                latency_ms=latency_ms,
            )
            return self._fallback_rank(results, config.final_count)

    async def _score_candidates(
        self,
        query: str,
        results: list[SearchResult],
        config: ReRankConfig,
    ) -> list[ReRankScore]:
        """Score candidates using LLM and structural priors.

        Args:
            query: Search query
            results: Candidates to score
            config: Re-ranking configuration

        Returns:
            List of ReRankScore with all score components

        """
        # Get LLM scores for all candidates
        llm_scores = await self._batch_llm_score(query, results)

        # Calculate structural priors if enabled
        if config.use_structural_priors:
            structural_scores = self._structural_scorer.score_batch([r.metadata for r in results])
        else:
            structural_scores = [0.0] * len(results)

        # Combine scores using weights
        scores: list[ReRankScore] = []
        for i, result in enumerate(results):
            base = result.score
            llm = llm_scores.get(result.chunk_id, 0.5)
            structural = structural_scores[i]

            # Weighted combination
            final = (RERANK_ALPHA * base) + (RERANK_BETA * llm) + (RERANK_GAMMA * structural)

            scores.append(
                ReRankScore(
                    chunk_id=result.chunk_id,
                    base_score=base,
                    llm_score=llm,
                    structural_score=structural,
                    final_score=final,
                )
            )

        return scores

    async def _batch_llm_score(
        self,
        query: str,
        results: list[SearchResult],
    ) -> dict[str, float]:
        """Score candidates using batch LLM call.

        Args:
            query: Search query
            results: Candidates to score

        Returns:
            Dict mapping chunk_id to relevance score (0.0-1.0)

        """
        # Build prompt with all candidates
        prompt = self._build_scoring_prompt(query, results)

        # Call LLM
        messages = [
            SystemMessage(content=self._get_system_prompt()),
            HumanMessage(content=prompt),
        ]

        response = await self.model.ainvoke(messages)
        content = response.content if isinstance(response.content, str) else str(response.content)

        # Parse scores from response
        return self._parse_scores(content, results)

    def _get_system_prompt(self) -> str:
        """Get system prompt for relevance scoring."""
        return """You are a search relevance scoring assistant. Your task is to rate
how relevant each document chunk is to a given search query.

For each document, output ONLY a relevance score from 0.0 to 1.0:
- 1.0 = Perfectly relevant, directly answers the query
- 0.7-0.9 = Highly relevant, contains useful information
- 0.4-0.6 = Somewhat relevant, tangentially related
- 0.1-0.3 = Slightly relevant, mostly unrelated
- 0.0 = Not relevant at all

Output format: One decimal number per line, in the same order as the documents.
Example output:
0.95
0.72
0.45
0.23

Do NOT include any explanation or text, only the numeric scores."""

    def _build_scoring_prompt(
        self,
        query: str,
        results: list[SearchResult],
    ) -> str:
        """Build prompt for batch relevance scoring.

        Truncates content for token efficiency while preserving enough
        context for accurate scoring.

        Args:
            query: Search query
            results: Candidates to score

        Returns:
            Formatted prompt string

        """
        max_content_length = 300  # Truncate to save tokens

        chunks_text = "\n\n".join(
            f"[Document {i + 1}]\n{result.content[:max_content_length]}{'...' if len(result.content) > max_content_length else ''}"
            for i, result in enumerate(results)
        )

        return f"""Query: {query}

Documents to score:

{chunks_text}

Rate the relevance of each document (0.0-1.0), one score per line:"""

    def _parse_scores(
        self,
        response: str,
        results: list[SearchResult],
    ) -> dict[str, float]:
        """Parse LLM response into score dictionary.

        Handles malformed responses gracefully by assigning default scores.

        Args:
            response: Raw LLM response text
            results: List of results being scored (for chunk_id mapping)

        Returns:
            Dict mapping chunk_id to parsed score (0.0-1.0)

        """
        scores: dict[str, float] = {}
        lines = response.strip().split("\n")

        for i, result in enumerate(results):
            try:
                if i < len(lines):
                    # Try to parse the score from the line
                    line = lines[i].strip()
                    # Handle potential formatting like "0.95" or "1. 0.95" or "[1] 0.95"
                    # Extract the last float-like number from the line
                    parts = line.replace("[", " ").replace("]", " ").split()
                    for part in reversed(parts):
                        try:
                            score = float(part)
                            score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
                            scores[result.chunk_id] = score
                            break
                        except ValueError:
                            continue
                    else:
                        # No valid float found
                        scores[result.chunk_id] = 0.5
                else:
                    scores[result.chunk_id] = 0.5  # Default on missing line
            except (ValueError, IndexError):
                scores[result.chunk_id] = 0.5  # Default on parse error

        return scores

    def _fallback_rank(
        self,
        results: list[SearchResult],
        final_count: int,
    ) -> list[SearchResult]:
        """Fallback ranking using base scores only.

        Used when re-ranking fails or times out. Provides graceful
        degradation to ensure users always receive results.

        Args:
            results: Original search results
            final_count: Number of results to return

        Returns:
            Results sorted by base score, truncated to final_count

        """
        # Sort by score descending, chunk_id as tiebreaker for determinism
        sorted_results = sorted(results, key=lambda r: (-r.score, r.chunk_id))
        return sorted_results[:final_count]
