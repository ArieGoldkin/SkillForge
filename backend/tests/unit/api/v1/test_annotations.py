"""Unit tests for annotation API endpoints.

Tests all endpoints in app/api/v1/annotations.py:
- POST /annotations/feedback: Submit user feedback
- POST /annotations/flag: Flag artifact for manual review
- GET /annotations/queue: Retrieve pending annotations with pagination
- PATCH /annotations/queue/{queue_id}/reviewed: Mark as reviewed
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.annotations import router
from app.core.annotation_service import get_annotation_service
from app.db.models.annotation_queue import AnnotationQueue
from app.db.repositories.annotation_repository import get_annotation_repository
from app.db.repositories.artifact_repository import get_artifact_repository


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def mock_service():
    """Create mock annotation service."""
    return AsyncMock()


@pytest.fixture
def mock_repository():
    """Create mock annotation repository."""
    return AsyncMock()


@pytest.fixture
def mock_artifact_repository():
    """Create mock artifact repository for trace_id lookup."""
    return AsyncMock()


@pytest.fixture
def client(app, mock_service, mock_repository, mock_artifact_repository):
    """Create test client with mocked dependencies."""
    app.dependency_overrides[get_annotation_service] = lambda: mock_service
    app.dependency_overrides[get_annotation_repository] = lambda: mock_repository
    app.dependency_overrides[get_artifact_repository] = lambda: mock_artifact_repository
    return TestClient(app)


@pytest.mark.unit
class TestSubmitFeedback:
    """Tests for POST /annotations/feedback endpoint."""

    def test_submit_feedback_success(self, client, mock_service):
        """Test successful feedback submission."""
        artifact_id = uuid4()
        trace_id = "trace-123"

        mock_service.submit_feedback.return_value = {
            "status": "success",
            "message": "Feedback submitted successfully",
            "langfuse_submitted": True,
        }

        response = client.post(
            "/api/v1/annotations/feedback",
            json={
                "artifact_id": str(artifact_id),
                "trace_id": trace_id,
                "feedback": "thumbs_up",
                "comment": None,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["langfuse_submitted"] is True

        # Verify service was called correctly
        mock_service.submit_feedback.assert_called_once()
        call_kwargs = mock_service.submit_feedback.call_args.kwargs
        assert call_kwargs["artifact_id"] == artifact_id
        assert call_kwargs["trace_id"] == trace_id
        assert call_kwargs["feedback"] == "thumbs_up"
        assert call_kwargs["comment"] is None

    def test_submit_feedback_with_comment(self, client, mock_service):
        """Test feedback submission with comment."""
        artifact_id = uuid4()

        mock_service.submit_feedback.return_value = {
            "status": "success",
            "message": "Feedback submitted successfully - queued for review",
            "langfuse_submitted": True,
        }

        response = client.post(
            "/api/v1/annotations/feedback",
            json={
                "artifact_id": str(artifact_id),
                "trace_id": None,
                "feedback": "thumbs_down",
                "comment": "Missing implementation details",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Verify comment was passed
        call_kwargs = mock_service.submit_feedback.call_args.kwargs
        assert call_kwargs["comment"] == "Missing implementation details"

    def test_submit_feedback_invalid_feedback_type(self, client, mock_service):
        """Test feedback submission with invalid feedback type."""
        artifact_id = uuid4()

        response = client.post(
            "/api/v1/annotations/feedback",
            json={
                "artifact_id": str(artifact_id),
                "trace_id": None,
                "feedback": "invalid_type",  # Not thumbs_up or thumbs_down
            },
        )

        # Should return 422 validation error
        assert response.status_code == 422

    def test_submit_feedback_missing_artifact_id(self, client, mock_service):
        """Test feedback submission without artifact_id."""
        response = client.post(
            "/api/v1/annotations/feedback",
            json={
                "feedback": "thumbs_up",
            },
        )

        # Should return 422 validation error
        assert response.status_code == 422

    def test_submit_feedback_comment_too_long(self, client, mock_service):
        """Test feedback submission with comment exceeding max length."""
        artifact_id = uuid4()

        response = client.post(
            "/api/v1/annotations/feedback",
            json={
                "artifact_id": str(artifact_id),
                "feedback": "thumbs_down",
                "comment": "x" * 1001,  # Exceeds 1000 char limit
            },
        )

        # Should return 422 validation error
        assert response.status_code == 422

    def test_submit_feedback_service_error(self, client, mock_service):
        """Test handling of service errors."""
        artifact_id = uuid4()

        mock_service.submit_feedback.side_effect = Exception("Service error")

        response = client.post(
            "/api/v1/annotations/feedback",
            json={
                "artifact_id": str(artifact_id),
                "feedback": "thumbs_up",
            },
        )

        # Should return 500 error
        assert response.status_code == 500
        assert "Failed to submit feedback" in response.json()["detail"]

    def test_submit_feedback_without_trace_id_looks_up_artifact(
        self, client, mock_service, mock_artifact_repository
    ):
        """Test feedback submission looks up artifact's trace_id when not provided."""
        artifact_id = uuid4()
        artifact_trace_id = "trace-from-artifact-abc123"

        # Mock artifact with trace_id
        mock_artifact = MagicMock()
        mock_artifact.trace_id = artifact_trace_id
        mock_artifact_repository.get_artifact_by_id.return_value = mock_artifact

        mock_service.submit_feedback.return_value = {
            "status": "success",
            "message": "Feedback submitted successfully",
            "langfuse_submitted": True,
        }

        response = client.post(
            "/api/v1/annotations/feedback",
            json={
                "artifact_id": str(artifact_id),
                "feedback": "thumbs_up",
            },
        )

        assert response.status_code == 200

        # Verify artifact repository was called to lookup trace_id
        mock_artifact_repository.get_artifact_by_id.assert_called_once_with(artifact_id)

        # Verify service received the artifact's trace_id
        call_kwargs = mock_service.submit_feedback.call_args.kwargs
        assert call_kwargs["trace_id"] == artifact_trace_id

    def test_submit_feedback_without_trace_id_artifact_not_found(
        self, client, mock_service, mock_artifact_repository
    ):
        """Test feedback submission when artifact not found uses None for trace_id."""
        artifact_id = uuid4()

        # Mock artifact not found
        mock_artifact_repository.get_artifact_by_id.return_value = None

        mock_service.submit_feedback.return_value = {
            "status": "success",
            "message": "Feedback submitted successfully",
            "langfuse_submitted": False,
        }

        response = client.post(
            "/api/v1/annotations/feedback",
            json={
                "artifact_id": str(artifact_id),
                "feedback": "thumbs_up",
            },
        )

        assert response.status_code == 200

        # Verify artifact repository was called
        mock_artifact_repository.get_artifact_by_id.assert_called_once_with(artifact_id)

        # Verify service received None for trace_id
        call_kwargs = mock_service.submit_feedback.call_args.kwargs
        assert call_kwargs["trace_id"] is None

    def test_submit_feedback_with_explicit_trace_id_skips_lookup(
        self, client, mock_service, mock_artifact_repository
    ):
        """Test feedback submission with explicit trace_id skips artifact lookup."""
        artifact_id = uuid4()
        explicit_trace_id = "explicit-trace-xyz"

        mock_service.submit_feedback.return_value = {
            "status": "success",
            "message": "Feedback submitted successfully",
            "langfuse_submitted": True,
        }

        response = client.post(
            "/api/v1/annotations/feedback",
            json={
                "artifact_id": str(artifact_id),
                "trace_id": explicit_trace_id,
                "feedback": "thumbs_down",
            },
        )

        assert response.status_code == 200

        # Verify artifact repository was NOT called (explicit trace_id provided)
        mock_artifact_repository.get_artifact_by_id.assert_not_called()

        # Verify service received the explicit trace_id
        call_kwargs = mock_service.submit_feedback.call_args.kwargs
        assert call_kwargs["trace_id"] == explicit_trace_id


