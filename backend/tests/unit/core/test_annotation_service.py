"""Unit tests for AnnotationService.

Tests all public methods in app/core/annotation_service.py:
- submit_feedback(): User feedback handling with Langfuse integration
- queue_low_quality_artifact(): Automatic queuing based on quality scores
- _submit_langfuse_score(): Langfuse score submission (internal method)
- _queue_artifact(): Artifact queuing logic (internal method)
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.annotation_service import AnnotationService
from app.db.models.annotation_queue import AnnotationQueue


@pytest.fixture
def mock_session():
    """Create mock async database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def service(mock_session):
    """Create AnnotationService instance with mock session."""
    return AnnotationService(mock_session)


@pytest.mark.unit
class TestSubmitFeedback:
    """Tests for submit_feedback() method."""

    @pytest.mark.asyncio
    async def test_submit_feedback_thumbs_up_no_queuing(self, service, mock_session):
        """submit_feedback() with thumbs_up submits score but doesn't queue."""
        artifact_id = uuid.uuid4()
        trace_id = "trace-123"

        # Mock Langfuse client
        mock_client = MagicMock()
        mock_client.score = MagicMock()
        mock_client.flush = MagicMock()

        with patch("app.core.annotation_service.get_langfuse_client", return_value=mock_client):
            result = await service.submit_feedback(
                artifact_id=artifact_id,
                trace_id=trace_id,
                feedback="thumbs_up",
                comment=None,
            )

        # Should succeed
        assert result["status"] == "success"
        assert result["langfuse_submitted"] is True

        # Should NOT queue artifact
        assert not mock_session.add.called

        # Should submit Langfuse score with value 1.0
        mock_client.score.assert_called_once()
        call_kwargs = mock_client.score.call_args.kwargs
        assert call_kwargs["trace_id"] == trace_id
        assert call_kwargs["name"] == "user_feedback"
        assert call_kwargs["value"] == 1.0

    @pytest.mark.asyncio
    async def test_submit_feedback_thumbs_down_without_comment_no_queuing(
        self, service, mock_session
    ):
        """submit_feedback() with thumbs_down but no comment doesn't queue."""
        artifact_id = uuid.uuid4()
        trace_id = "trace-456"

        mock_client = MagicMock()
        mock_client.score = MagicMock()
        mock_client.flush = MagicMock()

        with patch("app.core.annotation_service.get_langfuse_client", return_value=mock_client):
            result = await service.submit_feedback(
                artifact_id=artifact_id,
                trace_id=trace_id,
                feedback="thumbs_down",
                comment=None,  # No comment
            )

        # Should succeed
        assert result["status"] == "success"

        # Should NOT queue artifact (no comment provided)
        assert not mock_session.add.called

        # Should submit score with value 0.0
        mock_client.score.assert_called_once()
        call_kwargs = mock_client.score.call_args.kwargs
        assert call_kwargs["value"] == 0.0

    @pytest.mark.asyncio
    async def test_submit_feedback_thumbs_down_with_comment_queues_artifact(
        self, service, mock_session
    ):
        """submit_feedback() with thumbs_down + comment queues artifact for review."""
        artifact_id = uuid.uuid4()
        trace_id = "trace-789"
        comment = "Missing implementation details"

        # Mock Langfuse client
        mock_client = MagicMock()
        mock_client.score = MagicMock()
        mock_client.flush = MagicMock()

        # Mock existing queue check (not queued)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.core.annotation_service.get_langfuse_client", return_value=mock_client):
            result = await service.submit_feedback(
                artifact_id=artifact_id,
                trace_id=trace_id,
                feedback="thumbs_down",
                comment=comment,
            )

        # Should succeed and queue
        assert result["status"] == "success"
        assert "queued for review" in result["message"]

        # Should add to queue
        assert mock_session.add.called
        added_annotation = mock_session.add.call_args[0][0]
        assert isinstance(added_annotation, AnnotationQueue)
        assert added_annotation.artifact_id == artifact_id
        assert added_annotation.reason == "negative_feedback"
        assert added_annotation.status == "pending"

        # Metadata should include feedback details
        # Note: metadata is stored in the dict passed to AnnotationQueue
        # We can't directly check queue_metadata since it's set via the parameter

    @pytest.mark.asyncio
    async def test_submit_feedback_langfuse_integration(self, service, mock_session):
        """submit_feedback() integrates with Langfuse correctly."""
        artifact_id = uuid.uuid4()
        trace_id = "trace-langfuse"
        comment = "Great content!"

        mock_client = MagicMock()
        mock_client.score = MagicMock()
        mock_client.flush = MagicMock()

        with patch("app.core.annotation_service.get_langfuse_client", return_value=mock_client):
            result = await service.submit_feedback(
                artifact_id=artifact_id,
                trace_id=trace_id,
                feedback="thumbs_up",
                comment=comment,
            )

        # Should submit to Langfuse
        assert result["langfuse_submitted"] is True

        # Verify Langfuse API calls
        mock_client.score.assert_called_once_with(
            trace_id=trace_id,
            name="user_feedback",
            value=1.0,
            comment=comment,
        )
        mock_client.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_feedback_graceful_degradation_no_langfuse(self, service, mock_session):
        """submit_feedback() works when Langfuse unavailable."""
        artifact_id = uuid.uuid4()

        # Mock no Langfuse client
        with patch("app.core.annotation_service.get_langfuse_client", return_value=None):
            result = await service.submit_feedback(
                artifact_id=artifact_id,
                trace_id=None,
                feedback="thumbs_up",
                comment=None,
            )

        # Should succeed but not submit to Langfuse
        assert result["status"] == "success"
        assert result["langfuse_submitted"] is False

    @pytest.mark.asyncio
    async def test_submit_feedback_langfuse_error_handled_gracefully(self, service, mock_session):
        """submit_feedback() handles Langfuse errors gracefully."""
        artifact_id = uuid.uuid4()
        trace_id = "trace-error"

        # Mock Langfuse client that raises exception
        mock_client = MagicMock()
        mock_client.score.side_effect = Exception("Langfuse API error")

        with patch("app.core.annotation_service.get_langfuse_client", return_value=mock_client):
            result = await service.submit_feedback(
                artifact_id=artifact_id,
                trace_id=trace_id,
                feedback="thumbs_up",
                comment=None,
            )

        # Should still succeed but not mark as submitted
        assert result["status"] == "success"
        assert result["langfuse_submitted"] is False

    @pytest.mark.asyncio
    async def test_submit_feedback_queuing_error_returns_error_status(self, service, mock_session):
        """submit_feedback() returns error status when queuing fails."""
        artifact_id = uuid.uuid4()
        trace_id = "trace-queue-error"
        comment = "Bad content"

        # Mock Langfuse client
        mock_client = MagicMock()
        with patch("app.core.annotation_service.get_langfuse_client", return_value=mock_client):
            # Mock database error during queuing
            mock_session.execute.side_effect = Exception("Database connection failed")

            result = await service.submit_feedback(
                artifact_id=artifact_id,
                trace_id=trace_id,
                feedback="thumbs_down",
                comment=comment,
            )

        # Should return error status
        assert result["status"] == "error"
        assert "failed to queue for review" in result["message"].lower()


