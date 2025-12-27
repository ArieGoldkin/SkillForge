"""Integration tests for Langfuse tool tracing with @traced_tool decorator.

Tests that the @traced_tool decorator creates proper tool observation spans
in Langfuse's agent graph visualization, and that update_current_observation
correctly adds runtime metadata to tool traces.
"""

import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.core.tracing import traced_tool, update_current_observation


@pytest.mark.asyncio
@pytest.mark.integration
@patch("langfuse.observe")
async def test_traced_tool_creates_tool_span(mock_observe):
    """Test that @traced_tool creates a tool observation span in Langfuse."""
    # Skip if Langfuse is not enabled
    if os.getenv("LANGFUSE_ENABLED") != "true":
        pytest.skip("Langfuse not enabled - set LANGFUSE_ENABLED=true to run")

    captured_func = None

    def mock_decorator(func):
        nonlocal captured_func
        captured_func = func

        async def mock_wrapper(*args: Any, **kwargs: Any) -> Any:
            assert captured_func is not None, "captured_func must be set by decorator"
            return await captured_func(*args, **kwargs)

        return mock_wrapper

    mock_observe.return_value = mock_decorator

    # Create a tool function decorated with @traced_tool
    @traced_tool("test_tool", tags=["external_api", "test"])
    async def mock_tool(query: str) -> dict:
        """Mock tool that simulates an external API call."""
        return {"result": f"Processed: {query}", "count": 42}

    result = await mock_tool("test query")

    # Verify observe was called with tool type
    mock_observe.assert_called_once()
    call_kwargs = mock_observe.call_args.kwargs
    assert call_kwargs["name"] == "test_tool"
    assert call_kwargs["as_type"] == "tool"
    assert call_kwargs["capture_input"] is True
    assert call_kwargs["capture_output"] is True
    assert result == {"result": "Processed: test query", "count": 42}


@pytest.mark.asyncio
@pytest.mark.integration
@patch("langfuse.get_client")
async def test_update_current_observation_adds_runtime_metadata(mock_get_client):
    """Test that update_current_observation adds runtime metadata to tool observations."""
    # Skip if Langfuse is not enabled
    if os.getenv("LANGFUSE_ENABLED") != "true":
        pytest.skip("Langfuse not enabled - set LANGFUSE_ENABLED=true to run")

    # Mock Langfuse client
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Call update_current_observation with runtime metadata
    update_current_observation(
        metadata={
            "cache_hit": True,
            "result_count": 5,
            "response_time_ms": 123.45,
            "api_version": "v2",
        }
    )

    # Verify get_client().update_current_span was called (not update_current_observation)
    mock_get_client.assert_called_once()
    mock_client.update_current_span.assert_called_once()
    call_kwargs = mock_client.update_current_span.call_args.kwargs
    assert call_kwargs["metadata"]["cache_hit"] is True
    assert call_kwargs["metadata"]["result_count"] == 5
    assert call_kwargs["metadata"]["response_time_ms"] == 123.45
    assert call_kwargs["metadata"]["api_version"] == "v2"


@pytest.mark.asyncio
@pytest.mark.integration
@patch("langfuse.get_client")
async def test_update_current_observation_with_output(mock_get_client):
    """Test that update_current_observation can update output and status."""
    # Skip if Langfuse is not enabled
    if os.getenv("LANGFUSE_ENABLED") != "true":
        pytest.skip("Langfuse not enabled - set LANGFUSE_ENABLED=true to run")

    # Mock Langfuse client
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Call update_current_observation with output and status
    update_current_observation(
        output={"processed": True, "items": [1, 2, 3]},
        level="DEFAULT",
        status_message="Tool execution successful",
    )

    # Verify update was called with output and status
    mock_get_client.assert_called_once()
    mock_client.update_current_span.assert_called_once()
    call_kwargs = mock_client.update_current_span.call_args.kwargs
    assert call_kwargs["output"] == {"processed": True, "items": [1, 2, 3]}
    assert call_kwargs["level"] == "DEFAULT"
    assert call_kwargs["status_message"] == "Tool execution successful"


