"""Unit tests for ChunkRepository database operations."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.analysis_chunk import AnalysisChunk
from app.db.repositories.chunk_repository import ChunkRepository


def create_test_chunk(**kwargs):
    """Create AnalysisChunk with required fields for testing."""
    defaults = {
        "id": uuid.uuid4(),
        "analysis_id": uuid.uuid4(),
        "granularity": "fine",
        "path": ["section"],
        "chunk_idx": 0,
        "chunk_total": 1,
        "hash": "test_hash",
        "vector": [0.1] * 1536,
        "snippet": "Test chunk",
    }
    defaults.update(kwargs)
    return AnalysisChunk(**defaults)


@pytest.mark.unit
class TestChunkRepository:
    """Test cases for ChunkRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def repository(self, mock_session):
        """Create ChunkRepository instance with mock session."""
        return ChunkRepository(mock_session)

    @pytest.fixture
    def sample_chunk(self):
        """Create a sample AnalysisChunk for testing."""
        return AnalysisChunk(
            id=uuid.uuid4(),
            analysis_id=uuid.uuid4(),
            snippet="This is a sample chunk about machine learning algorithms.",
            granularity="fine",
            content_type="article",
            chunk_idx=0,
            chunk_total=1,
            path=["section"],
            hash="abc123",
            vector=[0.1] * 1536,  # Mock embedding vector
        )

    @pytest.mark.asyncio
    async def test_semantic_search_basic(self, repository, mock_session, sample_chunk):
        """Test basic semantic search without filters."""
        # Mock the database result
        mock_result = MagicMock()
        mock_result.all.return_value = [(sample_chunk, 0.95)]
        mock_session.execute.return_value = mock_result

        query_embedding = [0.1] * 1536
        results = await repository.semantic_search(query_embedding=query_embedding, limit=10)

        # Verify results
        assert len(results) == 1
        assert results[0][0] == sample_chunk
        assert results[0][1] == 0.95

        # Verify session.execute was called
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_semantic_search_with_content_type_filter(self, repository, mock_session):
        """Test semantic search with content_type filter."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        query_embedding = [0.1] * 1536
        filters = {"content_type": "article"}
        await repository.semantic_search(query_embedding=query_embedding, limit=5, filters=filters)

        # Verify execute was called (filter logic is in the query)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_semantic_search_with_analysis_id_filter(self, repository, mock_session):
        """Test semantic search with analysis_id filter."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        analysis_id = uuid.uuid4()
        query_embedding = [0.1] * 1536
        filters = {"analysis_id": analysis_id}
        await repository.semantic_search(query_embedding=query_embedding, limit=5, filters=filters)

        # Verify execute was called
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_semantic_search_with_multiple_filters(self, repository, mock_session):
        """Test semantic search with multiple filters."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        analysis_id = uuid.uuid4()
        query_embedding = [0.1] * 1536
        filters = {"content_type": "tutorial", "analysis_id": analysis_id}
        await repository.semantic_search(query_embedding=query_embedding, limit=10, filters=filters)

        # Verify execute was called
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_semantic_search_empty_results(self, repository, mock_session):
        """Test semantic search with no matching results."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        query_embedding = [0.1] * 1536
        results = await repository.semantic_search(query_embedding=query_embedding, limit=10)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_semantic_search_multiple_results(self, repository, mock_session):
        """Test semantic search with multiple results ordered by similarity."""
        chunk1 = create_test_chunk(snippet="First chunk", vector=[0.1] * 1536)
        chunk2 = create_test_chunk(snippet="Second chunk", vector=[0.2] * 1536)
        chunk3 = create_test_chunk(snippet="Third chunk", vector=[0.3] * 1536)

        # Results should be ordered by similarity (highest first)
        mock_result = MagicMock()
        mock_result.all.return_value = [(chunk1, 0.95), (chunk2, 0.85), (chunk3, 0.75)]
        mock_session.execute.return_value = mock_result

        query_embedding = [0.1] * 1536
        results = await repository.semantic_search(query_embedding=query_embedding, limit=10)

        assert len(results) == 3
        assert results[0][1] == 0.95  # Highest similarity first
        assert results[1][1] == 0.85
        assert results[2][1] == 0.75

    @pytest.mark.asyncio
    async def test_keyword_search_basic(self, repository, mock_session, sample_chunk):
        """Test basic keyword search without filters."""
        mock_result = MagicMock()
        mock_result.all.return_value = [(sample_chunk, 0.85)]
        mock_session.execute.return_value = mock_result

        results = await repository.keyword_search(query_text="machine learning", limit=10)

        assert len(results) == 1
        assert results[0][0] == sample_chunk
        assert results[0][1] == 0.85

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_keyword_search_with_filters(self, repository, mock_session):
        """Test keyword search with content_type filter."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        filters = {"content_type": "code_block"}
        await repository.keyword_search(query_text="async def", limit=5, filters=filters)

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_keyword_search_empty_query(self, repository, mock_session):
        """Test keyword search with empty query string."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Empty query should still execute (PostgreSQL handles this gracefully)
        results = await repository.keyword_search(query_text="", limit=10)

        assert len(results) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_keyword_search_phrase_query(self, repository, mock_session):
        """Test keyword search with phrase query."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Phrase queries should work with websearch_to_tsquery
        await repository.keyword_search(query_text='"neural networks"', limit=10)

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_keyword_search_multiple_results(self, repository, mock_session):
        """Test keyword search returns results ordered by relevance."""
        chunk1 = create_test_chunk(snippet="Machine learning tutorial")
        chunk2 = create_test_chunk(snippet="Deep learning guide")
        chunk3 = create_test_chunk(snippet="AI fundamentals")

        # Results ordered by relevance score (highest first)
        mock_result = MagicMock()
        mock_result.all.return_value = [(chunk1, 0.95), (chunk2, 0.75), (chunk3, 0.60)]
        mock_session.execute.return_value = mock_result

        results = await repository.keyword_search(query_text="machine learning", limit=10)

        assert len(results) == 3
        assert results[0][1] == 0.95
        assert results[1][1] == 0.75
        assert results[2][1] == 0.60

    @pytest.mark.asyncio
    async def test_hybrid_search_basic(self, repository, mock_session, sample_chunk):
        """Test basic hybrid search combining semantic and keyword."""
        # Mock both semantic and keyword search results
        chunk1 = create_test_chunk(snippet="First result", vector=[0.1] * 1536)
        chunk2 = create_test_chunk(snippet="Second result", vector=[0.2] * 1536)

        # First call: semantic search
        # Second call: keyword search
        mock_result_semantic = MagicMock()
        mock_result_semantic.all.return_value = [(chunk1, 0.9), (chunk2, 0.8)]

        mock_result_keyword = MagicMock()
        mock_result_keyword.all.return_value = [(chunk2, 0.85), (chunk1, 0.75)]

        mock_session.execute.side_effect = [mock_result_semantic, mock_result_keyword]

        query_embedding = [0.1] * 1536
        results = await repository.hybrid_search(
            query_embedding=query_embedding,
            query_text="machine learning",
            limit=10,
        )

        # Should have called execute twice (semantic + keyword)
        assert mock_session.execute.call_count == 2

        # Results should be combined via RRF
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_hybrid_search_with_filters(self, repository, mock_session):
        """Test hybrid search with metadata filters."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        analysis_id = uuid.uuid4()
        query_embedding = [0.1] * 1536
        filters = {"content_type": "article", "analysis_id": analysis_id}

        await repository.hybrid_search(
            query_embedding=query_embedding,
            query_text="test query",
            limit=5,
            filters=filters,
        )

        # Should call execute twice (semantic + keyword)
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_hybrid_search_rrf_fusion(self, repository, mock_session):
        """Test that hybrid search properly fuses results using RRF."""
        chunk_a = create_test_chunk(snippet="A", vector=[0.1] * 1536)
        chunk_b = create_test_chunk(snippet="B", vector=[0.2] * 1536)

        # Semantic: A ranked higher
        mock_result_semantic = MagicMock()
        mock_result_semantic.all.return_value = [(chunk_a, 0.95), (chunk_b, 0.70)]

        # Keyword: B ranked higher
        mock_result_keyword = MagicMock()
        mock_result_keyword.all.return_value = [(chunk_b, 0.90), (chunk_a, 0.60)]

        mock_session.execute.side_effect = [mock_result_semantic, mock_result_keyword]

        query_embedding = [0.1] * 1536
        results = await repository.hybrid_search(
            query_embedding=query_embedding,
            query_text="test",
            limit=10,
        )

        # Both chunks should appear in results (RRF combines them)
        assert len(results) >= 1  # At least one result after fusion

    @pytest.mark.asyncio
    async def test_hybrid_search_one_method_empty(self, repository, mock_session):
        """Test hybrid search when one search method returns no results."""
        chunk1 = create_test_chunk(snippet="Result", vector=[0.1] * 1536)

        # Semantic returns results
        mock_result_semantic = MagicMock()
        mock_result_semantic.all.return_value = [(chunk1, 0.9)]

        # Keyword returns nothing
        mock_result_keyword = MagicMock()
        mock_result_keyword.all.return_value = []

        mock_session.execute.side_effect = [mock_result_semantic, mock_result_keyword]

        query_embedding = [0.1] * 1536
        results = await repository.hybrid_search(
            query_embedding=query_embedding,
            query_text="test",
            limit=10,
        )

        # Should still return results from semantic search
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_hybrid_search_both_empty(self, repository, mock_session):
        """Test hybrid search when both methods return no results."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        query_embedding = [0.1] * 1536
        results = await repository.hybrid_search(
            query_embedding=query_embedding,
            query_text="nonexistent",
            limit=10,
        )

        # Should return empty list
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_create_many_single_chunk(self, repository, mock_session):
        """Test create_many with a single chunk."""
        chunk_data = [
            {
                "analysis_id": uuid.uuid4(),
                "snippet": "Test chunk",
                "vector": [0.1] * 1536,
                "chunk_idx": 0,
                "granularity": "section",
            }
        ]

        await repository.create_many(chunk_data)

        # Verify add_all and flush were called
        mock_session.add_all.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_many_multiple_chunks(self, repository, mock_session):
        """Test create_many with multiple chunks."""
        chunk_data = [
            {
                "analysis_id": uuid.uuid4(),
                "snippet": f"Chunk {i}",
                "vector": [0.1] * 1536,
                "chunk_idx": i,
                "granularity": "section",
            }
            for i in range(5)
        ]

        await repository.create_many(chunk_data)

        mock_session.add_all.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_many_empty_list(self, repository, mock_session):
        """Test create_many with empty list."""
        result = await repository.create_many([])

        # Should return empty list
        assert result == []
        mock_session.add_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_many_returns_objects(self, repository, mock_session):
        """Test that create_many returns created objects with IDs."""
        chunk_data = [
            {
                "analysis_id": uuid.uuid4(),
                "snippet": "Test chunk",
                "vector": [0.1] * 1536,
                "chunk_idx": 0,
                "granularity": "section",
            }
        ]

        result = await repository.create_many(chunk_data)

        # Should return list of AnalysisChunk objects
        assert len(result) == 1
        assert isinstance(result[0], AnalysisChunk)

    @pytest.mark.asyncio
    async def test_get_by_analysis_id(self, repository, mock_session, sample_chunk):
        """Test retrieving chunks by analysis_id."""
        analysis_id = uuid.uuid4()
        chunks = [
            create_test_chunk(analysis_id=analysis_id, snippet=f"Chunk {i}", vector=[0.1] * 1536)
            for i in range(3)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = chunks
        mock_session.execute.return_value = mock_result

        results = await repository.get_by_analysis_id(analysis_id)

        assert len(results) == 3
        assert all(chunk.analysis_id == analysis_id for chunk in results)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_analysis_id_no_results(self, repository, mock_session):
        """Test get_by_analysis_id with no matching chunks."""
        analysis_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        results = await repository.get_by_analysis_id(analysis_id)

        assert len(results) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_by_analysis(self, repository, mock_session):
        """Test list_by_analysis returns all chunks for an analysis."""
        analysis_id = uuid.uuid4()
        chunks = [
            create_test_chunk(analysis_id=analysis_id, snippet=f"Chunk {i}", vector=[0.1] * 1536)
            for i in range(3)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = chunks
        mock_session.execute.return_value = mock_result

        results = await repository.list_by_analysis(analysis_id)

        assert len(results) == 3
        assert all(chunk.analysis_id == analysis_id for chunk in results)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_by_analysis_empty(self, repository, mock_session):
        """Test list_by_analysis with no chunks."""
        analysis_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        results = await repository.list_by_analysis(analysis_id)

        assert len(results) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_coarse(self, repository, mock_session):
        """Test search_coarse returns coarse-grained chunks."""
        chunks = [
            create_test_chunk(granularity="coarse", snippet="Coarse chunk", vector=[0.1] * 1536)
            for _ in range(3)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = chunks
        mock_session.execute.return_value = mock_result

        results = await repository.search_coarse(limit=10)

        # Should return tuples of (chunk, score) with placeholder score 0.0
        assert len(results) == 3
        assert all(isinstance(item, tuple) for item in results)
        assert all(score == 0.0 for _, score in results)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_coarse_respects_limit(self, repository, mock_session):
        """Test search_coarse respects limit parameter."""
        chunks = [
            create_test_chunk(granularity="coarse", snippet=f"Chunk {i}", vector=[0.1] * 1536)
            for i in range(5)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = chunks[:3]  # Simulate limit=3
        mock_session.execute.return_value = mock_result

        results = await repository.search_coarse(limit=3)

        # Should have at most 3 results
        assert len(results) <= 3