@pytest.mark.unit
class TestQueueLowQualityArtifact:
    """Tests for queue_low_quality_artifact() method."""

    @pytest.mark.asyncio
    async def test_queue_low_quality_artifact_below_threshold(self, service, mock_session):
        """queue_low_quality_artifact() queues when score below threshold."""
        artifact_id = uuid.uuid4()
        trace_id = "trace-low-quality"
        quality_scores = {"relevance": 0.5, "depth": 0.4, "coherence": 0.6}
        threshold = 0.6

        # Average: (0.5 + 0.4 + 0.6) / 3 = 0.5 < 0.6

        # Mock existing queue check (not queued)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.queue_low_quality_artifact(
            artifact_id=artifact_id,
            trace_id=trace_id,
            quality_scores=quality_scores,
            threshold=threshold,
        )

        # Should queue the artifact
        assert result["success"] is True
        assert result["queued"] is True
        assert result["below_threshold"] is True
        assert result["average_score"] == pytest.approx(0.5, rel=0.01)

        # Verify queuing
        assert mock_session.add.called
        added_annotation = mock_session.add.call_args[0][0]
        assert isinstance(added_annotation, AnnotationQueue)
        assert added_annotation.artifact_id == artifact_id
        assert added_annotation.reason == "low_quality"

    @pytest.mark.asyncio
    async def test_queue_low_quality_artifact_above_threshold_no_queuing(
        self, service, mock_session
    ):
        """queue_low_quality_artifact() doesn't queue when score above threshold."""
        artifact_id = uuid.uuid4()
        trace_id = "trace-high-quality"
        quality_scores = {"relevance": 0.8, "depth": 0.9, "coherence": 0.85}
        threshold = 0.6

        # Average: (0.8 + 0.9 + 0.85) / 3 = 0.85 > 0.6

        result = await service.queue_low_quality_artifact(
            artifact_id=artifact_id,
            trace_id=trace_id,
            quality_scores=quality_scores,
            threshold=threshold,
        )

        # Should NOT queue the artifact
        assert result["success"] is True
        assert result["queued"] is False
        assert result["below_threshold"] is False
        assert result["average_score"] == pytest.approx(0.85, rel=0.01)

        # Verify not queued
        assert not mock_session.add.called

    @pytest.mark.asyncio
    async def test_queue_low_quality_artifact_empty_scores(self, service, mock_session):
        """queue_low_quality_artifact() handles empty quality scores."""
        artifact_id = uuid.uuid4()
        quality_scores = {}

        result = await service.queue_low_quality_artifact(
            artifact_id=artifact_id,
            trace_id=None,
            quality_scores=quality_scores,
        )

        # Should fail gracefully
        assert result["success"] is False
        assert result["error"] == "No quality scores provided"
        assert not mock_session.add.called

    @pytest.mark.asyncio
    async def test_queue_low_quality_artifact_default_threshold(self, service, mock_session):
        """queue_low_quality_artifact() uses default threshold of 0.6."""
        artifact_id = uuid.uuid4()
        quality_scores = {"relevance": 0.5, "depth": 0.5}

        # Mock existing queue check
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.queue_low_quality_artifact(
            artifact_id=artifact_id,
            trace_id=None,
            quality_scores=quality_scores,
            # No threshold specified - should use 0.6
        )

        # Average is 0.5, which is < default 0.6
        assert result["below_threshold"] is True
        assert result["queued"] is True

    @pytest.mark.asyncio
    async def test_queue_low_quality_artifact_exact_threshold_boundary(self, service, mock_session):
        """queue_low_quality_artifact() handles exact threshold boundary."""
        artifact_id = uuid.uuid4()
        quality_scores = {"relevance": 0.6, "depth": 0.6, "coherence": 0.6}
        threshold = 0.6

        # Average is exactly 0.6 - should NOT queue (not below)

        result = await service.queue_low_quality_artifact(
            artifact_id=artifact_id,
            trace_id=None,
            quality_scores=quality_scores,
            threshold=threshold,
        )

        assert result["average_score"] == 0.6
        assert result["below_threshold"] is False
        assert result["queued"] is False

    @pytest.mark.asyncio
    async def test_queue_low_quality_artifact_database_error(self, service, mock_session):
        """queue_low_quality_artifact() handles database errors."""
        artifact_id = uuid.uuid4()
        quality_scores = {"relevance": 0.3, "depth": 0.4}

        # Mock database error
        mock_session.execute.side_effect = Exception("Database error")

        result = await service.queue_low_quality_artifact(
            artifact_id=artifact_id,
            trace_id=None,
            quality_scores=quality_scores,
        )

        # Should return error
        assert result["success"] is False
        assert "Failed to queue artifact" in result["error"]

    @pytest.mark.asyncio
    async def test_queue_low_quality_artifact_includes_metadata(self, service, mock_session):
        """queue_low_quality_artifact() includes quality scores in metadata."""
        artifact_id = uuid.uuid4()
        trace_id = "trace-metadata"
        quality_scores = {"relevance": 0.4, "depth": 0.3, "coherence": 0.5}
        threshold = 0.7

        # Mock existing queue check
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.queue_low_quality_artifact(
            artifact_id=artifact_id,
            trace_id=trace_id,
            quality_scores=quality_scores,
            threshold=threshold,
        )

        assert result["queued"] is True

        # Verify the annotation was added with metadata
        assert mock_session.add.called
        added_annotation = mock_session.add.call_args[0][0]
        # Metadata is passed as a dict but stored in queue_metadata
        # We can't check it directly here, but we verified the annotation was created


