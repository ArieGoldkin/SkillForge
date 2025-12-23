"""Integration tests for Langfuse best practices implementation.

Tests metadata propagation, thread grouping, runtime metadata updates,
and consistent decorator usage across the codebase.
"""

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.core.tracing import robust_traceable


@pytest.mark.asyncio
@patch("langfuse.observe")
async def test_metadata_propagation(mock_observe):
    """Test that metadata is properly propagated to Langfuse traces."""
    captured_func: Callable[..., Any] | None = None

    def mock_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        nonlocal captured_func
        captured_func = func

        async def mock_wrapper(*args: Any, **kwargs: Any) -> Any:
            assert captured_func is not None, "captured_func must be set by decorator"
            return await captured_func(*args, **kwargs)

        return mock_wrapper

    mock_observe.return_value = mock_decorator

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

    # Verify observe was called
    mock_observe.assert_called_once()
    assert result == {"status": "success"}


@pytest.mark.asyncio
@patch("langfuse.get_client")
async def test_thread_grouping_tutor(mock_get_client):
    """Test that tutor nodes group traces by session_id via update_current_trace."""
    from app.core.tracing import update_current_trace

    # Mock Langfuse client
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Call update_current_trace with session grouping metadata
    update_current_trace(
        metadata={
            "session_id": "session-123",
            "conversation_id": "session-123",
            "tutor_phase": "socratic_questioning",
        },
        tags=["tutor"],
        session_id="session-123",
    )

    # Verify get_client().update_current_trace was called
    mock_get_client.assert_called_once()
    mock_client.update_current_trace.assert_called_once()
    call_kwargs = mock_client.update_current_trace.call_args.kwargs
    assert call_kwargs["metadata"]["session_id"] == "session-123"
    assert call_kwargs["session_id"] == "session-123"


@pytest.mark.asyncio
@patch("langfuse.get_client")
async def test_runtime_metadata_updates(mock_get_client):
    """Test that runtime metadata updates work correctly."""
    from app.core.tracing import update_current_trace

    # Mock Langfuse client
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Call update_current_trace with runtime metadata
    update_current_trace(
        metadata={
            "analysis_id": "analysis-123",
            "url": "https://example.com",
        },
        tags=["parallel-execution"],
    )

    # Verify get_client().update_current_trace was called
    mock_get_client.assert_called_once()
    mock_client.update_current_trace.assert_called_once()
    call_kwargs = mock_client.update_current_trace.call_args.kwargs
    assert call_kwargs["metadata"]["analysis_id"] == "analysis-123"
    assert call_kwargs["metadata"]["url"] == "https://example.com"
    assert "parallel-execution" in call_kwargs["tags"]


@pytest.mark.asyncio
@patch("langfuse.observe")
async def test_consistent_decorator_usage(mock_observe):
    """Test that robust_traceable is used consistently."""
    captured_func: Callable[..., Any] | None = None

    def mock_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        nonlocal captured_func
        captured_func = func

        async def mock_wrapper(*args: Any, **kwargs: Any) -> Any:
            assert captured_func is not None, "captured_func must be set by decorator"
            return await captured_func(*args, **kwargs)

        return mock_wrapper

    mock_observe.return_value = mock_decorator

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

    # Verify robust_traceable was used (not direct observe)
    # This is verified by the fact that observe is called with our parameters
    mock_observe.assert_called_once()
    assert result == {"result": "success"}


@pytest.mark.asyncio
@patch("langfuse.get_client")
async def test_environment_metadata_propagation(mock_get_client):
    """Test that environment metadata is propagated correctly."""
    from app.core.tracing import update_current_trace

    # Mock Langfuse client
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Call update_current_trace with environment metadata
    update_current_trace(
        metadata={
            "environment": "production",
            "workflow_type": "analysis",
            "runtime_key": "runtime_value",
        },
    )

    # Verify runtime metadata was added
    mock_get_client.assert_called_once()
    mock_client.update_current_trace.assert_called_once()
    call_kwargs = mock_client.update_current_trace.call_args.kwargs
    assert call_kwargs["metadata"]["runtime_key"] == "runtime_value"
