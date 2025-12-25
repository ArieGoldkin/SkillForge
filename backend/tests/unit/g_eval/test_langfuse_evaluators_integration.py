"""Test Langfuse multi-judge evaluator integration.

This module tests the integration between Langfuse evaluators and the quality gate.

Issue #GAP5: Test multi-judge evaluation integration.
"""

import pytest


class TestLangfuseEvaluatorIntegration:
    """Test Langfuse evaluator integration with quality gate."""

    def test_create_g_eval_evaluator_basic(self):
        """Test basic G-Eval evaluator creation."""
        from app.shared.services.g_eval.langfuse_evaluators import create_g_eval_evaluator

        # Create evaluator for relevance criterion
        evaluator = create_g_eval_evaluator(criterion="relevance", agent_type="tech_comparator")

        # Verify evaluator is callable
        assert callable(evaluator)
        assert evaluator.__name__ == "g_eval_relevance_evaluator"

    def test_create_g_eval_overall_evaluator_basic(self):
        """Test overall G-Eval evaluator creation."""
        from app.shared.services.g_eval.langfuse_evaluators import create_g_eval_overall_evaluator

        # Create overall evaluator
        evaluator = create_g_eval_overall_evaluator(agent_type="tech_comparator")

        # Verify evaluator is callable
        assert callable(evaluator)
        assert evaluator.__name__ == "g_eval_overall_evaluator"

    def test_get_standard_evaluators(self):
        """Test getting standard evaluator set."""
        from app.shared.services.g_eval.langfuse_evaluators import get_standard_evaluators

        # Get standard evaluators for tech_comparator
        evaluators = get_standard_evaluators(agent_type="tech_comparator")

        # Should return list of evaluators
        assert isinstance(evaluators, list)
        assert len(evaluators) > 0

        # All should be callable
        for evaluator in evaluators:
            assert callable(evaluator)

    @pytest.mark.asyncio
    async def test_multi_judge_evaluation_helper(self):
        """Test multi-judge evaluation helper function."""
        from app.shared.services.g_eval.multi_judge import calculate_weighted_score

        # Test weighted score calculation
        quality_scores = {
            "relevance": {"score": 0.8, "comment": "Highly relevant"},
            "depth": {"score": 0.9, "comment": "Deep analysis"},
            "coherence": {"score": 0.7, "comment": "Coherent structure"},
        }

        # Test with equal weighting
        avg_score = calculate_weighted_score(quality_scores)
        expected_avg = (0.8 + 0.9 + 0.7) / 3
        assert abs(avg_score - expected_avg) < 0.01

        # Test with custom weighting
        weights = {"relevance": 0.5, "depth": 0.3, "coherence": 0.2}
        weighted_score = calculate_weighted_score(quality_scores, weights)
        expected_weighted = 0.8 * 0.5 + 0.9 * 0.3 + 0.7 * 0.2
        assert abs(weighted_score - expected_weighted) < 0.01

    def test_quality_tier_classification(self):
        """Test quality tier classification."""
        from app.shared.services.g_eval.multi_judge import get_quality_tier

        # High quality
        assert get_quality_tier(0.85) == "quality:high"
        assert get_quality_tier(0.8) == "quality:high"

        # Medium quality
        assert get_quality_tier(0.75) == "quality:medium"
        assert get_quality_tier(0.6) == "quality:medium"

        # Low quality
        assert get_quality_tier(0.55) == "quality:low"
        assert get_quality_tier(0.3) == "quality:low"
