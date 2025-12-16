"""Unit tests for SSE helpers in tutor workflow."""

from unittest.mock import AsyncMock, patch

import pytest

from app.domains.tutor.workflows.nodes.sse_helpers import emit_tutor_event

@pytest.mark.unit


class TestEmitTutorEvent:
    """Tests for emit_tutor_event function."""

    @pytest.mark.asyncio
    @patch("app.domains.tutor.workflows.nodes.sse_helpers.broadcaster")
    async def test_emit_event_publishes_to_correct_channel(self, mock_broadcaster):
        """Test that event is published to correct channel."""
        mock_broadcaster.publish = AsyncMock()
        session_id = "test-session-123"

        await emit_tutor_event(
            session_id=session_id,
            event_type="progress",
            stage="syllabus",
            status="started",
        )

        # Verify channel is tutor:{session_id}
        call_args = mock_broadcaster.publish.call_args
        assert call_args[0][0] == f"tutor:{session_id}"

    @pytest.mark.asyncio
    @patch("app.domains.tutor.workflows.nodes.sse_helpers.broadcaster")
    async def test_emit_event_includes_required_fields(self, mock_broadcaster):
        """Test that event data includes all required fields."""
        mock_broadcaster.publish = AsyncMock()

        await emit_tutor_event(
            session_id="test-123",
            event_type="chunk",
            stage="lesson",
            status="in_progress",
        )

        event_data = mock_broadcaster.publish.call_args[0][1]
        assert event_data["type"] == "chunk"
        assert event_data["session_id"] == "test-123"
        assert event_data["stage"] == "lesson"
        assert event_data["status"] == "in_progress"
        assert "timestamp" in event_data

    @pytest.mark.asyncio
    @patch("app.domains.tutor.workflows.nodes.sse_helpers.broadcaster")
    async def test_emit_event_includes_extra_kwargs(self, mock_broadcaster):
        """Test that extra kwargs are included in event data."""
        mock_broadcaster.publish = AsyncMock()

        await emit_tutor_event(
            session_id="test-123",
            event_type="done",
            stage="review",
            status="completed",
            content="Test content",
            score=0.85,
        )

        event_data = mock_broadcaster.publish.call_args[0][1]
        assert event_data["content"] == "Test content"
        assert event_data["score"] == 0.85

    @pytest.mark.asyncio
    @patch("app.domains.tutor.workflows.nodes.sse_helpers.broadcaster")
    async def test_emit_event_timestamp_format(self, mock_broadcaster):
        """Test that timestamp is in ISO format."""
        mock_broadcaster.publish = AsyncMock()

        await emit_tutor_event(
            session_id="test-123",
            event_type="progress",
            stage="test",
            status="ok",
        )

        event_data = mock_broadcaster.publish.call_args[0][1]
        timestamp = event_data["timestamp"]
        # ISO format should contain T separator
        assert "T" in timestamp

    @pytest.mark.asyncio
    @patch("app.domains.tutor.workflows.nodes.sse_helpers.broadcaster")
    async def test_emit_error_event(self, mock_broadcaster):
        """Test emitting an error event."""
        mock_broadcaster.publish = AsyncMock()

        await emit_tutor_event(
            session_id="test-123",
            event_type="error",
            stage="lesson",
            status="failed",
            error_message="Something went wrong",
        )

        event_data = mock_broadcaster.publish.call_args[0][1]
        assert event_data["type"] == "error"
        assert event_data["status"] == "failed"
        assert event_data["error_message"] == "Something went wrong"
