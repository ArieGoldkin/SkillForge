"""Unit tests for streaming and GeneratorExit handling.

These tests verify that streaming works correctly without application-level timeouts.
Timeout handling is managed by LangGraph's step_timeout on the compiled graph.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.workflows.agents.streaming import stream_agent_response



@pytest.fixture
def mock_agent():
    """Mock agent with astream method."""
    agent = MagicMock()
    agent.astream = AsyncMock()
    return agent


@pytest.fixture(autouse=True)
def mock_emit_progress():
    """Auto-mock emit_agent_progress to avoid agent_type validation."""
    with patch(
        "app.workflows.agents.streaming_helpers.emit_agent_progress", new_callable=AsyncMock
    ):
        yield


@pytest.mark.asyncio
async def test_streaming_completes_successfully(mock_agent):
    """Test that streaming completes successfully without application-level timeout.

    With the new implementation, timeout is handled by LangGraph's step_timeout.
    The function should complete successfully and return results.
    """
    import asyncio

    chunk_count = 0

    # Mock agent.astream to be an async generator that yields chunks
    async def mock_astream_generator(*args, **kwargs):
        nonlocal chunk_count
        for i in range(5):  # 5 chunks
            await asyncio.sleep(0.01)  # 10ms per chunk
            chunk_count += 1
            yield {"messages": [{"role": "assistant", "content": f"chunk {i}"}]}

    # Set astream to return the async generator
    mock_agent.astream = mock_astream_generator

    input_messages = {"messages": [{"role": "user", "content": "test"}]}

    # Should complete successfully (timeout handled by step_timeout)
    result = await stream_agent_response(
        agent=mock_agent,
        input_messages=input_messages,
        analysis_id="test-id",
        agent_type="tech_comparator",
        timeout=5.0,  # Reference timeout (not used - step_timeout handles it)
    )

    # Verify chunks were processed and result returned
    assert chunk_count == 5
    assert result is not None


@pytest.mark.asyncio
async def test_streaming_generatorexit_still_handled_gracefully(mock_agent):
    """Test that GeneratorExit from external sources is still handled.

    Even though we no longer use asyncio.wait_for, GeneratorExit can still
    occur from LangGraph internals. This should be handled gracefully.
    """
    import asyncio

    # Mock agent.astream to raise GeneratorExit (simulating LangGraph internal closure)
    async def mock_astream_generator(*args, **kwargs):
        yield {"messages": [{"role": "assistant", "content": "partial"}]}
        await asyncio.sleep(0.01)
        msg = "Generator closed by LangGraph"
        raise GeneratorExit(msg)

    # Set astream to return the async generator
    mock_agent.astream = mock_astream_generator

    input_messages = {"messages": [{"role": "user", "content": "test"}]}

    # Should preserve partial result when GeneratorExit occurs
    result = await stream_agent_response(
        agent=mock_agent,
        input_messages=input_messages,
        analysis_id="test-id",
        agent_type="tech_comparator",
        timeout=5.0,  # Long timeout - GeneratorExit happens from generator itself
    )

    # Should return the partial result
    assert result is not None
    assert "messages" in result


@pytest.mark.asyncio
async def test_streaming_handles_slow_iteration(mock_agent):
    """Test that streaming handles slow iteration gracefully.

    With step_timeout handling timeouts, slow iteration will be cancelled
    by LangGraph's step_timeout. The function should handle this gracefully.
    """
    import asyncio

    # Mock agent.astream to be an async generator that yields after delay
    async def mock_astream_generator(*args, **kwargs):
        await asyncio.sleep(0.1)  # 100ms delay before first yield
        yield {"messages": [{"role": "assistant", "content": "result"}]}

    # Set astream to return the async generator
    mock_agent.astream = mock_astream_generator

    input_messages = {"messages": [{"role": "user", "content": "test"}]}

    # Should complete successfully (step_timeout will handle actual timeout)
    result = await stream_agent_response(
        agent=mock_agent,
        input_messages=input_messages,
        analysis_id="test-id",
        agent_type="tech_comparator",
        timeout=5.0,  # Reference timeout (not used - step_timeout handles it)
    )

    # Should return result
    assert result is not None


@pytest.mark.asyncio
async def test_streaming_generatorexit_preserves_partial_result(mock_agent):
    """Test that GeneratorExit preserves partial result when it occurs during iteration."""
    import asyncio

    # Mock agent.astream to yield partial result then raise GeneratorExit
    # This simulates a GeneratorExit that occurs during async iteration
    # (not from asyncio.wait_for timeout cancellation)
    async def mock_astream_generator(*args, **kwargs):
        yield {"messages": [{"role": "assistant", "content": "partial"}]}
        await asyncio.sleep(0.01)
        msg = "Generator closed"
        raise GeneratorExit(msg)

    # Set astream to return the async generator
    mock_agent.astream = mock_astream_generator

    input_messages = {"messages": [{"role": "user", "content": "test"}]}

    # When GeneratorExit occurs during iteration (not from timeout cancellation),
    # it's caught in the exception handler.
    # If a partial result exists, it's preserved and the function returns successfully.
    # This is the expected behavior - we want to preserve partial results when possible.
    result = await stream_agent_response(
        agent=mock_agent,
        input_messages=input_messages,
        analysis_id="test-id",
        agent_type="tech_comparator",
        timeout=5.0,  # Long timeout - GeneratorExit happens during iteration
    )

    # Should return the partial result that was yielded before GeneratorExit
    assert result is not None
    assert "messages" in result


@pytest.mark.asyncio
async def test_streaming_success_returns_result(mock_agent):
    """Test successful streaming returns result."""

    # Mock agent.astream to yield structured response
    async def mock_astream_generator(*args, **kwargs):
        yield {
            "structured_response": {"findings": "test"},
            "messages": [{"role": "assistant", "content": "complete"}],
        }

    # Set astream to return the async generator
    mock_agent.astream = mock_astream_generator

    input_messages = {"messages": [{"role": "user", "content": "test"}]}

    result = await stream_agent_response(
        agent=mock_agent,
        input_messages=input_messages,
        analysis_id="test-id",
        agent_type="tech_comparator",
        timeout=5.0,
    )

    assert result is not None
    assert "structured_response" in result
