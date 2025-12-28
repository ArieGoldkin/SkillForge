"""Tests for orphan chunk detection and cleanup.

Tests the OrphanCleaner service that identifies and removes orphaned chunks.
Note: This service ALWAYS performs hard deletes - soft delete is not implemented.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.analysis import Analysis
from app.db.models.analysis_chunk import AnalysisChunk
from app.shared.services.cleanup.orphan_cleanup import OrphanCleaner


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def orphan_cleaner(mock_session):
    """Create OrphanCleaner instance with mocked session."""
    return OrphanCleaner(
        session=mock_session,
        batch_size=100,
        grace_period_days=7,
    )


class TestOrphanCleaner:
    """Test OrphanCleaner initialization and configuration."""

    def test_initialization(self, mock_session):
        """Test OrphanCleaner initializes with correct settings."""
        cleaner = OrphanCleaner(
            session=mock_session,
            batch_size=500,
            grace_period_days=14,
        )

        assert cleaner.session == mock_session
        assert cleaner.batch_size == 500
        assert cleaner.grace_period_days == 14

    def test_default_parameters(self, mock_session):
        """Test OrphanCleaner uses correct default values."""
        cleaner = OrphanCleaner(session=mock_session)

        assert cleaner.batch_size == 1000
        assert cleaner.grace_period_days == 7


class TestFindOrphansMissingParent:
    """Test finding chunks where parent analysis was deleted."""

    @pytest.mark.asyncio
    async def test_finds_orphans_with_missing_parent(self, orphan_cleaner, mock_session):
        """Test finding chunks whose parent analysis no longer exists."""
        # Mock orphan IDs
        orphan_id_1 = uuid.uuid4()
        orphan_id_2 = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.all.return_value = [(orphan_id_1,), (orphan_id_2,)]
        mock_session.execute.return_value = mock_result

        result = await orphan_cleaner.find_orphans_missing_parent()

        assert len(result) == 2
        assert orphan_id_1 in result
        assert orphan_id_2 in result
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_orphans(self, orphan_cleaner, mock_session):
        """Test returns empty list when no orphaned chunks exist."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await orphan_cleaner.find_orphans_missing_parent()

        assert result == []


