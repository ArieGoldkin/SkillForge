"""Pytest configuration for retrieval smoke tests.

Provides fixtures for:
- Database session with test data
- Search service initialization
- Test documents and chunks
- Fixture data loading
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.smoke.retrieval.fixtures import FixtureLoader
from tests.smoke.retrieval.metrics import MetricsCalculator

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from app.models.analysis import Analysis
    from app.models.analysis_chunk import AnalysisChunk
    from app.services.embeddings import EmbeddingService
    from app.services.search.search_service import SearchService


# Mark all tests in this module as smoke tests
pytestmark = [
    pytest.mark.smoke,
    pytest.mark.retrieval,
]


@pytest.fixture(scope="module")
def fixture_loader() -> FixtureLoader:
    """Provide fixture loader for test data."""
    loader = FixtureLoader()

    # Validate fixtures before tests run
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


def requires_embedding_service():
    """Check if embedding service is available.

    Requires OpenAI API key for text-embedding-3-small.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-test"):
        return pytest.mark.skip(reason="OPENAI_API_KEY required for embedding service")
    return pytest.mark.usefixtures()


@pytest_asyncio.fixture
async def embedding_service() -> EmbeddingService:
    """Create embedding service for tests.

    Requires valid OpenAI API key.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-test"):
        pytest.skip("OPENAI_API_KEY required for embedding service")

    from app.services.embeddings import EmbeddingService

    return EmbeddingService()


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
    from app.models.analysis import Analysis

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
    from app.models.analysis_chunk import AnalysisChunk

    chunks: list[AnalysisChunk] = []
    analysis_id = smoke_test_analysis.id

    for doc in test_documents:
        for section in doc.get("sections", []):
            content = section["content"]

            # Generate embedding for chunk
            embedding = await embedding_service.generate_embedding(
                text=content,
                normalize=True,
            )

            # Create chunk with all required fields
            chunk = AnalysisChunk(
                id=uuid4(),
                analysis_id=analysis_id,
                content=content,
                embedding=embedding,
                chunk_type=section.get("granularity", "coarse"),
                section_title=section["title"],
                chunk_idx=0,
                chunk_total=len(doc["sections"]),
                # Metadata for filtering and identification
                metadata={
                    "section_id": section["id"],
                    "doc_id": doc["id"],
                    "content_type": doc["content_type"],
                    "bucket": doc["bucket"],
                    "language": doc["language"],
                    "tags": doc.get("tags", []),
                },
            )

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
    from app.services.search.search_service import SearchService

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
    },
    "keyword": {
        "specific": {"min_recall": 0.60, "min_mrr": 0.50, "min_ndcg": 0.55},
        "edge": {"min_recall": 0.50, "min_mrr": 0.40, "min_ndcg": 0.45},
    },
    "hybrid": {
        "specific": {"min_recall": 0.75, "min_mrr": 0.65, "min_ndcg": 0.70},
        "broad": {"min_recall": 0.55, "min_mrr": 0.45, "min_ndcg": 0.50},
    },
}


@pytest.fixture
def get_thresholds():
    """Get threshold configuration for a mode/category combination."""

    def _get(mode: str, category: str) -> dict:
        return THRESHOLDS.get(mode, {}).get(category, {})

    return _get
