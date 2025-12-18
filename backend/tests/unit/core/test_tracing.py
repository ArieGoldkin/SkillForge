"""Unit tests for Langfuse tracing utilities.

Tests the robust_traceable decorator which is the only public API
for tracing in this module.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.tracing import robust_traceable


@pytest.mark.unit
@pytest.mark.asyncio
@patch("langfuse.observe")
async def test_robust_traceable_with_metadata(mock_observe):
    """Test robust_traceable passes metadata to observe correctly."""
    captured_func = None

    def mock_decorator(func):
        nonlocal captured_func
        captured_func = func

        async def mock_wrapper(*args, **kwargs):
            return await captured_func(*args, **kwargs)

        return mock_wrapper

    mock_observe.return_value = mock_decorator

    @robust_traceable(
        name="test_node",
        run_type="chain",
        tags=["workflow", "node"],
        metadata={"environment": "test", "workflow_type": "analysis"},
    )
    async def test_function(arg1: str) -> dict:
        """Test function."""
        return {"result": arg1}

    result = await test_function("test")

    # Verify observe was called with correct parameters
    mock_observe.assert_called_once()
    call_kwargs = mock_observe.call_args.kwargs
    assert call_kwargs["name"] == "test_node"
    assert call_kwargs["as_type"] == "span"  # chain maps to span
    assert result == {"result": "test"}


@pytest.mark.asyncio
@patch("langfuse.observe")
async def test_robust_traceable_with_tags(mock_observe):
    """Test robust_traceable passes tags correctly."""
    captured_func = None

    def mock_decorator(func):
        nonlocal captured_func
        captured_func = func

        async def mock_wrapper(*args, **kwargs):
            return await captured_func(*args, **kwargs)

        return mock_wrapper

    mock_observe.return_value = mock_decorator

    @robust_traceable(
        name="test_agent",
        run_type="chain",
        tags=["agent", "test"],
    )
    async def test_agent_function(content: str) -> dict:
        """Test agent function."""
        return {"agent_result": content}

    result = await test_agent_function("test")

    # Verify observe was called
    assert result == {"agent_result": "test"}


@pytest.mark.asyncio
async def test_robust_traceable_propagates_exceptions():
    """Test that robust_traceable lets exceptions propagate naturally."""
    call_count = {"executed": 0, "completed": False}

    @robust_traceable(name="test_node", run_type="chain")
    async def test_node(value: int) -> int:
        call_count["executed"] += 1
        result = value * 2
        call_count["completed"] = True
        return result

    # Normal execution should work
    result = await test_node(5)

    assert result == 10
    assert call_count["executed"] == 1
    assert call_count["completed"] is True


@pytest.mark.asyncio
async def test_robust_traceable_preserves_other_exceptions():
    """Test that robust_traceable doesn't suppress real exceptions."""

    @robust_traceable(name="test_node", run_type="chain")
    async def test_node(value: int) -> int:
        msg = "Real error"
        raise ValueError(msg)

    with pytest.raises(ValueError, match="Real error"):
        await test_node(5)


@pytest.mark.asyncio
@patch("langfuse.get_client")
async def test_update_current_trace(mock_get_client):
    """Test that update_current_trace calls langfuse client correctly."""
    from app.core.tracing import update_current_trace

    # Setup mock client
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Call update_current_trace
    update_current_trace(
        metadata={"analysis_id": "test-analysis-id"},
        tags=["custom-tag"],
    )

    # Verify client.update_current_trace was called
    mock_client.update_current_trace.assert_called_once()
    call_kwargs = mock_client.update_current_trace.call_args.kwargs
    assert call_kwargs["tags"] == ["custom-tag"]
    assert call_kwargs["metadata"]["analysis_id"] == "test-analysis-id"


@pytest.mark.asyncio
@patch("langfuse.observe")
async def test_robust_traceable_defaults(mock_observe):
    """Test robust_traceable uses function name as default."""
    captured_func = None

    def mock_decorator(func):
        nonlocal captured_func
        captured_func = func

        async def mock_wrapper(*args, **kwargs):
            return await captured_func(*args, **kwargs)

        return mock_wrapper

    mock_observe.return_value = mock_decorator

    # Apply decorator without name
    @robust_traceable()
    async def my_test_function() -> dict:
        """Test function."""
        return {"result": "test"}

    result = await my_test_function()

    # Verify name defaults to function name
    call_kwargs = mock_observe.call_args.kwargs
    assert call_kwargs["name"] == "my_test_function"
    assert result == {"result": "test"}
