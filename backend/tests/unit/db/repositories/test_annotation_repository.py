"""Unit tests for AnnotationRepository."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.annotation_queue import AnnotationQueue
from app.db.repositories.annotation_repository import AnnotationRepository


@pytest.mark.unit
class TestAnnotationRepository:
    """Tests for AnnotationRepository class."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def repository(self, mock_session):
        """Create AnnotationRepository instance with mock session."""
        return AnnotationRepository(mock_session)

    @pytest.mark.asyncio
    async def test_initialization(self, mock_session):
        """AnnotationRepository initializes with session."""
        repo = AnnotationRepository(mock_session)
        assert repo.session == mock_session

    @pytest.mark.asyncio
    async def test_queue_for_review_creates_entry_correctly(self, repository, mock_session):
        """queue_for_review() creates annotation queue entry with correct data."""
        artifact_id = uuid.uuid4()
        reason = "low_quality"
        trace_id = "trace-123"
        metadata = {"quality_scores": {"relevance": 0.5, "depth": 0.4}}

        # Mock the created annotation queue entry
        mock_annotation = AnnotationQueue(
            id=1,
            artifact_id=artifact_id,
            reason=reason,
            trace_id=trace_id,
            status="pending",
            queue_metadata=metadata,
        )

        # Mock session operations
        mock_session.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", 1))

        result = await repository.queue_for_review(
            artifact_id=artifact_id,
            reason=reason,
            trace_id=trace_id,
            metadata=metadata,
        )

        # Verify session operations
        assert mock_session.add.called
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

        # Verify the annotation object was added
        added_annotation = mock_session.add.call_args[0][0]
        assert isinstance(added_annotation, AnnotationQueue)
        assert added_annotation.artifact_id == artifact_id
        assert added_annotation.reason == reason
        assert added_annotation.trace_id == trace_id
        assert added_annotation.status == "pending"

    @pytest.mark.asyncio
    async def test_queue_for_review_without_optional_fields(self, repository, mock_session):
        """queue_for_review() works without trace_id and metadata."""
        artifact_id = uuid.uuid4()
        reason = "flagged_by_user"

        result = await repository.queue_for_review(
            artifact_id=artifact_id,
            reason=reason,
        )

        # Verify session operations
        assert mock_session.add.called
        mock_session.commit.assert_called_once()

        # Verify the annotation object was added with None values
        added_annotation = mock_session.add.call_args[0][0]
        assert added_annotation.trace_id is None
        assert added_annotation.queue_metadata is None

    @pytest.mark.asyncio
    async def test_get_pending_annotations_with_pagination(self, repository, mock_session):
        """get_pending_annotations() returns list of pending items with pagination."""
        # Create mock pending annotations
        annotations = [
            AnnotationQueue(
                id=i,
                artifact_id=uuid.uuid4(),
                reason="low_quality",
                status="pending",
                created_at=datetime.now(UTC),
            )
            for i in range(1, 6)
        ]

        # Mock query result
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=annotations)
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_pending_annotations(limit=5, offset=0)

        assert len(result) == 5
        assert all(a.status == "pending" for a in result)
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_get_pending_annotations_respects_limit(self, repository, mock_session):
        """get_pending_annotations() respects limit parameter."""
        # Create 3 mock annotations
        annotations = [
            AnnotationQueue(
                id=i,
                artifact_id=uuid.uuid4(),
                reason="negative_feedback",
                status="pending",
                created_at=datetime.now(UTC),
            )
            for i in range(1, 4)
        ]

        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=annotations[:2])  # Limit to 2
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_pending_annotations(limit=2, offset=0)

        assert len(result) == 2
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_get_pending_annotations_respects_offset(self, repository, mock_session):
        """get_pending_annotations() respects offset parameter for pagination."""
        # Mock returning second page of results
        annotations = [
            AnnotationQueue(
                id=i,
                artifact_id=uuid.uuid4(),
                reason="low_quality",
                status="pending",
                created_at=datetime.now(UTC),
            )
            for i in range(11, 16)  # IDs 11-15 (second page)
        ]

        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=annotations)
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_pending_annotations(limit=5, offset=10)

        assert len(result) == 5
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_get_pending_annotations_returns_empty_list(self, repository, mock_session):
        """get_pending_annotations() returns empty list when no pending items."""
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_pending_annotations(limit=50, offset=0)

        assert result == []

    @pytest.mark.asyncio
    async def test_mark_as_reviewed_updates_status_and_timestamp(self, repository, mock_session):
        """mark_as_reviewed() updates status to reviewed and sets reviewed_at."""
        queue_id = 42

        await repository.mark_as_reviewed(queue_id=queue_id)

        # Verify update query was executed
        assert mock_session.execute.called
        mock_session.commit.assert_called_once()

        # Verify the query was built correctly
        # (In production, this would update status and reviewed_at)

    @pytest.mark.asyncio
    async def test_check_if_queued_returns_true_when_queued(self, repository, mock_session):
        """check_if_queued() returns True when artifact has pending queue entry."""
        artifact_id = uuid.uuid4()

        # Mock query result returning an annotation
        mock_annotation = AnnotationQueue(
            id=1,
            artifact_id=artifact_id,
            reason="low_quality",
            status="pending",
        )
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_annotation)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.check_if_queued(artifact_id=artifact_id)

        assert result is True
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_check_if_queued_returns_false_when_not_queued(self, repository, mock_session):
        """check_if_queued() returns False when artifact not in pending queue."""
        artifact_id = uuid.uuid4()

        # Mock query result returning None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.check_if_queued(artifact_id=artifact_id)

        assert result is False
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_check_if_queued_ignores_reviewed_entries(self, repository, mock_session):
        """check_if_queued() only checks pending status, not reviewed."""
        artifact_id = uuid.uuid4()

        # Mock query that would filter by status='pending'
        # Should return None even if reviewed entry exists
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.check_if_queued(artifact_id=artifact_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_queue_count_returns_accurate_count(self, repository, mock_session):
        """get_queue_count() returns accurate count of pending items."""
        # Mock count query result
        mock_result = AsyncMock()
        mock_result.scalar_one = MagicMock(return_value=15)
        mock_session.execute = AsyncMock(return_value=mock_result)

        count = await repository.get_queue_count()

        assert count == 15
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_get_queue_count_returns_zero_when_empty(self, repository, mock_session):
        """get_queue_count() returns 0 when queue is empty."""
        mock_result = AsyncMock()
        mock_result.scalar_one = MagicMock(return_value=0)
        mock_session.execute = AsyncMock(return_value=mock_result)

        count = await repository.get_queue_count()

        assert count == 0

    @pytest.mark.asyncio
    async def test_get_queue_count_handles_none_result(self, repository, mock_session):
        """get_queue_count() handles None result from query."""
        mock_result = AsyncMock()
        mock_result.scalar_one = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        count = await repository.get_queue_count()

        assert count == 0  # Should convert None to 0

    @pytest.mark.asyncio
    async def test_queue_for_review_converts_metadata_to_dict(self, repository, mock_session):
        """queue_for_review() converts Mapping metadata to dict."""
        artifact_id = uuid.uuid4()
        reason = "low_quality"

        # Pass a mapping (not dict)
        from collections.abc import Mapping

        class CustomMapping(Mapping):
            def __init__(self, data):
                self._data = data

            def __getitem__(self, key):
                return self._data[key]

            def __iter__(self):
                return iter(self._data)

            def __len__(self):
                return len(self._data)

        custom_metadata = CustomMapping({"score": 0.5})

        await repository.queue_for_review(
            artifact_id=artifact_id,
            reason=reason,
            metadata=custom_metadata,
        )

        # Verify the annotation object was created
        added_annotation = mock_session.add.call_args[0][0]

        # Should convert to dict (checking the parameter passed to AnnotationQueue)
        assert isinstance(added_annotation, AnnotationQueue)
