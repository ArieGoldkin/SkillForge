"""G-Eval LLM-as-Judge Scorer.

This module implements G-Eval scoring using LLM-as-Judge with
chain-of-thought reasoning for quality evaluation.

The scorer:
1. Uses agent-specific rubrics for domain-aware evaluation
2. Scores multiple criteria in parallel for efficiency
3. Provides confidence scores and reasoning for transparency
4. Two-layer caching: file-based cache + Redis semantic cache (at model level)

Reference: G-Eval paper (https://arxiv.org/abs/2303.16634)
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.timeout_config import create_runnable_config
from app.core.tracing import robust_traceable
from app.shared.services.g_eval.cache import get_cache
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
    voting_distribution: dict[str, dict[int, int]] | None = (
        None  # Per-criterion vote counts (score -> count)
    )

    @property
    def completeness(self) -> float:
        """Get completeness score (normalized 0-1)."""
        return self.criteria_scores.get(
            "completeness", CriterionScore("", 3, 0.6, 0.5, "")
        ).normalized

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

Evaluate the {criterion} of this output using the rubric provided.
Follow the response format exactly."""


# ============================================================================
# Parsing Functions
# ============================================================================


def _extract_text_from_llm_response(content: str | list) -> str:
    """Extract text from LLM response, handling various formats.

    Handles:
    - Simple string responses
    - Gemini's list format: [{'type': 'text', 'text': '...', 'extras': {...}}]
    - Other multi-part responses

    Args:
        content: Raw response content from LLM

    Returns:
        Extracted text string

    """
    if isinstance(content, str):
        return content

    if isinstance(content, list) and content:
        first_item = content[0]
        # Handle Gemini's dict format with 'text' key
        if isinstance(first_item, dict):
            return str(first_item.get("text", first_item))
        return str(first_item)

    return str(content)


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


def _submit_token_metrics_to_langfuse(
    response: Any,
    criterion: str,
    agent_type: str,
) -> None:
    """Submit token usage and cost metrics to Langfuse for cost tracking.

    Extracts token counts from LLM response and calculates cost based on
    model pricing. Submits individual metrics for:
    - Input token count
    - Output token count
    - Total token count
    - Estimated cost in USD

    Args:
        response: LLM response object (AIMessage) with usage_metadata
        criterion: The criterion being evaluated
        agent_type: Agent type for metric categorization

    """
    try:
        from app.core.langfuse_service import submit_langfuse_score
        from app.shared.services.g_eval.cost_tracker import GEvalCostTracker

        # Extract token usage from response
        # LangChain AIMessage has usage_metadata field (optional)
        usage = getattr(response, "usage_metadata", None)

        if not usage:
            logger.debug(
                "token_metrics_no_usage_data",
                criterion=criterion,
                agent_type=agent_type,
                message="No usage_metadata in response - skipping token metrics",
            )
            return

        # Extract token counts (handle both dict and object attribute access)
        input_tokens = (
            usage.get("input_tokens", 0)
            if isinstance(usage, dict)
            else getattr(usage, "input_tokens", 0)
        )
        output_tokens = (
            usage.get("output_tokens", 0)
            if isinstance(usage, dict)
            else getattr(usage, "output_tokens", 0)
        )
        total_tokens = (
            usage.get("total_tokens", 0)
            if isinstance(usage, dict)
            else getattr(usage, "total_tokens", 0)
        )

        # If total not provided, calculate it
        if total_tokens == 0 and (input_tokens > 0 or output_tokens > 0):
            total_tokens = input_tokens + output_tokens

        # Submit token metrics to Langfuse
        submit_langfuse_score(
            name="token_count_input",
            value=float(input_tokens),
            comment=f"G-Eval {criterion}: Input tokens for {agent_type}",
        )
        submit_langfuse_score(
            name="token_count_output",
            value=float(output_tokens),
            comment=f"G-Eval {criterion}: Output tokens for {agent_type}",
        )
        submit_langfuse_score(
            name="token_count_total",
            value=float(total_tokens),
            comment=f"G-Eval {criterion}: Total tokens for {agent_type}",
        )

        # Record usage in cost tracker for session-level analytics
        cost_tracker = GEvalCostTracker.get_instance()
        eval_id = f"g_eval_{criterion}_{agent_type}"

        # Extract model name from response metadata
        response_metadata = getattr(response, "response_metadata", {})
        model_name = response_metadata.get(
            "model_name", "gemini-3-flash"
        )  # Default to g_eval model

        # Cached tokens (if available) - Anthropic/Gemini provide this
        cached_tokens = (
            usage.get("cache_read_input_tokens", 0)
            if isinstance(usage, dict)
            else getattr(usage, "cache_read_input_tokens", 0)
        )

        cost = cost_tracker.record_usage(
            eval_id=eval_id,
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            variant=agent_type,
        )

        # Submit cost metric to Langfuse
        submit_langfuse_score(
            name="cost_usd",
            value=cost.total_cost,
            comment=f"G-Eval {criterion}: ${cost.total_cost:.6f} for {agent_type} ({model_name})",
        )

        logger.debug(
            "token_metrics_submitted_to_langfuse",
            criterion=criterion,
            agent_type=agent_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cached_tokens=cached_tokens,
            cost_usd=cost.total_cost,
            model=model_name,
        )

    except Exception as e:  # noqa: BLE001 - Graceful degradation for observability
        # Don't fail scoring if metric submission fails
        logger.warning(
            "token_metrics_submission_failed",
            criterion=criterion,
            agent_type=agent_type,
            error=str(e),
        )


