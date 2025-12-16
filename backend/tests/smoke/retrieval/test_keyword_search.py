"""Smoke tests for keyword search (PostgreSQL tsvector full-text search).

Tests keyword search functionality:
- Exact term matching via tsvector
- Short queries (single terms)
- Special character handling
- Score normalization

Run with: pytest tests/smoke/retrieval/test_keyword_search.py -v
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
    pytest.mark.keyword,
    pytest.mark.skipif(
        os.getenv("CI") == "true",
        reason="Fixtures use synthetic test data; golden dataset now has real production data",
    ),
]


class TestKeywordSearchPositive:
    """Test keyword search finds relevant documents."""

    @pytest.mark.asyncio
    async def test_specific_queries_find_expected_chunks(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        keyword_queries: list[Query],
        specific_queries: list[Query],
        metrics_calculator: MetricsCalculator,
        get_thresholds,
    ):
        """Specific queries with exact terms should find expected chunks.

        Tests queries like "OAuth2 password flow" which contain
        exact keywords in the document content.
        """
        # Filter to keyword-specific queries
        queries = [q for q in specific_queries if "keyword" in q["modes"]]

        if not queries:
            pytest.skip("No specific queries support keyword mode")

        thresholds = get_thresholds("keyword", "specific")
        results: list[tuple[str, any, bool]] = []

        for query in queries:
            search_results = await search_service.search(
                query=query["query"],
                mode=SearchMode.KEYWORD,
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
                print(f"    Expected: {query['expected_chunks']}")
                print(f"    Retrieved: {retrieved_section_ids}")
                print(f"    Paths: {[r.metadata.path for r in search_results]}")
                print(f"    {metrics.summary()}")

        aggregate = aggregate_metrics(results)
        print(f"\nKeyword specific queries: {aggregate.summary()}")

        # Keyword search may have lower pass rate than semantic
        min_pass_rate = 0.70
        actual_pass_rate = aggregate.passed_count / aggregate.query_count

        assert actual_pass_rate >= min_pass_rate, (
            f"Keyword search pass rate {actual_pass_rate:.1%} below threshold "
            f"{min_pass_rate:.1%}. Failed: {aggregate.failed_queries}"
        )


class TestKeywordSearchEdgeCases:
    """Test keyword search edge cases."""

    @pytest.mark.asyncio
    async def test_short_query_single_term(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        edge_queries: list[Query],
        get_thresholds,
    ):
        """Single-term queries should still find relevant content.

        Tests query like "JWT" which should find JWT tokens section.
        """
        short_queries = [
            q for q in edge_queries if "keyword" in q["modes"] and q["id"] == "q-edge-short"
        ]

        if not short_queries:
            pytest.skip("No short query edge cases for keyword mode")

        for query in short_queries:
            results = await search_service.search(
                query=query["query"],
                mode=SearchMode.KEYWORD,
                top_k=5,
            )

            # Should find results for single term
            assert len(results) > 0, f"Short query '{query['query']}' found no results"

            # Extract section IDs from search result metadata
            # The path is stored as [doc_id, section_id] in the database
            retrieved_sections = [
                r.metadata.path[1] if r.metadata.path and len(r.metadata.path) > 1 else r.chunk_id
                for r in results
            ]

            found_expected = any(
                section in query["expected_chunks"] for section in retrieved_sections
            )

            min_score = query.get("min_score", 0.5)
            if query["expected_chunks"]:
                assert found_expected or results[0].score >= min_score, (
                    f"Short query didn't find expected chunks or high-scoring results. "
                    f"Expected: {query['expected_chunks']}, "
                    f"Retrieved: {retrieved_sections[:3]}"
                )

    @pytest.mark.asyncio
    async def test_special_characters_handled_gracefully(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        edge_queries: list[Query],
    ):
        """Queries with special characters should not crash.

        Tests query like "OAuth2.0 JWT (tokens) & API-keys".
        """
        special_queries = [
            q for q in edge_queries if "keyword" in q["modes"] and q["id"] == "q-edge-special"
        ]

        if not special_queries:
            pytest.skip("No special character edge queries for keyword mode")

        for query in special_queries:
            # Should not raise exception
            try:
                results = await search_service.search(
                    query=query["query"],
                    mode=SearchMode.KEYWORD,
                    top_k=5,
                )
                assert isinstance(results, list), "Should return list"
            except Exception as e:
                pytest.fail(f"Special character query raised exception: {e}")

    @pytest.mark.asyncio
    async def test_empty_results_for_nonexistent_terms(
        self,
        search_service: SearchService,
        seeded_chunks: list,
    ):
        """Queries with no matching terms should return empty or low scores.

        Tests that keyword search doesn't return false positives.
        """
        nonexistent_query = "xyzzynonexistent123foobar"

        results = await search_service.search(
            query=nonexistent_query,
            mode=SearchMode.KEYWORD,
            top_k=5,
        )

        # Should return empty or very low scoring results
        if results:
            # If results exist, they should have very low scores
            max_score = max(r.score for r in results)
            assert max_score < 0.3, f"Nonexistent term query returned high score: {max_score}"


class TestKeywordSearchNegative:
    """Test keyword search negative cases."""

    @pytest.mark.asyncio
    async def test_unrelated_domain_queries_have_low_scores(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        negative_queries: list[Query],
    ):
        """Queries from unrelated domains should have low keyword match scores.

        Tests queries about quantum computing, Rust, etc.
        """
        queries = [q for q in negative_queries if "keyword" in q["modes"]]

        if not queries:
            pytest.skip("No negative queries support keyword mode")

        for query in queries:
            results = await search_service.search(
                query=query["query"],
                mode=SearchMode.KEYWORD,
                top_k=5,
            )

            max_allowed = query.get("max_score", 0.4)

            if results:
                top_score = results[0].score
                assert top_score <= max_allowed, (
                    f"Negative query '{query['id']}' returned too-high score "
                    f"{top_score:.3f} (max: {max_allowed})"
                )


class TestKeywordSearchScoring:
    """Test keyword search scoring behavior."""

    @pytest.mark.asyncio
    async def test_results_ordered_by_relevance(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        keyword_queries: list[Query],
    ):
        """Keyword search results should be ordered by relevance score."""
        query = keyword_queries[0] if keyword_queries else None
        if not query:
            pytest.skip("No keyword queries available")

        results = await search_service.search(
            query=query["query"],
            mode=SearchMode.KEYWORD,
            top_k=10,
        )

        if len(results) > 1:
            scores = [r.score for r in results]
            assert scores == sorted(scores, reverse=True), (
                "Keyword results not sorted by score descending"
            )

    @pytest.mark.asyncio
    async def test_scores_normalized_to_valid_range(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        keyword_queries: list[Query],
    ):
        """Keyword scores should be normalized to [0, 1] range."""
        for query in keyword_queries[:3]:
            results = await search_service.search(
                query=query["query"],
                mode=SearchMode.KEYWORD,
                top_k=5,
            )

            for result in results:
                assert 0.0 <= result.score <= 1.0, (
                    f"Keyword score {result.score} out of [0, 1] range for query '{query['id']}'"
                )

    @pytest.mark.asyncio
    async def test_exact_matches_score_higher_than_partial(
        self,
        search_service: SearchService,
        seeded_chunks: list,
    ):
        """Documents with more query term matches should score higher.

        Query "OAuth2 JWT tokens" should score higher for docs
        containing all three terms vs. docs with only one.
        """
        # Use a multi-term query
        results = await search_service.search(
            query="OAuth2 JWT tokens authentication",
            mode=SearchMode.KEYWORD,
            top_k=10,
        )

        if len(results) < 2:
            pytest.skip("Need multiple results to compare scores")

        # Top result should have meaningfully higher score than bottom
        top_score = results[0].score
        bottom_score = results[-1].score

        # If we have diverse results, there should be score variance
        # (top should be notably better than bottom)
        if len(results) >= 5:
            assert top_score > bottom_score, (
                f"Expected score variance: top={top_score}, bottom={bottom_score}"
            )


class TestKeywordSearchSnippets:
    """Test keyword search snippet generation."""

    @pytest.mark.asyncio
    async def test_snippets_contain_query_terms(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        keyword_queries: list[Query],
    ):
        """Search result snippets should contain query terms (highlighted).

        Verifies that snippets are relevant to the query.
        """
        query = keyword_queries[0] if keyword_queries else None
        if not query:
            pytest.skip("No keyword queries available")

        results = await search_service.search(
            query=query["query"],
            mode=SearchMode.KEYWORD,
            top_k=5,
        )

        # At least some results should have snippets with query terms
        query_terms = query["query"].lower().split()

        snippets_with_terms = 0
        for result in results:
            snippet_lower = result.snippet.lower()
            if any(term in snippet_lower for term in query_terms):
                snippets_with_terms += 1

        # Most results should have relevant snippets
        if results:
            assert snippets_with_terms >= len(results) * 0.5, (
                f"Only {snippets_with_terms}/{len(results)} snippets contain query terms"
            )

    @pytest.mark.asyncio
    async def test_snippets_have_mark_tags_for_highlights(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        keyword_queries: list[Query],
    ):
        """Search snippets should use <mark> tags for highlighting.

        Verifies highlighting implementation.
        """
        query = keyword_queries[0] if keyword_queries else None
        if not query:
            pytest.skip("No keyword queries available")

        results = await search_service.search(
            query=query["query"],
            mode=SearchMode.KEYWORD,
            top_k=5,
        )

        # Check if any snippet has mark tags
        has_highlights = any("<mark>" in result.snippet for result in results)

        # At least one result should have highlighted terms
        if results:
            assert has_highlights, "No snippets contain <mark> highlighting tags"
