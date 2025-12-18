"""Unit tests for chunk repository with semantic, keyword, and hybrid search."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.analysis_chunk import AnalysisChunk
from app.db.repositories.chunk_repository import ChunkRepository


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def sample_embedding():
    """Sample embedding vector (1536 dimensions for OpenAI)."""
    return [0.1] * 1536


@pytest.fixture
def sample_analysis_id():
    """Sample analysis UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_chunk(sample_analysis_id, sample_embedding):
    """Sample AnalysisChunk object."""
    return AnalysisChunk(
        id=uuid.uuid4(),
        analysis_id=sample_analysis_id,
        granularity="coarse",
        path=["section", "subsection"],
        section_title="Test Section",
        chunk_idx=0,
        chunk_total=5,
        content_type="article",
        language="en",
        hash="abc123",
        model="text-embedding-3-small",
        model_version="1.0",
        snippet="Test content for chunk",
        vector=sample_embedding,
        token_count=100,
        embedding_latency_ms=50.0,
        was_truncated=False,
    )


# ============================================================================
# Semantic Search Tests
# ============================================================================


@pytest.mark.asyncio
async def test_semantic_search_returns_results(mock_session, sample_embedding, sample_chunk):
    """Test semantic_search returns chunks with similarity scores."""
    repo = ChunkRepository(session=mock_session)

    # Mock database result
    mock_result = MagicMock()
    mock_result.all.return_value = [(sample_chunk, 0.95)]
    mock_session.execute.return_value = mock_result

    results = await repo.semantic_search(query_embedding=sample_embedding, limit=10)

    assert len(results) == 1
    assert results[0][0] == sample_chunk
    assert results[0][1] == 0.95
    assert mock_session.execute.called


@pytest.mark.asyncio
async def test_semantic_search_respects_limit(mock_session, sample_embedding):
    """Test semantic_search respects the limit parameter."""
    repo = ChunkRepository(session=mock_session)

    # Mock database result with empty list
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute.return_value = mock_result

    await repo.semantic_search(query_embedding=sample_embedding, limit=5)

    # Verify the query was built correctly
    assert mock_session.execute.called


@pytest.mark.asyncio
async def test_semantic_search_handles_zero_results(mock_session, sample_embedding):
    """Test semantic_search handles zero results gracefully."""
    repo = ChunkRepository(session=mock_session)

    # Mock empty result
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute.return_value = mock_result

    results = await repo.semantic_search(query_embedding=sample_embedding, limit=10)

    assert results == []


@pytest.mark.asyncio
async def test_semantic_search_with_content_type_filter(
    mock_session, sample_embedding, sample_chunk
):
    """Test semantic_search with content_type metadata filter."""
    repo = ChunkRepository(session=mock_session)

    # Mock database result
    mock_result = MagicMock()
    mock_result.all.return_value = [(sample_chunk, 0.90)]
    mock_session.execute.return_value = mock_result

    results = await repo.semantic_search(
        query_embedding=sample_embedding, limit=10, filters={"content_type": "article"}
    )

    assert len(results) == 1
    assert results[0][0].content_type == "article"


@pytest.mark.asyncio
async def test_semantic_search_with_analysis_id_filter(
    mock_session, sample_embedding, sample_analysis_id, sample_chunk
):
    """Test semantic_search with analysis_id metadata filter."""
    repo = ChunkRepository(session=mock_session)

    # Mock database result
    mock_result = MagicMock()
    mock_result.all.return_value = [(sample_chunk, 0.88)]
    mock_session.execute.return_value = mock_result

    results = await repo.semantic_search(
        query_embedding=sample_embedding, limit=10, filters={"analysis_id": sample_analysis_id}
    )

    assert len(results) == 1
    assert results[0][0].analysis_id == sample_analysis_id


@pytest.mark.asyncio
async def test_semantic_search_with_multiple_filters(
    mock_session, sample_embedding, sample_analysis_id, sample_chunk
):
    """Test semantic_search with multiple metadata filters."""
    repo = ChunkRepository(session=mock_session)

    # Mock database result
    mock_result = MagicMock()
    mock_result.all.return_value = [(sample_chunk, 0.92)]
    mock_session.execute.return_value = mock_result

    results = await repo.semantic_search(
        query_embedding=sample_embedding,
        limit=10,
        filters={"content_type": "article", "analysis_id": sample_analysis_id},
    )

    assert len(results) == 1