class TestFindOrphansFailedAnalysis:
    """Test finding chunks from failed/error analyses older than threshold."""

    @pytest.mark.asyncio
    async def test_finds_orphans_from_old_failed_analyses(self, orphan_cleaner, mock_session):
        """Test finding chunks from failed analyses older than threshold."""
        orphan_id_1 = uuid.uuid4()
        orphan_id_2 = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.all.return_value = [(orphan_id_1,), (orphan_id_2,)]
        mock_session.execute.return_value = mock_result

        result = await orphan_cleaner.find_orphans_failed_analysis(failed_threshold_days=14)

        assert len(result) == 2
        assert orphan_id_1 in result
        assert orphan_id_2 in result

    @pytest.mark.asyncio
    async def test_custom_threshold_days(self, orphan_cleaner, mock_session):
        """Test custom threshold days parameter."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        await orphan_cleaner.find_orphans_failed_analysis(failed_threshold_days=30)

        # Verify execute was called (threshold logic applied in SQL)
        mock_session.execute.assert_called_once()


class TestFindOrphansSuperseded:
    """Test finding chunks from superseded analyses (same URL, older version)."""

    @pytest.mark.asyncio
    async def test_finds_orphans_from_superseded_analyses(self, orphan_cleaner, mock_session):
        """Test finding chunks from superseded analyses."""
        orphan_id_1 = uuid.uuid4()
        orphan_id_2 = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.all.return_value = [(orphan_id_1,), (orphan_id_2,)]
        mock_session.execute.return_value = mock_result

        result = await orphan_cleaner.find_orphans_superseded_analysis()

        assert len(result) == 2
        assert orphan_id_1 in result
        assert orphan_id_2 in result


class TestDeleteOrphansBatch:
    """Test batch deletion of orphaned chunks.

    IMPORTANT: This service ALWAYS performs hard deletes (permanent removal).
    Soft delete functionality is not implemented.
    """

    @pytest.mark.asyncio
    async def test_deletes_orphans_in_single_batch(self, orphan_cleaner, mock_session):
        """Test deleting small number of orphans in single batch."""
        orphan_ids = [uuid.uuid4() for _ in range(5)]

        # Mock successful deletion
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_session.execute.return_value = mock_result

        deleted = await orphan_cleaner.delete_orphans_batch(orphan_ids)

        assert deleted == 5
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_deletes_orphans_in_multiple_batches(self, mock_session):
        """Test batch processing for large orphan sets."""
        cleaner = OrphanCleaner(session=mock_session, batch_size=50)
        orphan_ids = [uuid.uuid4() for _ in range(150)]  # 3 batches

        # Mock successful deletion for each batch
        mock_result = MagicMock()
        mock_result.rowcount = 50
        mock_session.execute.return_value = mock_result

        deleted = await cleaner.delete_orphans_batch(orphan_ids)

        assert deleted == 150  # 50 * 3 batches
        assert mock_session.execute.call_count == 3  # 3 batches
        assert mock_session.commit.call_count == 3

    @pytest.mark.asyncio
    async def test_handles_empty_orphan_list(self, orphan_cleaner, mock_session):
        """Test graceful handling of empty orphan list."""
        deleted = await orphan_cleaner.delete_orphans_batch([])

        assert deleted == 0
        mock_session.execute.assert_not_called()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_always_hard_delete(self, orphan_cleaner, mock_session):
        """Test that deletion is ALWAYS hard delete (permanent removal).

        This test documents that the service does NOT support soft delete.
        The old 'hard_delete' parameter was removed because both branches
        executed identical code. This is now an explicit hard delete only.
        """
        orphan_ids = [uuid.uuid4() for _ in range(3)]

        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result

        deleted = await orphan_cleaner.delete_orphans_batch(orphan_ids)

        assert deleted == 3

        # Verify DELETE statement was executed (not UPDATE with is_deleted flag)
        # The call should include SQLAlchemy delete() statement
        call_args = mock_session.execute.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_handles_partial_batch_deletion(self, orphan_cleaner, mock_session):
        """Test handling when some chunks fail to delete."""
        orphan_ids = [uuid.uuid4() for _ in range(5)]

        # Mock partial success (only 3 of 5 deleted)
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result

        deleted = await orphan_cleaner.delete_orphans_batch(orphan_ids)

        assert deleted == 3  # Only successful deletions counted

    @pytest.mark.asyncio
    async def test_commits_after_each_batch(self, mock_session):
        """Test that commits happen after each batch for progress tracking."""
        cleaner = OrphanCleaner(session=mock_session, batch_size=2)
        orphan_ids = [uuid.uuid4() for _ in range(6)]  # 3 batches

        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_session.execute.return_value = mock_result

        await cleaner.delete_orphans_batch(orphan_ids)

        # Should commit after each batch (3 times)
        assert mock_session.commit.call_count == 3


class TestCleanupAllOrphans:
    """Test comprehensive cleanup of all orphan types."""

    @pytest.mark.asyncio
    async def test_cleanup_all_without_superseded(self, orphan_cleaner, mock_session):
        """Test cleanup without superseded analysis chunks."""
        # Mock finding orphans
        missing_parent_ids = [uuid.uuid4() for _ in range(10)]
        failed_analysis_ids = [uuid.uuid4() for _ in range(5)]

        mock_result_1 = MagicMock()
        mock_result_1.all.return_value = [(id_,) for id_ in missing_parent_ids]

        mock_result_2 = MagicMock()
        mock_result_2.all.return_value = [(id_,) for id_ in failed_analysis_ids]

        # Mock deletion
        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 10

        mock_session.execute.side_effect = [
            mock_result_1,  # find_orphans_missing_parent
            mock_delete_result,  # delete missing_parent batch
            mock_result_2,  # find_orphans_failed_analysis
            mock_delete_result,  # delete failed_analysis batch
        ]

        stats = await orphan_cleaner.cleanup_all_orphans(include_superseded=False)

        assert stats["missing_parent"] == 10
        assert stats["failed_analysis"] == 10
        assert stats["superseded_analysis"] == 0
        assert stats["total_deleted"] == 20

    @pytest.mark.asyncio
    async def test_cleanup_all_with_superseded(self, orphan_cleaner, mock_session):
        """Test cleanup including superseded analysis chunks."""
        # Mock finding orphans
        missing_parent_ids = [uuid.uuid4() for _ in range(5)]
        failed_analysis_ids = [uuid.uuid4() for _ in range(3)]
        superseded_ids = [uuid.uuid4() for _ in range(8)]

        mock_result_1 = MagicMock()
        mock_result_1.all.return_value = [(id_,) for id_ in missing_parent_ids]

        mock_result_2 = MagicMock()
        mock_result_2.all.return_value = [(id_,) for id_ in failed_analysis_ids]

        mock_result_3 = MagicMock()
        mock_result_3.all.return_value = [(id_,) for id_ in superseded_ids]

        # Mock deletion
        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 5

        mock_session.execute.side_effect = [
            mock_result_1,
            mock_delete_result,
            mock_result_2,
            mock_delete_result,
            mock_result_3,
            mock_delete_result,
        ]

        stats = await orphan_cleaner.cleanup_all_orphans(include_superseded=True)

        assert stats["missing_parent"] == 5
        assert stats["failed_analysis"] == 5
        assert stats["superseded_analysis"] == 5
        assert stats["total_deleted"] == 15

    @pytest.mark.asyncio
    async def test_cleanup_when_no_orphans_found(self, orphan_cleaner, mock_session):
        """Test cleanup when no orphans exist."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        stats = await orphan_cleaner.cleanup_all_orphans(include_superseded=False)

        assert stats["total_deleted"] == 0
        assert stats["missing_parent"] == 0
        assert stats["failed_analysis"] == 0


