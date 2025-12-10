"""Pytest configuration for retrieval smoke tests.

Provides fixtures for:
- Database session with test data
- Search service initialization
- Test documents and chunks
- Fixture data loading

NOTE: Smoke tests require real API keys (not test placeholders).
      Ensure .env has valid OPENAI_API_KEY before running.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

# CRITICAL: Load .env BEFORE any other imports to get real API keys
# The main conftest.py sets placeholder keys, but smoke tests need real ones
# Path: tests/smoke/retrieval/conftest.py -> parent.parent.parent = tests/ -> parent = backend/
_env_file = Path(__file__).parent.parent.parent.parent / ".env"
if not _env_file.exists():
    # Try relative to backend/ (when running from backend dir)
    _env_file = Path(__file__).parent.parent.parent / ".." / ".env"
if _env_file.exists():
    from dotenv import load_dotenv

    # Override=True ensures we get real keys from .env, not placeholders
    load_dotenv(_env_file, override=True)

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from tests.smoke.retrieval.fixtures import FixtureLoader  # noqa: E402
from tests.smoke.retrieval.metrics import MetricsCalculator  # noqa: E402

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


@pytest.fixture(autouse=True)
def ensure_real_api_keys():
    """Verify real API keys are available for smoke tests.

    Smoke tests are marked with pytest.mark.smoke, which causes the main
    conftest.py to skip setting placeholder OPENAI_API_KEY. This fixture
    verifies that real keys from .env are available for live API calls.
    """
    from app.core.config import get_settings

    # Clear settings cache to ensure fresh load from environment
    get_settings.cache_clear()

    # Refresh the module-level settings object
    import app.core.config

    app.core.config.settings = get_settings()


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
async def embedding_service(ensure_real_api_keys) -> EmbeddingService:
    """Create embedding service for tests.

    Requires valid OpenAI API key from .env file.
    Directly reads the key and patches the settings module to bypass
    any cached references to placeholder keys from test fixtures.
    """
    # Read directly from .env to bypass any test mocking
    env_file = Path(__file__).parent.parent.parent.parent / ".env"
    if not env_file.exists():
        env_file = Path(__file__).parent.parent.parent / ".." / ".env"
    if not env_file.exists():
        env_file = Path(".env")

    api_key = None
    if env_file.exists():
        from dotenv import dotenv_values

        env_vars = dotenv_values(env_file)
        api_key = env_vars.get("OPENAI_API_KEY")

    if not api_key or api_key.startswith("sk-test"):
        pytest.skip("Valid OPENAI_API_KEY required in .env for embedding service")

    # CRITICAL: Must set OS env var AND patch app.core.config.settings
    # because EmbeddingService imports settings at module level
    os.environ["OPENAI_API_KEY"] = api_key

    from app.core.config import get_settings

    get_settings.cache_clear()

    import app.core.config

    app.core.config.settings = get_settings()

    # Also reload the embeddings module to pick up new settings reference
    import importlib

    import app.services.embeddings

    importlib.reload(app.services.embeddings)

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