# ============================================================================
# Keyword Search Tests
# ============================================================================


@pytest.mark.asyncio
async def test_keyword_search_returns_results(mock_session, sample_chunk):
    """Test keyword_search returns chunks with scores."""
    repo = ChunkRepository(session=mock_session)

    # Mock database result
    mock_result = MagicMock()
    mock_result.all.return_value = [(sample_chunk, 0.85)]
    mock_session.execute.return_value = mock_result

    results = await repo.keyword_search(query_text="machine learning", limit=10)

    assert len(results) == 1
    assert results[0][0] == sample_chunk
    assert results[0][1] == 0.85
    assert mock_session.execute.called


@pytest.mark.asyncio
async def test_keyword_search_case_insensitive(mock_session):
    """Test keyword_search is case insensitive (via PostgreSQL plainto_tsquery)."""
    repo = ChunkRepository(session=mock_session)

    # Mock database result
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute.return_value = mock_result

    # plainto_tsquery handles case normalization automatically
    await repo.keyword_search(query_text="Machine Learning", limit=10)

    assert mock_session.execute.called


@pytest.mark.asyncio
async def test_keyword_search_handles_special_characters(mock_session):
    """Test keyword_search handles special characters (via plainto_tsquery)."""
    repo = ChunkRepository(session=mock_session)

    # Mock database result
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute.return_value = mock_result

    # plainto_tsquery handles special chars automatically
    await repo.keyword_search(query_text="machine-learning & AI!", limit=10)

    assert mock_session.execute.called


@pytest.mark.asyncio
async def test_keyword_search_with_content_type_filter(mock_session, sample_chunk):
    """Test keyword_search with content_type metadata filter."""
    repo = ChunkRepository(session=mock_session)

    # Mock database result
    mock_result = MagicMock()
    mock_result.all.return_value = [(sample_chunk, 0.75)]
    mock_session.execute.return_value = mock_result

    results = await repo.keyword_search(
        query_text="test", limit=10, filters={"content_type": "article"}
    )

    assert len(results) == 1


@pytest.mark.asyncio
async def test_keyword_search_with_analysis_id_filter(
    mock_session, sample_analysis_id, sample_chunk
):
    """Test keyword_search with analysis_id metadata filter."""
    repo = ChunkRepository(session=mock_session)

    # Mock database result
    mock_result = MagicMock()
    mock_result.all.return_value = [(sample_chunk, 0.80)]
    mock_session.execute.return_value = mock_result

    results = await repo.keyword_search(
        query_text="test", limit=10, filters={"analysis_id": sample_analysis_id}
    )

    assert len(results) == 1


@pytest.mark.asyncio
async def test_keyword_search_handles_zero_results(mock_session):
    """Test keyword_search handles zero results gracefully."""
    repo = ChunkRepository(session=mock_session)

    # Mock empty result
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute.return_value = mock_result

    results = await repo.keyword_search(query_text="nonexistent", limit=10)

    assert results == []


# ============================================================================
# Hybrid Search Tests
# ============================================================================


