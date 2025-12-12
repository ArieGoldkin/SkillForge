"""Smoke tests for semantic search (vector similarity).

Tests semantic search functionality using predefined queries and expected results.
Validates that:
- Relevant documents are found with high similarity scores
- Irrelevant documents receive low scores (negative tests)
- Synonym and paraphrase queries work (semantic understanding)
- Metrics meet defined thresholds (Recall@5, MRR, NDCG)

Run with: pytest tests/smoke/retrieval/test_semantic_search.py -v
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.schemas.search import SearchMode
from tests.smoke.retrieval.metrics import MetricsCalculator, aggregate_metrics

if TYPE_CHECKING:
    from app.services.search.search_service import SearchService
    from tests.smoke.retrieval.fixtures.loader import Query

pytestmark = [
    pytest.mark.smoke,
    pytest.mark.retrieval,
    pytest.mark.semantic,
]


class TestSemanticSearchPositive:
    """Test semantic search finds relevant documents."""

    @pytest.mark.asyncio
    async def test_specific_queries_find_expected_chunks(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        semantic_queries: list[Query],
        specific_queries: list[Query],
        metrics_calculator: MetricsCalculator,
        get_thresholds,
    ):
        """Specific queries should find their expected chunks with high recall.

        Tests queries like "How to implement OAuth2 password flow in FastAPI?"
        which should match specific document sections.
        """
        # Filter to semantic-specific queries
        queries = [q for q in specific_queries if "semantic" in q["modes"]]

        if not queries:
            pytest.skip("No specific queries support semantic mode")

        thresholds = get_thresholds("semantic", "specific")
        results: list[tuple[str, any, bool]] = []

        for query in queries:
            # Execute semantic search
            search_results = await search_service.search(
                query=query["query"],
                mode=SearchMode.SEMANTIC,
                top_k=5,
            )

            # Extract section IDs from search result metadata
            # The path is stored as [doc_id, section_id] in the database
            retrieved_section_ids = [
                r.metadata.path[1] if r.metadata.path and len(r.metadata.path) > 1 else r.chunk_id
                for r in search_results
            ]

            # Compute metrics
            metrics = metrics_calculator.compute(
                retrieved_ids=retrieved_section_ids,
                expected_ids=query["expected_chunks"],
                k=5,
            )

            # Check if query passes thresholds
            passed = metrics.passes_thresholds(
                min_recall=thresholds.get("min_recall"),
                min_mrr=thresholds.get("min_mrr"),
                min_ndcg=thresholds.get("min_ndcg"),
            )

            results.append((query["id"], metrics, passed))

            # Log individual query results for debugging
            if not passed:
                print(f"\n  FAIL: {query['id']}")
                print(f"    Query: {query['query'][:60]}...")
                print(f"    Expected: {query['expected_chunks']}")
                print(f"    Retrieved: {retrieved_section_ids[:5]}")
                print(f"    {metrics.summary()}")

        # Aggregate results
        aggregate = aggregate_metrics(results)
        print(f"\n{aggregate.summary()}")

        # Assert overall pass rate meets threshold (80% of queries should pass)
        min_pass_rate = 0.80
        actual_pass_rate = aggregate.passed_count / aggregate.query_count

        assert actual_pass_rate >= min_pass_rate, (
            f"Semantic search pass rate {actual_pass_rate:.1%} below threshold "
            f"{min_pass_rate:.1%}. Failed queries: {aggregate.failed_queries}"
        )

    @pytest.mark.asyncio
    async def test_synonym_queries_find_relevant_content(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        semantic_queries: list[Query],
        metrics_calculator: MetricsCalculator,
        using_deterministic_embeddings: bool,
    ):
        """Synonym queries should match semantically similar content.

        Tests that "secure web API authentication mechanisms" finds
        OAuth2/JWT content even without exact keyword matches.

        Note: Skipped with deterministic embeddings since hash-based
        embeddings cannot capture semantic similarity between synonyms.
        """
        if using_deterministic_embeddings:
            pytest.skip(
                "Synonym tests require semantic embeddings - "
                "hash-based embeddings cannot understand synonyms"
            )

        # Find synonym test queries
        synonym_queries = [q for q in semantic_queries if q["id"].startswith("q-sem-synonym")]

        if not synonym_queries:
            pytest.skip("No synonym test queries found")

        for query in synonym_queries:
            search_results = await search_service.search(
                query=query["query"],
                mode=SearchMode.SEMANTIC,
                top_k=5,
            )

            # Extract section IDs from search result metadata
            # The path is stored as [doc_id, section_id] in the database
            retrieved_section_ids = [
                r.metadata.path[1] if r.metadata.path and len(r.metadata.path) > 1 else r.chunk_id
                for r in search_results
            ]

            metrics = metrics_calculator.compute(
                retrieved_ids=retrieved_section_ids,
                expected_ids=query["expected_chunks"],
                k=5,
            )

            # Synonym queries have lower threshold (0.6 min_score in fixture)
            min_recall = query.get("min_score", 0.6)

            assert metrics.recall_at_k >= min_recall, (
                f"Synonym query '{query['id']}' recall {metrics.recall_at_k:.2f} "
                f"below threshold {min_recall}. {metrics.summary()}"
            )

    @pytest.mark.asyncio
    async def test_paraphrase_queries_find_relevant_content(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        semantic_queries: list[Query],
        metrics_calculator: MetricsCalculator,
    ):
        """Paraphrase queries should match semantically equivalent content.

        Tests that "making database queries run faster" finds
        query optimization content.
        """
        paraphrase_queries = [q for q in semantic_queries if q["id"].startswith("q-sem-paraphrase")]

        if not paraphrase_queries:
            pytest.skip("No paraphrase test queries found")

        for query in paraphrase_queries:
            search_results = await search_service.search(
                query=query["query"],
                mode=SearchMode.SEMANTIC,
                top_k=5,
            )

            # Extract section IDs from search result metadata
            # The path is stored as [doc_id, section_id] in the database
            retrieved_section_ids = [
                r.metadata.path[1] if r.metadata.path and len(r.metadata.path) > 1 else r.chunk_id
                for r in search_results
            ]

            found_expected = any(
                section_id in query["expected_chunks"] for section_id in retrieved_section_ids
            )

            assert found_expected, (
                f"Paraphrase query '{query['id']}' did not find any expected chunks. "
                f"Expected: {query['expected_chunks']}, "
                f"Retrieved: {retrieved_section_ids[:5]}"
            )


class TestSemanticSearchNegative:
    """Test semantic search correctly rejects irrelevant queries."""

    @pytest.mark.asyncio
    async def test_unrelated_queries_have_low_scores(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        negative_queries: list[Query],
        get_thresholds,
    ):
        """Completely unrelated queries should return low similarity scores.

        Tests queries about quantum computing, Rust, etc. that should
        not match our Python/JS/SQL content.
        """
        # Filter to queries that support semantic mode
        queries = [q for q in negative_queries if "semantic" in q["modes"]]

        if not queries:
            pytest.skip("No negative queries support semantic mode")

        thresholds = get_thresholds("semantic", "negative")
        max_allowed_score = thresholds.get("max_score", 0.40)

        for query in queries:
            search_results = await search_service.search(
                query=query["query"],
                mode=SearchMode.SEMANTIC,
                top_k=5,
            )

            if search_results:
                # Check that top score is below threshold
                top_score = search_results[0].score

                assert top_score <= max_allowed_score, (
                    f"Negative query '{query['id']}' returned too-high score "
                    f"{top_score:.3f} (max allowed: {max_allowed_score}). "
                    f"Query: {query['query']}"
                )

    @pytest.mark.asyncio
    async def test_different_domain_queries_return_no_relevant_results(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        negative_queries: list[Query],
        metrics_calculator: MetricsCalculator,
    ):
        """Queries from completely different domains should have empty expected chunks."""
        queries = [q for q in negative_queries if "semantic" in q["modes"]]

        for query in queries:
            # These queries should have empty expected_chunks
            assert query["expected_chunks"] == [], (
                f"Negative query '{query['id']}' has expected_chunks - "
                "negative queries should expect no relevant results"
            )

            search_results = await search_service.search(
                query=query["query"],
                mode=SearchMode.SEMANTIC,
                top_k=5,
            )

            # If expected is empty and results have low scores, that's correct
            # We just verify the search doesn't crash and returns results
            # (even if irrelevant, semantic search returns k results)
            assert len(search_results) <= 5, "Should respect top_k limit"


class TestSemanticSearchBroad:
    """Test semantic search handles broad queries."""

    @pytest.mark.asyncio
    async def test_broad_queries_find_multiple_relevant_chunks(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        fixture_loader,
        metrics_calculator: MetricsCalculator,
        get_thresholds,
        using_deterministic_embeddings: bool,
    ):
        """Broad queries should find multiple relevant document sections.

        Tests queries like "API security and authentication methods"
        which should match OAuth2, JWT, and GraphQL auth sections.

        Note: Skipped with deterministic embeddings since broad semantic
        queries rely on understanding conceptual relationships across topics.
        """
        if using_deterministic_embeddings:
            pytest.skip(
                "Broad semantic queries require real embeddings - "
                "hash-based embeddings cannot understand conceptual relationships"
            )

        broad_queries = fixture_loader.get_queries_by_category("broad")
        queries = [q for q in broad_queries if "semantic" in q["modes"]]

        if not queries:
            pytest.skip("No broad queries support semantic mode")

        thresholds = get_thresholds("semantic", "broad")
        results = []

        for query in queries:
            search_results = await search_service.search(
                query=query["query"],
                mode=SearchMode.SEMANTIC,
                top_k=10,  # Larger k for broad queries
            )

            # Extract section IDs from search result metadata
            # The path is stored as [doc_id, section_id] in the database
            retrieved_section_ids = [
                r.metadata.path[1] if r.metadata.path and len(r.metadata.path) > 1 else r.chunk_id
                for r in search_results
            ]

            # Use k=10 for broad queries
            metrics = metrics_calculator.compute(
                retrieved_ids=retrieved_section_ids,
                expected_ids=query["expected_chunks"],
                k=10,
            )

            passed = metrics.passes_thresholds(
                min_recall=thresholds.get("min_recall"),
                min_mrr=thresholds.get("min_mrr"),
            )

            results.append((query["id"], metrics, passed))

        aggregate = aggregate_metrics(results)
        print(f"\nBroad queries: {aggregate.summary()}")

        # Broad queries have lower pass rate threshold (70%)
        min_pass_rate = 0.70
        actual_pass_rate = (
            aggregate.passed_count / aggregate.query_count if aggregate.query_count else 0
        )

        assert actual_pass_rate >= min_pass_rate, (
            f"Broad query pass rate {actual_pass_rate:.1%} below threshold. "
            f"Failed: {aggregate.failed_queries}"
        )


class TestSemanticSearchScoring:
    """Test semantic search score distribution and ordering."""

    @pytest.mark.asyncio
    async def test_results_ordered_by_score_descending(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        semantic_queries: list[Query],
    ):
        """Search results should be ordered by score (highest first)."""
        query = semantic_queries[0] if semantic_queries else None
        if not query:
            pytest.skip("No semantic queries available")

        results = await search_service.search(
            query=query["query"],
            mode=SearchMode.SEMANTIC,
            top_k=10,
        )

        if len(results) > 1:
            scores = [r.score for r in results]
            assert scores == sorted(scores, reverse=True), "Results not sorted by score descending"

    @pytest.mark.asyncio
    async def test_scores_in_valid_range(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        semantic_queries: list[Query],
    ):
        """All scores should be in [0.0, 1.0] range for semantic search."""
        for query in semantic_queries[:3]:  # Test first 3 queries
            results = await search_service.search(
                query=query["query"],
                mode=SearchMode.SEMANTIC,
                top_k=5,
            )

            for result in results:
                assert 0.0 <= result.score <= 1.0, (
                    f"Score {result.score} out of valid range [0, 1] for query '{query['id']}'"
                )
