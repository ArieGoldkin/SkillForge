"""G-Eval LLM-as-Judge Scorer.

This module implements G-Eval scoring using LLM-as-Judge with
chain-of-thought reasoning for quality evaluation.

The scorer:
1. Uses agent-specific rubrics for domain-aware evaluation
2. Scores multiple criteria in parallel for efficiency
3. Provides confidence scores and reasoning for transparency
4. Caches results to reduce redundant LLM calls

Reference: G-Eval paper (https://arxiv.org/abs/2303.16634)
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.shared.services.g_eval.rubrics import (
    format_rubric_for_prompt,
    get_agent_rubrics,
)

logger = get_logger(__name__)

# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class CriterionScore:
    """Score for a single evaluation criterion."""

    criterion: str
    score: int  # 1-5
    normalized: float  # 0.0-1.0
    confidence: float  # 0.0-1.0
    reasoning: str


@dataclass
class GEvalResult:
    """Complete G-Eval scoring result."""

    overall: float  # 0.0-1.0 weighted average
    criteria_scores: dict[str, CriterionScore] = field(default_factory=dict)
    confidence: float = 0.0  # Average confidence across criteria
    reasoning: dict[str, str] = field(default_factory=dict)  # Per-criterion reasoning
    agent_type: str = ""
    error: str | None = None

    @property
    def completeness(self) -> float:
        """Get completeness score (normalized 0-1)."""
        return self.criteria_scores.get("completeness", CriterionScore("", 3, 0.6, 0.5, "")).normalized

    @property
    def accuracy(self) -> float:
        """Get accuracy score (normalized 0-1)."""
        return self.criteria_scores.get("accuracy", CriterionScore("", 3, 0.6, 0.5, "")).normalized

    @property
    def coherence(self) -> float:
        """Get coherence score (normalized 0-1)."""
        return self.criteria_scores.get("coherence", CriterionScore("", 3, 0.6, 0.5, "")).normalized

    @property
    def depth(self) -> float:
        """Get depth score (normalized 0-1)."""
        return self.criteria_scores.get("depth", CriterionScore("", 3, 0.6, 0.5, "")).normalized


# ============================================================================
# Prompt Templates
# ============================================================================

G_EVAL_SYSTEM_PROMPT = """You are an expert evaluator assessing AI-generated content quality.

Your task is to evaluate the {criterion} of the output on a 1-5 scale.

## Rubric for {criterion}:
{rubric_text}

## Evaluation Process:
1. Read the input content and generated output carefully
2. Think step-by-step about how well the output addresses the criterion
3. Consider specific examples from the output that support your assessment
4. Be calibrated: use the full 1-5 range appropriately
5. Provide your reasoning, then your final score

## Response Format (MUST follow exactly):
<reasoning>
[Your step-by-step analysis here - be specific about what you observe]
</reasoning>

<score>[1-5]</score>
<confidence>[0.0-1.0]</confidence>
"""

G_EVAL_USER_PROMPT = """## Task/Input:
{input_content}

## Generated Output to Evaluate:
{output}