@pytest.mark.unit
class TestFlagForReview:
    """Tests for POST /annotations/flag endpoint."""

    def test_flag_for_review_success(self, client, mock_repository):
        """Test successful artifact flagging."""
        artifact_id = uuid4()

        # Mock repository responses
        mock_repository.check_if_queued.return_value = False
        mock_queue_entry = MagicMock()
        mock_queue_entry.id = 42
        mock_repository.queue_for_review.return_value = mock_queue_entry

        response = client.post(
            "/api/v1/annotations/flag",
            json={
                "artifact_id": str(artifact_id),
                "reason": "Contains outdated information that needs review",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["queue_id"] == 42
        assert data["message"] == "Artifact flagged for review"

        # Verify repository calls
        mock_repository.check_if_queued.assert_called_once_with(artifact_id=artifact_id)
        mock_repository.queue_for_review.assert_called_once_with(
            artifact_id=artifact_id,
            reason="flagged_by_user",
            metadata={"user_reason": "Contains outdated information that needs review"},
        )

    def test_flag_for_review_already_queued_returns_409(self, client, mock_repository):
        """Test flagging when artifact already queued returns conflict."""
        artifact_id = uuid4()

        # Mock artifact already queued
        mock_repository.check_if_queued.return_value = True

        response = client.post(
            "/api/v1/annotations/flag",
            json={
                "artifact_id": str(artifact_id),
                "reason": "Needs review",
            },
        )

        assert response.status_code == 409
        assert "already queued" in response.json()["detail"]
        assert str(artifact_id) in response.json()["detail"]

        # Should not attempt to queue
        mock_repository.queue_for_review.assert_not_called()

    def test_flag_for_review_reason_too_short(self, client, mock_repository):
        """Test flagging with reason below minimum length."""
        artifact_id = uuid4()

        response = client.post(
            "/api/v1/annotations/flag",
            json={
                "artifact_id": str(artifact_id),
                "reason": "short",  # Less than 10 chars
            },
        )

        # Should return 422 validation error
        assert response.status_code == 422

    def test_flag_for_review_reason_too_long(self, client, mock_repository):
        """Test flagging with reason exceeding maximum length."""
        artifact_id = uuid4()

        response = client.post(
            "/api/v1/annotations/flag",
            json={
                "artifact_id": str(artifact_id),
                "reason": "x" * 501,  # Exceeds 500 char limit
            },
        )

        # Should return 422 validation error
        assert response.status_code == 422

    def test_flag_for_review_missing_reason(self, client, mock_repository):
        """Test flagging without reason."""
        artifact_id = uuid4()

        response = client.post(
            "/api/v1/annotations/flag",
            json={
                "artifact_id": str(artifact_id),
            },
        )

        # Should return 422 validation error
        assert response.status_code == 422

    def test_flag_for_review_repository_error(self, client, mock_repository):
        """Test handling of repository errors."""
        artifact_id = uuid4()

        mock_repository.check_if_queued.return_value = False
        mock_repository.queue_for_review.side_effect = Exception("Database error")

        response = client.post(
            "/api/v1/annotations/flag",
            json={
                "artifact_id": str(artifact_id),
                "reason": "Valid reason for flagging",
            },
        )

        # Should return 500 error
        assert response.status_code == 500
        assert "Failed to flag artifact" in response.json()["detail"]


@pytest.mark.unit
class TestGetAnnotationQueue:
    """Tests for GET /annotations/queue endpoint."""

    def test_get_annotation_queue_success(self, client, mock_repository):
        """Test successful queue retrieval with pagination."""
        # Create mock queue entries
        queue_entries = [
            AnnotationQueue(
                id=i,
                artifact_id=uuid4(),
                trace_id=f"trace-{i}",
                reason="low_quality",
                status="pending",
                queue_metadata={"score": 0.5},
                created_at=datetime.now(UTC),
                reviewed_at=None,
            )
            for i in range(1, 6)
        ]

        mock_repository.get_pending_annotations.return_value = queue_entries
        mock_repository.get_queue_count.return_value = 15

        response = client.get("/api/v1/annotations/queue?limit=5&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["total"] == 15
        assert data["limit"] == 5
        assert data["offset"] == 0

        # Verify all fields are present in items
        first_item = data["items"][0]
        assert "id" in first_item
        assert "artifact_id" in first_item
        assert "trace_id" in first_item
        assert "reason" in first_item
        assert "status" in first_item
        assert "metadata" in first_item
        assert "created_at" in first_item
        assert "reviewed_at" in first_item

    def test_get_annotation_queue_with_pagination(self, client, mock_repository):
        """Test queue retrieval respects pagination parameters."""
        mock_repository.get_pending_annotations.return_value = []
        mock_repository.get_queue_count.return_value = 50

        response = client.get("/api/v1/annotations/queue?limit=20&offset=20")

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 20
        assert data["offset"] == 20
        assert data["total"] == 50

        # Verify repository called with correct parameters
        mock_repository.get_pending_annotations.assert_called_once_with(limit=20, offset=20)

    def test_get_annotation_queue_default_pagination(self, client, mock_repository):
        """Test queue retrieval uses default pagination values."""
        mock_repository.get_pending_annotations.return_value = []
        mock_repository.get_queue_count.return_value = 0

        response = client.get("/api/v1/annotations/queue")

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 20  # Default limit
        assert data["offset"] == 0  # Default offset

        # Verify defaults passed to repository
        mock_repository.get_pending_annotations.assert_called_once_with(limit=20, offset=0)

    def test_get_annotation_queue_empty(self, client, mock_repository):
        """Test queue retrieval when queue is empty."""
        mock_repository.get_pending_annotations.return_value = []
        mock_repository.get_queue_count.return_value = 0

        response = client.get("/api/v1/annotations/queue")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_get_annotation_queue_limit_validation(self, client, mock_repository):
        """Test queue retrieval validates limit bounds."""
        # Test limit too small
        response = client.get("/api/v1/annotations/queue?limit=0")
        assert response.status_code == 422

        # Test limit too large
        response = client.get("/api/v1/annotations/queue?limit=101")
        assert response.status_code == 422

    def test_get_annotation_queue_offset_validation(self, client, mock_repository):
        """Test queue retrieval validates offset is non-negative."""
        response = client.get("/api/v1/annotations/queue?offset=-1")
        assert response.status_code == 422

    def test_get_annotation_queue_repository_error(self, client, mock_repository):
        """Test handling of repository errors."""
        mock_repository.get_pending_annotations.side_effect = Exception("Database error")

        response = client.get("/api/v1/annotations/queue")

        assert response.status_code == 500
        assert "Failed to retrieve annotation queue" in response.json()["detail"]


@pytest.mark.unit
class TestMarkAsReviewed:
    """Tests for PATCH /annotations/queue/{queue_id}/reviewed endpoint."""

    def test_mark_as_reviewed_success(self, client, mock_repository):
        """Test successful marking as reviewed."""
        queue_id = 42
        artifact_id = uuid4()

        # Mock updated queue entry
        mock_queue_entry = AnnotationQueue(
            id=queue_id,
            artifact_id=artifact_id,
            trace_id="trace-123",
            reason="low_quality",
            status="reviewed",
            queue_metadata={"score": 0.5},
            created_at=datetime.now(UTC),
            reviewed_at=datetime.now(UTC),
        )

        mock_repository.mark_as_reviewed.return_value = mock_queue_entry

        response = client.patch(f"/api/v1/annotations/queue/{queue_id}/reviewed")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == queue_id
        assert data["status"] == "reviewed"
        assert data["reviewed_at"] is not None

        # Verify repository called
        mock_repository.mark_as_reviewed.assert_called_once_with(queue_id=queue_id)

    def test_mark_as_reviewed_not_found(self, client, mock_repository):
        """Test marking non-existent queue entry returns 404."""
        queue_id = 999

        # Mock repository returns None
        mock_repository.mark_as_reviewed.return_value = None

        response = client.patch(f"/api/v1/annotations/queue/{queue_id}/reviewed")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
        assert str(queue_id) in response.json()["detail"]

    def test_mark_as_reviewed_repository_error(self, client, mock_repository):
        """Test handling of repository errors."""
        queue_id = 42

        mock_repository.mark_as_reviewed.side_effect = Exception("Database error")

        response = client.patch(f"/api/v1/annotations/queue/{queue_id}/reviewed")

        assert response.status_code == 500
        assert "Failed to mark as reviewed" in response.json()["detail"]

    def test_mark_as_reviewed_invalid_id(self, client, mock_repository):
        """Test marking with invalid queue_id type."""
        response = client.patch("/api/v1/annotations/queue/invalid/reviewed")

        # Should return 422 validation error
        assert response.status_code == 422


@pytest.mark.unit
class TestIntegration:
    """Integration tests for annotation API endpoints."""

    def test_full_workflow_flag_to_review(self, client, mock_repository):
        """Test complete workflow: flag -> queue -> review."""
        artifact_id = uuid4()
        queue_id = 1

        # Step 1: Flag artifact
        mock_repository.check_if_queued.return_value = False
        mock_queue_entry = MagicMock()
        mock_queue_entry.id = queue_id
        mock_repository.queue_for_review.return_value = mock_queue_entry

        flag_response = client.post(
            "/api/v1/annotations/flag",
            json={
                "artifact_id": str(artifact_id),
                "reason": "Needs human review for accuracy",
            },
        )

        assert flag_response.status_code == 201
        assert flag_response.json()["queue_id"] == queue_id

        # Step 2: Get queue (should include flagged item)
        mock_queue_item = AnnotationQueue(
            id=queue_id,
            artifact_id=artifact_id,
            reason="flagged_by_user",
            status="pending",
            queue_metadata={"user_reason": "Needs human review for accuracy"},
            created_at=datetime.now(UTC),
            reviewed_at=None,
        )
        mock_repository.get_pending_annotations.return_value = [mock_queue_item]
        mock_repository.get_queue_count.return_value = 1

        queue_response = client.get("/api/v1/annotations/queue")

        assert queue_response.status_code == 200
        assert len(queue_response.json()["items"]) == 1
        assert queue_response.json()["total"] == 1

        # Step 3: Mark as reviewed
        mock_reviewed_entry = AnnotationQueue(
            id=queue_id,
            artifact_id=artifact_id,
            reason="flagged_by_user",
            status="reviewed",
            queue_metadata={"user_reason": "Needs human review for accuracy"},
            created_at=datetime.now(UTC),
            reviewed_at=datetime.now(UTC),
        )
        mock_repository.mark_as_reviewed.return_value = mock_reviewed_entry

        review_response = client.patch(f"/api/v1/annotations/queue/{queue_id}/reviewed")

        assert review_response.status_code == 200
        assert review_response.json()["status"] == "reviewed"

    def test_duplicate_flagging_prevented(self, client, mock_repository):
        """Test that duplicate flagging is prevented."""
        artifact_id = uuid4()

        # First flag succeeds
        mock_repository.check_if_queued.return_value = False
        mock_queue_entry = MagicMock()
        mock_queue_entry.id = 1
        mock_repository.queue_for_review.return_value = mock_queue_entry

        response1 = client.post(
            "/api/v1/annotations/flag",
            json={
                "artifact_id": str(artifact_id),
                "reason": "First flagging reason",
            },
        )

        assert response1.status_code == 201

        # Second flag returns conflict
        mock_repository.check_if_queued.return_value = True

        response2 = client.post(
            "/api/v1/annotations/flag",
            json={
                "artifact_id": str(artifact_id),
                "reason": "Second flagging reason",
            },
        )

        assert response2.status_code == 409