@pytest.mark.asyncio
@pytest.mark.integration
@patch("langfuse.get_client")
@patch("langfuse.observe")
async def test_traced_tool_with_metadata_and_runtime_updates(mock_observe, mock_get_client):
    """Test complete workflow: @traced_tool with static metadata + runtime updates."""
    # Skip if Langfuse is not enabled
    if os.getenv("LANGFUSE_ENABLED") != "true":
        pytest.skip("Langfuse not enabled - set LANGFUSE_ENABLED=true to run")

    # Mock Langfuse client
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    captured_func = None

    def mock_decorator(func):
        nonlocal captured_func
        captured_func = func

        async def mock_wrapper(*args: Any, **kwargs: Any) -> Any:
            assert captured_func is not None
            # Simulate calling the wrapped function which will update observation
            return await captured_func(*args, **kwargs)

        return mock_wrapper

    mock_observe.return_value = mock_decorator

    # Create a tool with static metadata
    @traced_tool(
        "tavily_search",
        tags=["external_api", "search"],
        metadata={"provider": "tavily", "max_results": 10},
    )
    async def search_tool(query: str) -> dict:
        """Mock search tool with runtime metadata updates."""
        # Simulate tool execution
        results = [{"title": "Result 1"}, {"title": "Result 2"}]

        # Update observation with runtime metadata
        update_current_observation(
            metadata={
                "cache_hit": False,
                "result_count": len(results),
                "response_time_ms": 234.56,
            }
        )

        return {"query": query, "results": results}

    result = await search_tool("test search query")

    # Verify observe was called with tool type and static metadata
    mock_observe.assert_called_once()
    observe_kwargs = mock_observe.call_args.kwargs
    assert observe_kwargs["name"] == "tavily_search"
    assert observe_kwargs["as_type"] == "tool"

    # Verify get_client was called to update observation metadata
    assert mock_get_client.called
    # Note: Called twice - once for static tags/metadata, once for runtime metadata
    assert mock_client.update_current_span.call_count >= 1

    # Verify result
    assert result["query"] == "test search query"
    assert len(result["results"]) == 2


@pytest.mark.asyncio
@pytest.mark.integration
@patch("langfuse.observe")
async def test_traced_tool_without_langfuse_installed(mock_observe):
    """Test that @traced_tool gracefully degrades when Langfuse is not installed."""
    # Simulate ImportError when Langfuse is not installed
    mock_observe.side_effect = ImportError("No module named 'langfuse'")

    # Create a tool - should not raise error
    @traced_tool("test_tool")
    async def mock_tool(query: str) -> dict:
        return {"result": query}

    # Tool should still work without tracing
    result = await mock_tool("test query")
    assert result == {"result": "test query"}


@pytest.mark.asyncio
@pytest.mark.integration
async def test_update_current_observation_without_trace_context():
    """Test that update_current_observation silently skips when not in trace context."""
    # This should not raise an error even if we're not in a trace context
    update_current_observation(
        metadata={"test": "value"},
        level="WARNING",
        status_message="No trace context",
    )
    # If we got here, the test passed (no exception raised)


@pytest.mark.asyncio
@pytest.mark.integration
@patch("langfuse.get_client")
async def test_traced_tool_error_handling(mock_get_client):
    """Test that tool errors are properly propagated and can be logged."""
    # Skip if Langfuse is not enabled
    if os.getenv("LANGFUSE_ENABLED") != "true":
        pytest.skip("Langfuse not enabled - set LANGFUSE_ENABLED=true to run")

    # Mock Langfuse client
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Create a tool that raises an error
    @traced_tool("failing_tool", tags=["test"])
    async def failing_tool(query: str) -> dict:
        """Tool that simulates an API error."""
        # Log error details before raising
        update_current_observation(
            metadata={"error": "API rate limit exceeded"},
            level="ERROR",
            status_message="Tool execution failed",
        )
        raise ValueError("API rate limit exceeded")

    # Verify error is propagated
    with pytest.raises(ValueError, match="API rate limit exceeded"):
        await failing_tool("test query")

    # Verify observation was updated with error metadata
    assert mock_client.update_current_span.called
    call_kwargs = mock_client.update_current_span.call_args.kwargs
    assert call_kwargs["metadata"]["error"] == "API rate limit exceeded"
    assert call_kwargs["level"] == "ERROR"
