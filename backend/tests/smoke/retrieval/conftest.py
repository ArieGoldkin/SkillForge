"""Pytest configuration for retrieval smoke tests.

Provides fixtures for:
- Database session with test data
- Search service initialization
- Test documents and chunks
- Fixture data loading

CI: GitHub Actions workflow runs on every PR to dev/main.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.shared.services.embeddings.cached import CachedEmbeddingService
from app.shared.services.embeddings.deterministic import DeterministicEmbeddingService
from tests.smoke.retrieval.fixtures import FixtureLoader
from tests.smoke.retrieval.metrics import MetricsCalculator

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.models.analysis import Analysis
    from app.db.models.analysis_chunk import AnalysisChunk
    from app.shared.services.embeddings.deterministic import (
        DeterministicEmbeddingService as EmbeddingService,
    )
    from app.shared.services.search.search_service import SearchService


# Mark all tests in this module as smoke tests
pytestmark = [
    pytest.mark.smoke,
    pytest.mark.retrieval,
    # TODO(#299): Skip retrieval smoke tests in CI until:
    # 1. embeddings_cache.json is generated for golden dataset
    # 2. queries.json is updated to match real golden dataset content
    # Once cache exists, CachedEmbeddingService will provide real OpenAI embeddings
    pytest.mark.skipif(
        os.getenv("CI") == "true"
        and not Path(__file__).parent.joinpath("fixtures/embeddings_cache.json").exists(),
        reason="Smoke tests require embeddings_cache.json with real OpenAI embeddings (issue #299)",
    ),
]


@pytest.fixture(scope="module")
def fixture_loader() -> FixtureLoader:
    """Provide fixture loader for test data.

    Uses expanded fixtures (documents_expanded.json, queries_expanded.json) which contain:
    - 100 documents with proper bucket values (short/long)
    - 208 queries with validated section references
    - Real content including Manus context engineering article

    The expanded fixtures were validated with 0 missing section references.
    """
    loader = FixtureLoader(use_expanded=True)

    # Skip validation in CI (temporary workaround for issue #299)
    if os.getenv("CI") != "true":
        errors = loader.validate()
        if errors:
            pytest.fail(f"Fixture validation failed: {errors}")

    return loader


@pytest.fixture(scope="module")
def metrics_calculator() -> MetricsCalculator:
    """Provide metrics calculator with default k=5."""
    return MetricsCalculator(k=5)


@pytest.fixture(scope="module")
def test_documents(fixture_loader: FixtureLoader):
    """Load test documents from fixtures."""
    return fixture_loader.load_documents()


@pytest.fixture(scope="module")
def test_queries(fixture_loader: FixtureLoader):
    """Load test queries from fixtures."""
    return fixture_loader.load_queries()


@pytest.fixture
def semantic_queries(fixture_loader: FixtureLoader):
    """Get queries that support semantic search mode."""
    return fixture_loader.get_queries_for_mode("semantic")


@pytest.fixture
def keyword_queries(fixture_loader: FixtureLoader):
    """Get queries that support keyword search mode."""
    return fixture_loader.get_queries_for_mode("keyword")


@pytest.fixture
def hybrid_queries(fixture_loader: FixtureLoader):
    """Get queries that support hybrid search mode."""
    return fixture_loader.get_queries_for_mode("hybrid")


@pytest.fixture
def specific_queries(fixture_loader: FixtureLoader):
    """Get specific (positive) test queries."""
    return fixture_loader.get_queries_by_category("specific")


@pytest.fixture
def negative_queries(fixture_loader: FixtureLoader):
    """Get negative test queries (should not match)."""
    return fixture_loader.get_queries_by_category("negative")


@pytest.fixture
def edge_queries(fixture_loader: FixtureLoader):
    """Get edge case test queries."""
    return fixture_loader.get_queries_by_category("edge")


@pytest.fixture
def coarse_to_fine_queries(fixture_loader: FixtureLoader):
    """Get coarse-to-fine hierarchical test queries."""
    return fixture_loader.get_coarse_to_fine_queries()


@pytest_asyncio.fixture
async def embedding_service():
    """Create embedding service for smoke tests with hybrid fallback strategy.

    Priority (in order):
    1. CachedEmbeddingService if embeddings_cache.json exists (real OpenAI embeddings)
    2. EmbeddingService if USE_REAL_EMBEDDINGS=true (live OpenAI API calls)
    3. DeterministicEmbeddingService (hash-based, offline-compatible)

    The cache provides real embeddings without API costs, ideal for CI/CD.
    """
    # Check for embeddings cache file first
    cache_path = Path(__file__).parent / "fixtures" / "embeddings_cache.json"

    if cache_path.exists():
        logger.info(
            "Using CachedEmbeddingService with real OpenAI embeddings from %s",
            cache_path,
        )
        return CachedEmbeddingService(cache_path=cache_path, expected_dimensions=1536)

    # Fall back to live OpenAI API if explicitly requested
    use_real = os.environ.get("USE_REAL_EMBEDDINGS", "").lower() == "true"
    if use_real:
        try:
            from app.shared.services.embeddings import EmbeddingService

            logger.info("Using live EmbeddingService (OpenAI API) - USE_REAL_EMBEDDINGS=true")
            return EmbeddingService()
        except ValueError as e:
            pytest.skip(f"Real embeddings requested but not available: {e}")

    # Default: deterministic embeddings for offline testing
    logger.info("Using DeterministicEmbeddingService (hash-based, offline)")
    return DeterministicEmbeddingService()


@pytest.fixture
def using_deterministic_embeddings(embedding_service) -> bool:
    """Detect if we're using deterministic (hash-based) embeddings.

    This is used to skip tests that require true semantic understanding
    (synonyms, paraphrases) which hash-based embeddings cannot provide.

    Returns False for:
    - CachedEmbeddingService (uses real OpenAI embeddings from cache)
    - EmbeddingService (live OpenAI API)

    Returns True only for DeterministicEmbeddingService.
    """
    return isinstance(embedding_service, DeterministicEmbeddingService)


@pytest_asyncio.fixture
async def smoke_db_session(
    check_database_available,
    reset_engine_connections,
) -> AsyncGenerator[AsyncSession]:
    """Create database session for smoke tests.

    Uses same setup as main test suite but scoped for smoke tests.
    Does NOT rollback - smoke tests may need persistent data.
    """
    from app.db.session import AsyncSessionLocal

    session = AsyncSessionLocal()
    try:
        await session.begin()
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@pytest_asyncio.fixture
async def smoke_test_analysis(
    smoke_db_session: AsyncSession,
) -> AsyncGenerator[Analysis]:
    """Create a test Analysis record for smoke tests.

    Creates a dedicated analysis record that will hold test chunks.
    Cleans up after tests complete.
    """
    from app.db.models.analysis import Analysis

    analysis_id = uuid4()
    analysis = Analysis(
        id=analysis_id,
        url="https://smoke-test.skillforge.local/retrieval",
        content_type="smoke_test",
        status="completed",
    )

    smoke_db_session.add(analysis)
    await smoke_db_session.flush()

    yield analysis

    # Cleanup: delete analysis and related chunks
    await smoke_db_session.execute(
        text("DELETE FROM analysis_chunks WHERE analysis_id = :id"),
        {"id": str(analysis_id)},
    )
    await smoke_db_session.execute(
        text("DELETE FROM analyses WHERE id = :id"),
        {"id": str(analysis_id)},
    )
    await smoke_db_session.commit()


@pytest_asyncio.fixture
async def seeded_chunks(
    smoke_db_session: AsyncSession,
    smoke_test_analysis: Analysis,
    embedding_service: EmbeddingService,
    test_documents: list,
) -> AsyncGenerator[list[AnalysisChunk]]:
    """Seed database with test document chunks.

    Creates AnalysisChunk records from fixture documents with:
    - Embedded vectors via embedding service
    - tsvector for keyword search
    - Proper metadata for filtering

    Returns list of created chunks for verification.
    """
    from app.db.models.analysis_chunk import AnalysisChunk

    chunks: list[AnalysisChunk] = []
    analysis_id = smoke_test_analysis.id

    import hashlib

    for doc in test_documents:
        for idx, section in enumerate(doc.get("sections", [])):
            content = section["content"]

            # Generate embedding for chunk
            embedding = await embedding_service.generate_embedding(
                text=content,
                normalize=True,
            )

            # Create content hash for deduplication
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            # Create chunk with actual column names (not property aliases)
            # Properties: content→snippet, embedding→vector, chunk_type→granularity
            chunk = AnalysisChunk(
                id=uuid4(),
                analysis_id=analysis_id,
                snippet=content,  # 'content' is read-only property alias
                vector=embedding,  # 'embedding' is read-only property alias
                granularity=section.get("granularity", "coarse"),  # 'chunk_type' is alias
                section_title=section["title"],
                chunk_idx=idx,
                chunk_total=len(doc["sections"]),
                path=[doc["id"], section["id"]],  # JSONB path for navigation
                hash=content_hash,  # Required for deduplication
                content_type=doc["content_type"],
                language=doc["language"],
                model="text-embedding-3-small",
                model_version="v1",
            )

            # Store metadata for test verification
            # We use a dynamic attribute that tests can access
            # path[0] = doc_id, path[1] = section_id
            chunk.metadata = {
                "section_id": section["id"],
                "doc_id": doc["id"],
                "bucket": doc["bucket"],
                "tags": doc.get("tags", []),
            }

            smoke_db_session.add(chunk)
            chunks.append(chunk)

    await smoke_db_session.flush()

    # Refresh chunks to get database-generated fields
    for chunk in chunks:
        await smoke_db_session.refresh(chunk)

    yield chunks

    # Cleanup handled by smoke_test_analysis fixture


@pytest_asyncio.fixture
async def search_service(
    smoke_db_session: AsyncSession,
    embedding_service: EmbeddingService,
) -> SearchService:
    """Create SearchService for smoke tests."""
    from app.shared.services.search.search_service import SearchService

    return SearchService(
        session=smoke_db_session,
        embedding_service=embedding_service,
    )


# Threshold configurations for different test categories
THRESHOLDS = {
    "semantic": {
        "specific": {"min_recall": 0.70, "min_mrr": 0.60, "min_ndcg": 0.65},
        "broad": {"min_recall": 0.50, "min_mrr": 0.40, "min_ndcg": 0.45},
        "negative": {"max_score": 0.40},
        "coarse-to-fine": {"min_recall": 0.50, "min_mrr": 0.40, "min_ndcg": 0.45},
    },
    "keyword": {
        "specific": {"min_recall": 0.60, "min_mrr": 0.50, "min_ndcg": 0.55},
        "edge": {"min_recall": 0.50, "min_mrr": 0.40, "min_ndcg": 0.45},
    },
    "hybrid": {
        "specific": {"min_recall": 0.75, "min_mrr": 0.65, "min_ndcg": 0.70},
        "broad": {"min_recall": 0.55, "min_mrr": 0.45, "min_ndcg": 0.50},
        "coarse-to-fine": {"min_recall": 0.60, "min_mrr": 0.50, "min_ndcg": 0.55},
    },
    "coarse_to_fine": {
        "coarse": {"min_recall": 0.50, "min_mrr": 0.40},
        "fine": {"min_recall": 0.40, "min_mrr": 0.30},
        "hierarchy": {"min_hierarchy_score": 0.50},
    },
}


@pytest.fixture
def get_thresholds():
    """Get threshold configuration for a mode/category combination."""

    def _get(mode: str, category: str) -> dict:
        return THRESHOLDS.get(mode, {}).get(category, {})

    return _get
