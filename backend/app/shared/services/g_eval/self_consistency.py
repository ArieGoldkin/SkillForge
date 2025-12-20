"""Self-Consistency Voting for G-Eval to Improve Accuracy.

This module implements self-consistency voting (Wang et al., 2022) for G-Eval scoring.
By generating multiple reasoning paths with sampling (temperature > 0), then using
majority voting, we can improve accuracy by 15-25% according to research.

Key techniques:
1. Generate N samples with temperature=0.7 for diverse reasoning paths
2. Use majority voting to select final score
3. Calculate confidence as agreement ratio (e.g., 3/3 agree = 1.0)
4. Run samples in parallel with asyncio for efficiency
5. Only use when initial confidence < 0.8 (cost optimization)

Reference:
- Self-Consistency (Wang et al., 2022): https://arxiv.org/abs/2203.11171
- G-Eval paper: https://arxiv.org/abs/2303.16634
"""

from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.timeout_config import create_runnable_config
from app.shared.services.g_eval.scorer import (
    G_EVAL_SYSTEM_PROMPT,
    G_EVAL_USER_PROMPT,
    CriterionScore,
    _parse_g_eval_response,
)

logger = get_logger(__name__)

# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class VotingDistribution:
    """Distribution of votes across score values."""

    score_counts: dict[int, int] = field(default_factory=dict)  # score -> count
    total_votes: int = 0
    winning_score: int = 3
    winning_count: int = 0
    confidence: float = 0.0  # agreement ratio (winning_count / total_votes)

    def __post_init__(self) -> None:
        """Calculate derived fields."""
        if self.score_counts:
            # Find most common score
            max_count = max(self.score_counts.values())
            # In case of tie, prefer higher score (benefit of doubt)
            winners = [score for score, count in self.score_counts.items() if count == max_count]
            self.winning_score = max(winners)
            self.winning_count = max_count
            self.total_votes = sum(self.score_counts.values())
            self.confidence = self.winning_count / self.total_votes if self.total_votes > 0 else 0.0


@dataclass
class SelfConsistencyResult:
    """Result from self-consistency voting for a single criterion."""

    criterion: str
    final_score: CriterionScore
    voting_distribution: VotingDistribution
    individual_samples: list[CriterionScore] = field(default_factory=list)
    error: str | None = None


# ============================================================================
# Core Self-Consistency Functions
# ============================================================================


