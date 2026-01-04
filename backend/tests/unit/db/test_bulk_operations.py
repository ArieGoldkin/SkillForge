"""Unit tests for BulkOperations using asyncpg COPY protocol."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.bulk_operations import BulkOperations


@pytest.mark.unit
class TestBulkOperations:
    """Test cases for BulkOperations class."""

    @pytest.fixture
    def mock_engine(self):
        """Create mock async engine with raw_connection support."""
        engine = AsyncMock()

        # Mock the asyncpg connection
        mock_asyncpg_conn = AsyncMock()
        mock_asyncpg_conn.copy_records_to_table = AsyncMock()

        # Mock the raw connection wrapper
        mock_raw_conn = AsyncMock()
        # driver_connection is an async property/coroutine in the real implementation
        mock_raw_conn.driver_connection = mock_asyncpg_conn

        # Mock the context manager
        # raw_connection() returns a context manager directly (sync, not async)
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_raw_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        engine.raw_connection = MagicMock(return_value=mock_context)

        # Store reference for tests to access
        engine._test_conn = mock_asyncpg_conn
        engine._test_raw_conn = mock_raw_conn

        return engine

    @pytest.fixture
    def bulk_ops(self, mock_engine):
        """Create BulkOperations instance with mock engine."""
        return BulkOperations(mock_engine)

    @pytest.fixture
    def sample_chunks(self):
        """Create sample chunk data for testing."""
        analysis_id = uuid.uuid4()
        return [
            {
                "analysis_id": analysis_id,
                "granularity": "fine",
                "path": ["intro", "overview"],
                "chunk_idx": 0,
                "chunk_total": 3,
                "hash": "hash1",
                "vector": [0.1] * 1536,
                "snippet": "First chunk content",
                "section_title": "Introduction",
                "content_type": "article",
                "language": "en",
                "model": "text-embedding-3-small",
                "model_version": "v1",
                "token_count": 100,
                "embedding_latency_ms": 50.5,
                "was_truncated": False,
                "pii_flag": False,
                "pii_types": None,
            },
            {
                "analysis_id": analysis_id,
                "granularity": "fine",
                "path": ["intro", "details"],
                "chunk_idx": 1,
                "chunk_total": 3,
                "hash": "hash2",
                "vector": [0.2] * 1536,
                "snippet": "Second chunk content",
                "section_title": "Details",
                "content_type": "article",
                "language": "en",
                "model": "text-embedding-3-small",
                "model_version": "v1",
                "token_count": 150,
                "embedding_latency_ms": 55.2,
                "was_truncated": False,
                "pii_flag": True,
                "pii_types": ["email"],
            },
        ]

    @pytest.fixture
    def sample_analyses(self):
        """Create sample analysis data for testing."""
        return [
            {
                "url": "https://example.com/article1",
                "content_type": "article",
                "title": "Test Article 1",
                "raw_content": "Article content here...",
                "content_embedding": [0.1] * 1536,
                "extraction_metadata": {"source": "web", "extracted_at": "2025-01-01"},
                "status": "completed",
                "content_summary": "This is a summary",
                "content_sections": {"sections": ["intro", "body"]},
                "retry_count": 0,
                "rerun_count": 0,
            },
            {
                "url": "https://example.com/article2",
                "content_type": "video",
                "title": "Test Video 1",
                "raw_content": None,
                "content_embedding": None,
                "extraction_metadata": None,
                "status": "pending",
                "content_summary": None,
                "content_sections": {},
                "retry_count": 0,
                "rerun_count": 0,
            },
        ]

    @pytest.fixture
    def sample_artifacts(self):
        """Create sample artifact data for testing."""
        analysis_id = uuid.uuid4()
        return [
            {
                "analysis_id": analysis_id,
                "markdown_content": "# Implementation Guide\n\nContent here...",
                "version": 1,
                "artifact_metadata": {"generated_by": "agent", "quality_score": 0.95},
                "download_count": 0,
                "trace_id": "langfuse-trace-123",
                "is_deleted": False,
                "deleted_at": None,
            },
            {
                "analysis_id": analysis_id,
                "markdown_content": "# Tutorial\n\nTutorial content...",
                "version": 2,
                "artifact_metadata": None,
                "download_count": 5,
                "trace_id": None,
                "is_deleted": False,
                "deleted_at": None,
            },
        ]

    @pytest.mark.asyncio
    async def test_bulk_insert_chunks_success(self, bulk_ops, mock_engine, sample_chunks):
        """Test successful bulk insertion of chunks."""
        result = await bulk_ops.bulk_insert_chunks(sample_chunks)

        # Verify result structure
        assert isinstance(result, dict)
        assert result["rows_inserted"] == 2
        assert result["table_name"] == "analysis_chunks"
        assert result["duration_ms"] > 0

        # Verify copy_records_to_table was called with correct arguments
        conn = mock_engine._test_conn
        conn.copy_records_to_table.assert_called_once()

        # Verify the call arguments
        call_args = conn.copy_records_to_table.call_args
        # call_args.args[0] is table name, kwargs contains records and columns
        assert call_args.args[0] == "analysis_chunks"
        assert len(call_args.kwargs["records"]) == 2

        # Verify columns are specified correctly
        expected_columns = [
            "analysis_id",
            "granularity",
            "path",
            "section_title",
            "chunk_idx",
            "chunk_total",
            "content_type",
            "language",
            "hash",
            "model",
            "model_version",
            "snippet",
            "vector",
            "token_count",
            "embedding_latency_ms",
            "was_truncated",
            "pii_flag",
            "pii_types",
        ]
        assert call_args.kwargs["columns"] == expected_columns

    @pytest.mark.asyncio
    async def test_bulk_insert_chunks_empty_list(self, bulk_ops):
        """Test that empty chunk list raises ValueError."""
        with pytest.raises(ValueError, match="chunks sequence cannot be empty"):
            await bulk_ops.bulk_insert_chunks([])

    @pytest.mark.asyncio
    async def test_bulk_insert_chunks_vector_conversion(self, bulk_ops, mock_engine):
        """Test that vector lists are properly converted to string format."""
        chunks = [
            {
                "analysis_id": uuid.uuid4(),
                "granularity": "fine",
                "path": ["test"],
                "chunk_idx": 0,
                "chunk_total": 1,
                "hash": "hash1",
                "vector": [0.1, 0.2, 0.3],  # Small vector for testing
                "snippet": "Test",
            }
        ]

        await bulk_ops.bulk_insert_chunks(chunks)

        # Get the records that were passed to copy_records_to_table
        conn = mock_engine._test_conn
        call_args = conn.copy_records_to_table.call_args
        records = call_args.kwargs["records"]

        # Verify vector was converted to string
        # The vector is the 13th element in the tuple (index 12)
        vector_str = records[0][12]
        assert isinstance(vector_str, str)
        assert "[0.1, 0.2, 0.3]" in vector_str

    @pytest.mark.asyncio
    async def test_bulk_insert_chunks_jsonb_conversion(self, bulk_ops, mock_engine):
        """Test that JSONB fields (path, pii_types) are properly converted."""
        chunks = [
            {
                "analysis_id": uuid.uuid4(),
                "granularity": "fine",
                "path": ["section", "subsection"],
                "chunk_idx": 0,
                "chunk_total": 1,
                "hash": "hash1",
                "vector": [0.1] * 1536,
                "pii_types": ["email", "phone"],
            }
        ]

        await bulk_ops.bulk_insert_chunks(chunks)

        conn = mock_engine._test_conn
        call_args = conn.copy_records_to_table.call_args
        records = call_args.kwargs["records"]

        # Verify path was converted to JSON (index 2)
        path_json = records[0][2]
        assert isinstance(path_json, str)
        assert '"section"' in path_json
        assert '"subsection"' in path_json

        # Verify pii_types was converted to JSON (index 17)
        pii_types_json = records[0][17]
        assert isinstance(pii_types_json, str)
        assert '"email"' in pii_types_json
        assert '"phone"' in pii_types_json

    @pytest.mark.asyncio
    async def test_bulk_insert_analyses_success(self, bulk_ops, mock_engine, sample_analyses):
        """Test successful bulk insertion of analyses."""
        result = await bulk_ops.bulk_insert_analyses(sample_analyses)

        # Verify result structure
        assert isinstance(result, dict)
        assert result["rows_inserted"] == 2
        assert result["table_name"] == "analyses"
        assert result["duration_ms"] > 0

        # Verify copy_records_to_table was called
        conn = mock_engine._test_conn
        conn.copy_records_to_table.assert_called_once()

        call_args = conn.copy_records_to_table.call_args
        assert call_args.args[0] == "analyses"
        assert len(call_args.kwargs["records"]) == 2

    @pytest.mark.asyncio
    async def test_bulk_insert_analyses_empty_list(self, bulk_ops):
        """Test that empty analyses list raises ValueError."""
        with pytest.raises(ValueError, match="analyses sequence cannot be empty"):
            await bulk_ops.bulk_insert_analyses([])

    @pytest.mark.asyncio
    async def test_bulk_insert_analyses_handles_nulls(self, bulk_ops, mock_engine):
        """Test that None values in analyses are handled correctly."""
        analyses = [
            {
                "url": "https://example.com/test",
                "content_type": "article",
                "title": None,
                "raw_content": None,
                "content_embedding": None,
                "extraction_metadata": None,
                "status": "pending",
            }
        ]

        await bulk_ops.bulk_insert_analyses(analyses)

        conn = mock_engine._test_conn
        call_args = conn.copy_records_to_table.call_args
        records = call_args.kwargs["records"]

        # Verify None values are preserved
        record = records[0]
        assert record[2] is None  # title
        assert record[3] is None  # raw_content
        assert record[4] is None  # content_embedding (as string)
        assert record[5] is None  # extraction_metadata

    @pytest.mark.asyncio
    async def test_bulk_insert_artifacts_success(self, bulk_ops, mock_engine, sample_artifacts):
        """Test successful bulk insertion of artifacts."""
        result = await bulk_ops.bulk_insert_artifacts(sample_artifacts)

        # Verify result structure
        assert isinstance(result, dict)
        assert result["rows_inserted"] == 2
        assert result["table_name"] == "artifacts"
        assert result["duration_ms"] > 0

        # Verify copy_records_to_table was called
        conn = mock_engine._test_conn
        conn.copy_records_to_table.assert_called_once()

        call_args = conn.copy_records_to_table.call_args
        assert call_args.args[0] == "artifacts"
        assert len(call_args.kwargs["records"]) == 2

    @pytest.mark.asyncio
    async def test_bulk_insert_artifacts_empty_list(self, bulk_ops):
        """Test that empty artifacts list raises ValueError."""
        with pytest.raises(ValueError, match="artifacts sequence cannot be empty"):
            await bulk_ops.bulk_insert_artifacts([])

    @pytest.mark.asyncio
    async def test_bulk_insert_artifacts_metadata_conversion(self, bulk_ops, mock_engine):
        """Test that artifact metadata JSONB is properly converted."""
        artifacts = [
            {
                "analysis_id": uuid.uuid4(),
                "markdown_content": "# Test",
                "version": 1,
                "artifact_metadata": {"key": "value", "score": 0.95},
            }
        ]

        await bulk_ops.bulk_insert_artifacts(artifacts)

        conn = mock_engine._test_conn
        call_args = conn.copy_records_to_table.call_args
        records = call_args.kwargs["records"]

        # Verify metadata was converted to JSON (index 3)
        metadata_json = records[0][3]
        assert isinstance(metadata_json, str)
        assert '"key"' in metadata_json
        assert '"value"' in metadata_json

    @pytest.mark.asyncio
    async def test_bulk_operations_performance_tracking(self, bulk_ops, mock_engine):
        """Test that all bulk operations track duration_ms."""
        chunks = [
            {
                "analysis_id": uuid.uuid4(),
                "granularity": "fine",
                "path": ["test"],
                "chunk_idx": 0,
                "chunk_total": 1,
                "hash": "hash1",
                "vector": [0.1] * 1536,
            }
        ]

        # Mock time.perf_counter to simulate elapsed time
        with patch("app.db.bulk_operations.time.perf_counter") as mock_time:
            mock_time.side_effect = [0.0, 0.05]  # 50ms elapsed
            result = await bulk_ops.bulk_insert_chunks(chunks)

        # Verify duration was calculated correctly
        assert result["duration_ms"] == 50.0

    @pytest.mark.asyncio
    async def test_result_type_dict_structure(self, bulk_ops, mock_engine):
        """Test that BulkInsertResult has correct TypedDict structure."""
        chunks = [
            {
                "analysis_id": uuid.uuid4(),
                "granularity": "fine",
                "path": ["test"],
                "chunk_idx": 0,
                "chunk_total": 1,
                "hash": "hash1",
                "vector": [0.1] * 1536,
            }
        ]

        result = await bulk_ops.bulk_insert_chunks(chunks)

        # Verify all required keys are present
        assert "rows_inserted" in result
        assert "duration_ms" in result
        assert "table_name" in result

        # Verify types
        assert isinstance(result["rows_inserted"], int)
        assert isinstance(result["duration_ms"], float)
        assert isinstance(result["table_name"], str)
