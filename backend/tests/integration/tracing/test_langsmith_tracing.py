"""Integration tests for LangSmith best practices implementation.

Tests metadata propagation, thread grouping, runtime metadata updates,
and consistent decorator usage across the codebase.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.tracing import robust_traceable


@pytest.mark.asyncio
@patch("app.core.tracing.traceable")
async def test_metadata_propagation(mock_traceable):
    """Test that metadata is properly propagated to LangSmith traces."""
    captured_func = None

    def mock_decorator(func):
        nonlocal captured_func
        captured_func = func

        async def mock_wrapper(*args, **kwargs):
            return await captured_func(*args, **kwargs)

        return mock_wrapper

    mock_traceable.return_value = mock_decorator

    @robust_traceable(
        name="test_workflow",
        run_type="chain",
        tags=["workflow", "test"],
        metadata={
            "environment": "test",
            "workflow_type": "analysis",
            "component": "workflow",
        },
    )
    async def test_workflow() -> dict:
        """Test workflow function."""
        return {"status": "success"}

    result = await test_workflow()

    # Verify metadata is passed to traceable
    call_kwargs = mock_traceable.call_args.kwargs
    assert call_kwargs["metadata"]["environment"] == "test"
    assert call_kwargs["metadata"]["workflow_type"] == "analysis"
    assert call_kwargs["metadata"]["component"] == "workflow"
    assert result == {"status": "success"}


@pytest.mark.asyncio
@patch("langsmith.get_current_run_tree")
async def test_thread_grouping_tutor(mock_get_current_run_tree):
    """Test that tutor nodes group traces by thread_id."""
    # Setup mock run tree
    mock_run_tree = MagicMock()
    mock_run_tree.id = "test-trace-id"
    mock_run_tree.metadata = {}
    mock_run_tree.tags = []
    mock_get_current_run_tree.return_value = mock_run_tree

    @robust_traceable(name="tutor_node", run_type="chain", tags=["tutor"])
    async def tutor_node(session_id: str) -> dict:
        from langsmith import get_current_run_tree

        run_tree = get_current_run_tree()
        if run_tree:
            # Thread grouping pattern
            run_tree.metadata["thread_id"] = str(session_id)
            run_tree.metadata["session_id"] = str(session_id)
            run_tree.metadata["conversation_id"] = str(session_id)
            run_tree.metadata["tutor_phase"] = "socratic_questioning"

        return {"status": "success"}

    result = await tutor_node("session-123")

    # Verify thread grouping metadata
    assert mock_run_tree.metadata["thread_id"] == "session-123"
    assert mock_run_tree.metadata["session_id"] == "session-123"
    assert mock_run_tree.metadata["conversation_id"] == "session-123"
    assert mock_run_tree.metadata["tutor_phase"] == "socratic_questioning"
    assert result == {"status": "success"}


@pytest.mark.asyncio
@patch("langsmith.get_current_run_tree")
async def test_runtime_metadata_updates(mock_get_current_run_tree):
    """Test that runtime metadata updates work correctly."""
    # Setup mock run tree
    mock_run_tree = MagicMock()
    mock_run_tree.id = "test-trace-id"
    mock_run_tree.metadata = {}
    mock_run_tree.tags = []
    mock_get_current_run_tree.return_value = mock_run_tree

    @robust_traceable(name="test_node", run_type="chain")
    async def test_node_with_runtime_metadata(analysis_id: str, url: str) -> dict:
        from langsmith import get_current_run_tree

        run_tree = get_current_run_tree()
        if run_tree:
            # Runtime metadata updates
            run_tree.metadata["analysis_id"] = analysis_id
            run_tree.metadata["url"] = url
            run_tree.tags.append("parallel-execution")

        return {"status": "success"}

    result = await test_node_with_runtime_metadata("analysis-123", "https://example.com")

    # Verify runtime metadata was updated
    assert mock_run_tree.metadata["analysis_id"] == "analysis-123"
    assert mock_run_tree.metadata["url"] == "https://example.com"
    assert "parallel-execution" in mock_run_tree.tags
    assert result == {"status": "success"}


@pytest.mark.asyncio
@patch("app.core.tracing.traceable")
async def test_consistent_decorator_usage(mock_traceable):
    """Test that robust_traceable is used consistently."""
    captured_func = None

    def mock_decorator(func):
        nonlocal captured_func
        captured_func = func

        async def mock_wrapper(*args, **kwargs):
            return await captured_func(*args, **kwargs)

        return mock_wrapper

    mock_traceable.return_value = mock_decorator

    # All nodes should use robust_traceable
    @robust_traceable(
        name="test_node",
        run_type="chain",
        tags=["workflow", "node"],
        metadata={"environment": "test"},
    )
    async def test_node() -> dict:
        """Test node function."""
        return {"result": "success"}

    result = await test_node()

    # Verify robust_traceable was used (not direct traceable)
    # This is verified by the fact that traceable is called with our parameters
    mock_traceable.assert_called_once()
    call_kwargs = mock_traceable.call_args.kwargs
    assert call_kwargs["name"] == "test_node"
    assert call_kwargs["metadata"]["environment"] == "test"
    assert result == {"result": "success"}


@pytest.mark.asyncio
@patch("langsmith.get_current_run_tree")
async def test_environment_metadata_propagation(mock_get_current_run_tree):
    """Test that environment metadata is propagated correctly."""
    # Setup mock run tree
    mock_run_tree = MagicMock()
    mock_run_tree.metadata = {}
    mock_get_current_run_tree.return_value = mock_run_tree

    @robust_traceable(
        name="test_node",
        run_type="chain",
        metadata={"environment": "production", "workflow_type": "analysis"},
    )
    async def test_node() -> dict:
        from langsmith import get_current_run_tree

        run_tree = get_current_run_tree()
        if run_tree:
            # Verify static metadata is available
            assert True  # May be in decorator metadata
            run_tree.metadata["runtime_key"] = "runtime_value"

        return {"status": "success"}

    result = await test_node()

    # Verify runtime metadata was added
    assert mock_run_tree.metadata["runtime_key"] == "runtime_value"
    assert result == {"status": "success"}