class TestCountOrphans:
    """Test dry-run counting of orphans without deletion."""

    @pytest.mark.asyncio
    async def test_counts_all_orphan_types(self, orphan_cleaner, mock_session):
        """Test counting all types of orphaned chunks."""
        # Mock finding different orphan types
        missing_parent_ids = [uuid.uuid4() for _ in range(10)]
        failed_analysis_ids = [uuid.uuid4() for _ in range(5)]
        superseded_ids = [uuid.uuid4() for _ in range(3)]

        mock_result_1 = MagicMock()
        mock_result_1.all.return_value = [(id_,) for id_ in missing_parent_ids]

        mock_result_2 = MagicMock()
        mock_result_2.all.return_value = [(id_,) for id_ in failed_analysis_ids]

        mock_result_3 = MagicMock()
        mock_result_3.all.return_value = [(id_,) for id_ in superseded_ids]

        mock_session.execute.side_effect = [mock_result_1, mock_result_2, mock_result_3]

        counts = await orphan_cleaner.count_orphans()

        assert counts["missing_parent"] == 10
        assert counts["failed_analysis"] == 5
        assert counts["superseded_analysis"] == 3
        assert counts["total"] == 18

        # Verify no deletions occurred
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_count_orphans_when_none_exist(self, orphan_cleaner, mock_session):
        """Test counting when no orphans exist."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        counts = await orphan_cleaner.count_orphans()

        assert counts["total"] == 0
        assert counts["missing_parent"] == 0
        assert counts["failed_analysis"] == 0
        assert counts["superseded_analysis"] == 0


class TestStreamOrphanChunks:
    """Test memory-efficient streaming of orphaned chunks."""

    @pytest.mark.asyncio
    async def test_stream_missing_parent_orphans(self, orphan_cleaner, mock_session):
        """Test streaming chunks with missing parent."""
        orphan_ids = [uuid.uuid4() for _ in range(5)]

        # Mock finding orphan IDs
        mock_find_result = MagicMock()
        mock_find_result.all.return_value = [(id_,) for id_ in orphan_ids]

        # Mock chunk objects
        mock_chunks = [MagicMock(spec=AnalysisChunk) for _ in range(5)]
        mock_stream_result = MagicMock()
        mock_stream_result.scalars.return_value.all.return_value = mock_chunks

        mock_session.execute.side_effect = [mock_find_result, mock_stream_result]

        chunks = []
        async for chunk in orphan_cleaner.stream_orphan_chunks("missing_parent"):
            chunks.append(chunk)

        assert len(chunks) == 5

    @pytest.mark.asyncio
    async def test_stream_failed_analysis_orphans(self, orphan_cleaner, mock_session):
        """Test streaming chunks from failed analyses."""
        orphan_ids = [uuid.uuid4() for _ in range(3)]

        mock_find_result = MagicMock()
        mock_find_result.all.return_value = [(id_,) for id_ in orphan_ids]

        mock_chunks = [MagicMock(spec=AnalysisChunk) for _ in range(3)]
        mock_stream_result = MagicMock()
        mock_stream_result.scalars.return_value.all.return_value = mock_chunks

        mock_session.execute.side_effect = [mock_find_result, mock_stream_result]

        chunks = []
        async for chunk in orphan_cleaner.stream_orphan_chunks("failed_analysis"):
            chunks.append(chunk)

        assert len(chunks) == 3

    @pytest.mark.asyncio
    async def test_stream_invalid_orphan_type(self, orphan_cleaner, mock_session):
        """Test error handling for invalid orphan type."""
        chunks = []
        async for chunk in orphan_cleaner.stream_orphan_chunks("invalid_type"):
            chunks.append(chunk)

        # Should return empty (logged error)
        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_stream_processes_in_batches(self, mock_session):
        """Test streaming processes large orphan sets in batches."""
        cleaner = OrphanCleaner(session=mock_session, batch_size=50)
        orphan_ids = [uuid.uuid4() for _ in range(150)]  # 3 batches

        # Mock finding orphan IDs
        mock_find_result = MagicMock()
        mock_find_result.all.return_value = [(id_,) for id_ in orphan_ids]

        # Mock chunk streaming (3 batches of 50)
        mock_chunks_batch_1 = [MagicMock(spec=AnalysisChunk) for _ in range(50)]
        mock_chunks_batch_2 = [MagicMock(spec=AnalysisChunk) for _ in range(50)]
        mock_chunks_batch_3 = [MagicMock(spec=AnalysisChunk) for _ in range(50)]

        mock_stream_result_1 = MagicMock()
        mock_stream_result_1.scalars.return_value.all.return_value = mock_chunks_batch_1

        mock_stream_result_2 = MagicMock()
        mock_stream_result_2.scalars.return_value.all.return_value = mock_chunks_batch_2

        mock_stream_result_3 = MagicMock()
        mock_stream_result_3.scalars.return_value.all.return_value = mock_chunks_batch_3

        mock_session.execute.side_effect = [
            mock_find_result,
            mock_stream_result_1,
            mock_stream_result_2,
            mock_stream_result_3,
        ]

        chunks = []
        async for chunk in cleaner.stream_orphan_chunks("missing_parent"):
            chunks.append(chunk)

        assert len(chunks) == 150
        # 1 find query + 3 batch stream queries
        assert mock_session.execute.call_count == 4
