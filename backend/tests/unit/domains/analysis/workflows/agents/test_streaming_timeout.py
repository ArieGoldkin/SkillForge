"""Unit tests for streaming and GeneratorExit handling.

These tests verify that streaming works correctly without application-level timeouts.
Timeout handling is managed by LangGraph's step_timeout on the compiled graph.

Also includes tests for LLM cost tracking functionality.
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
        "app.domains.analysis.workflows.agents.base.emit_agent_progress", new_callable=AsyncMock
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


# ===== Cost Tracking Tests =====


@pytest.mark.asyncio
async def test_streaming_extracts_model_name_from_chunks(mock_agent):
    """Test that model name is extracted from response_metadata in streaming chunks."""

    # Mock chunks with response_metadata containing model name
    async def mock_astream_generator(*args, **kwargs):
        # First chunk has model in response_metadata
        chunk1 = MagicMock()
        chunk1.response_metadata = {"model": "claude-3-5-sonnet-20241022"}
        chunk1.usage_metadata = None
        yield chunk1

        # Second chunk has usage metadata
        chunk2 = MagicMock()
        chunk2.response_metadata = {}
        chunk2.usage_metadata = MagicMock(input_tokens=1000, output_tokens=500)
        yield chunk2

        # Final chunk with structured response
        yield {
            "structured_response": {"findings": "test"},
            "messages": [MagicMock(content="complete")],
        }

    mock_agent.astream = mock_astream_generator

    with (
        patch(
            "app.domains.analysis.workflows.agents.streaming.calculate_llm_cost"
        ) as mock_cost_calc,
        patch(
            "app.domains.analysis.workflows.agents.streaming.get_langfuse_service"
        ) as mock_langfuse,
    ):
        mock_cost_calc.return_value = 0.0105
        mock_langfuse_service = MagicMock()
        mock_langfuse.return_value = mock_langfuse_service

        result = await stream_agent_response(
            agent=mock_agent,
            input_messages={"messages": [{"role": "user", "content": "test"}]},
            analysis_id="test-id",
            agent_type="tech_comparator",
            timeout=5.0,
        )

        # Verify cost calculation was called with correct model name
        mock_cost_calc.assert_called_once_with(
            model="claude-3-5-sonnet-20241022", input_tokens=1000, output_tokens=500
        )
        assert result is not None


@pytest.mark.asyncio
async def test_streaming_accumulates_token_counts(mock_agent):
    """Test that input and output tokens are accumulated correctly across chunks."""

    # Mock chunks with incremental token usage
    async def mock_astream_generator(*args, **kwargs):
        # First chunk with initial tokens
        chunk1 = MagicMock()
        chunk1.response_metadata = {"model": "gpt-4o"}
        chunk1.usage_metadata = MagicMock(input_tokens=500, output_tokens=100)
        yield chunk1

        # Second chunk with additional output tokens
        chunk2 = MagicMock()
        chunk2.response_metadata = {}
        chunk2.usage_metadata = MagicMock(input_tokens=500, output_tokens=150)
        yield chunk2

        # Third chunk with more output tokens
        chunk3 = MagicMock()
        chunk3.response_metadata = {}
        chunk3.usage_metadata = MagicMock(input_tokens=500, output_tokens=200)
        yield chunk3

        # Final chunk with structured response
        yield {
            "structured_response": {"findings": "test"},
            "messages": [MagicMock(content="complete")],
        }

    mock_agent.astream = mock_astream_generator

    with (
        patch(
            "app.domains.analysis.workflows.agents.streaming.calculate_llm_cost"
        ) as mock_cost_calc,
        patch(
            "app.domains.analysis.workflows.agents.streaming.get_langfuse_service"
        ) as mock_langfuse,
    ):
        mock_cost_calc.return_value = 0.005
        mock_langfuse_service = MagicMock()
        mock_langfuse.return_value = mock_langfuse_service

        await stream_agent_response(
            agent=mock_agent,
            input_messages={"messages": [{"role": "user", "content": "test"}]},
            analysis_id="test-id",
            agent_type="tech_comparator",
            timeout=5.0,
        )

        # Verify cost calculation was called with accumulated tokens
        # input_tokens should be 500 (last value, not accumulated)
        # output_tokens should be 450 (100 + 150 + 200)
        mock_cost_calc.assert_called_once_with(model="gpt-4o", input_tokens=500, output_tokens=450)


@pytest.mark.asyncio
async def test_streaming_submits_cost_score_to_langfuse(mock_agent):
    """Test that calculated cost is submitted to Langfuse as a score."""

    async def mock_astream_generator(*args, **kwargs):
        chunk = MagicMock()
        chunk.response_metadata = {"model": "claude-3-5-sonnet-20241022"}
        chunk.usage_metadata = MagicMock(input_tokens=2000, output_tokens=1000)
        yield chunk
        yield {
            "structured_response": {"findings": "test"},
            "messages": [MagicMock(content="complete")],
        }

    mock_agent.astream = mock_astream_generator

    with (
        patch(
            "app.domains.analysis.workflows.agents.streaming.calculate_llm_cost"
        ) as mock_cost_calc,
        patch(
            "app.domains.analysis.workflows.agents.streaming.get_langfuse_service"
        ) as mock_langfuse,
    ):
        mock_cost_calc.return_value = 0.021  # (2000/1M * 3) + (1000/1M * 15)
        mock_langfuse_service = MagicMock()
        mock_langfuse.return_value = mock_langfuse_service

        await stream_agent_response(
            agent=mock_agent,
            input_messages={"messages": [{"role": "user", "content": "test"}]},
            analysis_id="test-id",
            agent_type="tech_comparator",
            timeout=5.0,
        )

        # Verify Langfuse score submission
        mock_langfuse_service.submit_score.assert_called_once_with(
            name="cost_usd",
            value=0.021,
            comment="claude-3-5-sonnet-20241022: 2000in + 1000out = $0.021000",
        )


@pytest.mark.asyncio
async def test_streaming_handles_model_name_from_different_fields(mock_agent):
    """Test extraction of model name from various response_metadata field names."""

    # Test with "model_name" field instead of "model"
    async def mock_astream_generator_model_name(*args, **kwargs):
        chunk = MagicMock()
        chunk.response_metadata = {"model_name": "gpt-4-turbo-preview"}
        chunk.usage_metadata = MagicMock(input_tokens=1000, output_tokens=500)
        yield chunk
        yield {"structured_response": {"findings": "test"}, "messages": [MagicMock(content="done")]}

    mock_agent.astream = mock_astream_generator_model_name

    with (
        patch(
            "app.domains.analysis.workflows.agents.streaming.calculate_llm_cost"
        ) as mock_cost_calc,
        patch("app.domains.analysis.workflows.agents.streaming.get_langfuse_service"),
    ):
        mock_cost_calc.return_value = 0.025
        await stream_agent_response(
            agent=mock_agent,
            input_messages={"messages": [{"role": "user", "content": "test"}]},
            analysis_id="test-id",
            agent_type="tech_comparator",
            timeout=5.0,
        )
        mock_cost_calc.assert_called_once_with(
            model="gpt-4-turbo-preview", input_tokens=1000, output_tokens=500
        )

    # Test with "model_id" field
    async def mock_astream_generator_model_id(*args, **kwargs):
        chunk = MagicMock()
        chunk.response_metadata = {"model_id": "gemini-1.5-pro"}
        chunk.usage_metadata = MagicMock(input_tokens=800, output_tokens=400)
        yield chunk
        yield {"structured_response": {"findings": "test"}, "messages": [MagicMock(content="done")]}

    mock_agent.astream = mock_astream_generator_model_id

    with (
        patch(
            "app.domains.analysis.workflows.agents.streaming.calculate_llm_cost"
        ) as mock_cost_calc,
        patch("app.domains.analysis.workflows.agents.streaming.get_langfuse_service"),
    ):
        mock_cost_calc.return_value = 0.003
        await stream_agent_response(
            agent=mock_agent,
            input_messages={"messages": [{"role": "user", "content": "test"}]},
            analysis_id="test-id",
            agent_type="tech_comparator",
            timeout=5.0,
        )
        mock_cost_calc.assert_called_once_with(
            model="gemini-1.5-pro", input_tokens=800, output_tokens=400
        )


@pytest.mark.asyncio
async def test_streaming_skips_cost_tracking_when_model_unknown(mock_agent):
    """Test that cost tracking is skipped when model name cannot be determined."""

    async def mock_astream_generator(*args, **kwargs):
        # Chunk without response_metadata (model stays "unknown")
        chunk = MagicMock()
        chunk.response_metadata = {}
        chunk.usage_metadata = MagicMock(input_tokens=1000, output_tokens=500)
        yield chunk
        yield {"structured_response": {"findings": "test"}, "messages": [MagicMock(content="done")]}

    mock_agent.astream = mock_astream_generator

    with (
        patch(
            "app.domains.analysis.workflows.agents.streaming.calculate_llm_cost"
        ) as mock_cost_calc,
        patch(
            "app.domains.analysis.workflows.agents.streaming.get_langfuse_service"
        ) as mock_langfuse,
    ):
        await stream_agent_response(
            agent=mock_agent,
            input_messages={"messages": [{"role": "user", "content": "test"}]},
            analysis_id="test-id",
            agent_type="tech_comparator",
            timeout=5.0,
        )

        # Cost calculation should NOT be called when model is "unknown"
        mock_cost_calc.assert_not_called()
        mock_langfuse.assert_not_called()


@pytest.mark.asyncio
async def test_streaming_skips_cost_tracking_when_no_input_tokens(mock_agent):
    """Test that cost tracking is skipped when input_tokens is 0."""

    async def mock_astream_generator(*args, **kwargs):
        chunk = MagicMock()
        chunk.response_metadata = {"model": "claude-3-5-sonnet-20241022"}
        chunk.usage_metadata = MagicMock(input_tokens=0, output_tokens=500)
        yield chunk
        yield {"structured_response": {"findings": "test"}, "messages": [MagicMock(content="done")]}

    mock_agent.astream = mock_astream_generator

    with (
        patch(
            "app.domains.analysis.workflows.agents.streaming.calculate_llm_cost"
        ) as mock_cost_calc,
        patch(
            "app.domains.analysis.workflows.agents.streaming.get_langfuse_service"
        ) as mock_langfuse,
    ):
        await stream_agent_response(
            agent=mock_agent,
            input_messages={"messages": [{"role": "user", "content": "test"}]},
            analysis_id="test-id",
            agent_type="tech_comparator",
            timeout=5.0,
        )

        # Cost calculation should NOT be called when input_tokens is 0
        mock_cost_calc.assert_not_called()
        mock_langfuse.assert_not_called()


@pytest.mark.asyncio
async def test_streaming_cost_tracking_graceful_degradation(mock_agent):
    """Test that cost tracking failures don't break agent execution."""

    async def mock_astream_generator(*args, **kwargs):
        chunk = MagicMock()
        chunk.response_metadata = {"model": "claude-3-5-sonnet-20241022"}
        chunk.usage_metadata = MagicMock(input_tokens=1000, output_tokens=500)
        yield chunk
        yield {
            "structured_response": {"findings": "test"},
            "messages": [MagicMock(content="complete")],
        }

    mock_agent.astream = mock_astream_generator

    # Mock calculate_llm_cost to raise an exception
    with (
        patch(
            "app.domains.analysis.workflows.agents.streaming.calculate_llm_cost",
            side_effect=ValueError("Pricing not found"),
        ),
        patch(
            "app.domains.analysis.workflows.agents.streaming.get_langfuse_service"
        ) as mock_langfuse,
    ):
        mock_langfuse_service = MagicMock()
        mock_langfuse.return_value = mock_langfuse_service

        # Should complete successfully despite cost tracking failure
        result = await stream_agent_response(
            agent=mock_agent,
            input_messages={"messages": [{"role": "user", "content": "test"}]},
            analysis_id="test-id",
            agent_type="tech_comparator",
            timeout=5.0,
        )

        # Verify agent execution succeeded
        assert result is not None
        assert "structured_response" in result

        # Langfuse submit_score should NOT be called due to cost calculation error
        mock_langfuse_service.submit_score.assert_not_called()