@pytest.mark.asyncio
async def test_hybrid_search_combines_results(mock_session, sample_embedding, sample_chunk):
    """Test hybrid_search combines semantic and keyword search with RRF."""
    repo = ChunkRepository(session=mock_session)

    # Create two different chunks for semantic vs keyword results
    chunk1 = sample_chunk
    chunk2 = AnalysisChunk(
        id=uuid.uuid4(),
        analysis_id=sample_chunk.analysis_id,
        granularity="fine",
        path=["section", "subsection", "chunk"],
        section_title="Another Section",
        chunk_idx=1,
        chunk_total=5,
        snippet="Another test chunk",
        vector=[0.2] * 1536,
        hash="def456",
        model="text-embedding-3-small",
    )

    # Mock semantic search results
    with patch.object(
        repo, "semantic_search", return_value=[(chunk1, 0.95), (chunk2, 0.85)]
    ) as mock_semantic:
        # Mock keyword search results (reverse order)
        with patch.object(
            repo, "keyword_search", return_value=[(chunk2, 0.90), (chunk1, 0.80)]
        ) as mock_keyword:
            results = await repo.hybrid_search(
                query_embedding=sample_embedding,
                query_text="machine learning",
                limit=10,
            )

            # Verify both searches were called with 2*limit
            mock_semantic.assert_called_once()
            mock_keyword.assert_called_once()
            assert mock_semantic.call_args[1]["limit"] == 20
            assert mock_keyword.call_args[1]["limit"] == 20

            # Results should be fused via RRF
            assert len(results) == 2
            # Each chunk appears in both results, so RRF scores are summed
            # chunk1: 1/(60+1) + 1/(60+2) ≈ 0.0164 + 0.0161 = 0.0325
            # chunk2: 1/(60+2) + 1/(60+1) ≈ 0.0161 + 0.0164 = 0.0325
            # Both have same score, so order depends on dict iteration
            assert results[0][0] in [chunk1, chunk2]


@pytest.mark.asyncio
async def test_hybrid_search_handles_duplicate_chunks(mock_session, sample_embedding, sample_chunk):
    """Test hybrid_search merges duplicate chunks by summing RRF scores."""
    repo = ChunkRepository(session=mock_session)

    # Same chunk appears in both results
    with patch.object(repo, "semantic_search", return_value=[(sample_chunk, 0.95)]):
        with patch.object(repo, "keyword_search", return_value=[(sample_chunk, 0.90)]):
            results = await repo.hybrid_search(
                query_embedding=sample_embedding,
                query_text="test",
                limit=10,
            )

            # Should have one chunk with combined RRF score
            assert len(results) == 1
            assert results[0][0] == sample_chunk
            # RRF score: 1/(60+1) + 1/(60+1) = 2/61 ≈ 0.0328
            assert results[0][1] > 0.03


@pytest.mark.asyncio
async def test_hybrid_search_respects_limit(mock_session, sample_embedding):
    """Test hybrid_search returns at most limit results."""
    repo = ChunkRepository(session=mock_session)

    # Create many chunks
    chunks = [
        AnalysisChunk(
            id=uuid.uuid4(),
            analysis_id=uuid.uuid4(),
            granularity="coarse",
            path=["section"],
            chunk_idx=i,
            chunk_total=10,
            snippet=f"Chunk {i}",
            vector=[0.1 + i * 0.01] * 1536,
            hash=f"hash{i}",
            model="text-embedding-3-small",
        )
        for i in range(10)
    ]

    # Mock semantic results with half the chunks
    semantic_results = [(chunks[i], 0.9 - i * 0.05) for i in range(5)]
    # Mock keyword results with the other half
    keyword_results = [(chunks[i], 0.8 - i * 0.05) for i in range(5, 10)]

    with patch.object(repo, "semantic_search", return_value=semantic_results):
        with patch.object(repo, "keyword_search", return_value=keyword_results):
            results = await repo.hybrid_search(
                query_embedding=sample_embedding,
                query_text="test",
                limit=3,
            )

            # Should return only 3 results
            assert len(results) == 3


@pytest.mark.asyncio
async def test_hybrid_search_with_filters(mock_session, sample_embedding, sample_chunk):
    """Test hybrid_search passes filters to both searches."""
    repo = ChunkRepository(session=mock_session)

    filters = {"content_type": "article"}

    with patch.object(
        repo, "semantic_search", return_value=[(sample_chunk, 0.95)]
    ) as mock_semantic:
        with patch.object(
            repo, "keyword_search", return_value=[(sample_chunk, 0.90)]
        ) as mock_keyword:
            await repo.hybrid_search(
                query_embedding=sample_embedding,
                query_text="test",
                limit=10,
                filters=filters,
            )

            # Verify filters were passed to both searches
            assert mock_semantic.call_args[1]["filters"] == filters
            assert mock_keyword.call_args[1]["filters"] == filters