def _submit_g_eval_scores_to_langfuse(
    criteria_scores: dict[str, CriterionScore],
    overall: float,
    agent_type: str,
    trace_id: str | None = None,
) -> None:
    """Submit G-Eval scores to Langfuse for quality analytics.

    This enables quality dashboards in Langfuse UI showing:
    - Score distributions over time
    - Per-criterion quality trends
    - Agent-specific quality patterns

    Args:
        criteria_scores: Dictionary of criterion name to CriterionScore
        overall: Overall weighted average score (0.0-1.0)
        agent_type: Agent type for score categorization
        trace_id: Langfuse trace ID to attach scores to

    """
    try:
        from app.core.langfuse_service import submit_langfuse_score

        # Submit each criterion score individually for detailed analytics
        for criterion, score_obj in criteria_scores.items():
            submit_langfuse_score(
                trace_id=trace_id,
                name=f"g_eval_{criterion}",
                value=score_obj.normalized,
                comment=f"{agent_type}: {score_obj.reasoning[:200]}",  # Truncate reasoning
            )

        # Submit overall G-Eval score
        submit_langfuse_score(
            trace_id=trace_id,
            name="g_eval_overall",
            value=overall,
            comment=f"{agent_type}: Weighted average across {len(criteria_scores)} criteria",
        )

        logger.debug(
            "g_eval_scores_submitted_to_langfuse",
            agent_type=agent_type,
            criteria_count=len(criteria_scores),
            overall_score=overall,
            trace_id=trace_id,
        )

    except Exception as e:  # noqa: BLE001 - Graceful degradation for observability
        # Don't fail scoring if Langfuse submission fails
        logger.warning(
            "g_eval_langfuse_submission_failed",
            agent_type=agent_type,
            error=str(e),
        )