Evaluate the {criterion} of this output using the rubric provided. Follow the response format exactly."""


# ============================================================================
# Parsing Functions
# ============================================================================


def _parse_g_eval_response(response: str, criterion: str) -> CriterionScore:
    """Parse G-Eval LLM response to extract structured score.

    Args:
        response: Raw LLM response text
        criterion: The criterion being evaluated

    Returns:
        CriterionScore with parsed values

    """
    # Extract reasoning
    reasoning_match = re.search(r"<reasoning>(.*?)</reasoning>", response, re.DOTALL)
    reasoning = reasoning_match.group(1).strip() if reasoning_match else "No reasoning provided"

    # Extract score (1-5)
    score_match = re.search(r"<score>\s*(\d)\s*</score>", response)
    score = int(score_match.group(1)) if score_match else 3  # Default to middle
    score = max(1, min(5, score))  # Clamp to valid range

    # Extract confidence (0.0-1.0)
    confidence_match = re.search(r"<confidence>\s*([\d.]+)\s*</confidence>", response)
    confidence = float(confidence_match.group(1)) if confidence_match else 0.7
    confidence = max(0.0, min(1.0, confidence))

    # Normalize score to 0-1 range
    normalized = (score - 1) / 4.0  # Maps 1-5 to 0.0-1.0

    return CriterionScore(
        criterion=criterion,
        score=score,
        normalized=normalized,
        confidence=confidence,
        reasoning=reasoning[:500],  # Truncate for storage
    )


# ============================================================================
# Core Scoring Functions
# ============================================================================


async def _score_criterion(
    input_content: str,
    output: str,
    criterion: str,
    agent_type: str,
) -> CriterionScore:
    """Score a single criterion using G-Eval LLM-as-Judge.

    Args:
        input_content: The original input/task
        output: The generated output to evaluate
        criterion: The evaluation criterion
        agent_type: Agent type for rubric selection

    Returns:
        CriterionScore with evaluation results

    """
    model = get_chat_model()

    # Get agent-specific rubric
    rubric_text = format_rubric_for_prompt(agent_type, criterion)

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
        response = await model.ainvoke(messages)
        return _parse_g_eval_response(response.content, criterion)
    except Exception as e:  # noqa: BLE001 - Graceful degradation for LLM errors
        logger.exception("g_eval_criterion_error", criterion=criterion, error=str(e))
        # Return neutral score on error
        return CriterionScore(
            criterion=criterion,
            score=3,
            normalized=0.5,
            confidence=0.0,
            reasoning=f"Error during evaluation: {e!s}",
        )


async def g_eval_score(
    input_content: str,
    output: dict[str, Any] | str,
    agent_type: str,
    criteria: list[str] | None = None,
) -> GEvalResult:
    """Score output quality using G-Eval LLM-as-Judge.

    Args:
        input_content: The original input/task that generated the output
        output: The generated output to evaluate (dict or string)
        agent_type: Agent type for rubric selection
        criteria: Optional list of criteria to evaluate (defaults to agent config)

    Returns:
        GEvalResult with overall score and per-criterion breakdown

    """
    # Convert output to string if needed
    if isinstance(output, dict):
        output_str = json.dumps(output, indent=2, default=str)
    else:
        output_str = str(output)

    # Get agent-specific configuration
    config = get_agent_rubrics(agent_type)
    eval_criteria = criteria or config.get("criteria", ["completeness", "accuracy", "coherence", "depth"])
    weights = config.get("weights", {c: 1.0 / len(eval_criteria) for c in eval_criteria})

    logger.info(
        "g_eval_scoring_started",
        agent_type=agent_type,
        criteria=eval_criteria,
        output_length=len(output_str),
    )

    # Score all criteria in parallel for efficiency
    tasks = [
        _score_criterion(input_content, output_str, criterion, agent_type)
        for criterion in eval_criteria
    ]

    try:
        results = await asyncio.gather(*tasks)
    except Exception as e:  # noqa: BLE001 - Graceful degradation for LLM batch errors
        logger.exception("g_eval_batch_error", error=str(e))
        return GEvalResult(
            overall=0.5,
            agent_type=agent_type,
            error=str(e),
        )

    # Build result
    criteria_scores = {r.criterion: r for r in results}
    reasoning = {r.criterion: r.reasoning for r in results}

    # Calculate weighted overall score
    overall = sum(
        criteria_scores[c].normalized * weights.get(c, 1.0 / len(eval_criteria))
        for c in eval_criteria
        if c in criteria_scores
    )

    # Average confidence
    avg_confidence = sum(r.confidence for r in results) / len(results) if results else 0.5

    logger.info(
        "g_eval_scoring_completed",
        agent_type=agent_type,
        overall=overall,
        confidence=avg_confidence,
        scores={c: r.score for c, r in criteria_scores.items()},
    )

    return GEvalResult(
        overall=overall,
        criteria_scores=criteria_scores,
        confidence=avg_confidence,
        reasoning=reasoning,
        agent_type=agent_type,
    )


async def g_eval_score_batch(
    items: list[tuple[str, dict | str, str]],
    criteria: list[str] | None = None,
) -> list[GEvalResult]:
    """Score multiple outputs in parallel.

    Args:
        items: List of (input_content, output, agent_type) tuples
        criteria: Optional criteria list (uses agent defaults if None)

    Returns:
        List of GEvalResult for each item

    """
    tasks = [
        g_eval_score(input_content, output, agent_type, criteria)
        for input_content, output, agent_type in items
    ]

    return await asyncio.gather(*tasks)