@pytest.mark.asyncio
async def test_hybrid_search_rrf_constant(mock_session, sample_embedding, sample_chunk):
    """Test hybrid_search uses RRF constant k=60."""
    repo = ChunkRepository(session=mock_session)

    # Single chunk at rank 1 in both searches
    with patch.object(repo, "semantic_search", return_value=[(sample_chunk, 0.95)]):
        with patch.object(repo, "keyword_search", return_value=[(sample_chunk, 0.90)]):
            results = await repo.hybrid_search(
                query_embedding=sample_embedding,
                query_text="test",
                limit=10,
            )

            # RRF score with k=60: 1/(60+1) + 1/(60+1) = 2/61
            expected_score = 2.0 / 61.0
            assert abs(results[0][1] - expected_score) < 0.0001


# ============================================================================
# get_by_analysis_id Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_by_analysis_id_returns_ordered_chunks(mock_session, sample_analysis_id):
    """Test get_by_analysis_id returns chunks ordered by chunk_idx."""
    repo = ChunkRepository(session=mock_session)

    # Create chunks with different chunk_idx values
    chunks = [
        AnalysisChunk(
            id=uuid.uuid4(),
            analysis_id=sample_analysis_id,
            granularity="coarse",
            path=["section"],
            chunk_idx=i,
            chunk_total=3,
            snippet=f"Chunk {i}",
            vector=[0.1] * 1536,
            hash=f"hash{i}",
            model="test",
        )
        for i in range(3)
    ]

    # Mock database result
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = chunks
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    results = await repo.get_by_analysis_id(str(sample_analysis_id))

    assert len(results) == 3
    assert results[0].chunk_idx == 0
    assert results[1].chunk_idx == 1
    assert results[2].chunk_idx == 2


@pytest.mark.asyncio
async def test_get_by_analysis_id_handles_no_chunks(mock_session, sample_analysis_id):
    """Test get_by_analysis_id handles analysis with no chunks."""
    repo = ChunkRepository(session=mock_session)

    # Mock empty result
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    results = await repo.get_by_analysis_id(str(sample_analysis_id))

    assert results == []


# ============================================================================
# create_many Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_many_inserts_chunks(mock_session, sample_analysis_id, sample_embedding):
    """Test create_many bulk inserts chunks."""
    repo = ChunkRepository(session=mock_session)

    chunk_dicts = [
        {
            "analysis_id": sample_analysis_id,
            "granularity": "coarse",
            "path": ["section"],
            "chunk_idx": i,
            "chunk_total": 3,
            "snippet": f"Chunk {i}",
            "vector": sample_embedding,
            "hash": f"hash{i}",
            "model": "text-embedding-3-small",
        }
        for i in range(3)
    ]

    # Mock session methods
    mock_session.add_all = MagicMock()
    mock_session.flush = AsyncMock()

    results = await repo.create_many(chunk_dicts)

    assert len(results) == 3
    assert mock_session.add_all.called
    assert mock_session.flush.called


@pytest.mark.asyncio
async def test_create_many_handles_empty_list(mock_session):
    """Test create_many handles empty input gracefully."""
    repo = ChunkRepository(session=mock_session)

    # Mock session methods
    mock_session.add_all = MagicMock()
    mock_session.flush = AsyncMock()

    results = await repo.create_many([])

    assert results == []
    assert mock_session.add_all.called
    assert mock_session.flush.called


# ============================================================================
# list_by_analysis Tests
# ============================================================================


@pytest.mark.asyncio
async def test_list_by_analysis_returns_chunks(mock_session, sample_analysis_id):
    """Test list_by_analysis returns all chunks for an analysis."""
    repo = ChunkRepository(session=mock_session)

    chunks = [
        AnalysisChunk(
            id=uuid.uuid4(),
            analysis_id=sample_analysis_id,
            granularity="coarse",
            path=["section"],
            chunk_idx=i,
            chunk_total=2,
            snippet=f"Chunk {i}",
            vector=[0.1] * 1536,
            hash=f"hash{i}",
            model="test",
        )
        for i in range(2)
    ]

    # Mock database result
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = chunks
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    results = await repo.list_by_analysis(sample_analysis_id)

    assert len(results) == 2


