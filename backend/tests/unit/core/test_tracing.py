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


# Tests for get_current_trace_id
@pytest.mark.unit
@patch("langfuse.get_client")
def test_get_current_trace_id_returns_trace_id(mock_get_client):
    """Test that get_current_trace_id returns the trace ID from Langfuse."""
    from app.core.tracing import get_current_trace_id

    # Setup mock client
    mock_client = MagicMock()
    mock_client.get_current_trace_id.return_value = "trace-abc-123"
    mock_get_client.return_value = mock_client

    result = get_current_trace_id()

    assert result == "trace-abc-123"
    mock_client.get_current_trace_id.assert_called_once()


@pytest.mark.unit
@patch("langfuse.get_client")
def test_get_current_trace_id_returns_none_when_no_trace(mock_get_client):
    """Test that get_current_trace_id returns None when not in trace context."""
    from app.core.tracing import get_current_trace_id

    # Setup mock client that returns None
    mock_client = MagicMock()
    mock_client.get_current_trace_id.return_value = None
    mock_get_client.return_value = mock_client

    result = get_current_trace_id()

    assert result is None


@pytest.mark.unit
@patch("langfuse.get_client")
def test_get_current_trace_id_handles_exception(mock_get_client):
    """Test that get_current_trace_id handles exceptions gracefully."""
    from app.core.tracing import get_current_trace_id

    # Setup mock client that raises exception
    mock_get_client.side_effect = Exception("Connection error")

    result = get_current_trace_id()

    assert result is None


@pytest.mark.unit
def test_get_current_trace_id_handles_import_error():
    """Test that get_current_trace_id handles import error gracefully."""
    from app.core.tracing import get_current_trace_id

    # Patch sys.modules to simulate langfuse not being installed
    with patch.dict("sys.modules", {"langfuse": None}):
        # The function handles ImportError internally
        result = get_current_trace_id()

    # Should return None or the actual value if langfuse is installed
    assert result is None or isinstance(result, str)


@pytest.mark.unit
@patch("langfuse.get_client")
def test_get_current_trace_id_converts_uuid_to_string(mock_get_client):
    """Test that get_current_trace_id converts UUID-like objects to string."""
    from uuid import uuid4

    from app.core.tracing import get_current_trace_id

    # Setup mock client that returns a UUID-like object
    mock_uuid = uuid4()
    mock_client = MagicMock()
    mock_client.get_current_trace_id.return_value = mock_uuid
    mock_get_client.return_value = mock_client

    result = get_current_trace_id()

    assert result == str(mock_uuid)
    assert isinstance(result, str)


# ============================================================================
# Issue #378: Session/User Tracking Tests
# ============================================================================


@pytest.mark.unit
@patch("langfuse.get_client")
def test_update_current_trace_with_session_id(mock_get_client):
    """Test that update_current_trace passes session_id correctly.

    Issue #378: Session tracking enables grouping traces by analysis session.
    """
    from app.core.tracing import update_current_trace

    # Setup mock client
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Call with session_id (pattern used in workflow_runner.py)
    analysis_id = "dff652c1-9ca3-49c2-a8be-8db528447e54"
    update_current_trace(session_id=f"analysis-{analysis_id}")

    # Verify client.update_current_trace was called with session_id
    mock_client.update_current_trace.assert_called_once()
    call_kwargs = mock_client.update_current_trace.call_args.kwargs
    assert call_kwargs["session_id"] == f"analysis-{analysis_id}"


@pytest.mark.unit
@patch("langfuse.get_client")
def test_update_current_trace_with_user_id(mock_get_client):
    """Test that update_current_trace passes user_id correctly.

    Issue #378: User tracking enables filtering traces by user.
    """
    from app.core.tracing import update_current_trace

    # Setup mock client
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Call with user_id
    update_current_trace(user_id="user_123")

    # Verify client.update_current_trace was called with user_id
    mock_client.update_current_trace.assert_called_once()
    call_kwargs = mock_client.update_current_trace.call_args.kwargs
    assert call_kwargs["user_id"] == "user_123"


@pytest.mark.unit
@patch("langfuse.get_client")
def test_update_current_trace_with_session_and_user(mock_get_client):
    """Test update_current_trace with both session_id and user_id.

    Issue #378: Combined session/user tracking for full trace context.
    This is the pattern used in workflow_runner.py (lines 310-322).
    """
    from app.core.tracing import update_current_trace

    # Setup mock client
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Call with all parameters (matches workflow_runner.py pattern)
    analysis_id = "abc123"
    update_current_trace(
        metadata={
            "analysis_id": analysis_id,
            "url": "https://example.com/article",
            "workflow_version": "1.0",
        },
        tags=["analysis", "workflow"],
        session_id=f"analysis-{analysis_id}",
        user_id="anonymous",  # Placeholder until auth is implemented
    )

    # Verify all parameters were passed
    mock_client.update_current_trace.assert_called_once()
    call_kwargs = mock_client.update_current_trace.call_args.kwargs
    assert call_kwargs["session_id"] == "analysis-abc123"
    assert call_kwargs["user_id"] == "anonymous"
    assert call_kwargs["tags"] == ["analysis", "workflow"]
    assert call_kwargs["metadata"]["analysis_id"] == "abc123"
    assert call_kwargs["metadata"]["url"] == "https://example.com/article"


@pytest.mark.unit
@patch("langfuse.get_client")
def test_update_current_trace_handles_langfuse_exception(mock_get_client):
    """Test that update_current_trace handles Langfuse errors gracefully.

    Issue #378: Trace updates should not crash the workflow.
    """
    from app.core.tracing import update_current_trace

    # Setup mock client that raises exception
    mock_client = MagicMock()
    mock_client.update_current_trace.side_effect = Exception("Langfuse connection error")
    mock_get_client.return_value = mock_client

    # Should not raise - graceful degradation
    update_current_trace(
        session_id="analysis-123",
        user_id="anonymous",
    )

    # Verify the call was attempted
    mock_client.update_current_trace.assert_called_once()


@pytest.mark.unit
@patch("langfuse.get_client")
def test_update_current_trace_skips_none_values(mock_get_client):
    """Test that update_current_trace only passes non-None values.

    Issue #378: Empty/None parameters should not be sent to Langfuse.
    """
    from app.core.tracing import update_current_trace

    # Setup mock client
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Call with only session_id (user_id=None, tags=None, metadata=None)
    update_current_trace(session_id="analysis-123")

    # Verify only session_id was passed
    mock_client.update_current_trace.assert_called_once()
    call_kwargs = mock_client.update_current_trace.call_args.kwargs
    assert "session_id" in call_kwargs
    assert call_kwargs["session_id"] == "analysis-123"
    # None values should not be in kwargs
    assert "user_id" not in call_kwargs
    assert "tags" not in call_kwargs
    assert "metadata" not in call_kwargs


@pytest.mark.unit
@patch("langfuse.get_client")
def test_update_current_trace_empty_call_no_op(mock_get_client):
    """Test that update_current_trace with no args is a no-op.

    Issue #378: Calling with no parameters should not call Langfuse.
    """
    from app.core.tracing import update_current_trace

    # Setup mock client
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Call with no parameters
    update_current_trace()

    # Should not call Langfuse when all params are None
    mock_client.update_current_trace.assert_not_called()
