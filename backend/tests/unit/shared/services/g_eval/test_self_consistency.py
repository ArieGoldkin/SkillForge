"""Tests for G-Eval self-consistency voting module."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.shared.services.g_eval.scorer import CriterionScore
from app.shared.services.g_eval.self_consistency import (
    VotingDistribution,
    score_criterion_with_self_consistency,
)


class TestVotingDistribution:
    """Tests for VotingDistribution data class."""

    def test_voting_distribution_unanimous(self) -> None:
        """Test voting distribution when all samples agree."""
        dist = VotingDistribution(score_counts={4: 3})

        assert dist.winning_score == 4
        assert dist.winning_count == 3
        assert dist.total_votes == 3
        assert dist.confidence == 1.0  # 3/3 = 100% agreement

    def test_voting_distribution_majority(self) -> None:
        """Test voting distribution with clear majority."""
        dist = VotingDistribution(score_counts={3: 1, 4: 2})

        assert dist.winning_score == 4  # Most common
        assert dist.winning_count == 2
        assert dist.total_votes == 3
        assert dist.confidence == pytest.approx(0.67, abs=0.01)  # 2/3 ≈ 67%

    def test_voting_distribution_tie_prefers_higher(self) -> None:
        """Test voting distribution tie-breaking (prefers higher score)."""
        dist = VotingDistribution(score_counts={3: 2, 4: 2})

        assert dist.winning_score == 4  # Tie broken in favor of higher score
        assert dist.winning_count == 2
        assert dist.total_votes == 4
        assert dist.confidence == 0.5  # 2/4 = 50%

    def test_voting_distribution_diverse(self) -> None:
        """Test voting distribution with diverse scores."""
        dist = VotingDistribution(score_counts={2: 1, 3: 1, 4: 2, 5: 1})

        assert dist.winning_score == 4  # Most common
        assert dist.winning_count == 2
        assert dist.total_votes == 5
        assert dist.confidence == 0.4  # 2/5 = 40%


class TestSelfConsistencyScoring:
    """Tests for self-consistency scoring functions."""

    @pytest.mark.asyncio
    async def test_score_criterion_with_self_consistency_unanimous(self) -> None:
        """Test self-consistency scoring when all samples agree."""
        # Mock the LLM to return identical scores
        with patch("app.shared.services.g_eval.self_consistency.get_chat_model") as mock_model:
            mock_response = MagicMock()
            mock_response.content = """
            <reasoning>The output is comprehensive and well-structured.</reasoning>
            <score>4</score>
            <confidence>0.9</confidence>
            """
            mock_llm = AsyncMock()
            # Mock abatch to return 3 identical responses
            mock_llm.abatch = AsyncMock(return_value=[mock_response] * 3)
            mock_model.return_value = mock_llm

            result = await score_criterion_with_self_consistency(
                input_content="Test input",
                output="Test output",
                criterion="completeness",
                agent_type="test_agent",
                rubric_text="Score 1-5",
                n_samples=3,
            )

            # All 3 samples should agree on score 4
            assert result.final_score.score == 4
            assert result.voting_distribution.winning_score == 4
            assert result.voting_distribution.total_votes == 3
            assert result.voting_distribution.confidence == 1.0  # All agree
            assert len(result.individual_samples) == 3

            # Verify LLM abatch was called once with 3 inputs
            assert mock_llm.abatch.call_count == 1

    @pytest.mark.asyncio
    async def test_score_criterion_with_self_consistency_majority(self) -> None:
        """Test self-consistency scoring with majority voting."""
        # Mock the LLM to return different scores
        with patch("app.shared.services.g_eval.self_consistency.get_chat_model") as mock_model:
            # Create 3 different mock responses
            mock_response1 = MagicMock()
            mock_response1.content = (
                """<reasoning>Good</reasoning><score>4</score><confidence>0.8</confidence>"""
            )
            mock_response2 = MagicMock()
            mock_response2.content = (
                """<reasoning>Good</reasoning><score>4</score><confidence>0.9</confidence>"""
            )
            mock_response3 = MagicMock()
            mock_response3.content = (
                """<reasoning>Fair</reasoning><score>3</score><confidence>0.7</confidence>"""
            )

            mock_llm = AsyncMock()
            # Mock abatch to return 3 different responses
            mock_llm.abatch = AsyncMock(
                return_value=[mock_response1, mock_response2, mock_response3]
            )
            mock_model.return_value = mock_llm

            result = await score_criterion_with_self_consistency(
                input_content="Test input",
                output="Test output",
                criterion="accuracy",
                agent_type="test_agent",
                rubric_text="Score 1-5",
                n_samples=3,
            )

            # Majority vote should be 4 (2 out of 3)
            assert result.final_score.score == 4
            assert result.voting_distribution.score_counts == {3: 1, 4: 2}
            assert result.voting_distribution.confidence == pytest.approx(0.67, abs=0.01)
            assert len(result.individual_samples) == 3

    @pytest.mark.asyncio
    async def test_score_criterion_with_self_consistency_parallel_execution(self) -> None:
        """Test that samples are generated in parallel using abatch."""
        import time

        with patch("app.shared.services.g_eval.self_consistency.get_chat_model") as mock_model:
            mock_response = MagicMock()
            mock_response.content = """
            <reasoning>Test</reasoning>
            <score>3</score>
            <confidence>0.7</confidence>
            """

            async def slow_abatch(*args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate 100ms batch LLM call
                # Return 3 responses (abatch processes all inputs in parallel)
                return [mock_response] * 3

            mock_llm = AsyncMock()
            mock_llm.abatch = slow_abatch
            mock_model.return_value = mock_llm

            start_time = time.time()

            await score_criterion_with_self_consistency(
                input_content="Test input",
                output="Test output",
                criterion="depth",
                agent_type="test_agent",
                rubric_text="Score 1-5",
                n_samples=3,
            )

            elapsed = time.time() - start_time

            # With abatch, all 3 samples are processed in one batch call (~0.1s)
            # Allow some overhead, but should be much less than 0.3s (sequential would be)
            assert elapsed < 0.25  # Parallel execution should complete in < 250ms

    @pytest.mark.asyncio
    async def test_score_criterion_with_self_consistency_temperature(self) -> None:
        """Test that sampling uses specified temperature."""
        with patch("app.shared.services.g_eval.self_consistency.get_chat_model") as mock_model:
            mock_response = MagicMock()
            mock_response.content = """
            <reasoning>Test</reasoning>
            <score>3</score>
            <confidence>0.7</confidence>
            """
            mock_llm = AsyncMock()
            mock_llm.abatch = AsyncMock(return_value=[mock_response] * 2)
            mock_model.return_value = mock_llm

            await score_criterion_with_self_consistency(
                input_content="Test input",
                output="Test output",
                criterion="coherence",
                agent_type="test_agent",
                rubric_text="Score 1-5",
                n_samples=2,
                temperature=0.8,  # Custom temperature
            )

            # Verify model was created with temperature=0.8
            mock_model.assert_called()
            call_args = mock_model.call_args
            assert call_args[1]["config"]["configurable"]["temperature"] == 0.8

    @pytest.mark.asyncio
    async def test_score_criterion_with_self_consistency_minimum_samples(self) -> None:
        """Test that minimum 2 samples are enforced."""
        with patch("app.shared.services.g_eval.self_consistency.get_chat_model") as mock_model:
            mock_response = MagicMock()
            mock_response.content = """
            <reasoning>Test</reasoning>
            <score>3</score>
            <confidence>0.7</confidence>
            """
            mock_llm = AsyncMock()
            # Mock abatch to return 2 responses (minimum enforced by code)
            mock_llm.abatch = AsyncMock(return_value=[mock_response] * 2)
            mock_model.return_value = mock_llm

            result = await score_criterion_with_self_consistency(
                input_content="Test input",
                output="Test output",
                criterion="completeness",
                agent_type="test_agent",
                rubric_text="Score 1-5",
                n_samples=1,  # Try to use only 1 sample
            )

            # Should still generate 2 samples (minimum)
            assert len(result.individual_samples) >= 2
            # abatch should be called once with 2 inputs
            assert mock_llm.abatch.call_count == 1

    @pytest.mark.asyncio
    async def test_score_criterion_with_self_consistency_error_handling(self) -> None:
        """Test error handling when abatch fails."""
        # When abatch fails, the try-except block catches it and returns a neutral score
        with patch("app.shared.services.g_eval.self_consistency.get_chat_model") as mock_model:
            mock_llm = AsyncMock()
            mock_llm.abatch = AsyncMock(side_effect=Exception("LLM service error"))
            mock_model.return_value = mock_llm

            result = await score_criterion_with_self_consistency(
                input_content="Test input",
                output="Test output",
                criterion="accuracy",
                agent_type="test_agent",
                rubric_text="Score 1-5",
                n_samples=3,
            )

            # Batch failed, so error handling returns neutral score
            assert result.final_score.score == 3  # Neutral
            assert result.voting_distribution.winning_score == 3
            # Voting distribution shows 100% confidence (1 sample, all agree on score 3)
            # But the final_score confidence is 0.0 (error condition)
            assert result.voting_distribution.confidence == 1.0
            assert result.final_score.confidence == 0.0  # Error condition
            # Error should be captured
            assert result.error is not None
            assert "LLM service error" in result.error

    @pytest.mark.asyncio
    async def test_self_consistency_preserves_reasoning(self) -> None:
        """Test that reasoning from winning sample is preserved."""
        with patch("app.shared.services.g_eval.self_consistency.get_chat_model") as mock_model:
            # Create 3 different mock responses
            mock_response1 = MagicMock()
            mock_response1.content = """<reasoning>First reasoning</reasoning><score>4</score><confidence>0.8</confidence>"""
            mock_response2 = MagicMock()
            mock_response2.content = """<reasoning>Second reasoning (winner)</reasoning><score>4</score><confidence>0.9</confidence>"""
            mock_response3 = MagicMock()
            mock_response3.content = """<reasoning>Third reasoning</reasoning><score>3</score><confidence>0.7</confidence>"""

            mock_llm = AsyncMock()
            # Mock abatch to return all 3 responses
            mock_llm.abatch = AsyncMock(
                return_value=[mock_response1, mock_response2, mock_response3]
            )
            mock_model.return_value = mock_llm

            result = await score_criterion_with_self_consistency(
                input_content="Test input",
                output="Test output",
                criterion="depth",
                agent_type="test_agent",
                rubric_text="Score 1-5",
                n_samples=3,
            )

            # Winning score is 4 (appears twice)
            # Should use reasoning from the winning sample with highest confidence
            assert result.final_score.score == 4
            assert "Second reasoning (winner)" in result.final_score.reasoning


class TestLangfuseScoreSubmission:
    """Tests for Langfuse score submission in G-Eval."""

    @pytest.mark.asyncio
    async def test_g_eval_submits_scores_to_langfuse(self) -> None:
        """Test that G-Eval scores are submitted to Langfuse."""
        from app.shared.services.g_eval.scorer import g_eval_score

        # Create mock cache that returns pre-populated scores to avoid LLM calls
        with (
            patch("app.shared.services.g_eval.scorer.get_cache") as mock_cache_factory,
            patch("app.core.langfuse_service.submit_langfuse_score") as mock_submit,
        ):
            # Mock cache to return scores (simulates cache hits)
            mock_cache = MagicMock()

            # Create mock cached score objects with required attributes
            completeness_cached = MagicMock()
            completeness_cached.score = 4
            completeness_cached.normalized = 0.75
            completeness_cached.confidence = 0.85
            completeness_cached.reasoning = "Good completeness"

            accuracy_cached = MagicMock()
            accuracy_cached.score = 5
            accuracy_cached.normalized = 1.0
            accuracy_cached.confidence = 0.9
            accuracy_cached.reasoning = "Excellent accuracy"

            # Return cached scores to avoid LLM calls
            mock_cache.get.side_effect = [completeness_cached, accuracy_cached]
            mock_cache_factory.return_value = mock_cache

            result = await g_eval_score(
                input_content="Test input",
                output="Test output",
                agent_type="test_agent",
                criteria=["completeness", "accuracy"],
                use_self_consistency=False,
            )

            # Verify scores were submitted to Langfuse
            # Cache hits submit analytics: 2 cache hit scores + 2 criteria scores + 1 overall = 5
            assert mock_submit.call_count == 5

            # Verify individual criterion scores
            calls = mock_submit.call_args_list
            criterion_calls = [c for c in calls if c[1]["name"].startswith("g_eval_")]

            # Check completeness score
            completeness_call = next(c for c in calls if c[1]["name"] == "g_eval_completeness")
            assert completeness_call[1]["value"] == 0.75
            assert "test_agent" in completeness_call[1]["comment"]

            # Check accuracy score
            accuracy_call = next(c for c in calls if c[1]["name"] == "g_eval_accuracy")
            assert accuracy_call[1]["value"] == 1.0

            # Check overall score
            overall_call = next(c for c in calls if c[1]["name"] == "g_eval_overall")
            assert overall_call[1]["value"] == result.overall
            assert "test_agent" in overall_call[1]["comment"]

    @pytest.mark.asyncio
    async def test_g_eval_gracefully_handles_langfuse_failure(self) -> None:
        """Test that G-Eval continues if Langfuse submission fails."""
        from app.shared.services.g_eval.scorer import g_eval_score

        with (
            patch("app.shared.services.g_eval.scorer.get_cache") as mock_cache_factory,
            patch("app.core.langfuse_service.submit_langfuse_score") as mock_submit,
            patch("app.shared.services.g_eval.scorer.get_agent_rubrics") as mock_rubrics,
        ):
            # Mock agent rubrics to return only the criteria we're testing
            mock_rubrics.return_value = {
                "criteria": ["completeness"],
                "weights": {"completeness": 1.0},
            }

            # Mock cache to return score (avoid LLM calls)
            mock_cache = MagicMock()
            completeness_cached = MagicMock()
            completeness_cached.score = 4
            completeness_cached.normalized = 0.75
            completeness_cached.confidence = 0.85
            completeness_cached.reasoning = "Good completeness"

            mock_cache.get.return_value = completeness_cached
            mock_cache_factory.return_value = mock_cache

            # Mock Langfuse failure
            mock_submit.side_effect = Exception("Langfuse connection error")

            # Should still complete successfully despite Langfuse failure
            result = await g_eval_score(
                input_content="Test input",
                output="Test output",
                agent_type="test_agent",
                criteria=["completeness"],
                use_self_consistency=False,
            )

            # Result should still be valid
            assert result.overall > 0
            assert result.overall == 0.75  # normalized score from mock
            assert "completeness" in result.criteria_scores
            # Error should be caught and logged, not propagated
            assert result.error is None


class TestSelfConsistencyIntegration:
    """Integration tests for self-consistency with g_eval_score."""

    @pytest.mark.asyncio
    async def test_g_eval_score_with_self_consistency_enabled(self) -> None:
        """Test g_eval_score with self_consistency=True."""
        from app.shared.services.g_eval.scorer import g_eval_score

        with patch("app.shared.services.g_eval.self_consistency.get_chat_model") as mock_model:
            mock_response = MagicMock()
            mock_response.content = """
            <reasoning>Good quality output</reasoning>
            <score>4</score>
            <confidence>0.85</confidence>
            """
            mock_llm = AsyncMock()
            # Mock abatch to return 3 responses per batch call
            mock_llm.abatch = AsyncMock(return_value=[mock_response] * 3)
            mock_model.return_value = mock_llm

            result = await g_eval_score(
                input_content="Test input",
                output="Test output",
                agent_type="test_agent",
                criteria=["completeness", "accuracy"],
                use_self_consistency=True,
                n_samples=3,
            )

            # Should have voting distributions
            assert result.voting_distribution is not None
            assert "completeness" in result.voting_distribution
            assert "accuracy" in result.voting_distribution

            # Each criterion should have been scored with 3 samples in one batch
            # 2 criteria x 1 batch call each = 2 abatch calls
            assert mock_llm.abatch.call_count == 2

    @pytest.mark.asyncio
    async def test_g_eval_score_without_self_consistency(self) -> None:
        """Test g_eval_score with default self_consistency=False."""
        from app.shared.services.g_eval.scorer import g_eval_score

        with (
            patch("app.shared.services.g_eval.scorer.get_cache") as mock_cache_factory,
            patch("app.shared.services.g_eval.scorer.get_agent_rubrics") as mock_rubrics,
        ):
            # Mock agent rubrics to return only the criteria we're testing
            mock_rubrics.return_value = {
                "criteria": ["completeness"],
                "weights": {"completeness": 1.0},
            }

            # Mock cache to return score (simulates scoring without self-consistency)
            mock_cache = MagicMock()
            completeness_cached = MagicMock()
            completeness_cached.score = 4
            completeness_cached.normalized = 0.75
            completeness_cached.confidence = 0.85
            completeness_cached.reasoning = "Good"

            mock_cache.get.return_value = completeness_cached
            mock_cache_factory.return_value = mock_cache

            result = await g_eval_score(
                input_content="Test input",
                output="Test output",
                agent_type="test_agent",
                criteria=["completeness"],
                use_self_consistency=False,  # Explicit False
            )

            # Should NOT have voting distributions
            assert result.voting_distribution is None

            # Verify result came from cache (standard mode, not self-consistency)
            assert result.overall == 0.75
            assert result.criteria_scores["completeness"].score == 4
