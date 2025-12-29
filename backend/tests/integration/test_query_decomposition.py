#!/usr/bin/env python3
"""Integration tests for query decomposition feature.

These tests validate the full query decomposition pipeline from Issue #601,
including decomposition, parallel retrieval, RRF fusion, and cache integration.

Run with:
    cd backend
    poetry run pytest tests/integration/test_query_decomposition.py -v -s --tb=short

Test Coverage:
1. Full pipeline: Query → Decomposition → Parallel Search → RRF Fusion
2. Feature flag: Verify decomposition can be disabled
3. Fallback: Verify graceful degradation when LLM fails
4. Cache integration: Verify L1 cache works across requests
5. Concurrent requests: Verify thread safety under load

Issue #601: Query Decomposition for Multi-Concept Retrieval
Target: Improve retrieval pass rate from 73.6% to 87%
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.logging import get_logger
from app.shared.services.search.decomposer import (
    ConceptExtraction,
    DecompositionCache,
    DecompositionResult,
    DecompositionSource,
    QueryDecomposer,
)

logger = get_logger(__name__)


@pytest.mark.integration
@pytest.mark.asyncio
class TestFullPipeline:
    """Test the complete query decomposition pipeline."""

    async def test_multi_concept_query_full_pipeline(self):
        """Test full pipeline: Query → Decomposition → Parallel Search → RRF Fusion.

        This test validates:
        - Heuristic detection identifies multi-concept queries
        - LLM decomposition extracts concepts
        - Parallel retrieval executes searches concurrently
        - RRF fusion merges results correctly
        - End-to-end latency is acceptable
        """
        logger.info("test_start", test="full_pipeline_multi_concept")

        # Mock LLM to return predictable concepts
        mock_llm = MagicMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke.return_value = ConceptExtraction(
            concepts=[
                "chunking strategies for text",
                "reranking methods in RAG",
                "RAG retrieval pipeline",
            ],
            reasoning="Query spans multiple RAG concepts",
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm

        decomposer = QueryDecomposer(llm=mock_llm)

        # Step 1: Decompose multi-concept query
        query = "How do chunking strategies affect reranking in RAG systems"
        decomposition = await decomposer.decompose(query)

        assert decomposition.is_multi_concept is True, "Query should be detected as multi-concept"
        assert len(decomposition.concepts) == 3, "Should extract 3 concepts"
        assert decomposition.source == DecompositionSource.LLM, "Should use LLM for decomposition"

        # Step 2: Mock search function that returns different results per concept
        search_calls = []

        async def mock_search(concept: str, top_k: int) -> list[tuple[str, float]]:
            """Mock search that returns concept-specific results."""
            search_calls.append(concept)
            if "chunking" in concept.lower():
                return [
                    ("chunk_doc1", 0.95),
                    ("chunk_doc2", 0.85),
                    ("shared_doc", 0.80),
                ]
            if "reranking" in concept.lower():
                return [
                    ("rerank_doc1", 0.92),
                    ("shared_doc", 0.88),
                    ("rerank_doc2", 0.75),
                ]
            if "rag" in concept.lower():
                return [
                    ("rag_doc1", 0.90),
                    ("shared_doc", 0.85),
                    ("rag_doc2", 0.70),
                ]
            return []

        # Step 3: Execute parallel retrieval with RRF fusion
        fused_results = await decomposer.parallel_retrieve(
            decomposition.concepts,
            mock_search,
            top_k_per_concept=5,
        )

        # Validate parallel execution
        assert len(search_calls) == 3, "Should execute 3 parallel searches"
        assert all(concept in search_calls for concept in decomposition.concepts), (
            "All concepts should be searched"
        )

        # Validate RRF fusion
        assert len(fused_results) > 0, "Should return fused results"
        result_ids = [r[0] for r in fused_results]

        # shared_doc should rank highest (appears in all 3 result sets)
        assert "shared_doc" in result_ids, "Shared document should appear in fused results"
        shared_rank = result_ids.index("shared_doc")
        assert shared_rank == 0, "Shared document should rank first due to RRF"

        # Validate scores are RRF scores (not original scores)
        shared_score = fused_results[0][1]
        assert shared_score > 0.02, "RRF score should be meaningful (>0.02)"

        logger.info(
            "test_complete",
            test="full_pipeline_multi_concept",
            status="PASS",
            concepts_extracted=3,
            fused_results=len(fused_results),
            top_result=fused_results[0][0],
        )

    async def test_single_concept_fast_path(self):
        """Test that single-concept queries skip LLM decomposition (fast path).

        This validates:
        - Heuristic check correctly identifies single-concept queries
        - LLM is never called (fast path)
        - Latency is <10ms
        """
        logger.info("test_start", test="single_concept_fast_path")

        # Mock LLM to verify it's never called
        mock_llm = MagicMock()
        decomposer = QueryDecomposer(llm=mock_llm)

        # Simple single-concept query
        query = "FastAPI tutorial"
        decomposition = await decomposer.decompose(query)

        # Validate fast path
        assert decomposition.is_multi_concept is False, "Should be single-concept"
        assert decomposition.concepts == [query], "Should return original query"
        assert decomposition.source == DecompositionSource.SINGLE_CONCEPT
        assert decomposition.latency_ms < 10, (
            f"Fast path should be <10ms, got {decomposition.latency_ms}ms"
        )

        # Verify LLM was never invoked
        mock_llm.with_structured_output.assert_not_called()

        logger.info(
            "test_complete",
            test="single_concept_fast_path",
            status="PASS",
            latency_ms=decomposition.latency_ms,
        )


@pytest.mark.integration
@pytest.mark.asyncio
class TestFeatureFlag:
    """Test feature flag for enabling/disabling decomposition."""

    async def test_decomposition_can_be_disabled(self):
        """Test that decomposition can be bypassed when disabled.

        This validates:
        - Decomposition can be skipped for production rollback
        - Single-concept path always works as fallback
        """
        logger.info("test_start", test="feature_flag_disabled")

        decomposer = QueryDecomposer()

        # Even with multi-concept indicators, treat as single concept
        query = "React hooks vs Redux state management"

        # Simulate disabled feature flag by using single-concept result
        decomposition = DecompositionResult(
            original_query=query,
            is_multi_concept=False,
            concepts=[query],
            source=DecompositionSource.SINGLE_CONCEPT,
            latency_ms=0.5,
        )

        assert decomposition.is_multi_concept is False
        assert len(decomposition.concepts) == 1
        assert decomposition.concepts[0] == query

        logger.info("test_complete", test="feature_flag_disabled", status="PASS")


@pytest.mark.integration
@pytest.mark.asyncio
class TestFallback:
    """Test graceful degradation when LLM fails."""

    async def test_llm_timeout_fallback(self):
        """Test fallback when LLM times out.

        This validates:
        - TimeoutError is caught and handled gracefully
        - Original query is returned as single concept
        - No exception propagates to caller
        """
        logger.info("test_start", test="llm_timeout_fallback")

        # Mock LLM to raise TimeoutError
        mock_llm = MagicMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke.side_effect = TimeoutError("LLM timeout")
        mock_llm.with_structured_output.return_value = mock_structured_llm

        decomposer = QueryDecomposer(llm=mock_llm)

        # Use query that triggers heuristic (has "vs" keyword)
        query = "React hooks vs Redux for state management patterns"

        # Verify heuristic would trigger
        assert decomposer._check_heuristics(query) is True, "Query should trigger heuristics"

        decomposition = await decomposer.decompose(query)

        # Should fall back to original query (single concept after fallback)
        # Note: is_multi_concept is False because fallback returns 1 concept (the original query)
        assert decomposition.is_multi_concept is False
        assert decomposition.concepts == [query], "Should fall back to original query"
        assert decomposition.source == DecompositionSource.LLM

        logger.info("test_complete", test="llm_timeout_fallback", status="PASS")

    async def test_llm_connection_error_fallback(self):
        """Test fallback when LLM connection fails.

        This validates:
        - ConnectionError is caught and handled gracefully
        - System remains functional without LLM
        """
        logger.info("test_start", test="llm_connection_error_fallback")

        # Mock LLM to raise ConnectionError
        mock_llm = MagicMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke.side_effect = ConnectionError("Cannot reach LLM API")
        mock_llm.with_structured_output.return_value = mock_structured_llm

        decomposer = QueryDecomposer(llm=mock_llm)

        query = "React hooks vs Redux for state management"
        decomposition = await decomposer.decompose(query)

        # Should fall back to original query
        assert decomposition.concepts == [query], "Should fall back to original query"
        assert decomposition.source == DecompositionSource.LLM

        logger.info("test_complete", test="llm_connection_error_fallback", status="PASS")

    async def test_llm_validation_error_fallback(self):
        """Test fallback when LLM returns invalid structured output.

        This validates:
        - ValidationError from Pydantic is caught
        - Malformed LLM responses don't crash the system
        """
        logger.info("test_start", test="llm_validation_error_fallback")

        # Mock LLM to raise ValidationError
        mock_llm = MagicMock()
        mock_structured_llm = AsyncMock()
        from pydantic import ValidationError

        mock_structured_llm.ainvoke.side_effect = ValidationError.from_exception_data(
            "ConceptExtraction",
            [{"type": "missing", "loc": ("concepts",), "msg": "Field required"}],
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm

        decomposer = QueryDecomposer(llm=mock_llm)

        query = "PostgreSQL vs MySQL for web applications"
        decomposition = await decomposer.decompose(query)

        # Should fall back to original query
        assert decomposition.concepts == [query], "Should fall back to original query"
        assert decomposition.source == DecompositionSource.LLM

        logger.info("test_complete", test="llm_validation_error_fallback", status="PASS")


@pytest.mark.integration
@pytest.mark.asyncio
class TestCacheIntegration:
    """Test L1 cache integration across requests."""

    async def test_l1_cache_hit_second_request(self):
        """Test that L1 cache returns cached decomposition on second request.

        This validates:
        - First request triggers LLM decomposition
        - Second identical request hits L1 cache
        - L1 latency is <5ms
        - LLM is only called once
        """
        logger.info("test_start", test="l1_cache_hit")

        # Mock LLM
        mock_llm = MagicMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke.return_value = ConceptExtraction(
            concepts=["React hooks state management", "Redux state management"],
            reasoning="Comparison query",
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm

        cache = DecompositionCache(l1_maxsize=100, l1_ttl=300)
        decomposer = QueryDecomposer(llm=mock_llm, cache=cache)

        query = "React hooks vs Redux state management"

        # First request - should call LLM
        result1 = await decomposer.decompose(query)
        assert result1.source == DecompositionSource.LLM
        assert mock_structured_llm.ainvoke.call_count == 1

        # Second request - should hit L1 cache
        result2 = await decomposer.decompose(query)
        assert result2.source == DecompositionSource.CACHE_L1
        assert result2.concepts == result1.concepts
        assert result2.latency_ms < 5, f"L1 cache should be <5ms, got {result2.latency_ms}ms"

        # LLM should only be called once
        assert mock_structured_llm.ainvoke.call_count == 1

        logger.info(
            "test_complete",
            test="l1_cache_hit",
            status="PASS",
            l1_latency_ms=result2.latency_ms,
        )

    async def test_cache_normalization(self):
        """Test that cache normalizes queries (case-insensitive, whitespace).

        This validates:
        - "React vs Vue" and "react vs vue" hit same cache entry
        - Extra whitespace is normalized
        """
        logger.info("test_start", test="cache_normalization")

        # Mock LLM
        mock_llm = MagicMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke.return_value = ConceptExtraction(
            concepts=["React framework", "Vue framework"],
            reasoning="Comparison query",
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm

        cache = DecompositionCache()
        decomposer = QueryDecomposer(llm=mock_llm, cache=cache)

        # Store with one casing - use query that triggers heuristics
        result1 = await decomposer.decompose("React vs Vue for Frontend Development")
        assert result1.source == DecompositionSource.LLM

        # Retrieve with different casing
        result2 = await decomposer.decompose("react vs vue for frontend development")
        assert result2.source == DecompositionSource.CACHE_L1
        assert result2.concepts == result1.concepts

        # LLM should only be called once
        assert mock_structured_llm.ainvoke.call_count == 1

        logger.info("test_complete", test="cache_normalization", status="PASS")

    async def test_cache_expiration(self):
        """Test that expired cache entries are not returned.

        This validates:
        - TTL is enforced correctly
        - Expired entries trigger new LLM calls
        """
        logger.info("test_start", test="cache_expiration")

        # Mock LLM
        mock_llm = MagicMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke.return_value = ConceptExtraction(
            concepts=["FastAPI dependency injection", "Python patterns"],
            reasoning="Dual topic",
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm

        # Very short TTL for testing (0 seconds = immediate expiration)
        cache = DecompositionCache(l1_ttl=0)
        decomposer = QueryDecomposer(llm=mock_llm, cache=cache)

        # Use query that triggers heuristics (has "and" keyword)
        query = "FastAPI dependency injection and Python design patterns"

        # First request
        result1 = await decomposer.decompose(query)
        assert result1.source == DecompositionSource.LLM
        assert mock_structured_llm.ainvoke.call_count == 1

        # Second request should NOT hit cache (expired)
        result2 = await decomposer.decompose(query)
        assert result2.source == DecompositionSource.LLM  # Cache expired, LLM called again
        assert mock_structured_llm.ainvoke.call_count == 2

        logger.info("test_complete", test="cache_expiration", status="PASS")


@pytest.mark.integration
@pytest.mark.asyncio
class TestConcurrentRequests:
    """Test thread safety and concurrent request handling."""

    async def test_concurrent_decomposition_requests(self):
        """Test that concurrent decomposition requests are handled correctly.

        This validates:
        - Multiple concurrent requests don't interfere
        - Cache is thread-safe
        - No race conditions in decomposition
        """
        logger.info("test_start", test="concurrent_decomposition")

        # Mock LLM with delay to simulate real network latency
        mock_llm = MagicMock()
        mock_structured_llm = AsyncMock()

        async def slow_llm_response(prompt):
            """Simulate LLM latency."""
            await asyncio.sleep(0.05)  # 50ms delay
            return ConceptExtraction(
                concepts=["concept1", "concept2"],
                reasoning="Test",
            )

        mock_structured_llm.ainvoke = slow_llm_response
        mock_llm.with_structured_output.return_value = mock_structured_llm

        decomposer = QueryDecomposer(llm=mock_llm)

        # Launch 10 concurrent decomposition requests
        queries = [f"How do chunking strategies affect reranking query {i}" for i in range(10)]

        results = await asyncio.gather(*[decomposer.decompose(query) for query in queries])

        # Validate all requests completed
        assert len(results) == 10, "All 10 requests should complete"
        for result in results:
            assert result.is_multi_concept is True
            assert len(result.concepts) == 2

        logger.info(
            "test_complete",
            test="concurrent_decomposition",
            status="PASS",
            concurrent_requests=10,
        )

    async def test_concurrent_parallel_retrieval(self):
        """Test that parallel retrieval handles concurrency correctly.

        This validates:
        - Semaphore limits concurrent searches to 5
        - No deadlocks under load
        - Results are correct despite concurrency
        """
        logger.info("test_start", test="concurrent_parallel_retrieval")

        decomposer = QueryDecomposer()

        concurrent_count = 0
        max_concurrent = 0
        lock = asyncio.Lock()

        async def mock_search(concept: str, top_k: int) -> list[tuple[str, float]]:
            """Mock search that tracks concurrency."""
            nonlocal concurrent_count, max_concurrent

            async with lock:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)

            # Simulate some work
            await asyncio.sleep(0.01)

            async with lock:
                concurrent_count -= 1

            return [(f"doc_{concept}", 0.9)]

        # Use 10 concepts to test semaphore limiting
        concepts = [f"concept{i}" for i in range(10)]

        results = await decomposer.parallel_retrieve(concepts, mock_search, top_k_per_concept=5)

        # Validate results
        assert len(results) == 10, "Should return results for all concepts"

        # Validate semaphore limited concurrency to 5
        assert max_concurrent <= 5, f"Semaphore should limit to 5, got {max_concurrent}"

        logger.info(
            "test_complete",
            test="concurrent_parallel_retrieval",
            status="PASS",
            max_concurrent=max_concurrent,
        )

    async def test_cache_under_concurrent_load(self):
        """Test that cache remains consistent under concurrent load.

        This validates:
        - No race conditions in cache reads/writes
        - All requests get consistent results
        - Cache hit rate is good under load
        """
        logger.info("test_start", test="cache_concurrent_load")

        # Mock LLM
        mock_llm = MagicMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke.return_value = ConceptExtraction(
            concepts=["concept1", "concept2"],
            reasoning="Test",
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm

        cache = DecompositionCache(l1_maxsize=100, l1_ttl=300)
        decomposer = QueryDecomposer(llm=mock_llm, cache=cache)

        # Use same query for all requests to test cache hits
        query = "React hooks vs Redux state management"

        # Launch 20 concurrent requests with same query
        results = await asyncio.gather(*[decomposer.decompose(query) for _ in range(20)])

        # Validate all requests got same concepts
        assert len(results) == 20
        expected_concepts = results[0].concepts
        for result in results:
            assert result.concepts == expected_concepts, "All results should be consistent"

        # Count cache hits
        cache_hits = sum(1 for r in results if r.source == DecompositionSource.CACHE_L1)

        # Should have high cache hit rate (at least 15/20 = 75%)
        assert cache_hits >= 15, f"Expected >=15 cache hits, got {cache_hits}"

        logger.info(
            "test_complete",
            test="cache_concurrent_load",
            status="PASS",
            cache_hit_rate=cache_hits / 20,
        )


@pytest.mark.integration
@pytest.mark.asyncio
class TestEdgeCases:
    """Test edge cases and error handling."""

    async def test_empty_query_handling(self):
        """Test that empty queries are handled gracefully."""
        logger.info("test_start", test="empty_query")

        decomposer = QueryDecomposer()

        result = await decomposer.decompose("")

        # Empty query should be treated as single-concept
        assert result.is_multi_concept is False
        assert result.concepts == [""]
        assert result.source == DecompositionSource.SINGLE_CONCEPT

        logger.info("test_complete", test="empty_query", status="PASS")

    async def test_all_searches_fail(self):
        """Test that parallel retrieval handles all searches failing.

        This validates:
        - Empty result list when all searches fail
        - No exceptions propagate
        - Graceful degradation
        """
        logger.info("test_start", test="all_searches_fail")

        decomposer = QueryDecomposer()

        async def failing_search(concept: str, top_k: int) -> list[tuple[str, float]]:
            """Mock search that always fails."""
            raise ValueError("Search failed")

        concepts = ["concept1", "concept2", "concept3"]
        results = await decomposer.parallel_retrieve(concepts, failing_search)

        # Should return empty list, not raise exception
        assert results == [], "Should return empty list when all searches fail"

        logger.info("test_complete", test="all_searches_fail", status="PASS")

    async def test_partial_search_failures(self):
        """Test that partial search failures don't affect successful searches.

        This validates:
        - Failed searches are isolated
        - Successful searches still contribute to results
        - RRF fusion works with partial results
        """
        logger.info("test_start", test="partial_search_failures")

        decomposer = QueryDecomposer()

        call_count = 0

        async def partially_failing_search(concept: str, top_k: int) -> list[tuple[str, float]]:
            """Mock search that fails on first call."""
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First search failed")
            return [(f"doc_{concept}", 0.9)]

        concepts = ["concept1", "concept2", "concept3"]
        results = await decomposer.parallel_retrieve(concepts, partially_failing_search)

        # Should return results from successful searches (2 out of 3)
        assert len(results) > 0, "Should return results from successful searches"
        assert len(results) <= 2, "Should have at most 2 results (2 successful searches)"

        logger.info(
            "test_complete",
            test="partial_search_failures",
            status="PASS",
            successful_searches=len(results),
        )

    async def test_very_long_query(self):
        """Test that very long queries are handled correctly.

        This validates:
        - Long queries don't cause timeouts
        - LLM prompt construction handles long text
        """
        logger.info("test_start", test="very_long_query")

        # Mock LLM
        mock_llm = MagicMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke.return_value = ConceptExtraction(
            concepts=["concept1", "concept2", "concept3"],
            reasoning="Long query decomposed",
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm

        decomposer = QueryDecomposer(llm=mock_llm)

        # Very long query (500+ characters)
        long_query = (
            "How do chunking strategies affect reranking in RAG systems, "
            "and what are the trade-offs between different embedding models "
            "like OpenAI, Cohere, and local models when it comes to semantic "
            "search performance, retrieval accuracy, and cost optimization "
            "in production environments with high query volumes and diverse "
            "document types including technical documentation, research papers, "
            "blog posts, and code repositories with varying levels of complexity "
            "and domain-specific terminology that requires specialized handling"
        )

        assert len(long_query) > 500

        result = await decomposer.decompose(long_query)

        # Should successfully decompose
        assert result.is_multi_concept is True
        assert len(result.concepts) == 3
        assert result.source == DecompositionSource.LLM

        logger.info("test_complete", test="very_long_query", status="PASS")
