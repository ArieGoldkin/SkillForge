"""Unit tests for cleanup service."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.services.cleanup.cleanup_service import CleanupService
from app.shared.services.cleanup.integrity_checks import VectorIntegrityChecker
from app.shared.services.cleanup.orphan_cleanup import OrphanCleaner
from app.shared.services.cleanup.ttl_cleanup import TTLCleaner

@pytest.mark.unit


@pytest.fixture
def mock_session():
    """Mock AsyncSession."""
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def cleanup_service(mock_session):
    """Create CleanupService with mocked session."""
    return CleanupService(mock_session, batch_size=100)


@pytest.fixture
def orphan_cleaner(mock_session):
    """Create OrphanCleaner with mocked session."""
    return OrphanCleaner(mock_session, batch_size=100)


@pytest.fixture
def integrity_checker(mock_session):
    """Create VectorIntegrityChecker with mocked session."""
    return VectorIntegrityChecker(mock_session, batch_size=100)


@pytest.fixture
def ttl_cleaner(mock_session):
    """Create TTLCleaner with mocked session."""
    return TTLCleaner(mock_session, batch_size=100)


class TestOrphanCleaner:
    """Test orphan cleanup functionality."""

    async def test_find_orphans_missing_parent_empty(self, orphan_cleaner, mock_session):
        """Test finding orphans when none exist."""
        # Mock empty result
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        orphan_ids = await orphan_cleaner.find_orphans_missing_parent()

        assert orphan_ids == []
        assert mock_session.execute.called

    async def test_find_orphans_missing_parent_found(self, orphan_cleaner, mock_session):
        """Test finding orphans with missing parent."""
        # Mock result with orphans
        orphan_id1 = uuid.uuid4()
        orphan_id2 = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.all.return_value = [(orphan_id1,), (orphan_id2,)]
        mock_session.execute.return_value = mock_result

        orphan_ids = await orphan_cleaner.find_orphans_missing_parent()

        assert len(orphan_ids) == 2
        assert orphan_id1 in orphan_ids
        assert orphan_id2 in orphan_ids

    async def test_find_orphans_failed_analysis(self, orphan_cleaner, mock_session):
        """Test finding orphans from failed analyses."""
        mock_result = MagicMock()
        mock_result.all.return_value = [(uuid.uuid4(),)]
        mock_session.execute.return_value = mock_result

        orphan_ids = await orphan_cleaner.find_orphans_failed_analysis(failed_threshold_days=7)

        assert len(orphan_ids) == 1
        assert mock_session.execute.called

    async def test_delete_orphans_batch_empty(self, orphan_cleaner):
        """Test delete with empty orphan list."""
        deleted = await orphan_cleaner.delete_orphans_batch([])

        assert deleted == 0

    async def test_delete_orphans_batch_single_batch(self, orphan_cleaner, mock_session):
        """Test delete with single batch."""
        orphan_ids = [uuid.uuid4() for _ in range(50)]

        # Mock delete result
        mock_result = MagicMock()
        mock_result.rowcount = 50
        mock_session.execute.return_value = mock_result

        deleted = await orphan_cleaner.delete_orphans_batch(orphan_ids, hard_delete=True)

        assert deleted == 50
        assert mock_session.execute.called
        assert mock_session.commit.called

    async def test_count_orphans(self, orphan_cleaner, mock_session):
        """Test counting orphans without deletion."""
        # Mock results for each orphan type
        mock_result = MagicMock()
        mock_result.all.return_value = [(uuid.uuid4(),)]
        mock_session.execute.return_value = mock_result

        counts = await orphan_cleaner.count_orphans()

        assert "missing_parent" in counts
        assert "failed_analysis" in counts
        assert "superseded_analysis" in counts
        assert "total" in counts
        assert counts["total"] >= 0


class TestVectorIntegrityChecker:
    """Test vector integrity checks."""

    async def test_check_chunk_vector_dimensions_valid(self, integrity_checker, mock_session):
        """Test dimension check with all valid vectors."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        invalid_ids = await integrity_checker.check_chunk_vector_dimensions()

        assert invalid_ids == []

    async def test_check_chunk_vector_dimensions_invalid(self, integrity_checker, mock_session):
        """Test dimension check with invalid vectors."""
        invalid_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.all.return_value = [(invalid_id,)]
        mock_session.execute.return_value = mock_result

        invalid_ids = await integrity_checker.check_chunk_vector_dimensions()

        assert len(invalid_ids) == 1
        assert invalid_id in invalid_ids

    async def test_check_null_chunk_vectors(self, integrity_checker, mock_session):
        """Test finding chunks with NULL vectors."""
        null_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.all.return_value = [(null_id,)]
        mock_session.execute.return_value = mock_result

        null_ids = await integrity_checker.check_null_chunk_vectors()

        assert len(null_ids) == 1
        assert null_id in null_ids

    async def test_check_invalid_values_empty(self, integrity_checker, mock_session):
        """Test invalid values check with no chunks."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        issues = await integrity_checker.check_invalid_values_in_chunks(check_batch_size=100)

        assert issues == []

    async def test_check_zero_vectors(self, integrity_checker, mock_session):
        """Test finding zero vectors."""
        # Mock chunk with zero vector
        chunk_id = uuid.uuid4()
        zero_vector = [0.0] * 1536

        # First call returns zero vector, second call returns empty (to break loop)
        first_result = MagicMock()
        first_result.all.return_value = [(chunk_id, zero_vector)]
        empty_result = MagicMock()
        empty_result.all.return_value = []

        mock_session.execute.side_effect = [first_result, empty_result]

        zero_ids = await integrity_checker.check_zero_vectors_in_chunks()

        assert len(zero_ids) == 1
        assert chunk_id in zero_ids


class TestTTLCleaner:
    """Test TTL-based cleanup."""

    def test_set_ttl_policy(self, ttl_cleaner):
        """Test setting custom TTL policy."""
        ttl_cleaner.set_ttl_policy("draft", 14)

        assert ttl_cleaner.ttl_policies["draft"] == 14

    def test_set_ttl_policy_remove(self, ttl_cleaner):
        """Test removing TTL policy."""
        ttl_cleaner.set_ttl_policy("draft", None)

        assert "draft" not in ttl_cleaner.ttl_policies

    async def test_find_expired_analyses_empty(self, ttl_cleaner, mock_session):
        """Test finding expired analyses when none exist."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        expired = await ttl_cleaner.find_expired_analyses()

        assert expired == []

    async def test_find_expired_analyses_found(self, ttl_cleaner, mock_session):
        """Test finding expired analyses."""
        analysis_id = uuid.uuid4()
        old_date = datetime.now(UTC) - timedelta(days=30)
        mock_result = MagicMock()
        mock_result.all.return_value = [(analysis_id, "draft", old_date)]
        mock_session.execute.return_value = mock_result

        expired = await ttl_cleaner.find_expired_analyses(status="draft")

        assert len(expired) == 1
        assert expired[0][0] == analysis_id
        assert expired[0][1] == "draft"

    async def test_count_expired_by_status(self, ttl_cleaner, mock_session):
        """Test counting expired analyses by status."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        mock_session.execute.return_value = mock_result

        counts = await ttl_cleaner.count_expired_by_status()

        assert "total" in counts
        assert counts["total"] >= 0

    async def test_get_ttl_status_report(self, ttl_cleaner, mock_session):
        """Test generating TTL status report."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        report = await ttl_cleaner.get_ttl_status_report()

        assert "policies" in report
        assert "expired_counts" in report
        assert "timestamp" in report


