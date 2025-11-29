"""Unit tests for streaming timeout and GeneratorExit handling.

These tests verify the clean timeout handling pattern that avoids
asyncio.wait_for cancellation (which causes GeneratorExit errors in LangGraph).
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.workflows.agents.streaming import stream_agent_response


@pytest.fixture
def mock_agent():
    """Mock agent with astream method."""
    agent = MagicMock()
    agent.astream = AsyncMock()
    return agent


@pytest.mark.asyncio
async def test_streaming_timeout_uses_clean_break_not_cancellation(mock_agent):
    """Test that timeout uses clean break instead of asyncio cancellation.

    The new implementation checks timeout manually and breaks the loop,
    which avoids GeneratorExit from asyncio.wait_for cancellation.
    """
    import asyncio

    chunk_count = 0

    # Mock agent.astream to be an async generator that yields slowly
    async def mock_astream_generator(*args, **kwargs):
        nonlocal chunk_count
        for i in range(100):  # Many chunks
            await asyncio.sleep(0.02)  # 20ms per chunk
            chunk_count += 1
            yield {"messages": [{"role": "assistant", "content": f"chunk {i}"}]}

    # Set astream to return the async generator
    mock_agent.astream = mock_astream_generator

    input_messages = {"messages": [{"role": "user", "content": "test"}]}

    # Should raise TimeoutError via clean timeout check (not asyncio cancellation)
    with pytest.raises(TimeoutError, match="exceeded timeout"):
        await stream_agent_response(
            agent=mock_agent,
            input_messages=input_messages,
            analysis_id="test-id",
            agent_type="test_agent",
            timeout=0.05,  # 50ms timeout - should process ~2-3 chunks
        )

    # Verify some chunks were processed before timeout
    assert chunk_count > 0


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
        raise GeneratorExit("Generator closed by LangGraph")

    # Set astream to return the async generator
    mock_agent.astream = mock_astream_generator

    input_messages = {"messages": [{"role": "user", "content": "test"}]}

    # Should preserve partial result when GeneratorExit occurs
    result = await stream_agent_response(
        agent=mock_agent,
        input_messages=input_messages,
        analysis_id="test-id",
        agent_type="test_agent",
        timeout=5.0,  # Long timeout - GeneratorExit happens from generator itself
    )

    # Should return the partial result
    assert result is not None
    assert "messages" in result


@pytest.mark.asyncio
async def test_streaming_timeout_handles_slow_iteration(mock_agent):
    """Test that timeout works when iteration is slow."""
    import asyncio

    # Mock agent.astream to be an async generator that never yields
    async def mock_astream_generator(*args, **kwargs):
        await asyncio.sleep(10)  # Very long sleep before first yield
        yield {"messages": []}

    # Set astream to return the async generator
    mock_agent.astream = mock_astream_generator

    input_messages = {"messages": [{"role": "user", "content": "test"}]}

    # Note: With the new implementation, timeout is checked between chunks.
    # If the first chunk takes too long, the timeout won't trigger until
    # after the chunk is received. For truly blocking operations, we may
    # need asyncio.timeout (Python 3.11+) or different approach.
    # This test verifies current behavior.
    with pytest.raises((TimeoutError, asyncio.TimeoutError)):
        await stream_agent_response(
            agent=mock_agent,
            input_messages=input_messages,
            analysis_id="test-id",
            agent_type="test_agent",
            timeout=0.05,  # Very short timeout
        )


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
        raise GeneratorExit("Generator closed")

    # Set astream to return the async generator
    mock_agent.astream = mock_astream_generator

    input_messages = {"messages": [{"role": "user", "content": "test"}]}

    # When GeneratorExit occurs during iteration (not from timeout cancellation),
    # it's caught in the inner try-except block (lines 141-151).
    # If a partial result exists, it's preserved and the function returns successfully.
    # This is the expected behavior - we want to preserve partial results when possible.
    result = await stream_agent_response(
        agent=mock_agent,
        input_messages=input_messages,
        analysis_id="test-id",
        agent_type="test_agent",
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
        agent_type="test_agent",
        timeout=5.0,
    )

    assert result is not None
    assert "structured_response" in result
