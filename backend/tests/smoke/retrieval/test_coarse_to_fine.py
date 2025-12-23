"""Smoke tests for coarse-to-fine (hierarchical) retrieval.

Tests two-stage retrieval where:
1. Coarse stage: Find relevant sections (high-level)
2. Fine stage: Find specific paragraphs within those sections

This validates SkillForge's hierarchical chunking system where content
is stored at multiple granularity levels with parent-child relationships.

Run with: pytest tests/smoke/retrieval/test_coarse_to_fine.py -v
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

from app.schemas.search import SearchMode
from tests.smoke.retrieval.metrics import MetricsCalculator, aggregate_metrics

if TYPE_CHECKING:
    from app.shared.services.search.search_service import SearchService
    from tests.smoke.retrieval.fixtures.loader import Query

# TODO(#299): Skip in CI until queries.json is updated for real golden dataset
pytestmark = [
    pytest.mark.smoke,
    pytest.mark.retrieval,
    pytest.mark.coarse_to_fine,
    pytest.mark.skipif(
        os.getenv("CI") == "true",
        reason="Fixtures use synthetic test data; golden dataset now has real production data",
    ),
]


class TestCoarseStageRetrieval:
    """Test coarse (section-level) retrieval stage."""

    @pytest.mark.asyncio
    async def test_coarse_queries_find_section_chunks(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        coarse_to_fine_queries: list[Query],
        metrics_calculator: MetricsCalculator,
        get_thresholds,
    ):
        """Coarse queries should find section-level chunks.

        Tests that broad topic queries find the right coarse sections
        before drilling down to fine paragraphs.
        """
        # Filter to coarse-stage queries
        queries = [q for q in coarse_to_fine_queries if q.get("granularity") == "coarse"]

        if not queries:
            pytest.skip("No coarse-stage queries found")

        thresholds = get_thresholds("coarse_to_fine", "coarse")
        results: list[tuple[str, any, bool]] = []

        for query in queries:
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

            # Filter to only coarse sections in retrieved results
            coarse_retrieved = [
                sid
                for sid in retrieved_section_ids
                if not any(
                    chunk.metadata.get("section_id") == sid and chunk.granularity == "fine"
                    for chunk in seeded_chunks
                    if chunk.metadata
                )
            ]

            metrics = metrics_calculator.compute(
                retrieved_ids=coarse_retrieved,
                expected_ids=query["expected_chunks"],
                k=5,
            )

            passed = metrics.passes_thresholds(
                min_recall=thresholds.get("min_recall"),
                min_mrr=thresholds.get("min_mrr"),
            )

            results.append((query["id"], metrics, passed))

            if not passed:
                print(f"\n  FAIL: {query['id']}")
                print(f"    Query: {query['query'][:60]}...")
                print(f"    Expected (coarse): {query['expected_chunks']}")
                print(f"    Retrieved: {coarse_retrieved[:5]}")
                print(f"    {metrics.summary()}")

        aggregate = aggregate_metrics(results)
        print(f"\nCoarse stage: {aggregate.summary()}")

        # At least 60% of coarse queries should pass
        min_pass_rate = 0.60
        actual_pass_rate = (
            aggregate.passed_count / aggregate.query_count if aggregate.query_count else 0
        )

        assert actual_pass_rate >= min_pass_rate, (
            f"Coarse retrieval pass rate {actual_pass_rate:.1%} below threshold. "
            f"Failed: {aggregate.failed_queries}"
        )


class TestFineStageRetrieval:
    """Test fine (paragraph-level) retrieval stage."""

    @pytest.mark.asyncio
    async def test_fine_queries_find_paragraph_chunks(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        coarse_to_fine_queries: list[Query],
        metrics_calculator: MetricsCalculator,
        get_thresholds,
    ):
        """Fine queries should find specific paragraph-level chunks.

        Tests that specific questions find the right fine-grained paragraphs.
        """
        # Filter to fine-stage queries
        queries = [q for q in coarse_to_fine_queries if q.get("granularity") == "fine"]

        if not queries:
            pytest.skip("No fine-stage queries found")

        thresholds = get_thresholds("coarse_to_fine", "fine")
        results: list[tuple[str, any, bool]] = []

        for query in queries:
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

            passed = metrics.passes_thresholds(
                min_recall=thresholds.get("min_recall"),
                min_mrr=thresholds.get("min_mrr"),
            )

            results.append((query["id"], metrics, passed))

            if not passed:
                print(f"\n  FAIL: {query['id']}")
                print(f"    Query: {query['query'][:60]}...")
                print(f"    Expected (fine): {query['expected_chunks']}")
                print(f"    Retrieved: {retrieved_section_ids[:5]}")
                print(f"    {metrics.summary()}")

        aggregate = aggregate_metrics(results)
        print(f"\nFine stage: {aggregate.summary()}")

        # At least 50% of fine queries should pass (lower threshold for specificity)
        min_pass_rate = 0.50
        actual_pass_rate = (
            aggregate.passed_count / aggregate.query_count if aggregate.query_count else 0
        )

        assert actual_pass_rate >= min_pass_rate, (
            f"Fine retrieval pass rate {actual_pass_rate:.1%} below threshold. "
            f"Failed: {aggregate.failed_queries}"
        )


class TestHierarchicalNavigation:
    """Test hierarchical navigation from coarse to fine chunks."""

    @pytest.mark.asyncio
    async def test_fine_chunks_have_valid_parent_sections(
        self,
        seeded_chunks: list,
        fixture_loader,
    ):
        """Fine-grained chunks should have valid parent section references.

        Validates the hierarchical structure is correctly established.
        """
        fine_sections = fixture_loader.get_sections_by_granularity("fine")

        if not fine_sections:
            pytest.skip("No fine-grained sections in fixtures")

        for section in fine_sections:
            parent_id = section.get("parent_section")

            assert parent_id is not None, (
                f"Fine section '{section['id']}' missing parent_section reference"
            )

            # Verify parent exists in seeded chunks
            parent_found = any(
                chunk.metadata.get("section_id") == parent_id
                for chunk in seeded_chunks
                if chunk.metadata
            )

            assert parent_found, (
                f"Fine section '{section['id']}' references non-existent parent '{parent_id}'"
            )

    @pytest.mark.asyncio
    async def test_path_field_enables_hierarchy_traversal(
        self,
        seeded_chunks: list,
    ):
        """Chunk path field should enable coarse-to-fine navigation.

        The path field (JSONB array) stores [doc_id, section_id] for
        hierarchical traversal.
        """
        for chunk in seeded_chunks:
            path = chunk.path

            assert path is not None, f"Chunk {chunk.id} missing path field"
            assert len(path) >= 2, (
                f"Chunk {chunk.id} path should have at least [doc_id, section_id]"
            )
            assert isinstance(path, list), f"Chunk {chunk.id} path should be a list"

    @pytest.mark.asyncio
    async def test_two_stage_retrieval_flow(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        coarse_to_fine_queries: list[Query],
    ):
        """Test complete two-stage retrieval: coarse -> fine.

        Simulates the full coarse-to-fine retrieval pattern:
        1. Search for coarse sections matching the query
        2. Filter to find fine chunks under those sections
        """
        # Find a coarse query that has expected fine chunks
        coarse_queries = [
            q
            for q in coarse_to_fine_queries
            if q.get("granularity") == "coarse" and q.get("expected_fine_chunks")
        ]

        if not coarse_queries:
            pytest.skip("No coarse queries with expected_fine_chunks")

        query = coarse_queries[0]

        # Stage 1: Coarse retrieval
        coarse_results = await search_service.search(
            query=query["query"],
            mode=SearchMode.SEMANTIC,
            top_k=3,
        )

        assert len(coarse_results) > 0, "Coarse stage should return results"

        # Extract section IDs from search result metadata
        # The path is stored as [doc_id, section_id] in the database
        coarse_section_ids = {
            r.metadata.path[1] if r.metadata.path and len(r.metadata.path) > 1 else r.chunk_id
            for r in coarse_results
        }

        print(f"\nCoarse stage found sections: {coarse_section_ids}")

        # Stage 2: Find fine chunks under coarse sections (simulated)
        # In production, this would be a second query filtered by parent_section
        fine_chunks_under_coarse = [
            chunk
            for chunk in seeded_chunks
            if chunk.metadata
            and chunk.granularity == "fine"
            and chunk.metadata.get("section_id", "").rsplit("/", 1)[0] in coarse_section_ids
        ]

        # Verify we found expected fine chunks
        expected_fine = query.get("expected_fine_chunks", [])
        found_fine_ids = [chunk.metadata.get("section_id") for chunk in fine_chunks_under_coarse]

        print(f"Expected fine chunks: {expected_fine}")
        print(f"Found fine chunks: {found_fine_ids}")

        # At least one expected fine chunk should be found
        found_expected = any(fid in expected_fine for fid in found_fine_ids)

        assert found_expected or not expected_fine, (
            f"Two-stage retrieval did not find expected fine chunks. "
            f"Expected: {expected_fine}, Found: {found_fine_ids}"
        )


class TestGranularityFiltering:
    """Test filtering chunks by granularity level."""

    @pytest.mark.asyncio
    async def test_chunks_have_granularity_field(
        self,
        seeded_chunks: list,
    ):
        """All chunks should have a granularity field set."""
        for chunk in seeded_chunks:
            assert chunk.granularity in ("coarse", "fine"), (
                f"Chunk {chunk.id} has invalid granularity: {chunk.granularity}"
            )

    @pytest.mark.asyncio
    async def test_coarse_and_fine_chunks_present(
        self,
        seeded_chunks: list,
    ):
        """Test data should include both coarse and fine chunks."""
        granularities = {chunk.granularity for chunk in seeded_chunks}

        assert "coarse" in granularities, "No coarse chunks in test data"
        assert "fine" in granularities, "No fine chunks in test data"

        coarse_count = sum(1 for c in seeded_chunks if c.granularity == "coarse")
        fine_count = sum(1 for c in seeded_chunks if c.granularity == "fine")

        print(f"\nGranularity distribution: {coarse_count} coarse, {fine_count} fine")

        # Most chunks should be coarse (sections), with some fine (paragraphs)
        assert coarse_count > fine_count, "Expected more coarse sections than fine paragraphs"

    @pytest.mark.asyncio
    async def test_both_granularity_query_finds_hierarchy(
        self,
        search_service: SearchService,
        seeded_chunks: list,
        coarse_to_fine_queries: list[Query],
    ):
        """Queries marked 'both' should find both coarse and fine chunks."""
        both_queries = [q for q in coarse_to_fine_queries if q.get("granularity") == "both"]

        if not both_queries:
            pytest.skip("No 'both' granularity queries")

        for query in both_queries:
            results = await search_service.search(
                query=query["query"],
                mode=SearchMode.SEMANTIC,
                top_k=10,
            )

            # Extract section IDs from search result metadata
            # The path is stored as [doc_id, section_id] in the database
            retrieved_ids = [
                r.metadata.path[1] if r.metadata.path and len(r.metadata.path) > 1 else r.chunk_id
                for r in results
            ]

            # Check if results include expected chunks (can be mix of granularities)
            expected = set(query.get("expected_chunks", []))
            found = set(retrieved_ids) & expected

            assert len(found) > 0, (
                f"Query '{query['id']}' (both granularity) found none of "
                f"expected chunks: {expected}"
            )