@pytest.mark.asyncio
async def test_streaming_cost_tracking_langfuse_submission_failure(mock_agent):
    """Test that Langfuse submission failures don't break agent execution."""

    async def mock_astream_generator(*args, **kwargs):
        chunk = MagicMock()
        chunk.response_metadata = {"model": "gpt-4o"}
        chunk.usage_metadata = MagicMock(input_tokens=1000, output_tokens=500)
        yield chunk
        yield {
            "structured_response": {"findings": "test"},
            "messages": [MagicMock(content="complete")],
        }

    mock_agent.astream = mock_astream_generator

    with (
        patch(
            "app.domains.analysis.workflows.agents.streaming.calculate_llm_cost"
        ) as mock_cost_calc,
        patch(
            "app.domains.analysis.workflows.agents.streaming.get_langfuse_service"
        ) as mock_langfuse,
    ):
        mock_cost_calc.return_value = 0.0075
        mock_langfuse_service = MagicMock()
        # Mock submit_score to raise an exception
        mock_langfuse_service.submit_score.side_effect = RuntimeError("Langfuse API down")
        mock_langfuse.return_value = mock_langfuse_service

        # Should complete successfully despite Langfuse failure
        result = await stream_agent_response(
            agent=mock_agent,
            input_messages={"messages": [{"role": "user", "content": "test"}]},
            analysis_id="test-id",
            agent_type="tech_comparator",
            timeout=5.0,
        )

        # Verify agent execution succeeded
        assert result is not None
        assert "structured_response" in result

        # Cost calculation should have been called
        mock_cost_calc.assert_called_once_with(model="gpt-4o", input_tokens=1000, output_tokens=500)