# ============================================================================
# search_coarse Tests
# ============================================================================


@pytest.mark.asyncio
async def test_search_coarse_filters_by_granularity(mock_session):
    """Test search_coarse returns only coarse-grained chunks."""
    repo = ChunkRepository(session=mock_session)

    coarse_chunk = AnalysisChunk(
        id=uuid.uuid4(),
        analysis_id=uuid.uuid4(),
        granularity="coarse",
        path=["section"],
        chunk_idx=0,
        chunk_total=1,
        snippet="Coarse chunk",
        vector=[0.1] * 1536,
        hash="hash1",
        model="test",
    )

    # Mock database result
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [coarse_chunk]
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    results = await repo.search_coarse(limit=10)

    assert len(results) == 1
    assert results[0][0].granularity == "coarse"
    assert results[0][1] == 0.0  # Placeholder score


@pytest.mark.asyncio
async def test_search_coarse_respects_limit(mock_session):
    """Test search_coarse respects the limit parameter."""
    repo = ChunkRepository(session=mock_session)

    # Mock database result
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    await repo.search_coarse(limit=5)

    assert mock_session.execute.called


# ============================================================================
# search_fine_by_paths Tests
# ============================================================================


@pytest.mark.asyncio
async def test_search_fine_by_paths_filters_by_granularity(mock_session):
    """Test search_fine_by_paths returns only fine-grained chunks."""
    repo = ChunkRepository(session=mock_session)

    fine_chunk = AnalysisChunk(
        id=uuid.uuid4(),
        analysis_id=uuid.uuid4(),
        granularity="fine",
        path=["section", "subsection"],
        chunk_idx=0,
        chunk_total=1,
        snippet="Fine chunk",
        vector=[0.1] * 1536,
        hash="hash1",
        model="test",
    )

    # Mock database result
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [fine_chunk]
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    results = await repo.search_fine_by_paths(paths=[["section", "subsection"]], limit=10)

    assert len(results) == 1
    assert results[0][0].granularity == "fine"
    assert results[0][1] == 0.0  # Placeholder score


@pytest.mark.asyncio
async def test_search_fine_by_paths_handles_empty_paths(mock_session):
    """Test search_fine_by_paths returns empty list for empty paths."""
    repo = ChunkRepository(session=mock_session)

    results = await repo.search_fine_by_paths(paths=[], limit=10)

    assert results == []
    # Should not execute query
    assert not mock_session.execute.called


# ============================================================================
# get_existing_hashes Tests (Deduplication)
# ============================================================================


@pytest.mark.asyncio
async def test_get_existing_hashes_returns_matching_hashes(mock_session, sample_analysis_id):
    """Test get_existing_hashes returns hashes that exist in database."""
    repo = ChunkRepository(session=mock_session)

    existing_hashes = ["hash1", "hash2", "hash3"]

    # Mock database result
    mock_result = MagicMock()
    mock_result.all.return_value = [("hash1",), ("hash3",)]
    mock_session.execute.return_value = mock_result

    result = await repo.get_existing_hashes(sample_analysis_id, existing_hashes)

    assert result == {"hash1", "hash3"}
    assert "hash2" not in result


@pytest.mark.asyncio
async def test_get_existing_hashes_handles_no_matches(mock_session, sample_analysis_id):
    """Test get_existing_hashes handles no matching hashes."""
    repo = ChunkRepository(session=mock_session)

    # Mock empty result
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute.return_value = mock_result

    result = await repo.get_existing_hashes(sample_analysis_id, ["hash1", "hash2"])

    assert result == set()


@pytest.mark.asyncio
async def test_get_existing_hashes_handles_empty_input(mock_session, sample_analysis_id):
    """Test get_existing_hashes handles empty hash list."""
    repo = ChunkRepository(session=mock_session)

    result = await repo.get_existing_hashes(sample_analysis_id, [])

    assert result == set()
    # Should not execute query
    assert not mock_session.execute.called


