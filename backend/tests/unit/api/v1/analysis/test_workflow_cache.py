"""Unit tests for WorkflowCache and checkpointer injection.

Issue #602: Tests for AsyncPostgresSaver injection via dependency injection pattern.
"""

from unittest.mock import MagicMock, patch

from fastapi import Request

from app.api.v1.analysis.endpoints import WorkflowCache, get_orchestrator


class TestWorkflowCache:
    """Tests for WorkflowCache singleton cache by checkpointer type."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        WorkflowCache._instances.clear()

    def teardown_method(self) -> None:
        """Clear cache after each test."""
        WorkflowCache._instances.clear()

    @patch("app.api.v1.analysis.endpoints.create_analysis_workflow")
    def test_caches_workflow_by_checkpointer_type(self, mock_create: MagicMock) -> None:
        """Test that workflows are cached by checkpointer type."""
        mock_workflow = MagicMock()
        mock_create.return_value = mock_workflow

        # First call creates workflow
        result1 = WorkflowCache.get_or_create(checkpointer=None)
        assert result1 == mock_workflow
        assert mock_create.call_count == 1

        # Second call with same checkpointer type returns cached
        result2 = WorkflowCache.get_or_create(checkpointer=None)
        assert result2 == mock_workflow
        assert mock_create.call_count == 1  # Not called again

    @patch("app.api.v1.analysis.endpoints.create_analysis_workflow")
    def test_different_checkpointer_types_create_separate_workflows(
        self, mock_create: MagicMock
    ) -> None:
        """Test that different checkpointer types get separate cached workflows."""
        mock_workflow1 = MagicMock(name="workflow1")
        mock_workflow2 = MagicMock(name="workflow2")
        mock_create.side_effect = [mock_workflow1, mock_workflow2]

        # Create mock checkpointers of different types
        mock_memory_saver = MagicMock()
        mock_memory_saver.__class__.__name__ = "MemorySaver"

        mock_postgres_saver = MagicMock()
        mock_postgres_saver.__class__.__name__ = "AsyncPostgresSaver"

        # First call with MemorySaver
        result1 = WorkflowCache.get_or_create(checkpointer=mock_memory_saver)
        assert result1 == mock_workflow1

        # Second call with AsyncPostgresSaver creates new workflow
        result2 = WorkflowCache.get_or_create(checkpointer=mock_postgres_saver)
        assert result2 == mock_workflow2
        assert mock_create.call_count == 2

    @patch("app.api.v1.analysis.endpoints.create_analysis_workflow")
    def test_passes_checkpointer_to_workflow_factory(self, mock_create: MagicMock) -> None:
        """Test that checkpointer is passed to create_analysis_workflow."""
        mock_workflow = MagicMock()
        mock_create.return_value = mock_workflow
        mock_checkpointer = MagicMock()

        WorkflowCache.get_or_create(checkpointer=mock_checkpointer)

        mock_create.assert_called_once_with(checkpointer=mock_checkpointer)


class TestGetOrchestrator:
    """Tests for get_orchestrator dependency injection."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        WorkflowCache._instances.clear()

    def teardown_method(self) -> None:
        """Clear cache after each test."""
        WorkflowCache._instances.clear()

    @patch("app.api.v1.analysis.endpoints.WorkflowOrchestrator")
    @patch("app.api.v1.analysis.endpoints.create_analysis_workflow")
    def test_extracts_checkpointer_from_app_state(
        self, mock_create: MagicMock, mock_orchestrator_class: MagicMock
    ) -> None:
        """Test that checkpointer is extracted from request.app.state."""
        mock_workflow = MagicMock()
        mock_create.return_value = mock_workflow
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        # Create mock request with app.state.checkpointer
        mock_checkpointer = MagicMock()
        mock_request = MagicMock(spec=Request)
        mock_request.app.state.checkpointer = mock_checkpointer

        result = get_orchestrator(mock_request)

        # Verify checkpointer was passed to workflow creation
        mock_create.assert_called_once_with(checkpointer=mock_checkpointer)
        mock_orchestrator_class.assert_called_once_with(workflow=mock_workflow)
        assert result == mock_orchestrator

    @patch("app.api.v1.analysis.endpoints.WorkflowOrchestrator")
    @patch("app.api.v1.analysis.endpoints.create_analysis_workflow")
    def test_handles_missing_checkpointer_gracefully(
        self, mock_create: MagicMock, mock_orchestrator_class: MagicMock
    ) -> None:
        """Test that missing checkpointer defaults to None."""
        mock_workflow = MagicMock()
        mock_create.return_value = mock_workflow
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        # Create mock request without checkpointer attribute
        mock_request = MagicMock(spec=Request)
        mock_request.app.state = MagicMock(spec=[])  # No checkpointer attr

        result = get_orchestrator(mock_request)

        # Should use None as checkpointer (fallback)
        mock_create.assert_called_once_with(checkpointer=None)