async def _score_criterion_with_temperature(  # noqa: PLR0913 - Function needs all these parameters
    input_content: str,
    output: str,
    criterion: str,
    agent_type: str,
    rubric_text: str,
    temperature: float = 0.7,
) -> CriterionScore:
    """Score a single criterion with specified temperature for sampling.

    Args:
        input_content: The original input/task
        output: The generated output to evaluate
        criterion: The evaluation criterion
        agent_type: Agent type for rubric selection
        rubric_text: Pre-formatted rubric text
        temperature: Sampling temperature (0.7 recommended for diversity)

    Returns:
        CriterionScore with evaluation results

    """
    # Get model with specific temperature for sampling and task routing for cost optimization
    model = get_chat_model(
        config={
            "configurable": {
                "temperature": temperature,
            }
        },
        task_type="g_eval",
    )

    system_prompt = G_EVAL_SYSTEM_PROMPT.format(
        criterion=criterion,
        rubric_text=rubric_text,
    )

    user_prompt = G_EVAL_USER_PROMPT.format(
        input_content=input_content[:2000],  # Truncate for context limits
        output=output[:3000],
        criterion=criterion,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    try:
        config = create_runnable_config()
        response = await model.ainvoke(messages, config=config)
        # Ensure content is a string (handle LangChain's str | list type)
        content = response.content if isinstance(response.content, str) else str(response.content)
        result = _parse_g_eval_response(content, criterion)

        # Submit token usage and cost metrics to Langfuse
        # Import here to avoid circular dependency
        from app.shared.services.g_eval.scorer import _submit_token_metrics_to_langfuse

        _submit_token_metrics_to_langfuse(
            response=response,
            criterion=f"{criterion}_sc_sample",  # Mark as self-consistency sample
            agent_type=agent_type,
        )

        return result
    except Exception as e:
        logger.exception(
            "self_consistency_sample_error",
            criterion=criterion,
            temperature=temperature,
            error=str(e),
        )
        # Return neutral score on error
        return CriterionScore(
            criterion=criterion,
            score=3,
            normalized=0.5,
            confidence=0.0,
            reasoning=f"Error during sampling: {e!s}",
        )


async def score_criterion_with_self_consistency(  # noqa: PLR0913 - Function needs all these parameters
    input_content: str,
    output: str,
    criterion: str,
    agent_type: str,
    rubric_text: str,
    n_samples: int = 3,
    temperature: float = 0.7,
) -> SelfConsistencyResult:
    """Score a criterion using self-consistency voting.

    Generates N independent samples with temperature sampling, then uses
    majority voting to determine the final score. This improves accuracy
    by 15-25% according to research (Wang et al., 2022).

    Args:
        input_content: The original input/task
        output: The generated output to evaluate
        criterion: The evaluation criterion
        agent_type: Agent type for rubric selection
        rubric_text: Pre-formatted rubric text
        n_samples: Number of samples to generate (default=3, min=2)
        temperature: Sampling temperature (0.7 for diversity)

    Returns:
        SelfConsistencyResult with voting distribution and final score

    """
    # Ensure minimum samples for meaningful voting
    n_samples = max(2, n_samples)

    logger.info(
        "self_consistency_voting_started",
        criterion=criterion,
        agent_type=agent_type,
        n_samples=n_samples,
        temperature=temperature,
    )

    # Generate N samples in parallel
    tasks = [
        _score_criterion_with_temperature(
            input_content=input_content,
            output=output,
            criterion=criterion,
            agent_type=agent_type,
            rubric_text=rubric_text,
            temperature=temperature,
        )
        for _ in range(n_samples)
    ]

    try:
        samples = await asyncio.gather(*tasks)
    except Exception as e:
        logger.exception("self_consistency_batch_error", error=str(e))
        # Return error result with neutral score
        neutral_score = CriterionScore(
            criterion=criterion,
            score=3,
            normalized=0.5,
            confidence=0.0,
            reasoning=f"Error during self-consistency voting: {e!s}",
        )
        return SelfConsistencyResult(
            criterion=criterion,
            final_score=neutral_score,
            voting_distribution=VotingDistribution(
                score_counts={3: 1},
                total_votes=1,
                winning_score=3,
                winning_count=1,
                confidence=0.0,
            ),
            individual_samples=[neutral_score],
            error=str(e),
        )

    # Count votes for each score
    score_votes = Counter(sample.score for sample in samples)
    distribution = VotingDistribution(score_counts=dict(score_votes))

    # Find the sample that matches the winning score (prefer higher confidence if tie)
    winning_samples = [s for s in samples if s.score == distribution.winning_score]
    final_sample = max(winning_samples, key=lambda s: s.confidence)

    # Update confidence to reflect voting agreement
    # If all samples agree: confidence = 1.0
    # If 2/3 agree: confidence = 0.67
    final_score = CriterionScore(
        criterion=criterion,
        score=distribution.winning_score,
        normalized=final_sample.normalized,
        confidence=distribution.confidence,  # Use voting confidence
        reasoning=final_sample.reasoning,  # Use reasoning from winning sample
    )

    logger.info(
        "self_consistency_voting_completed",
        criterion=criterion,
        final_score=distribution.winning_score,
        voting_confidence=distribution.confidence,
        score_distribution=distribution.score_counts,
        n_samples=n_samples,
    )

    return SelfConsistencyResult(
        criterion=criterion,
        final_score=final_score,
        voting_distribution=distribution,
        individual_samples=samples,
    )


async def score_with_adaptive_self_consistency(  # noqa: PLR0913 - Function needs all these parameters
    input_content: str,
    output: str,
    criterion: str,
    agent_type: str,
    rubric_text: str,
    initial_score: CriterionScore,
    confidence_threshold: float = 0.8,
    n_samples: int = 3,
) -> SelfConsistencyResult:
    """Adaptively use self-consistency only when initial confidence is low.

    Cost optimization: Only run expensive self-consistency voting when the
    initial single-shot score has low confidence (< threshold).

    Args:
        input_content: The original input/task
        output: The generated output to evaluate
        criterion: The evaluation criterion
        agent_type: Agent type for rubric selection
        rubric_text: Pre-formatted rubric text
        initial_score: Initial single-shot score (temperature=0)
        confidence_threshold: Only use voting if confidence < this (default=0.8)
        n_samples: Number of samples for voting (default=3)

    Returns:
        SelfConsistencyResult - if voting was used, includes distribution;
        if not used, returns initial score wrapped in result

    """
    # If initial confidence is high, skip expensive voting
    if initial_score.confidence >= confidence_threshold:
        logger.info(
            "self_consistency_skipped",
            criterion=criterion,
            initial_confidence=initial_score.confidence,
            threshold=confidence_threshold,
        )

        # Return initial score wrapped in self-consistency result
        return SelfConsistencyResult(
            criterion=criterion,
            final_score=initial_score,
            voting_distribution=VotingDistribution(
                score_counts={initial_score.score: 1},
                total_votes=1,
                winning_score=initial_score.score,
                winning_count=1,
                confidence=initial_score.confidence,
            ),
            individual_samples=[initial_score],
        )

    # Low confidence - use self-consistency voting
    logger.info(
        "self_consistency_triggered",
        criterion=criterion,
        initial_confidence=initial_score.confidence,
        threshold=confidence_threshold,
    )

    return await score_criterion_with_self_consistency(
        input_content=input_content,
        output=output,
        criterion=criterion,
        agent_type=agent_type,
        rubric_text=rubric_text,
        n_samples=n_samples,
    )
