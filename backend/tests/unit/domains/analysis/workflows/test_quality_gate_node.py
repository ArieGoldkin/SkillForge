"""Unit tests for quality gate node.

Tests the quality gate validation logic using LLM-as-judge evaluators.
"""

from typing import TYPE_CHECKING

import pytest

from app.domains.analysis.workflows.nodes.quality_gate_node import (
    _format_insights_for_evaluation,
    should_retry_synthesis,
)

if TYPE_CHECKING:
    from app.domains.analysis.workflows.state import AnalysisState


@pytest.mark.unit
class TestFormatInsightsForEvaluation:
    """Test formatting of aggregated insights for evaluation."""

    def test_format_complete_insights(self):
        """Test formatting insights with all sections."""
        insights = {
            "executive_summary": "This is a test summary.",
            "key_findings": [
                "Finding 1",
                "Finding 2",
                "Finding 3",
            ],
            "synthesis": {
                "security": "Security analysis content",
                "performance": "Performance analysis content",
            },
            "recommendations": [
                "Recommendation 1",
                "Recommendation 2",
            ],
        }

        result = _format_insights_for_evaluation(insights)

        assert "Executive Summary:" in result
        assert "This is a test summary." in result
        assert "Key Findings:" in result
        assert "- Finding 1" in result
        assert "Security:" in result
        assert "Performance:" in result
        assert "Recommendations:" in result
        assert "- Recommendation 1" in result

    def test_format_partial_insights(self):
        """Test formatting insights with only some sections."""
        insights = {
            "executive_summary": "Summary only.",
        }

        result = _format_insights_for_evaluation(insights)

        assert "Executive Summary:" in result
        assert "Summary only." in result

    def test_format_empty_insights(self):
        """Test formatting empty insights dict."""
        insights = {}

        result = _format_insights_for_evaluation(insights)

        # Should return empty string or minimal representation
        assert isinstance(result, str)

    def test_format_non_dict_insights(self):
        """Test formatting non-dict insights."""
        insights = "Just a string"

        result = _format_insights_for_evaluation(insights)

        assert result == "Just a string"

    def test_format_truncates_long_output(self):
        """Test that output is truncated to 8000 chars.

        Issue #299-304: Increased from 2000 to 8000 to preserve analytical depth.
        """
        insights = {
            "executive_summary": "A" * 10000,  # Long summary (exceeds 8000)
        }

        result = _format_insights_for_evaluation(insights)

        assert len(result) <= 8000


class TestShouldRetrySynthesis:
    """Test retry logic for synthesis."""

    def test_continue_when_gate_passed(self):
        """Test that we continue when quality gate passed."""
        state: AnalysisState = {
            "analysis_id": "test-id",
            "quality_gate_passed": True,
            "quality_gate_retry_count": 0,
            "quality_gate_avg_score": 0.8,
        }  # type: ignore

        result = should_retry_synthesis(state)

        assert result == "continue"

    def test_retry_when_gate_failed_and_retries_available(self):
        """Test that we retry when gate failed and retries available."""
        state: AnalysisState = {
            "analysis_id": "test-id",
            "quality_gate_passed": False,
            "quality_gate_retry_count": 0,
            "quality_gate_avg_score": 0.5,
        }  # type: ignore

        result = should_retry_synthesis(state)

        assert result == "retry_synthesis"

    def test_fail_when_max_retries_reached(self):
        """Test that we FAIL (fail-closed) when max retries reached.

        UPDATED: Previously expected 'continue' (fail-open).
        Now expects 'fail' (fail-closed) to prevent shipping garbage artifacts.
        """
        from unittest.mock import patch

        state: AnalysisState = {
            "analysis_id": "test-id",
            "quality_gate_passed": False,
            "quality_gate_retry_count": 2,  # MAX_RETRY_ATTEMPTS = 2
            "quality_gate_avg_score": 0.5,
            "quality_scores": {
                "relevance": {"score": 0.4, "comment": "Low"},
            },
        }  # type: ignore

        with patch("app.domains.analysis.workflows.nodes.quality_gate_node.logger"):
            result = should_retry_synthesis(state)

            # UPDATED: Should return "fail" (fail-closed), not "continue"
            assert result == "fail"

    def test_continue_when_no_gate_result(self):
        """Test that we continue when no gate result (defaults to passed)."""
        state: AnalysisState = {
            "analysis_id": "test-id",
        }  # type: ignore

        result = should_retry_synthesis(state)

        assert result == "continue"


@pytest.mark.asyncio
class TestQualityGateNode:
    """Integration tests for quality gate node.

    Note: These tests mock the LLM evaluators to avoid actual API calls.
    """

    async def test_quality_gate_skips_when_no_insights(self):
        """Test that quality gate is skipped when no insights."""
        from app.domains.analysis.workflows.nodes.quality_gate_node import quality_gate_node

        state: AnalysisState = {
            "analysis_id": "test-id",
            "aggregated_insights": {},
        }  # type: ignore

        result = await quality_gate_node(state)

        assert result["quality_gate_passed"] is True
        assert result["quality_scores"] == {}

    async def test_quality_gate_fail_closed_on_error(self, monkeypatch):
        """Test that quality gate raises WorkflowStageError on evaluator creation error.

        Issue #454: Requires >= 100 chars formatted content for G-Eval evaluation.

        Note: Evaluator EXECUTION errors are now handled gracefully (default score 0.5).
        This test verifies that evaluator CREATION errors still raise WorkflowStageError.
        """
        from app.core.exceptions import WorkflowStageError
        from app.domains.analysis.workflows.nodes.quality_gate_node import quality_gate_node

        # Mock evaluator creation to raise exception (not execution)
        def mock_create_evaluator(*args, **kwargs):
            raise ValueError("Evaluator creation error")

        monkeypatch.setattr(
            "app.shared.services.g_eval.langfuse_evaluators.create_g_eval_evaluator",
            mock_create_evaluator,
        )

        # Issue #454: Content must be >= 100 chars formatted for G-Eval
        state: AnalysisState = {
            "analysis_id": "test-id",
            "raw_content": "Test content with sufficient length for evaluation and analysis purposes",
            "aggregated_insights": {
                "executive_summary": "Test summary with comprehensive details covering technical implementation patterns and best practices for development workflows",
                "key_findings": [
                    "Finding 1: Technical pattern analysis",
                    "Finding 2: Implementation recommendation",
                ],
            },
        }  # type: ignore

        # Should raise WorkflowStageError with stage context
        with pytest.raises(WorkflowStageError) as exc_info:
            await quality_gate_node(state)

        assert exc_info.value.stage == "quality_gate"
        assert isinstance(exc_info.value.original_exception, ValueError)
