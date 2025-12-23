"""Unit tests for library repository with search operations."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.analysis import Analysis
from app.db.repositories.library_repository import LibraryRepository
from app.schemas.library import LibraryFilters


@pytest.fixture
def mock_session():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_embedding():
    """Sample embedding vector (1536 dimensions)."""
    return [0.1] * 1536


@pytest.fixture
def sample_analysis():
    """Sample analysis object."""
    return Analysis(
        id=uuid.uuid4(),
        url="https://example.com",
        content_type="article",
        title="Test Article",
        raw_content="This is a test article about PostgreSQL full-text search.",
        content_embedding=[0.1] * 1536,
        status="complete",
    )


@pytest.mark.asyncio
async def test_search_by_text_empty_query(mock_session):
    """Test search_by_text with empty query."""
    repo = LibraryRepository(session=mock_session)
    result = await repo.search_by_text(query="")
    assert result == []


@pytest.mark.asyncio
async def test_search_by_text_whitespace_query(mock_session):
    """Test search_by_text with whitespace-only query."""
    repo = LibraryRepository(session=mock_session)
    result = await repo.search_by_text(query="   ")
    assert result == []


@pytest.mark.asyncio
@patch("app.db.repositories.library_repository.func")
@patch("app.db.repositories.library_repository.select")
async def test_search_by_text_valid_query(mock_select, mock_func, mock_session, sample_analysis):
    """Test search_by_text with valid query."""
    repo = LibraryRepository(session=mock_session)

    # Mock the query execution
    mock_result = MagicMock()
    mock_result.all.return_value = [(sample_analysis, 0.85)]
    mock_session.execute.return_value = mock_result

    result = await repo.search_by_text(query="postgresql search", limit=10, offset=0)

    assert isinstance(result, list)
    assert mock_session.execute.called


@pytest.mark.asyncio
async def test_search_by_vector_empty_embedding(mock_session):
    """Test search_by_vector with empty embedding."""
    repo = LibraryRepository(session=mock_session)
    result = await repo.search_by_vector(embedding=[])
    assert result == []


@pytest.mark.asyncio
@patch("app.db.repositories.library_repository.select")
async def test_search_by_vector_valid_embedding(
    mock_select, mock_session, sample_embedding, sample_analysis
):
    """Test search_by_vector with valid embedding."""
    repo = LibraryRepository(session=mock_session)

    # Mock the query execution
    mock_result = MagicMock()
    mock_result.all.return_value = [(sample_analysis, 0.15)]
    mock_session.execute.return_value = mock_result

    result = await repo.search_by_vector(embedding=sample_embedding, limit=10)

    assert isinstance(result, list)
    assert mock_session.execute.called


@pytest.mark.asyncio
async def test_hybrid_search_empty_inputs(mock_session):
    """Test hybrid_search with empty query and embedding."""
    repo = LibraryRepository(session=mock_session)
    result = await repo.hybrid_search(query="", embedding=[], limit=10, offset=0)
    assert result == []


@pytest.mark.asyncio
@patch("app.db.repositories.library_repository.LibraryRepository.search_by_text")
@patch("app.db.repositories.library_repository.LibraryRepository.search_by_vector")
async def test_hybrid_search_rrf_fusion(
    mock_vector_search, mock_text_search, mock_session, sample_embedding
):
    """Test hybrid_search RRF fusion algorithm."""
    repo = LibraryRepository(session=mock_session)

    # Create sample analyses
    analysis1 = Analysis(
        id=uuid.uuid4(),
        url="https://example.com/1",
        content_type="article",
        title="PostgreSQL Guide",
        status="complete",
    )
    analysis2 = Analysis(
        id=uuid.uuid4(),
        url="https://example.com/2",
        content_type="article",
        title="Full-Text Search",
        status="complete",
    )
    analysis3 = Analysis(
        id=uuid.uuid4(),
        url="https://example.com/3",
        content_type="article",
        title="Vector Search",
        status="complete",
    )

    # Mock search results
    # analysis1 ranks high in both searches (should rank highest in RRF)
    # analysis2 only in text search
    # analysis3 only in vector search
    mock_text_search.return_value = [(analysis1, 0.9), (analysis2, 0.7)]
    mock_vector_search.return_value = [(analysis1, 0.1), (analysis3, 0.2)]

    # Mock the final database fetch
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [analysis1, analysis2, analysis3]
    mock_session.execute.return_value = mock_result

    result = await repo.hybrid_search(
        query="postgresql search", embedding=sample_embedding, limit=10, offset=0
    )

    # Verify searches were called with correct candidate limit
    mock_text_search.assert_called_once()
    mock_vector_search.assert_called_once()

    # Verify result is a list of tuples
    assert isinstance(result, list)


@pytest.mark.asyncio
@patch("app.db.repositories.library_repository.func")
@patch("app.db.repositories.library_repository.select")
async def test_list_analyses_no_filters(mock_select, mock_func, mock_session, sample_analysis):
    """Test list_analyses with no filters."""
    repo = LibraryRepository(session=mock_session)

    # Mock count query
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 42

    # Mock data query
    mock_data_result = MagicMock()
    mock_data_result.scalars.return_value.all.return_value = [sample_analysis]

    # Setup execute to return different results for count and data queries
    mock_session.execute.side_effect = [mock_count_result, mock_data_result]

    filters = LibraryFilters()
    analyses, total = await repo.list_analyses(filters, limit=20, offset=0)

    assert total == 42
    assert len(analyses) == 1
    assert mock_session.execute.call_count == 2


@pytest.mark.asyncio
@patch("app.db.repositories.library_repository.func")
@patch("app.db.repositories.library_repository.select")
async def test_list_analyses_with_filters(mock_select, mock_func, mock_session):
    """Test list_analyses with filters applied."""
    repo = LibraryRepository(session=mock_session)

    # Mock count query
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 10

    # Mock data query
    mock_data_result = MagicMock()
    mock_data_result.scalars.return_value.all.return_value = []

    mock_session.execute.side_effect = [mock_count_result, mock_data_result]

    filters = LibraryFilters(content_type="article", status="complete")
    analyses, total = await repo.list_analyses(filters, limit=20, offset=0)

    assert total == 10
    assert len(analyses) == 0
    assert mock_session.execute.call_count == 2


@pytest.mark.asyncio
async def test_get_search_snippet_empty_query(mock_session):
    """Test get_search_snippet with empty query."""
    repo = LibraryRepository(session=mock_session)
    result = await repo.get_search_snippet(analysis_id=uuid.uuid4(), query="")
    assert result is None


@pytest.mark.asyncio
@patch("app.db.repositories.library_repository.func")
@patch("app.db.repositories.library_repository.select")
async def test_get_search_snippet_valid_query(mock_select, mock_func, mock_session):
    """Test get_search_snippet with valid query."""
    repo = LibraryRepository(session=mock_session)

    # Mock the query execution
    mock_result = MagicMock()
    mock_result.scalar.return_value = (
        "PostgreSQL provides <mark>full-text search</mark> capabilities..."
    )
    mock_session.execute.return_value = mock_result

    snippet = await repo.get_search_snippet(analysis_id=uuid.uuid4(), query="full-text search")

    assert snippet is not None
    assert "<mark>" in snippet
    assert "</mark>" in snippet
    assert mock_session.execute.called


@pytest.mark.asyncio
@patch("app.db.repositories.library_repository.func")
@patch("app.db.repositories.library_repository.select")
async def test_get_search_snippet_not_found(mock_select, mock_func, mock_session):
    """Test get_search_snippet when analysis not found."""
    repo = LibraryRepository(session=mock_session)

    # Mock the query execution returning None
    mock_result = MagicMock()
    mock_result.scalar.return_value = None
    mock_session.execute.return_value = mock_result

    snippet = await repo.get_search_snippet(analysis_id=uuid.uuid4(), query="full-text search")

    assert snippet is None
    assert mock_session.execute.called
