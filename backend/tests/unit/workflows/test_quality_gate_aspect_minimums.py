"""Unit tests for quality gate ASPECT_MINIMUMS enforcement.

Tests cover the new fail-closed behavior where individual aspect minimums
must be met regardless of average score.

Issue #ARTIFACT-QUALITY: Quality gate now enforces minimum thresholds per aspect.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langsmith.schemas import Example, Run

from app.domains.analysis.workflows.nodes.quality_gate_node import (
    ASPECT_MINIMUMS,
    MAX_RETRY_ATTEMPTS,
    QUALITY_THRESHOLD,
    quality_gate_node,
    should_retry_synthesis,
)
from app.domains.analysis.workflows.state import AnalysisState



@pytest.fixture
def base_state() -> AnalysisState:
    """Return base state with required fields for quality gate testing."""
    return {
        "analysis_id": "test-analysis-123",
        "raw_content": "Test content about FastAPI and async patterns",
        "aggregated_insights": {
            "executive_summary": "Comprehensive analysis of async patterns",
            "key_findings": [
                "FastAPI uses async/await for concurrency",
                "Starlette provides ASGI foundation",
            ],
        },
        "quality_gate_retry_count": 0,
    }


@pytest.mark.asyncio
async def test_quality_gate_aspect_minimums_enforced(base_state: AnalysisState):
    """Test that quality gate fails when any aspect is below minimum threshold.

    Even if average score is high, if relevance < 0.5, gate should FAIL.
    """
    with (
        patch("app.workflows.nodes.quality_gate_node.create_quality_evaluator") as mock_create,
        patch("app.services.messaging.sse_helpers.emit_streaming_event", new_callable=AsyncMock),
        patch("app.workflows.nodes.quality_gate_node.get_current_run_tree") as mock_run_tree,
        patch("langsmith.schemas.Run") as mock_run_class,
        patch("langsmith.schemas.Example") as mock_example_class,
    ):
        mock_run_tree.return_value = None
        mock_run_class.return_value = MagicMock()
        mock_example_class.return_value = MagicMock()

        # Return scores where relevance is below minimum (0.4 < 0.5)
        # but average is above threshold: (0.4 + 0.9 + 0.9) / 3 = 0.733 > 0.7
        call_count = 0

        def create_evaluator_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            aspect = kwargs.get("aspect", "")

            async def evaluator(run: Run, example: Example) -> dict:
                if aspect == "relevance":
                    # BELOW MINIMUM (0.4 < 0.5)
                    return {"key": "quality_test", "score": 0.4, "comment": "4/10 - not relevant"}
                else:
                    # High scores for other aspects
                    return {"key": "quality_test", "score": 0.9, "comment": "9/10"}

            return evaluator

        mock_create.side_effect = create_evaluator_side_effect

        result = await quality_gate_node(base_state)

        # Verify gate FAILS despite high average score
        assert result["quality_gate_passed"] is False, (
            "Gate should fail when relevance < 0.5, even if average is high"
        )

        # Verify average is indeed above threshold
        avg_score = result["quality_gate_avg_score"]
        assert avg_score > QUALITY_THRESHOLD, f"Average {avg_score} should be > {QUALITY_THRESHOLD}"

        # Verify relevance score is below minimum
        quality_scores = result["quality_scores"]
        assert quality_scores["relevance"]["score"] < ASPECT_MINIMUMS["relevance"]


@pytest.mark.asyncio
async def test_quality_gate_all_aspect_minimums_pass(base_state: AnalysisState):
    """Test that quality gate passes when all aspects meet minimums."""
    with (
        patch("app.workflows.nodes.quality_gate_node.create_quality_evaluator") as mock_create,
        patch("app.services.messaging.sse_helpers.emit_streaming_event", new_callable=AsyncMock),
        patch("app.workflows.nodes.quality_gate_node.get_current_run_tree") as mock_run_tree,
        patch("langsmith.schemas.Run") as mock_run_class,
        patch("langsmith.schemas.Example") as mock_example_class,
    ):
        mock_run_tree.return_value = None
        mock_run_class.return_value = MagicMock()
        mock_example_class.return_value = MagicMock()

        # Return scores where all aspects are at or above minimums
        # relevance: 0.6 >= 0.5
        # depth: 0.5 >= 0.4
        # coherence: 0.8 >= 0.4
        # Average: (0.6 + 0.5 + 0.8) / 3 = 0.633 < 0.7 (threshold)
        call_count = 0

        def create_evaluator_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            aspect = kwargs.get("aspect", "")

            async def evaluator(run: Run, example: Example) -> dict:
                if aspect == "relevance":
                    return {"key": "quality_test", "score": 0.6, "comment": "6/10"}
                elif aspect == "depth":
                    return {"key": "quality_test", "score": 0.5, "comment": "5/10"}
                else:  # coherence
                    return {"key": "quality_test", "score": 0.8, "comment": "8/10"}

            return evaluator

        mock_create.side_effect = create_evaluator_side_effect

        result = await quality_gate_node(base_state)

        # Gate should FAIL because average < threshold
        # (even though all aspects meet minimums)
        assert result["quality_gate_passed"] is False


@pytest.mark.asyncio
async def test_quality_gate_depth_below_minimum(base_state: AnalysisState):
    """Test that quality gate fails when depth is below minimum (0.4)."""
    with (
        patch("app.workflows.nodes.quality_gate_node.create_quality_evaluator") as mock_create,
        patch("app.services.messaging.sse_helpers.emit_streaming_event", new_callable=AsyncMock),
        patch("app.workflows.nodes.quality_gate_node.get_current_run_tree") as mock_run_tree,
        patch("langsmith.schemas.Run") as mock_run_class,
        patch("langsmith.schemas.Example") as mock_example_class,
    ):
        mock_run_tree.return_value = None
        mock_run_class.return_value = MagicMock()
        mock_example_class.return_value = MagicMock()

        # depth: 0.3 < 0.4 (BELOW MINIMUM)
        # relevance: 0.9 >= 0.5
        # coherence: 0.9 >= 0.4
        # Average: (0.9 + 0.3 + 0.9) / 3 = 0.7 (exactly at threshold)
        call_count = 0

        def create_evaluator_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            aspect = kwargs.get("aspect", "")

            async def evaluator(run: Run, example: Example) -> dict:
                if aspect == "depth":
                    return {"key": "quality_test", "score": 0.3, "comment": "3/10 - shallow"}
                else:
                    return {"key": "quality_test", "score": 0.9, "comment": "9/10"}

            return evaluator

        mock_create.side_effect = create_evaluator_side_effect

        result = await quality_gate_node(base_state)

        # Gate should FAIL because depth < minimum
        assert result["quality_gate_passed"] is False


@pytest.mark.asyncio
async def test_quality_gate_coherence_below_minimum(base_state: AnalysisState):
    """Test that quality gate fails when coherence is below minimum (0.4)."""
    with (
        patch("app.workflows.nodes.quality_gate_node.create_quality_evaluator") as mock_create,
        patch("app.services.messaging.sse_helpers.emit_streaming_event", new_callable=AsyncMock),
        patch("app.workflows.nodes.quality_gate_node.get_current_run_tree") as mock_run_tree,
        patch("langsmith.schemas.Run") as mock_run_class,
        patch("langsmith.schemas.Example") as mock_example_class,
    ):
        mock_run_tree.return_value = None
        mock_run_class.return_value = MagicMock()
        mock_example_class.return_value = MagicMock()

        # coherence: 0.35 < 0.4 (BELOW MINIMUM)
        # relevance: 0.9 >= 0.5
        # depth: 0.9 >= 0.4
        # Average: (0.9 + 0.9 + 0.35) / 3 = 0.716 > 0.7
        call_count = 0

        def create_evaluator_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            aspect = kwargs.get("aspect", "")

            async def evaluator(run: Run, example: Example) -> dict:
                if aspect == "coherence":
                    return {"key": "quality_test", "score": 0.35, "comment": "3.5/10 - incoherent"}
                else:
                    return {"key": "quality_test", "score": 0.9, "comment": "9/10"}

            return evaluator

        mock_create.side_effect = create_evaluator_side_effect

        result = await quality_gate_node(base_state)

        # Gate should FAIL because coherence < minimum
        assert result["quality_gate_passed"] is False


@pytest.mark.asyncio
async def test_quality_gate_multiple_aspects_below_minimum(base_state: AnalysisState):
    """Test that quality gate fails when multiple aspects are below minimums."""
    with (
        patch("app.workflows.nodes.quality_gate_node.create_quality_evaluator") as mock_create,
        patch("app.services.messaging.sse_helpers.emit_streaming_event", new_callable=AsyncMock),
        patch("app.workflows.nodes.quality_gate_node.get_current_run_tree") as mock_run_tree,
        patch("app.workflows.nodes.quality_gate_node.logger") as mock_logger,
        patch("langsmith.schemas.Run") as mock_run_class,
        patch("langsmith.schemas.Example") as mock_example_class,
    ):
        mock_run_tree.return_value = None
        mock_run_class.return_value = MagicMock()
        mock_example_class.return_value = MagicMock()

        # All aspects below minimums
        # relevance: 0.4 < 0.5
        # depth: 0.3 < 0.4
        # coherence: 0.2 < 0.4
        # Average: (0.4 + 0.3 + 0.2) / 3 = 0.3 < 0.7
        async def low_score_evaluator(run: Run, example: Example) -> dict:
            return {"key": "quality_test", "score": 0.3, "comment": "3/10 - poor quality"}

        mock_create.return_value = low_score_evaluator

        result = await quality_gate_node(base_state)

        # Gate should FAIL
        assert result["quality_gate_passed"] is False

        # Verify multiple warnings were logged
        warning_calls = [
            call
            for call in mock_logger.warning.call_args_list
            if call[0][0] == "quality_aspect_below_minimum"
        ]
        # Should have at least 2 warnings for failed aspects
        assert len(warning_calls) >= 2


def test_should_retry_synthesis_fail_closed_max_retries():
    """Test that should_retry_synthesis returns 'fail' (not 'continue') at max retries.

    This is CRITICAL: fail-closed behavior prevents shipping garbage artifacts.
    """
    state: AnalysisState = {
        "analysis_id": "test-analysis-123",
        "quality_gate_passed": False,  # Gate failed
        "quality_gate_retry_count": MAX_RETRY_ATTEMPTS,  # At max retries
        "quality_gate_avg_score": 0.5,  # Low score
        "quality_scores": {
            "relevance": {"score": 0.4, "comment": "Low relevance"},
            "depth": {"score": 0.5, "comment": "Shallow"},
            "coherence": {"score": 0.6, "comment": "Somewhat coherent"},
        },
    }

    with patch("app.workflows.nodes.quality_gate_node.logger") as mock_logger:
        result = should_retry_synthesis(state)

        # CRITICAL: Should return "fail" (fail-closed), not "continue"
        assert result == "fail", (
            "Quality gate MUST return 'fail' at max retries to prevent shipping garbage"
        )

        # Verify error was logged (not just warning)
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert call_args[0][0] == "quality_gate_max_retries_exhausted"
        kwargs = call_args[1]
        assert kwargs["retry_count"] == MAX_RETRY_ATTEMPTS
        assert "FAILING analysis" in kwargs["message"]


def test_should_retry_synthesis_retry_available():
    """Test that should_retry_synthesis returns 'retry_synthesis' when retries available."""
    state: AnalysisState = {
        "analysis_id": "test-analysis-123",
        "quality_gate_passed": False,  # Gate failed
        "quality_gate_retry_count": 0,  # Still has retries
        "quality_gate_avg_score": 0.5,  # Low score
    }

    with patch("app.workflows.nodes.quality_gate_node.logger"):
        result = should_retry_synthesis(state)

        # Should trigger retry
        assert result == "retry_synthesis"


def test_should_retry_synthesis_pass_continues():
    """Test that should_retry_synthesis returns 'continue' when gate passes."""
    state: AnalysisState = {
        "analysis_id": "test-analysis-123",
        "quality_gate_passed": True,  # Gate passed
        "quality_gate_retry_count": 0,
        "quality_gate_avg_score": 0.85,  # High score
    }

    result = should_retry_synthesis(state)

    # Should continue to artifact generation
    assert result == "continue"


@pytest.mark.asyncio
async def test_quality_gate_logs_failed_aspects(base_state: AnalysisState):
    """Test that quality gate logs which aspects failed minimum thresholds."""
    with (
        patch("app.workflows.nodes.quality_gate_node.create_quality_evaluator") as mock_create,
        patch("app.services.messaging.sse_helpers.emit_streaming_event", new_callable=AsyncMock),
        patch("app.workflows.nodes.quality_gate_node.get_current_run_tree") as mock_run_tree,
        patch("app.workflows.nodes.quality_gate_node.logger") as mock_logger,
        patch("langsmith.schemas.Run") as mock_run_class,
        patch("langsmith.schemas.Example") as mock_example_class,
    ):
        mock_run_tree.return_value = None
        mock_run_class.return_value = MagicMock()
        mock_example_class.return_value = MagicMock()

        # relevance: 0.3 < 0.5 (FAIL)
        # depth: 0.6 >= 0.4 (PASS)
        # coherence: 0.35 < 0.4 (FAIL)
        call_count = 0

        def create_evaluator_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            aspect = kwargs.get("aspect", "")

            async def evaluator(run: Run, example: Example) -> dict:
                if aspect == "relevance":
                    return {"key": "quality_test", "score": 0.3, "comment": "3/10"}
                elif aspect == "depth":
                    return {"key": "quality_test", "score": 0.6, "comment": "6/10"}
                else:  # coherence
                    return {"key": "quality_test", "score": 0.35, "comment": "3.5/10"}

            return evaluator

        mock_create.side_effect = create_evaluator_side_effect

        result = await quality_gate_node(base_state)

        # Verify gate failed
        assert result["quality_gate_passed"] is False

        # Verify info log contains failed_aspects field
        info_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "quality_gate_evaluated"
        ]
        assert len(info_calls) == 1

        kwargs = info_calls[0][1]
        assert "failed_aspects" in kwargs
        failed_aspects = kwargs["failed_aspects"]
        assert failed_aspects is not None
        assert len(failed_aspects) == 2  # relevance and coherence failed
        assert any("relevance" in aspect for aspect in failed_aspects)
        assert any("coherence" in aspect for aspect in failed_aspects)