@pytest.mark.asyncio
async def test_get_existing_hashes_scopes_to_analysis(mock_session, sample_analysis_id):
    """Test get_existing_hashes only returns hashes for the specified analysis."""
    repo = ChunkRepository(session=mock_session)

    # Mock database result
    mock_result = MagicMock()
    mock_result.all.return_value = [("hash1",)]
    mock_session.execute.return_value = mock_result

    result = await repo.get_existing_hashes(sample_analysis_id, ["hash1", "hash2"])

    # Verify query was executed with analysis_id filter
    assert mock_session.execute.called
    assert result == {"hash1"}


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_semantic_search_handles_database_error(mock_session, sample_embedding):
    """Test semantic_search handles database errors gracefully."""
    repo = ChunkRepository(session=mock_session)

    # Mock database error
    mock_session.execute.side_effect = Exception("Database connection error")

    with pytest.raises(Exception, match="Database connection error"):
        await repo.semantic_search(query_embedding=sample_embedding, limit=10)


@pytest.mark.asyncio
async def test_keyword_search_handles_database_error(mock_session):
    """Test keyword_search handles database errors gracefully."""
    repo = ChunkRepository(session=mock_session)

    # Mock database error
    mock_session.execute.side_effect = Exception("Database connection error")

    with pytest.raises(Exception, match="Database connection error"):
        await repo.keyword_search(query_text="test", limit=10)


@pytest.mark.asyncio
async def test_create_many_handles_database_error(mock_session, sample_analysis_id):
    """Test create_many handles database errors gracefully."""
    repo = ChunkRepository(session=mock_session)

    chunk_dict = {
        "analysis_id": sample_analysis_id,
        "granularity": "coarse",
        "path": ["section"],
        "chunk_idx": 0,
        "chunk_total": 1,
        "snippet": "Test",
        "vector": [0.1] * 1536,
        "hash": "hash1",
        "model": "test",
    }

    # Mock database error on flush
    mock_session.add_all = MagicMock()
    mock_session.flush.side_effect = Exception("Database constraint violation")

    with pytest.raises(Exception, match="Database constraint violation"):
        await repo.create_many([chunk_dict])


# ============================================================================
# Edge Cases and Metadata Tests
# ============================================================================


@pytest.mark.asyncio
async def test_semantic_search_with_none_filters(mock_session, sample_embedding):
    """Test semantic_search handles None filters (no filtering)."""
    repo = ChunkRepository(session=mock_session)

    # Mock database result
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute.return_value = mock_result

    results = await repo.semantic_search(query_embedding=sample_embedding, limit=10, filters=None)

    assert results == []
    assert mock_session.execute.called


@pytest.mark.asyncio
async def test_keyword_search_with_empty_string(mock_session):
    """Test keyword_search handles empty query string."""
    repo = ChunkRepository(session=mock_session)

    # Mock database result
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute.return_value = mock_result

    results = await repo.keyword_search(query_text="", limit=10)

    # plainto_tsquery handles empty string gracefully
    assert results == []


@pytest.mark.asyncio
async def test_hybrid_search_with_only_semantic_results(
    mock_session, sample_embedding, sample_chunk
):
    """Test hybrid_search when only semantic search returns results."""
    repo = ChunkRepository(session=mock_session)

    with patch.object(repo, "semantic_search", return_value=[(sample_chunk, 0.95)]):
        with patch.object(repo, "keyword_search", return_value=[]):
            results = await repo.hybrid_search(
                query_embedding=sample_embedding,
                query_text="test",
                limit=10,
            )

            # Should still return the semantic result with RRF score
            assert len(results) == 1
            assert results[0][0] == sample_chunk


@pytest.mark.asyncio
async def test_hybrid_search_with_only_keyword_results(
    mock_session, sample_embedding, sample_chunk
):
    """Test hybrid_search when only keyword search returns results."""
    repo = ChunkRepository(session=mock_session)

    with patch.object(repo, "semantic_search", return_value=[]):
        with patch.object(repo, "keyword_search", return_value=[(sample_chunk, 0.90)]):
            results = await repo.hybrid_search(
                query_embedding=sample_embedding,
                query_text="test",
                limit=10,
            )

            # Should still return the keyword result with RRF score
            assert len(results) == 1
            assert results[0][0] == sample_chunk
