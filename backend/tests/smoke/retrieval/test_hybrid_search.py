"""Smoke tests for hybrid search (RRF fusion of semantic + keyword).

Tests hybrid search combining vector similarity and full-text search:
- Verifies RRF fusion produces better recall than individual modes
- Tests that both semantic and keyword matches contribute to results
- Validates score normalization and ordering

Run with: pytest tests/smoke/retrieval/test_hybrid_search.py -v
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

from app.schemas.search import SearchMode
from tests.smoke.retrieval.fixtures.loader import Query
from tests.smoke.retrieval.metrics import MetricsCalculator

if TYPE_CHECKING:
    from app.services.search.search_service import SearchService


# FIXME(#299): Skip in CI until queries.json is updated for real golden dataset
pytestmark = [
    pytest.mark.smoke,
    pytest.mark.retrieval,
    pytest.mark.hybrid,
    pytest.mark.skipif(
        os.getenv("CI") == "true",
        reason="Fixtures use synthetic test data; golden dataset now has real production data"
    ),
]


class TestHybridSearchPositive:
    """Test hybrid search finds relevant documents."""

    @pytest.mark.asyncio
    async def test_specific_queries_with_high_recall(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        hybrid_queries: list[Query],
        specific_queries: list[Query],
        metrics_calculator: MetricsCalculator,
        get_thresholds,
    ):
        """Specific queries should achieve higher recall with hybrid search.

        Hybrid mode combines semantic understanding with keyword matching,
        typically outperforming either mode alone.
        """
        # Filter to hybrid-specific queries
        queries = [q for q in specific_queries if "hybrid" in q["modes"]]

        if not queries:
            pytest.skip("No specific queries support hybrid mode")

        thresholds = get_thresholds("hybrid", "specific")
        results: list[tuple[str, any, bool]] = []

        for query in queries:
            search_results = await search_service.search(
                query=query["query"],
                mode=SearchMode.HYBRID,
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

            passed = metrics.passes_thresholds(
                min_recall=thresholds.get("min_recall"),
                min_mrr=thresholds.get("min_mrr"),
                min_ndcg=thresholds.get("min_ndcg"),
            )

            results.append((query["id"], metrics, passed))

            if not passed:
                print(f"\n  FAIL: {query['id']}")
                print(f"    Query: {query['query'][:60]}...")
                print(f"    {metrics.summary()}")

        aggregate = aggregate_metrics(results)
        print(f"\nHybrid specific queries: {aggregate.summary()}")

        # Hybrid should have high pass rate (85%)
        min_pass_rate = 0.85
        actual_pass_rate = aggregate.passed_count / aggregate.query_count

        assert actual_pass_rate >= min_pass_rate, (
            f"Hybrid search pass rate {actual_pass_rate:.1%} below threshold "
            f"{min_pass_rate:.1%}. Failed: {aggregate.failed_queries}"
        )

    @pytest.mark.asyncio
    async def test_broad_queries_find_diverse_results(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        fixture_loader,
        metrics_calculator: MetricsCalculator,
        get_thresholds,
    ):
        """Broad queries should find results from multiple document sources.

        Tests queries like "API security and authentication methods"
        which should find OAuth2, JWT, and GraphQL auth content.
        """
        broad_queries = fixture_loader.get_queries_by_category("broad")
        queries = [q for q in broad_queries if "hybrid" in q["modes"]]

        if not queries:
            pytest.skip("No broad queries support hybrid mode")

        thresholds = get_thresholds("hybrid", "broad")

        for query in queries:
            search_results = await search_service.search(
                query=query["query"],
                mode=SearchMode.HYBRID,
                top_k=10,
            )

            # Track unique source documents
            # The path is stored as [doc_id, section_id] in the database
            unique_docs = {
                r.metadata.path[0] if r.metadata.path and len(r.metadata.path) > 0 else "unknown"
                for r in search_results
            }

            # Broad queries should find results from multiple documents
            min_unique_docs = 2
            assert len(unique_docs) >= min_unique_docs, (
                f"Broad query '{query['id']}' only found {len(unique_docs)} "
                f"unique docs, expected at least {min_unique_docs}"
            )


class TestHybridVsSingleMode:
    """Compare hybrid search against individual modes."""

    @pytest.mark.asyncio
    async def test_hybrid_recall_at_least_as_good_as_semantic(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        hybrid_queries: list[Query],
        metrics_calculator: MetricsCalculator,
    ):
        """Hybrid search should have recall >= semantic search.

        RRF fusion should capture all semantic matches plus
        additional keyword matches.
        """
        # Test on queries that support both modes
        test_queries = [
            q for q in hybrid_queries if "semantic" in q["modes"] and "hybrid" in q["modes"]
        ][:5]  # Test first 5

        if not test_queries:
            pytest.skip("No queries support both semantic and hybrid modes")

        hybrid_better_count = 0
        equal_count = 0

        for query in test_queries:
            # Run both search modes
            semantic_results = await search_service.search(
                query=query["query"],
                mode=SearchMode.SEMANTIC,
                top_k=5,
            )
            hybrid_results = await search_service.search(
                query=query["query"],
                mode=SearchMode.HYBRID,
                top_k=5,
            )

            # Extract section IDs from search result metadata
            # The path is stored as [doc_id, section_id] in the database
            semantic_sections = [
                r.metadata.path[1] if r.metadata.path and len(r.metadata.path) > 1 else r.chunk_id
                for r in semantic_results
            ]
            hybrid_sections = [
                r.metadata.path[1] if r.metadata.path and len(r.metadata.path) > 1 else r.chunk_id
                for r in hybrid_results
            ]

            semantic_metrics = metrics_calculator.compute(
                retrieved_ids=semantic_sections,
                expected_ids=query["expected_chunks"],
            )
            hybrid_metrics = metrics_calculator.compute(
                retrieved_ids=hybrid_sections,
                expected_ids=query["expected_chunks"],
            )

            if hybrid_metrics.recall_at_k > semantic_metrics.recall_at_k:
                hybrid_better_count += 1
            elif hybrid_metrics.recall_at_k == semantic_metrics.recall_at_k:
                equal_count += 1

        # Hybrid should be at least as good in most cases
        assert hybrid_better_count + equal_count >= len(test_queries) * 0.8, (
            f"Hybrid only matched/exceeded semantic in "
            f"{hybrid_better_count + equal_count}/{len(test_queries)} queries"
        )

    @pytest.mark.asyncio
    async def test_hybrid_recall_at_least_as_good_as_keyword(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        hybrid_queries: list[Query],
        metrics_calculator: MetricsCalculator,
    ):
        """Hybrid search should have recall >= keyword search."""
        test_queries = [
            q for q in hybrid_queries if "keyword" in q["modes"] and "hybrid" in q["modes"]
        ][:5]

        if not test_queries:
            pytest.skip("No queries support both keyword and hybrid modes")

        hybrid_better_or_equal = 0

        for query in test_queries:
            keyword_results = await search_service.search(
                query=query["query"],
                mode=SearchMode.KEYWORD,
                top_k=5,
            )
            hybrid_results = await search_service.search(
                query=query["query"],
                mode=SearchMode.HYBRID,
                top_k=5,
            )

            # Extract section IDs from search result metadata
            # The path is stored as [doc_id, section_id] in the database
            keyword_sections = [
                r.metadata.path[1] if r.metadata.path and len(r.metadata.path) > 1 else r.chunk_id
                for r in keyword_results
            ]
            hybrid_sections = [
                r.metadata.path[1] if r.metadata.path and len(r.metadata.path) > 1 else r.chunk_id
                for r in hybrid_results
            ]

            keyword_metrics = metrics_calculator.compute(
                retrieved_ids=keyword_sections,
                expected_ids=query["expected_chunks"],
            )
            hybrid_metrics = metrics_calculator.compute(
                retrieved_ids=hybrid_sections,
                expected_ids=query["expected_chunks"],
            )

            if hybrid_metrics.recall_at_k >= keyword_metrics.recall_at_k:
                hybrid_better_or_equal += 1

        assert hybrid_better_or_equal >= len(test_queries) * 0.8, (
            f"Hybrid only matched/exceeded keyword in "
            f"{hybrid_better_or_equal}/{len(test_queries)} queries"
        )


class TestHybridSearchRRF:
    """Test RRF fusion behavior."""

    @pytest.mark.asyncio
    async def test_rrf_scores_are_normalized(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        hybrid_queries: list[Query],
    ):
        """RRF scores should be normalized to [0, 1] range."""
        query = hybrid_queries[0] if hybrid_queries else None
        if not query:
            pytest.skip("No hybrid queries available")

        results = await search_service.search(
            query=query["query"],
            mode=SearchMode.HYBRID,
            top_k=10,
        )

        for result in results:
            assert 0.0 <= result.score <= 1.0, f"RRF score {result.score} out of [0, 1] range"

    @pytest.mark.asyncio
    async def test_rrf_results_ordered_by_score(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        hybrid_queries: list[Query],
    ):
        """Hybrid results should be sorted by RRF score descending."""
        query = hybrid_queries[0] if hybrid_queries else None
        if not query:
            pytest.skip("No hybrid queries available")

        results = await search_service.search(
            query=query["query"],
            mode=SearchMode.HYBRID,
            top_k=10,
        )

        if len(results) > 1:
            scores = [r.score for r in results]
            assert scores == sorted(scores, reverse=True), (
                "Hybrid results not sorted by score descending"
            )

    @pytest.mark.asyncio
    async def test_hybrid_finds_semantic_only_matches(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        fixture_loader,
    ):
        """Hybrid should include results that only semantic would find.

        For queries with synonyms/paraphrases, hybrid should still
        find semantically similar content.
        """
        # Find a semantic-only query (synonym or paraphrase)
        all_queries = fixture_loader.load_queries()
        semantic_only = [
            q
            for q in all_queries
            if "semantic" in q["modes"] and "keyword" not in q["modes"] and "hybrid" in q["modes"]
        ]

        if not semantic_only:
            pytest.skip("No semantic-specific queries with hybrid support")

        for query in semantic_only[:2]:
            results = await search_service.search(
                query=query["query"],
                mode=SearchMode.HYBRID,
                top_k=5,
            )

            # Should still find results even without keyword matches
            assert len(results) > 0, (
                f"Hybrid search found no results for semantic query '{query['id']}'"
            )


class TestHybridSearchEdgeCases:
    """Test hybrid search edge cases."""

    @pytest.mark.asyncio
    async def test_handles_special_characters_in_query(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        edge_queries: list[Query],
    ):
        """Hybrid search should handle special characters gracefully.

        Tests queries like "OAuth2.0 JWT (tokens) & API-keys".
        """
        special_char_queries = [
            q for q in edge_queries if "hybrid" in q["modes"] and q["id"] == "q-edge-special"
        ]

        if not special_char_queries:
            pytest.skip("No special character edge queries for hybrid")

        for query in special_char_queries:
            # Should not raise exception
            results = await search_service.search(
                query=query["query"],
                mode=SearchMode.HYBRID,
                top_k=5,
            )

            # Should return results (not crash)
            assert isinstance(results, list), "Should return list of results"

            # Check if expected chunks are found
            # Extract section IDs from search result metadata
            # The path is stored as [doc_id, section_id] in the database
            retrieved_sections = [
                r.metadata.path[1] if r.metadata.path and len(r.metadata.path) > 1 else r.chunk_id
                for r in results
            ]

            # At least one expected chunk should be found
            found_any = any(section in query["expected_chunks"] for section in retrieved_sections)

            if query["expected_chunks"]:  # Only assert if we expect something
                assert found_any, (
                    f"Special char query didn't find expected results. "
                    f"Expected: {query['expected_chunks']}"
                )