class TestCleanupService:
    """Test main cleanup service orchestration."""

    async def test_health_check_healthy(self, cleanup_service, mock_session):
        """Test health check when system is healthy."""
        # Mock all counts as zero
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_result.scalar_one.return_value = 0
        mock_session.execute.return_value = mock_result

        health = await cleanup_service.health_check()

        assert "healthy" in health
        assert "total_issues" in health
        assert "orphan_chunks" in health
        assert "expired_analyses" in health
        assert "integrity_issues" in health

    async def test_health_check_unhealthy(self, cleanup_service, mock_session):
        """Test health check when issues exist."""
        # Mock database to return orphans for count
        orphan_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.all.return_value = [(orphan_id,)]
        mock_result.scalar_one.return_value = 1

        # Create empty result for all the batch iteration checks
        empty_result = MagicMock()
        empty_result.all.return_value = []
        empty_result.scalar_one.return_value = 0

        # Use a generator that returns mock_result once, then empty_result forever
        def infinite_results():
            yield mock_result  # First call finds orphan
            while True:
                yield empty_result  # All subsequent calls return empty

        mock_session.execute.side_effect = infinite_results()

        health = await cleanup_service.health_check()

        assert "healthy" in health
        assert "total_issues" in health

    async def test_run_full_cleanup_dry_run(self, cleanup_service, mock_session):
        """Test full cleanup in dry run mode."""
        # Mock empty results
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_result.scalar_one.return_value = 0
        mock_session.execute.return_value = mock_result

        result = await cleanup_service.run_full_cleanup(dry_run=True)

        assert "summary" in result
        assert result["summary"]["dry_run"] is True
        assert not mock_session.commit.called  # No commits in dry run

    async def test_schedule_cleanup_health(self, cleanup_service, mock_session):
        """Test scheduled cleanup with health check type."""
        # Mock empty results
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_result.scalar_one.return_value = 0
        mock_session.execute.return_value = mock_result

        result = await cleanup_service.schedule_cleanup(cleanup_type="health")

        assert "health_check" in result

    async def test_schedule_cleanup_invalid_type(self, cleanup_service):
        """Test scheduled cleanup with invalid type."""
        result = await cleanup_service.schedule_cleanup(cleanup_type="invalid")

        assert "error" in result


class TestIntegration:
    """Integration tests for cleanup workflow."""

    async def test_full_cleanup_workflow(self, cleanup_service, mock_session):
        """Test complete cleanup workflow."""
        # Mock all operations as successful but empty
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_result.scalar_one.return_value = 0
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        # Run full cleanup
        result = await cleanup_service.run_full_cleanup(
            include_orphans=True,
            include_expired=True,
            include_superseded=False,
            hard_delete=False,
            dry_run=False,
        )

        # Verify structure
        assert "orphan_cleanup" in result
        assert "ttl_cleanup" in result
        assert "integrity_checks" in result
        assert "summary" in result

        # Verify summary
        summary = result["summary"]
        assert "dry_run" in summary
        assert summary["dry_run"] is False
        assert "total_items_affected" in summary