@pytest.mark.asyncio
async def test_streaming_cost_tracking_logs_correctly(mock_agent):
    """Test that cost tracking generates correct log messages."""

    async def mock_astream_generator(*args, **kwargs):
        chunk = MagicMock()
        chunk.response_metadata = {"model": "claude-3-5-sonnet-20241022"}
        chunk.usage_metadata = MagicMock(input_tokens=1500, output_tokens=750)
        yield chunk
        yield {"structured_response": {"findings": "test"}, "messages": [MagicMock(content="done")]}

    mock_agent.astream = mock_astream_generator

    with (
        patch(
            "app.domains.analysis.workflows.agents.streaming.calculate_llm_cost"
        ) as mock_cost_calc,
        patch(
            "app.domains.analysis.workflows.agents.streaming.get_langfuse_service"
        ) as mock_langfuse,
        patch("app.domains.analysis.workflows.agents.streaming.logger") as mock_logger,
    ):
        mock_cost_calc.return_value = 0.01575  # (1500/1M * 3) + (750/1M * 15)
        mock_langfuse_service = MagicMock()
        mock_langfuse.return_value = mock_langfuse_service

        await stream_agent_response(
            agent=mock_agent,
            input_messages={"messages": [{"role": "user", "content": "test"}]},
            analysis_id="test-id",
            agent_type="tech_comparator",
            timeout=5.0,
        )

        # Verify logging calls
        # Should log token usage
        assert any(
            call.args[0] == "streaming_llm_usage" for call in mock_logger.info.call_args_list
        ), "Should log streaming_llm_usage"

        # Should log cost tracked
        assert any(
            call.args[0] == "streaming_cost_tracked" for call in mock_logger.debug.call_args_list
        ), "Should log streaming_cost_tracked"


