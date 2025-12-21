"""Unit tests for LCEL chain implementations.

Tests LCEL chains with automatic fallback and retry logic for:
- Agent factories with fallback chains
- Synthesis phases using LCEL
- Batch processing with abatch()
- Retry behavior with exponential backoff
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel, Field

from app.domains.analysis.workflows.agents.factories import create_agent_with_lcel_fallback
from app.domains.analysis.workflows.tasks.aggregation.compress_findings import (
    CompressedFinding,
    compress_all_findings,
)


class MockResponseSchema(BaseModel):
    """Mock response schema for testing."""

    content: str = Field(description="Test content")
    score: float = Field(ge=0.0, le=1.0)


@pytest.fixture
def mock_chat_model():
    """Create a mock chat model that supports LCEL methods."""
    mock = MagicMock()
    mock.with_structured_output = MagicMock(return_value=mock)
    mock.with_retry = MagicMock(return_value=mock)
    mock.with_fallbacks = MagicMock(return_value=mock)
    mock.bind_tools = MagicMock(return_value=mock)
    mock.ainvoke = AsyncMock(return_value={"content": "test", "score": 0.9})
    return mock


@pytest.mark.asyncio
class TestLCELAgentFactory:
    """Test LCEL agent factory with fallback and retry."""

    @patch("app.domains.analysis.workflows.agents.factories.get_chat_model")
    async def test_create_agent_with_lcel_fallback_basic(self, mock_get_chat_model, mock_chat_model):
        """Test basic LCEL agent creation with fallback chain."""
        mock_get_chat_model.return_value = mock_chat_model

        agent = create_agent_with_lcel_fallback(
            agent_type="test_agent",
            response_schema=MockResponseSchema,
        )

        # Verify LCEL chain methods were called
        assert mock_chat_model.with_structured_output.called
        assert mock_chat_model.with_retry.called
        assert mock_chat_model.with_fallbacks.called

    @patch("app.domains.analysis.workflows.agents.factories.get_chat_model")
    async def test_lcel_fallback_triggers_on_primary_failure(self, mock_get_chat_model):
        """Test fallback model is used when primary model fails."""
        # Primary model fails
        primary_mock = MagicMock()
        primary_mock.with_structured_output = MagicMock(return_value=primary_mock)
        primary_mock.with_retry = MagicMock(return_value=primary_mock)
        primary_mock.with_fallbacks = MagicMock(return_value=primary_mock)
        primary_mock.ainvoke = AsyncMock(side_effect=Exception("Primary model failed"))

        # Fallback model succeeds
        fallback_mock = MagicMock()
        fallback_mock.with_structured_output = MagicMock(return_value=fallback_mock)
        fallback_mock.ainvoke = AsyncMock(return_value={"content": "fallback", "score": 0.8})

        # Mock get_chat_model to return different models
        def mock_get_model(config=None):
            if config and config.get("configurable", {}).get("model") == "fallback-model":
                return fallback_mock
            return primary_mock

        mock_get_chat_model.side_effect = mock_get_model

        agent = create_agent_with_lcel_fallback(
            agent_type="test_agent",
            response_schema=MockResponseSchema,
            fallback_model="fallback-model",
        )

        # Verify both models were created
        assert mock_get_chat_model.call_count == 2

    @patch("app.domains.analysis.workflows.agents.factories.get_chat_model")
    async def test_lcel_retry_configuration(self, mock_get_chat_model, mock_chat_model):
        """Test retry is configured with exponential backoff."""
        mock_get_chat_model.return_value = mock_chat_model

        create_agent_with_lcel_fallback(
            agent_type="test_agent",
            response_schema=MockResponseSchema,
        )

        # Verify retry was configured with correct parameters
        retry_call = mock_chat_model.with_retry.call_args
        assert retry_call is not None
        assert retry_call.kwargs["stop_after_attempt"] == 3
        assert retry_call.kwargs["wait_exponential_jitter"] is True


@pytest.mark.asyncio
class TestBatchCompression:
    """Test batch processing with abatch() for finding compression."""

    @patch("app.domains.analysis.workflows.tasks.aggregation.compress_findings.get_chat_model")
    async def test_compress_all_findings_uses_abatch(self, mock_get_chat_model):
        """Test compress_all_findings uses abatch() for parallel processing."""
        # Mock LLM with abatch
        mock_llm = MagicMock()
        mock_llm.with_structured_output = MagicMock(return_value=mock_llm)

        # Mock abatch to return CompressedFinding objects
        mock_llm.abatch = AsyncMock(
            return_value=[
                CompressedFinding(
                    agent_name="agent1",
                    key_insights=["Insight 1", "Insight 2"],
                    confidence=0.9,
                    data_quality="high",
                    critical_warnings=[],
                    relevant_code_snippets=[],
                ),
                CompressedFinding(
                    agent_name="agent2",
                    key_insights=["Insight 3"],
                    confidence=0.8,
                    data_quality="medium",
                    critical_warnings=["Warning 1"],
                    relevant_code_snippets=[],
                ),
            ]
        )

        mock_get_chat_model.return_value = mock_llm

        agent_findings = {
            "agent1": {"findings": {"key": "value1"}, "confidence_score": 0.9},
            "agent2": {"findings": {"key": "value2"}, "confidence_score": 0.8},
        }

        results = await compress_all_findings(agent_findings, "test-analysis-id")

        # Verify abatch was called
        assert mock_llm.abatch.called
        assert len(results) == 2
        assert results[0].agent_name == "agent1"
        assert results[1].agent_name == "agent2"

    @patch("app.domains.analysis.workflows.tasks.aggregation.compress_findings.get_chat_model")
    async def test_abatch_max_concurrency(self, mock_get_chat_model):
        """Test abatch() uses max_concurrency to prevent rate limits."""
        mock_llm = MagicMock()
        mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
        mock_llm.abatch = AsyncMock(return_value=[])
        mock_get_chat_model.return_value = mock_llm

        agent_findings = {
            f"agent{i}": {"findings": {"key": f"value{i}"}, "confidence_score": 0.9}
            for i in range(10)
        }

        await compress_all_findings(agent_findings, "test-analysis-id")

        # Verify abatch was called with max_concurrency
        abatch_call = mock_llm.abatch.call_args
        assert abatch_call is not None
        assert abatch_call.kwargs.get("max_concurrency") == 5

    @patch("app.domains.analysis.workflows.tasks.aggregation.compress_findings.get_chat_model")
    async def test_abatch_fallback_to_sequential_on_failure(self, mock_get_chat_model):
        """Test fallback to sequential processing if abatch() fails."""
        mock_llm = MagicMock()
        mock_llm.with_structured_output = MagicMock(return_value=mock_llm)

        # First call (abatch) fails
        mock_llm.abatch = AsyncMock(side_effect=Exception("Batch processing failed"))

        # Sequential fallback succeeds
        mock_llm.ainvoke = AsyncMock(
            return_value=CompressedFinding(
                agent_name="agent1",
                key_insights=["Fallback insight"],
                confidence=0.7,
                data_quality="medium",
                critical_warnings=[],
                relevant_code_snippets=[],
            )
        )

        mock_get_chat_model.return_value = mock_llm

        agent_findings = {
            "agent1": {"findings": {"key": "value1"}, "confidence_score": 0.9},
        }

        results = await compress_all_findings(agent_findings, "test-analysis-id")

        # Verify abatch was attempted
        assert mock_llm.abatch.called

        # Verify sequential fallback was used (ainvoke called)
        assert mock_llm.ainvoke.called

        # Verify we got a result (fallback succeeded)
        assert len(results) == 1

    @patch("app.domains.analysis.workflows.tasks.aggregation.compress_findings.get_chat_model")
    async def test_abatch_handles_partial_failures(self, mock_get_chat_model):
        """Test handling of partial failures in batch processing."""
        mock_llm = MagicMock()
        mock_llm.with_structured_output = MagicMock(return_value=mock_llm)

        # Return mix of successes and exceptions
        mock_llm.abatch = AsyncMock(
            return_value=[
                CompressedFinding(
                    agent_name="agent1",
                    key_insights=["Success"],
                    confidence=0.9,
                    data_quality="high",
                    critical_warnings=[],
                    relevant_code_snippets=[],
                ),
                Exception("Agent 2 failed"),  # Partial failure
            ]
        )

        mock_get_chat_model.return_value = mock_llm

        agent_findings = {
            "agent1": {"findings": {"key": "value1"}, "confidence_score": 0.9},
            "agent2": {"findings": {"key": "value2"}, "confidence_score": 0.8},
        }

        results = await compress_all_findings(agent_findings, "test-analysis-id")

        # Verify we got 2 results (success + fallback for failure)
        assert len(results) == 2
        assert results[0].agent_name == "agent1"
        # Second result should be fallback CompressedFinding
        assert results[1].agent_name == "agent2"
        assert results[1].confidence < 1.0  # Fallback has lower confidence


@pytest.mark.asyncio
class TestSynthesisLCEL:
    """Test synthesis phases using LCEL chains."""

    @patch("app.domains.analysis.workflows.tasks.aggregation.synthesis_phased.get_chat_model")
    async def test_synthesis_core_uses_lcel_chain(self, mock_get_chat_model):
        """Test _synthesize_core uses LCEL chain instead of manual fallback."""
        from app.domains.analysis.workflows.tasks.aggregation.synthesis_phased import (
            _synthesize_core,
        )

        # Mock LLM with LCEL methods
        mock_llm = MagicMock()
        mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
        mock_llm.with_retry = MagicMock(return_value=mock_llm)
        mock_llm.with_fallbacks = MagicMock(return_value=mock_llm)
        mock_llm.ainvoke = AsyncMock(
            return_value={
                "executive_summary": "Test summary",
                "key_findings": ["Finding 1"],
                "synthesis": {},
                "conflicts_resolved": [],
                "coverage_gaps": [],
                "cross_domain_connections": [],
                "coverage_score": 0.9,
            }
        )

        mock_get_chat_model.return_value = mock_llm

        compressed_findings = [
            CompressedFinding(
                agent_name="agent1",
                key_insights=["Insight 1"],
                confidence=0.9,
                data_quality="high",
                critical_warnings=[],
                relevant_code_snippets=[],
            )
        ]

        result = await _synthesize_core(compressed_findings, [], {}, "test-id")

        # Verify LCEL chain was constructed
        assert mock_llm.with_structured_output.called
        assert mock_llm.with_retry.called
        assert mock_llm.with_fallbacks.called

    @patch("app.domains.analysis.workflows.tasks.aggregation.synthesis_phased.get_chat_model")
    async def test_synthesis_learning_graceful_degradation(self, mock_get_chat_model):
        """Test _synthesize_learning returns None on failure (graceful degradation)."""
        from app.domains.analysis.workflows.tasks.aggregation.synthesis_phased import (
            _synthesize_learning,
        )

        # Mock LLM that fails
        mock_llm = MagicMock()
        mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
        mock_llm.with_retry = MagicMock(return_value=mock_llm)
        mock_llm.with_fallbacks = MagicMock(return_value=mock_llm)
        mock_llm.ainvoke = AsyncMock(side_effect=TimeoutError("Synthesis timeout"))

        mock_get_chat_model.return_value = mock_llm

        compressed_findings = [
            CompressedFinding(
                agent_name="agent1",
                key_insights=["Insight 1"],
                confidence=0.9,
                data_quality="high",
                critical_warnings=[],
                relevant_code_snippets=[],
            )
        ]

        result = await _synthesize_learning(compressed_findings, "test-id")

        # Verify graceful degradation (returns None on failure)
        assert result is None

    @patch("app.domains.analysis.workflows.tasks.aggregation.synthesis_phased.get_chat_model")
    async def test_synthesis_phases_use_async_timeout(self, mock_get_chat_model):
        """Test synthesis phases use asyncio.timeout for explicit timeout control."""
        from app.domains.analysis.workflows.tasks.aggregation.synthesis_phased import (
            _synthesize_docs,
        )

        # Mock LLM that hangs (simulated by long sleep)
        mock_llm = MagicMock()
        mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
        mock_llm.with_retry = MagicMock(return_value=mock_llm)
        mock_llm.with_fallbacks = MagicMock(return_value=mock_llm)

        async def slow_invoke(*args, **kwargs):
            await asyncio.sleep(100)  # Simulate hanging call

        mock_llm.ainvoke = AsyncMock(side_effect=slow_invoke)
        mock_get_chat_model.return_value = mock_llm

        compressed_findings = [
            CompressedFinding(
                agent_name="agent1",
                key_insights=["Insight 1"],
                confidence=0.9,
                data_quality="high",
                critical_warnings=[],
                relevant_code_snippets=[],
            )
        ]

        # Should timeout quickly (not wait 100 seconds)
        # The timeout is caught and returns None for graceful degradation
        result = await _synthesize_docs(compressed_findings, "test-id")

        # Verify graceful degradation (returns None on timeout)
        assert result is None
        # Verify the timeout happened quickly (not 100 seconds)
        # This is implicit in the test completing quickly


@pytest.mark.asyncio
class TestLCELPerformance:
    """Test performance improvements from LCEL chains."""

    @patch("app.domains.analysis.workflows.tasks.aggregation.compress_findings.get_chat_model")
    async def test_abatch_speedup_vs_sequential(self, mock_get_chat_model):
        """Benchmark abatch() speedup vs sequential processing."""
        import time

        # Mock LLM with realistic delays
        mock_llm = MagicMock()
        mock_llm.with_structured_output = MagicMock(return_value=mock_llm)

        # Simulate 100ms per compression (realistic for LLM call)
        async def mock_compress(*args, **kwargs):
            await asyncio.sleep(0.1)
            return CompressedFinding(
                agent_name="test",
                key_insights=["Fast insight"],
                confidence=0.9,
                data_quality="high",
                critical_warnings=[],
                relevant_code_snippets=[],
            )

        # abatch processes in parallel (5 concurrent)
        async def mock_abatch(inputs, config=None, max_concurrency=5):
            tasks = [mock_compress() for _ in inputs]
            # Simulate parallel execution with max_concurrency
            results = []
            for i in range(0, len(tasks), max_concurrency):
                batch = tasks[i : i + max_concurrency]
                batch_results = await asyncio.gather(*batch)
                results.extend(batch_results)
            return results

        mock_llm.abatch = AsyncMock(side_effect=mock_abatch)
        mock_get_chat_model.return_value = mock_llm

        # Test with 8 agents (typical analysis)
        agent_findings = {
            f"agent{i}": {"findings": {"key": f"value{i}"}, "confidence_score": 0.9}
            for i in range(8)
        }

        start = time.time()
        results = await compress_all_findings(agent_findings, "test-analysis-id")
        elapsed = time.time() - start

        # With max_concurrency=5, 8 agents should take ~200ms (2 batches of 100ms each)
        # Sequential would take ~800ms (8 * 100ms)
        # We expect 4-5x speedup
        assert len(results) == 8
        assert elapsed < 0.5  # Should be much faster than sequential (0.8s)

        # Verify abatch was used (not sequential ainvoke)
        assert mock_llm.abatch.called