@robust_traceable(
    name="g_eval_score_criterion",
    run_type="llm",
    tags=["g_eval", "criterion", "llm_call"],
    metadata={"service": "g_eval"},
)
async def _score_criterion(
    input_content: str,
    output: str,
    criterion: str,
    agent_type: str,
    use_cache: bool = True,
) -> CriterionScore:
    """Score a single criterion using G-Eval LLM-as-Judge.

    Args:
        input_content: The original input/task
        output: The generated output to evaluate
        criterion: The evaluation criterion
        agent_type: Agent type for rubric selection
        use_cache: Whether to use caching (default True)

    Returns:
        CriterionScore with evaluation results

    """
    cache = get_cache()

    # Check L1 file-based cache first (fastest, exact match)
    if use_cache:
        cached = cache.get(input_content, output, agent_type, criterion)
        if cached:
            logger.debug(
                "g_eval_file_cache_hit",
                criterion=criterion,
                agent_type=agent_type,
            )
            # Submit cache hit metric to Langfuse
            try:
                from app.core.langfuse_service import submit_langfuse_score

                submit_langfuse_score(
                    name="g_eval_cache_hit",
                    value=1,
                    comment=f"G-Eval file cache hit: {criterion}",
                )
            except Exception as e:  # noqa: BLE001 - Graceful degradation
                logger.warning("g_eval_cache_hit_score_submission_failed", error=str(e))

            return CriterionScore(
                criterion=criterion,
                score=cached.score,
                normalized=cached.normalized,
                confidence=cached.confidence,
                reasoning=cached.reasoning,
            )

    # L1 miss - call LLM with task routing for cost optimization
    # L2 Redis semantic cache is automatically integrated at model level via get_chat_model()
    # This provides semantic matching for similar (but not identical) evaluations

    # Submit cache miss metric to Langfuse (only if cache was enabled)
    if use_cache:
        try:
            from app.core.langfuse_service import submit_langfuse_score

            submit_langfuse_score(
                name="g_eval_cache_hit",
                value=0,
                comment=f"G-Eval file cache miss: {criterion}",
            )
        except Exception as e:  # noqa: BLE001 - Graceful degradation
            logger.warning("g_eval_cache_miss_score_submission_failed", error=str(e))

    model = get_chat_model(task_type="g_eval")

    # Get agent-specific rubric
    rubric_text = format_rubric_for_prompt(agent_type, criterion)

    system_prompt = G_EVAL_SYSTEM_PROMPT.format(
        criterion=criterion,
        rubric_text=rubric_text,
    )

    user_prompt = G_EVAL_USER_PROMPT.format(
        # Issue #299-304: Increased limits to preserve analytical depth
        # Previous limits (2000/3000) were too aggressive, causing G-Eval
        # to see only shallow summaries, resulting in low depth scores (5/10)
        input_content=input_content[:8000],
        output=output[:12000],
        criterion=criterion,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    try:
        config = create_runnable_config()
        response = await model.ainvoke(messages, config=config)
        # Extract text from response (handles Gemini's new dict format)
        content = _extract_text_from_llm_response(response.content)
        result = _parse_g_eval_response(content, criterion)

        # Submit token usage and cost metrics to Langfuse
        _submit_token_metrics_to_langfuse(
            response=response,
            criterion=criterion,
            agent_type=agent_type,
        )

        # Store in L1 file-based cache for future exact matches
        # L2 Redis semantic cache is automatically managed by LangChain at the model level
        if use_cache:
            cache.set(
                input_content=input_content,
                output=output,
                agent_type=agent_type,
                criterion=criterion,
                score=result.score,
                normalized=result.normalized,
                confidence=result.confidence,
                reasoning=result.reasoning,
            )
            logger.debug(
                "g_eval_file_cache_set",
                criterion=criterion,
                agent_type=agent_type,
                score=result.score,
            )

        return result
    except Exception as e:
        logger.exception("g_eval_criterion_error", criterion=criterion, error=str(e))
        # Return neutral score on error
        return CriterionScore(
            criterion=criterion,
            score=3,
            normalized=0.5,
            confidence=0.0,
            reasoning=f"Error during evaluation: {e!s}",
        )


@robust_traceable(
    name="g_eval_score",
    run_type="chain",
    tags=["g_eval", "quality", "llm_judge"],
    metadata={"service": "g_eval"},
)
async def g_eval_score(  # noqa: PLR0913, PLR0915, PLR0912 - Complex batch processing with cache optimization
    input_content: str,
    output: dict[str, Any] | str,
    agent_type: str,
    criteria: list[str] | None = None,
    use_cache: bool = True,
    use_self_consistency: bool = False,
    n_samples: int = 3,
    trace_id: str | None = None,
    submit_to_langfuse: bool = True,
) -> GEvalResult:
    """Score output quality using G-Eval LLM-as-Judge.

    Args:
        input_content: The original input/task that generated the output
        output: The generated output to evaluate (dict or string)
        agent_type: Agent type for rubric selection
        criteria: Optional list of criteria to evaluate (defaults to agent config)
        use_cache: Whether to use caching (default True)
        use_self_consistency: Enable self-consistency voting for 15-25% accuracy boost
        n_samples: Number of samples for self-consistency voting (default=3)
        trace_id: Langfuse trace ID to attach scores to (optional)
        submit_to_langfuse: Whether to submit scores to Langfuse directly (default True).
            Set to False when using Langfuse evaluators via run_experiment() since
            those return Evaluation objects that Langfuse handles automatically.

    Returns:
        GEvalResult with overall score and per-criterion breakdown.
        If use_self_consistency=True, includes voting_distribution field.

    """
    # Convert output to string if needed
    if isinstance(output, dict):
        output_str = json.dumps(output, indent=2, default=str)
    else:
        output_str = str(output)

    # Get agent-specific configuration
    config = get_agent_rubrics(agent_type)
    eval_criteria = criteria or config.get(
        "criteria", ["completeness", "accuracy", "coherence", "depth"]
    )
    weights = config.get("weights", {c: 1.0 / len(eval_criteria) for c in eval_criteria})

    logger.info(
        "g_eval_scoring_started",
        agent_type=agent_type,
        criteria=eval_criteria,
        output_length=len(output_str),
        use_self_consistency=use_self_consistency,
    )

    # Branch based on self-consistency mode
    if use_self_consistency:
        # Import here to avoid circular dependency
        from app.shared.services.g_eval.self_consistency import (
            score_criterion_with_self_consistency,
        )

        # Pre-format rubrics for all criteria (avoid redundant formatting)
        rubric_texts = {c: format_rubric_for_prompt(agent_type, c) for c in eval_criteria}

        # Score all criteria with self-consistency voting in parallel
        tasks = [
            score_criterion_with_self_consistency(
                input_content=input_content,
                output=output_str,
                criterion=criterion,
                agent_type=agent_type,
                rubric_text=rubric_texts[criterion],
                n_samples=n_samples,
            )
            for criterion in eval_criteria
        ]

        try:
            sc_results = await asyncio.gather(*tasks)
        except Exception as e:
            logger.exception("g_eval_self_consistency_batch_error", error=str(e))
            return GEvalResult(
                overall=0.5,
                agent_type=agent_type,
                error=str(e),
            )

        # Extract final scores and voting distributions
        criteria_scores = {r.final_score.criterion: r.final_score for r in sc_results}
        reasoning = {r.criterion: r.final_score.reasoning for r in sc_results}
        voting_dist = {r.criterion: r.voting_distribution.score_counts for r in sc_results}

        # Calculate weighted overall score
        overall = sum(
            criteria_scores[c].normalized * weights.get(c, 1.0 / len(eval_criteria))
            for c in eval_criteria
            if c in criteria_scores
        )

        # Average confidence (using voting confidence)
        avg_confidence = (
            sum(r.final_score.confidence for r in sc_results) / len(sc_results)
            if sc_results
            else 0.5
        )

        logger.info(
            "g_eval_scoring_completed",
            agent_type=agent_type,
            overall=overall,
            confidence=avg_confidence,
            scores={c: r.score for c, r in criteria_scores.items()},
            voting_distributions=voting_dist,
        )

        # Submit G-Eval scores to Langfuse for quality analytics
        # Issue #428: Only submit directly when not using Langfuse evaluators
        # (evaluators return Evaluation objects that Langfuse handles automatically)
        if submit_to_langfuse:
            _submit_g_eval_scores_to_langfuse(
                criteria_scores=criteria_scores,
                overall=overall,
                agent_type=agent_type,
                trace_id=trace_id,
            )

        return GEvalResult(
            overall=overall,
            criteria_scores=criteria_scores,
            confidence=avg_confidence,
            reasoning=reasoning,
            agent_type=agent_type,
            voting_distribution=voting_dist,
        )

    # Standard mode without self-consistency
    # Score all criteria with optimized batch processing using abatch()
    cache = get_cache()
    cached_results: dict[str, CriterionScore] = {}
    criteria_to_score: list[str] = []

    # First pass: check cache for all criteria
    if use_cache:
        for criterion in eval_criteria:
            cached = cache.get(input_content, output_str, agent_type, criterion)
            if cached:
                logger.debug(
                    "g_eval_file_cache_hit",
                    criterion=criterion,
                    agent_type=agent_type,
                )
                # Submit cache hit metric to Langfuse
                try:
                    from app.core.langfuse_service import submit_langfuse_score

                    submit_langfuse_score(
                        name="g_eval_cache_hit",
                        value=1,
                        comment=f"G-Eval file cache hit: {criterion}",
                    )
                except Exception as e:  # noqa: BLE001 - Graceful degradation
                    logger.warning("g_eval_cache_hit_score_submission_failed", error=str(e))

                cached_results[criterion] = CriterionScore(
                    criterion=criterion,
                    score=cached.score,
                    normalized=cached.normalized,
                    confidence=cached.confidence,
                    reasoning=cached.reasoning,
                )
            else:
                criteria_to_score.append(criterion)
                # Submit cache miss metric to Langfuse
                try:
                    from app.core.langfuse_service import submit_langfuse_score

                    submit_langfuse_score(
                        name="g_eval_cache_hit",
                        value=0,
                        comment=f"G-Eval file cache miss: {criterion}",
                    )
                except Exception as e:  # noqa: BLE001 - Graceful degradation
                    logger.warning("g_eval_cache_miss_score_submission_failed", error=str(e))
    else:
        criteria_to_score = list(eval_criteria)

    # Second pass: batch score all cache misses using abatch() for 5-10x speedup
    batch_results: list[CriterionScore] = []
    if criteria_to_score:
        try:
            # Build batch inputs for parallel processing
            model = get_chat_model(task_type="g_eval")

            batch_inputs: list[list[BaseMessage]] = []
            for criterion in criteria_to_score:
                rubric_text = format_rubric_for_prompt(agent_type, criterion)
                system_prompt = G_EVAL_SYSTEM_PROMPT.format(
                    criterion=criterion,
                    rubric_text=rubric_text,
                )
                user_prompt = G_EVAL_USER_PROMPT.format(
                    input_content=input_content[:8000],
                    output=output_str[:12000],
                    criterion=criterion,
                )
                batch_inputs.append(
                    [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=user_prompt),
                    ]
                )

            # Use abatch() for parallel LLM processing (5-10x faster than gather)
            config = create_runnable_config()
            # Type checker doesn't see list[BaseMessage] as valid Sequence[BaseMessage]
            responses = await model.abatch(
                batch_inputs,  # type: ignore[arg-type]
                config=config,
                max_concurrency=5,  # Prevent rate limit violations
            )

            # Parse responses and cache results
            for i, response in enumerate(responses):
                criterion = criteria_to_score[i]
                content = _extract_text_from_llm_response(response.content)
                result = _parse_g_eval_response(content, criterion)

                # Submit token usage and cost metrics to Langfuse
                _submit_token_metrics_to_langfuse(
                    response=response,
                    criterion=criterion,
                    agent_type=agent_type,
                )

                # Store in cache
                if use_cache:
                    cache.set(
                        input_content=input_content,
                        output=output_str,
                        agent_type=agent_type,
                        criterion=criterion,
                        score=result.score,
                        normalized=result.normalized,
                        confidence=result.confidence,
                        reasoning=result.reasoning,
                    )
                    logger.debug(
                        "g_eval_file_cache_set",
                        criterion=criterion,
                        agent_type=agent_type,
                        score=result.score,
                    )

                batch_results.append(result)

        except Exception as e:
            logger.exception("g_eval_batch_error", error=str(e))
            return GEvalResult(
                overall=0.5,
                agent_type=agent_type,
                error=str(e),
            )

    # Combine cached and batch results
    results = list(cached_results.values()) + batch_results

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

    # Submit G-Eval scores to Langfuse for quality analytics
    # Issue #428: Only submit directly when not using Langfuse evaluators
    if submit_to_langfuse:
        _submit_g_eval_scores_to_langfuse(
            criteria_scores=criteria_scores,
            overall=overall,
            agent_type=agent_type,
            trace_id=trace_id,
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
