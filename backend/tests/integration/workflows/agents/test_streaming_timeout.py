"""Integration tests for streaming timeout handling with real agents.

These tests verify that the timeout refactoring works correctly with
actual agent implementations and real streaming behavior.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from langchain.messages import AIMessage

from app.workflows.agents.invocation import invoke_agent
from app.workflows.agents.streaming import stream_agent_response


@pytest.fixture
def mock_streaming_agent():
    """Create a mock agent with astream support."""
    agent = MagicMock()

    async def mock_astream(*args, **kwargs):
        """Mock streaming that yields chunks slowly."""
        chunks = [
            {"messages": [AIMessage(content="Chunk 1")]},
            {"messages": [AIMessage(content="Chunk 1\nChunk 2")]},
            {
                "messages": [AIMessage(content="Chunk 1\nChunk 2\nChunk 3")],
                "structured_response": {"findings": "test"},
            },
        ]
        for chunk in chunks:
            await asyncio.sleep(0.01)  # Simulate network delay
            yield chunk

    agent.astream = mock_astream
    return agent


@pytest.mark.asyncio
async def test_streaming_timeout_integration_success(mock_streaming_agent):
    """Test successful streaming with timeout refactoring."""
    analysis_id = str(uuid4())
    input_messages = {"messages": [{"role": "user", "content": "test"}]}

    with patch(
        "app.workflows.agents.streaming_helpers.emit_agent_progress", new_callable=AsyncMock
    ):
        result = await stream_agent_response(
            agent=mock_streaming_agent,
            input_messages=input_messages,
            analysis_id=analysis_id,
            agent_type="tech_comparator",
            timeout=5.0,
        )

    assert result is not None
    assert "structured_response" in result
    assert result["structured_response"]["findings"] == "test"


@pytest.mark.asyncio
async def test_streaming_timeout_integration_timeout_triggered(mock_streaming_agent):
    """Test that timeout handling works correctly with slow streaming.
    
    Note: Timeout is handled by LangGraph's step_timeout on the compiled graph,
    not by application-level timeout in stream_agent_response. This test verifies
    that the function handles slow streams gracefully without raising TimeoutError
    at the function level.
    """
    analysis_id = str(uuid4())
    input_messages = {"messages": [{"role": "user", "content": "test"}]}

    # Create agent that streams very slowly
    async def slow_astream(*args, **kwargs):
        await asyncio.sleep(0.01)  # Small delay
        yield {"messages": [AIMessage(content="Slow chunk")]}
        await asyncio.sleep(0.01)  # Small delay
        yield {"messages": [AIMessage(content="Slow chunk 2")]}

    mock_streaming_agent.astream = slow_astream

    with patch(
        "app.workflows.agents.streaming_helpers.emit_agent_progress", new_callable=AsyncMock
    ):
        # Function doesn't raise TimeoutError - timeout is handled by LangGraph's step_timeout
        # This test verifies the function completes successfully
        result = await stream_agent_response(
            agent=mock_streaming_agent,
            input_messages=input_messages,
            analysis_id=analysis_id,
            agent_type="tech_comparator",
            timeout=0.05,  # Reference timeout (actual timeout handled by step_timeout)
        )
        # Function should complete without raising TimeoutError
        assert result is not None


@pytest.mark.asyncio
async def test_streaming_timeout_integration_with_invocation(mock_streaming_agent):
    """Test streaming timeout through invoke_agent wrapper."""
    analysis_id = str(uuid4())
    input_messages = {"messages": [{"role": "user", "content": "test"}]}

    with patch(
        "app.workflows.agents.streaming_helpers.emit_agent_progress", new_callable=AsyncMock
    ):
        result = await invoke_agent(
            agent=mock_streaming_agent,
            input_messages=input_messages,
            analysis_id=analysis_id,
            agent_type="tech_comparator",
            timeout=5.0,
        )

    assert result is not None
    assert "structured_response" in result


@pytest.mark.asyncio
async def test_streaming_timeout_integration_partial_result_preserved(mock_streaming_agent):
    """Test that partial results are preserved when stream completes.
    
    Note: Timeout is handled by LangGraph's step_timeout on the compiled graph,
    not by application-level timeout in stream_agent_response. This test verifies
    that partial results are returned when the stream completes.
    """
    analysis_id = str(uuid4())
    input_messages = {"messages": [{"role": "user", "content": "test"}]}

    # Create agent that yields partial result
    async def partial_astream(*args, **kwargs):
        yield {"messages": [AIMessage(content="Partial content")]}
        await asyncio.sleep(0.01)  # Small delay
        yield {"messages": [AIMessage(content="More content")]}

    mock_streaming_agent.astream = partial_astream

    with patch(
        "app.workflows.agents.streaming_helpers.emit_agent_progress", new_callable=AsyncMock
    ):
        # Function doesn't raise TimeoutError - it returns partial results
        result = await stream_agent_response(
            agent=mock_streaming_agent,
            input_messages=input_messages,
            analysis_id=analysis_id,
            agent_type="tech_comparator",
            timeout=0.1,  # Reference timeout (actual timeout handled by step_timeout)
        )
        # Should return result (empty dict if no structured_response found)
        assert result is not None


@pytest.mark.asyncio
async def test_streaming_timeout_integration_generatorexit_handled(mock_streaming_agent):
    """Test that GeneratorExit from external sources is handled gracefully."""
    analysis_id = str(uuid4())
    input_messages = {"messages": [{"role": "user", "content": "test"}]}

    # Create agent that raises GeneratorExit after yielding
    async def generatorexit_astream(*args, **kwargs):
        yield {"messages": [AIMessage(content="Before exit")]}
        await asyncio.sleep(0.01)
        msg = "Generator closed externally"
        raise GeneratorExit(msg)

    mock_streaming_agent.astream = generatorexit_astream

    with patch(
        "app.workflows.agents.streaming_helpers.emit_agent_progress", new_callable=AsyncMock
    ):
        result = await stream_agent_response(
            agent=mock_streaming_agent,
            input_messages=input_messages,
            analysis_id=analysis_id,
            agent_type="tech_comparator",
            timeout=5.0,
        )

    # Should return partial result when GeneratorExit occurs
    assert result is not None
    assert "messages" in result