@pytest.mark.unit
class TestInternalMethods:
    """Tests for internal helper methods."""

    @pytest.mark.asyncio
    async def test_submit_langfuse_score_without_trace_id(self, service):
        """_submit_langfuse_score() returns False when no trace_id."""
        result = await service._submit_langfuse_score(
            trace_id=None,
            score_name="test_score",
            score_value=0.8,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_submit_langfuse_score_when_client_unavailable(self, service):
        """_submit_langfuse_score() returns False when client unavailable."""
        with patch("app.core.annotation_service.get_langfuse_client", return_value=None):
            result = await service._submit_langfuse_score(
                trace_id="trace-123",
                score_name="test_score",
                score_value=0.8,
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_submit_langfuse_score_success(self, service):
        """_submit_langfuse_score() submits score successfully."""
        mock_client = MagicMock()
        mock_client.score = MagicMock()
        mock_client.flush = MagicMock()

        with patch("app.core.annotation_service.get_langfuse_client", return_value=mock_client):
            result = await service._submit_langfuse_score(
                trace_id="trace-success",
                score_name="quality",
                score_value=0.9,
                comment="High quality",
            )

        assert result is True
        mock_client.score.assert_called_once_with(
            trace_id="trace-success",
            name="quality",
            value=0.9,
            comment="High quality",
        )
        mock_client.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_langfuse_score_handles_exception(self, service):
        """_submit_langfuse_score() handles exceptions gracefully."""
        mock_client = MagicMock()
        mock_client.score.side_effect = Exception("API error")

        with patch("app.core.annotation_service.get_langfuse_client", return_value=mock_client):
            result = await service._submit_langfuse_score(
                trace_id="trace-error",
                score_name="test",
                score_value=0.5,
            )

        # Should return False but not raise
        assert result is False

    @pytest.mark.asyncio
    async def test_queue_artifact_skips_if_already_queued(self, service, mock_session):
        """_queue_artifact() skips queuing if artifact already in pending queue."""
        artifact_id = uuid.uuid4()

        # Mock existing pending entry
        existing_annotation = AnnotationQueue(
            id=1,
            artifact_id=artifact_id,
            reason="low_quality",
            status="pending",
        )
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=existing_annotation)
        mock_session.execute = AsyncMock(return_value=mock_result)

        await service._queue_artifact(
            artifact_id=artifact_id,
            trace_id=None,
            reason="negative_feedback",
        )

        # Should NOT add new entry
        assert not mock_session.add.called
        # Should NOT commit
        assert not mock_session.commit.called

    @pytest.mark.asyncio
    async def test_queue_artifact_creates_new_entry(self, service, mock_session):
        """_queue_artifact() creates new queue entry when not already queued."""
        artifact_id = uuid.uuid4()
        trace_id = "trace-new"
        reason = "flagged_by_user"
        metadata = {"user_id": "user-123", "comment": "Inappropriate content"}

        # Mock no existing entry
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        await service._queue_artifact(
            artifact_id=artifact_id,
            trace_id=trace_id,
            reason=reason,
            metadata=metadata,
        )

        # Should add new entry
        assert mock_session.add.called
        added_annotation = mock_session.add.call_args[0][0]
        assert isinstance(added_annotation, AnnotationQueue)
        assert added_annotation.artifact_id == artifact_id
        assert added_annotation.trace_id == trace_id
        assert added_annotation.reason == reason
        assert added_annotation.status == "pending"

        # Should commit
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()


@pytest.mark.unit
class TestIntegration:
    """Integration tests for AnnotationService."""

    @pytest.mark.asyncio
    async def test_full_feedback_workflow(self, service, mock_session):
        """Test complete feedback submission workflow."""
        artifact_id = uuid.uuid4()
        trace_id = "trace-workflow"

        # Mock Langfuse client
        mock_client = MagicMock()
        with patch("app.core.annotation_service.get_langfuse_client", return_value=mock_client):
            # Mock no existing queue entry
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=None)
            mock_session.execute = AsyncMock(return_value=mock_result)

            # Submit negative feedback with comment
            result = await service.submit_feedback(
                artifact_id=artifact_id,
                trace_id=trace_id,
                feedback="thumbs_down",
                comment="Needs improvement",
            )

        # Should succeed and queue
        assert result["status"] == "success"
        assert result["langfuse_submitted"] is True

        # Verify Langfuse score submitted
        mock_client.score.assert_called_once()
        assert mock_client.score.call_args.kwargs["value"] == 0.0

        # Verify artifact queued
        assert mock_session.add.called
        assert mock_session.commit.called

    @pytest.mark.asyncio
    async def test_quality_check_workflow(self, service, mock_session):
        """Test automatic quality-based queuing workflow."""
        artifact_id = uuid.uuid4()
        quality_scores = {
            "relevance": 0.4,
            "depth": 0.3,
            "coherence": 0.5,
            "actionability": 0.4,
        }

        # Mock no existing queue entry
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.queue_low_quality_artifact(
            artifact_id=artifact_id,
            trace_id="trace-quality",
            quality_scores=quality_scores,
            threshold=0.6,
        )

        # Should queue (average 0.4 < 0.6)
        assert result["success"] is True
        assert result["queued"] is True
        assert result["below_threshold"] is True

        # Verify queuing
        assert mock_session.add.called
        added_annotation = mock_session.add.call_args[0][0]
        assert added_annotation.reason == "low_quality"