@pytest.mark.asyncio
async def test_streaming_cost_tracking_no_tokens_consumed(mock_agent):
    """Test that cost tracking is skipped when total_tokens is 0."""

    async def mock_astream_generator(*args, **kwargs):
        # Chunk without usage_metadata (total_tokens stays 0)
        chunk = MagicMock()
        chunk.response_metadata = {"model": "claude-3-5-sonnet-20241022"}
        chunk.usage_metadata = None
        yield chunk
        yield {"structured_response": {"findings": "test"}, "messages": [MagicMock(content="done")]}

    mock_agent.astream = mock_astream_generator

    with (
        patch(
            "app.domains.analysis.workflows.agents.streaming.calculate_llm_cost"
        ) as mock_cost_calc,
        patch(
            "app.domains.analysis.workflows.agents.streaming.get_langfuse_service"
        ) as mock_langfuse,
        patch("app.domains.analysis.workflows.agents.streaming.logger") as mock_logger,
    ):
        await stream_agent_response(
            agent=mock_agent,
            input_messages={"messages": [{"role": "user", "content": "test"}]},
            analysis_id="test-id",
            agent_type="tech_comparator",
            timeout=5.0,
        )

        # Should NOT log token usage when total_tokens is 0
        assert not any(
            call.args[0] == "streaming_llm_usage" for call in mock_logger.info.call_args_list
        ), "Should not log streaming_llm_usage when total_tokens is 0"

        # Cost calculation and Langfuse submission should NOT be called
        mock_cost_calc.assert_not_called()
        mock_langfuse.assert_not_called()
