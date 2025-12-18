"""Unit tests for analysis repository with vector search."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.analysis_repository import AnalysisRepository
from app.db.models.analysis import Analysis


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


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
        content_embedding=[0.1] * 1536,
    )


@pytest.mark.asyncio
async def test_find_similar_analyses_empty_query(mock_session):
    """Test find_similar_analyses with empty query."""
    repo = AnalysisRepository(session=mock_session)
    result = await repo.find_similar_analyses(query_embedding=[])
    assert result == []


@pytest.mark.asyncio
async def test_find_similar_analyses_invalid_dimensions(mock_session):
    """Test find_similar_analyses with invalid embedding dimensions."""
    repo = AnalysisRepository(session=mock_session)
    result = await repo.find_similar_analyses(query_embedding=[0.1] * 100)
    assert result == []


@pytest.mark.asyncio
@patch("app.db.repositories.analysis_repository.func")
@patch("app.db.repositories.analysis_repository.select")
async def test_find_similar_analyses_two_stage_search(
    mock_select, mock_func, mock_session, sample_embedding
):
    """Test two-stage vector search implementation."""
    repo = AnalysisRepository(session=mock_session)

    # Mock the subquery and final query
    mock_subquery = MagicMock()
    # Chain mock return values for subquery construction
    # Break long chain into multiple lines for readability
    where_result = mock_select.return_value.where.return_value
    order_by_result = where_result.order_by.return_value
    limit_result = order_by_result.limit.return_value
    mock_subquery_chain = limit_result.subquery
    mock_subquery_chain.return_value = mock_subquery

    mock_final_query = MagicMock()
    mock_select.return_value.order_by.return_value.limit.return_value = mock_final_query

    mock_scalars_result = MagicMock()
    mock_scalars_result.all.return_value = []
    mock_session.scalars.return_value = mock_scalars_result

    result = await repo.find_similar_analyses(
        query_embedding=sample_embedding, limit=5, fast_search_limit=20
    )

    assert isinstance(result, list)
    # Verify subquery was created (binary quantization search)
    assert mock_select.return_value.where.called
    # Verify final query was executed (re-ranking)
    assert mock_session.scalars.called


@pytest.mark.asyncio
async def test_stream_all_analyses(mock_session):
    """Test stream_all_analyses method."""
    repo = AnalysisRepository(session=mock_session)

    # Mock stream_scalars as async context manager
    # stream_scalars returns an AsyncScalarResult that is an async context manager
    mock_analysis = MagicMock(spec=Analysis)
    mock_result = AsyncMock()
    mock_result.__aiter__.return_value = [mock_analysis]
    mock_result.__aenter__ = AsyncMock(return_value=mock_result)
    mock_result.__aexit__ = AsyncMock(return_value=None)
    # stream_scalars is a regular method (not async) that returns async context manager
    mock_session.stream_scalars = MagicMock(return_value=mock_result)

    results = []
    async for analysis in repo.stream_all_analyses(limit=10):
        results.append(analysis)

    assert len(results) == 1
    assert mock_session.stream_scalars.called


@pytest.mark.asyncio
async def test_stream_all_analyses_invalid_order_by(mock_session):
    """Test stream_all_analyses with invalid order_by column."""
    repo = AnalysisRepository(session=mock_session)

    # Mock stream_scalars as async context manager
    # stream_scalars is a regular method (not async) that returns async context manager
    mock_result = AsyncMock()
    mock_result.__aiter__.return_value = []
    mock_result.__aenter__ = AsyncMock(return_value=mock_result)
    mock_result.__aexit__ = AsyncMock(return_value=None)
    mock_session.stream_scalars = MagicMock(return_value=mock_result)

    # Invalid column should default to "created_at"
    results = []
    async for _ in repo.stream_all_analyses(order_by="invalid_column"):
        results.append(_)

    # Should still work (defaults to created_at)
    assert mock_session.stream_scalars.called


@pytest.mark.asyncio
@patch("app.db.repositories.analysis_repository.func")
@patch("app.db.repositories.analysis_repository.select")
@patch("sqlalchemy.text")
async def test_find_similar_analyses_vector_query_conversion(
    mock_text, mock_select, mock_func, mock_session, sample_embedding
):
    """Test that Python list is correctly converted to PostgreSQL array format for vector query.

    This test verifies the vector conversion implementation where the embedding list
    is converted to PostgreSQL array format string '[0.1,0.2,...]' and cast to vector type.
    This approach is safe because query_embedding is list[float] from embedding service,
    not user input.
    """
    repo = AnalysisRepository(session=mock_session)

    # Mock the query chain
    where_result = mock_select.return_value.where.return_value
    order_by_result = where_result.order_by.return_value
    limit_result = order_by_result.limit.return_value
    mock_subquery = MagicMock()
    limit_result.subquery.return_value = mock_subquery

    mock_final_query = MagicMock()
    mock_select.return_value.order_by.return_value.limit.return_value = mock_final_query

    mock_scalars_result = MagicMock()
    mock_scalars_result.all.return_value = []
    mock_session.scalars.return_value = mock_scalars_result

    # Mock text() to capture the literal vector format call
    mock_text_expr = MagicMock()
    mock_text.return_value = mock_text_expr

    result = await repo.find_similar_analyses(
        query_embedding=sample_embedding, limit=5, fast_search_limit=20
    )

    # Verify text() was called with vector literal format
    assert mock_text.called
    text_call = mock_text.call_args
    text_arg = text_call[0][0]

    # Verify it uses PostgreSQL vector literal format: '[...]'::vector
    # The implementation creates: "'[0.1,0.1,...]'::vector"
    assert "::vector" in text_arg, "Vector cast operator '::vector' should be present"
    assert "'" in text_arg, "Vector literal should be quoted"
    assert "[" in text_arg and "]" in text_arg, "Vector array should use square brackets"

    # Verify query executed successfully
    assert isinstance(result, list)
    assert mock_session.scalars.called
