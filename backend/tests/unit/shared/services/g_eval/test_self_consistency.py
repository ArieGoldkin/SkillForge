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
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
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

            # Verify LLM was called 3 times
            assert mock_llm.ainvoke.call_count == 3

    @pytest.mark.asyncio
    async def test_score_criterion_with_self_consistency_majority(self) -> None:
        """Test self-consistency scoring with majority voting."""
        # Mock the LLM to return different scores
        responses = [
            """<reasoning>Good</reasoning><score>4</score><confidence>0.8</confidence>""",
            """<reasoning>Good</reasoning><score>4</score><confidence>0.9</confidence>""",
            """<reasoning>Fair</reasoning><score>3</score><confidence>0.7</confidence>""",
        ]

        with patch("app.shared.services.g_eval.self_consistency.get_chat_model") as mock_model:
            mock_llm = AsyncMock()
            call_count = 0

            async def mock_ainvoke(*args, **kwargs):
                nonlocal call_count
                mock_response = MagicMock()
                mock_response.content = responses[call_count]
                call_count += 1
                return mock_response

            mock_llm.ainvoke = mock_ainvoke
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
        """Test that samples are generated in parallel."""
        import time

        with patch("app.shared.services.g_eval.self_consistency.get_chat_model") as mock_model:
            mock_response = MagicMock()
            mock_response.content = """
            <reasoning>Test</reasoning>
            <score>3</score>
            <confidence>0.7</confidence>
            """

            async def slow_invoke(*args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate 100ms LLM call
                return mock_response

            mock_llm = AsyncMock()
            mock_llm.ainvoke = slow_invoke
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

            # If parallel: ~0.1s, if sequential: ~0.3s
            # Allow some overhead, but should be much less than 0.3s
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
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
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
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
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
            assert mock_llm.ainvoke.call_count >= 2

    @pytest.mark.asyncio
    async def test_score_criterion_with_self_consistency_error_handling(self) -> None:
        """Test error handling when individual LLM samples fail gracefully."""
        # When individual samples fail, they return neutral scores (score=3)
        # The voting should still work with those neutral scores
        with patch("app.shared.services.g_eval.self_consistency.get_chat_model") as mock_model:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM service error"))
            mock_model.return_value = mock_llm

            result = await score_criterion_with_self_consistency(
                input_content="Test input",
                output="Test output",
                criterion="accuracy",
                agent_type="test_agent",
                rubric_text="Score 1-5",
                n_samples=3,
            )

            # All samples failed, so voting returns all neutral scores (3)
            assert result.final_score.score == 3  # Neutral
            # When all samples fail and return neutral scores with 0 confidence,
            # voting confidence will be 1.0 (all agree on score 3)
            assert result.voting_distribution.winning_score == 3
            assert result.voting_distribution.confidence == 1.0  # All samples agree
            # No error at the voting level (errors are handled at sample level)
            assert result.error is None

    @pytest.mark.asyncio
    async def test_self_consistency_preserves_reasoning(self) -> None:
        """Test that reasoning from winning sample is preserved."""
        responses = [
            """<reasoning>First reasoning</reasoning><score>4</score><confidence>0.8</confidence>""",
            """<reasoning>Second reasoning (winner)</reasoning><score>4</score><confidence>0.9</confidence>""",
            """<reasoning>Third reasoning</reasoning><score>3</score><confidence>0.7</confidence>""",
        ]

        with patch("app.shared.services.g_eval.self_consistency.get_chat_model") as mock_model:
            mock_llm = AsyncMock()
            call_count = 0

            async def mock_ainvoke(*args, **kwargs):
                nonlocal call_count
                mock_response = MagicMock()
                mock_response.content = responses[call_count]
                call_count += 1
                return mock_response

            mock_llm.ainvoke = mock_ainvoke
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

        with (
            patch("app.shared.services.g_eval.scorer._score_criterion") as mock_score,
            patch("app.core.langfuse_config.submit_langfuse_score") as mock_submit,
        ):
            # Mock criterion scores
            mock_score.side_effect = [
                CriterionScore(
                    criterion="completeness",
                    score=4,
                    normalized=0.75,
                    confidence=0.85,
                    reasoning="Good completeness",
                ),
                CriterionScore(
                    criterion="accuracy",
                    score=5,
                    normalized=1.0,
                    confidence=0.9,
                    reasoning="Excellent accuracy",
                ),
            ]

            result = await g_eval_score(
                input_content="Test input",
                output="Test output",
                agent_type="test_agent",
                criteria=["completeness", "accuracy"],
                use_self_consistency=False,
            )

            # Verify scores were submitted to Langfuse
            # Should submit 3 scores: 2 criteria + 1 overall
            assert mock_submit.call_count == 3

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
            patch("app.shared.services.g_eval.scorer._score_criterion") as mock_score,
            patch("app.core.langfuse_config.submit_langfuse_score") as mock_submit,
        ):
            # Mock Langfuse failure
            mock_submit.side_effect = Exception("Langfuse connection error")

            # Mock criterion scores
            mock_score.return_value = CriterionScore(
                criterion="completeness",
                score=4,
                normalized=0.75,
                confidence=0.85,
                reasoning="Good completeness",
            )

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
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
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

            # Each criterion should have been scored with 3 samples
            # 2 criteria x 3 samples = 6 LLM calls
            assert mock_llm.ainvoke.call_count == 6

    @pytest.mark.asyncio
    async def test_g_eval_score_without_self_consistency(self) -> None:
        """Test g_eval_score with default self_consistency=False."""
        from app.shared.services.g_eval.scorer import g_eval_score

        with patch("app.shared.services.g_eval.scorer._score_criterion") as mock_score:
            mock_score.return_value = CriterionScore(
                criterion="completeness",
                score=4,
                normalized=0.75,
                confidence=0.85,
                reasoning="Good",
            )

            result = await g_eval_score(
                input_content="Test input",
                output="Test output",
                agent_type="test_agent",
                criteria=["completeness"],
                use_self_consistency=False,  # Explicit False
            )

            # Should NOT have voting distributions
            assert result.voting_distribution is None

            # Should call standard scorer only once per criterion
            assert mock_score.call_count == 1
