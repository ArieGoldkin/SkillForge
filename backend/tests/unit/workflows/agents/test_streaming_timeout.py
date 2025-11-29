"""Unit tests for streaming timeout and GeneratorExit handling."""

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
async def test_streaming_timeout_converts_generatorexit_to_timeouterror(mock_agent):
    """Test that GeneratorExit from timeout is converted to TimeoutError."""
    import asyncio

    # Mock agent.astream to be an async generator that raises GeneratorExit
    async def mock_astream_generator(*args, **kwargs):
        await asyncio.sleep(0.01)  # Small delay
        raise GeneratorExit("Generator closed by timeout")
        yield  # This line won't be reached, but makes it an async generator

    # Set astream to return the async generator, not a coroutine
    mock_agent.astream = mock_astream_generator

    input_messages = {"messages": [{"role": "user", "content": "test"}]}

    # Should convert GeneratorExit to TimeoutError
    with pytest.raises(TimeoutError, match="exceeded timeout.*generator closed"):
        await stream_agent_response(
            agent=mock_agent,
            input_messages=input_messages,
            analysis_id="test-id",
            agent_type="test_agent",
            timeout=0.05,  # Very short timeout to trigger quickly
        )


@pytest.mark.asyncio
async def test_streaming_timeout_handles_timeouterror(mock_agent):
    """Test that TimeoutError is handled correctly."""
    import asyncio

    # Mock agent.astream to be an async generator that never completes
    async def mock_astream_generator(*args, **kwargs):
        await asyncio.sleep(10)  # Longer than timeout
        yield {"messages": []}

    # Set astream to return the async generator
    mock_agent.astream = mock_astream_generator

    input_messages = {"messages": [{"role": "user", "content": "test"}]}

    # Should raise TimeoutError
    with pytest.raises(TimeoutError, match="exceeded timeout"):
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
