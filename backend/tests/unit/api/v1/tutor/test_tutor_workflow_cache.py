"""Unit tests for TutorWorkflowCache and checkpointer injection.

Issue #602: Tests for AsyncPostgresSaver injection in tutor workflow.
"""

from unittest.mock import MagicMock, patch

from fastapi import Request

from app.api.v1.tutor.sessions import TutorWorkflowCache, get_tutor_workflow


class TestTutorWorkflowCache:
    """Tests for TutorWorkflowCache singleton cache by checkpointer type."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        TutorWorkflowCache._instances.clear()

    def teardown_method(self) -> None:
        """Clear cache after each test."""
        TutorWorkflowCache._instances.clear()

    @patch("app.api.v1.tutor.sessions.create_tutor_workflow")
    def test_caches_workflow_by_checkpointer_type(self, mock_create: MagicMock) -> None:
        """Test that workflows are cached by checkpointer type."""
        mock_workflow = MagicMock()
        mock_create.return_value = mock_workflow

        # First call creates workflow
        result1 = TutorWorkflowCache.get_or_create(checkpointer=None)
        assert result1 == mock_workflow
        assert mock_create.call_count == 1

        # Second call with same checkpointer type returns cached
        result2 = TutorWorkflowCache.get_or_create(checkpointer=None)
        assert result2 == mock_workflow
        assert mock_create.call_count == 1  # Not called again

    @patch("app.api.v1.tutor.sessions.create_tutor_workflow")
    def test_passes_checkpointer_to_workflow_factory(self, mock_create: MagicMock) -> None:
        """Test that checkpointer is passed to create_tutor_workflow."""
        mock_workflow = MagicMock()
        mock_create.return_value = mock_workflow
        mock_checkpointer = MagicMock()

        TutorWorkflowCache.get_or_create(checkpointer=mock_checkpointer)

        mock_create.assert_called_once_with(checkpointer=mock_checkpointer)


class TestGetTutorWorkflow:
    """Tests for get_tutor_workflow dependency injection."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        TutorWorkflowCache._instances.clear()

    def teardown_method(self) -> None:
        """Clear cache after each test."""
        TutorWorkflowCache._instances.clear()

    @patch("app.api.v1.tutor.sessions.create_tutor_workflow")
    def test_extracts_checkpointer_from_app_state(self, mock_create: MagicMock) -> None:
        """Test that checkpointer is extracted from request.app.state."""
        mock_workflow = MagicMock()
        mock_create.return_value = mock_workflow

        # Create mock request with app.state.checkpointer
        mock_checkpointer = MagicMock()
        mock_request = MagicMock(spec=Request)
        mock_request.app.state.checkpointer = mock_checkpointer

        result = get_tutor_workflow(mock_request)

        # Verify checkpointer was passed to workflow creation
        mock_create.assert_called_once_with(checkpointer=mock_checkpointer)
        assert result == mock_workflow

    @patch("app.api.v1.tutor.sessions.create_tutor_workflow")
    def test_handles_missing_checkpointer_gracefully(self, mock_create: MagicMock) -> None:
        """Test that missing checkpointer defaults to None."""
        mock_workflow = MagicMock()
        mock_create.return_value = mock_workflow

        # Create mock request without checkpointer attribute
        mock_request = MagicMock(spec=Request)
        mock_request.app.state = MagicMock(spec=[])  # No checkpointer attr

        result = get_tutor_workflow(mock_request)

        # Should use None as checkpointer (fallback)
        mock_create.assert_called_once_with(checkpointer=None)
