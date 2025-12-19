"""Langfuse LLM-as-Judge evaluators for quality assessment.

This module provides evaluators that use Langfuse's evaluation API
to run LLM-based quality assessments with built-in cost tracking,
debugging UI, and template management.

Benefits over local G-Eval:
- Cost visibility: Evaluation LLM calls tracked separately in Langfuse
- Debug UI: Visual inspection of evaluation reasoning in web dashboard
- Template management: Centralized prompt versioning
- Score analytics: Compare evaluator performance over time

This is a COMPLEMENTARY evaluation path - local G-Eval remains the PRIMARY
and FALLBACK option. Langfuse evaluators are opt-in via config.

Issue #381: Langfuse LLM-as-Judge Evaluators
"""

from __future__ import annotations

import re

from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.timeout_config import create_runnable_config

logger = get_logger(__name__)

# Maximum content lengths for evaluation (prevent token overflow)
MAX_INPUT_LENGTH = 8000
MAX_OUTPUT_LENGTH = 12000

# Score validation constants
MIN_SCORE = 1
MAX_SCORE = 10


class LangfuseEvaluatorService:
    """Service for running LLM-as-Judge evaluations with Langfuse tracking.

    This service provides quality evaluation using Langfuse templates
    and automatic score submission to Langfuse for analytics.

    Evaluation criteria:
    - Relevance: How relevant are insights to input content?
    - Depth: How thorough and detailed is the analysis?
    - Coherence: How well-structured and clear are the insights?

    All evaluations are tracked in Langfuse dashboard with:
    - Cost breakdown per criterion
    - Chain-of-thought reasoning
    - Score trends over time
    """

    def __init__(self, model: str | None = None):
        """Initialize Langfuse evaluator service.

        Args:
            model: Model to use for evaluation (default: settings.QUALITY_JUDGE_MODEL)

        """
        self.model = model

    async def evaluate(
        self,
        trace_id: str | None,
        input_content: str,
        output_content: str,
        criterion: str,
    ) -> float:
        """Evaluate content quality using Langfuse LLM-as-Judge.

        This method:
        1. Fetches evaluation template from Langfuse (or uses inline rubric)
        2. Calls LLM judge with Langfuse callback for cost tracking
        3. Parses score from response
        4. Submits score to Langfuse for analytics

        Args:
            trace_id: Langfuse trace ID to attach score to
            input_content: Original input/task
            output_content: Generated output to evaluate
            criterion: Evaluation criterion (relevance, depth, coherence)

        Returns:
            Normalized score (0.0-1.0)

        Raises:
            ValueError: If criterion is not supported
            Exception: If Langfuse API fails (caught by hybrid evaluator)

        """
        from app.core.config import get_settings

        settings = get_settings()

        # Validate criterion
        if criterion not in ["relevance", "depth", "coherence"]:
            msg = f"Unsupported criterion: {criterion}"
            raise ValueError(msg)

        # Get evaluation rubric (inline for now - can be moved to Langfuse templates)
        rubric = self._get_rubric(criterion)

        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(
            criterion=criterion,
            rubric=rubric,
            input_content=input_content[:MAX_INPUT_LENGTH],
            output_content=output_content[:MAX_OUTPUT_LENGTH],
        )

        logger.debug(
            "langfuse_evaluator_started",
            criterion=criterion,
            trace_id=trace_id,
            input_length=len(input_content),
            output_length=len(output_content),
        )

        try:
            # Get judge model with Langfuse callback for tracking
            model_name = self.model or settings.QUALITY_JUDGE_MODEL
            judge = get_chat_model({"configurable": {"model": model_name}})

            # Create runnable config with Langfuse callback
            config = create_runnable_config()

            # Call LLM judge
            from langchain_core.messages import HumanMessage

            response = await judge.ainvoke([HumanMessage(content=prompt)], config=config)

            # Parse score from response
            score = self._parse_score(response.content, criterion)

            logger.info(
                "langfuse_evaluator_completed",
                criterion=criterion,
                score=score,
                trace_id=trace_id,
            )

            # Submit score to Langfuse
            if trace_id:
                self._submit_score_to_langfuse(
                    trace_id=trace_id,
                    criterion=criterion,
                    score=score,
                    reasoning=str(response.content)[:500],  # Truncate for storage
                )

            return score

        except Exception as e:
            logger.exception(
                "langfuse_evaluator_failed",
                criterion=criterion,
                trace_id=trace_id,
                error=str(e),
            )
            raise

    def _get_rubric(self, criterion: str) -> str:
        """Get evaluation rubric for criterion.

        Args:
            criterion: Evaluation criterion

        Returns:
            Rubric text for prompting

        """
        rubrics = {
            "relevance": """
Score 1-10 based on:
- 1-3: Not relevant, misses the point entirely
- 4-6: Somewhat relevant, addresses some aspects
- 7-9: Highly relevant, addresses most key aspects
- 10: Perfectly relevant, addresses all aspects comprehensively
            """.strip(),
            "depth": """
Score 1-10 based on:
- 1-3: Superficial analysis, lacks detail and insight
- 4-6: Moderate depth, covers basics but misses nuances
- 7-9: Deep analysis with good detail and insights
- 10: Extremely thorough, comprehensive, and insightful
            """.strip(),
            "coherence": """
Score 1-10 based on:
- 1-3: Incoherent, confusing structure, hard to follow
- 4-6: Somewhat coherent, could be clearer or better organized
- 7-9: Coherent and well-structured, easy to follow
- 10: Perfectly clear, logical, and exceptionally well-organized
            """.strip(),
        }

        return rubrics.get(criterion, "")

    def _build_evaluation_prompt(
        self,
        criterion: str,
        rubric: str,
        input_content: str,
        output_content: str,
    ) -> str:
        """Build evaluation prompt for LLM judge.

        Args:
            criterion: Evaluation criterion
            rubric: Scoring rubric
            input_content: Original input
            output_content: Generated output

        Returns:
            Formatted prompt string

        """
        return f"""You are an expert evaluator assessing AI-generated content quality.

Your task is to evaluate the {criterion} of the output on a 1-10 scale.

## Rubric for {criterion}:
{rubric}

## Evaluation Process:
1. Read the input content and generated output carefully
2. Think step-by-step about how well the output addresses the criterion
3. Consider specific examples from the output that support your assessment
4. Be calibrated: use the full 1-10 range appropriately
5. Provide your reasoning, then your final score

## Input Content:
{input_content}

## Generated Output to Evaluate:
{output_content}

## Response Format (MUST follow exactly):
<reasoning>
[Your step-by-step analysis here - be specific about what you observe]
</reasoning>

<score>[1-10]</score>
"""

    def _parse_score(self, response_content: str | list, criterion: str) -> float:
        """Parse score from LLM judge response.

        Handles multiple response formats:
        - Simple string with <score>N</score>
        - Gemini's list format: [{'type': 'text', 'text': '...'}]

        Args:
            response_content: Raw LLM response
            criterion: Criterion being evaluated (for error messages)

        Returns:
            Normalized score (0.0-1.0)

        Raises:
            ValueError: If score cannot be parsed

        """
        # Extract text from response (handles Gemini's dict format)
        if isinstance(response_content, str):
            content = response_content
        elif isinstance(response_content, list) and response_content:
            first_item = response_content[0]
            if isinstance(first_item, dict):
                content = str(first_item.get("text", first_item))
            else:
                content = str(first_item)
        else:
            content = str(response_content)

        # Extract score from <score>N</score> tags
        score_match = re.search(r"<score>\s*(\d+)\s*</score>", content)
        if score_match:
            score = int(score_match.group(1))
            score = max(1, min(10, score))  # Clamp to valid range
            # Normalize to 0.0-1.0 (1->0.0, 10->1.0)
            normalized = (score - 1) / 9.0
            return normalized

        # Fallback: Look for any number in response
        number_match = re.search(r"\b(\d+)\b", content)
        if number_match:
            score = int(number_match.group(1))
            if MIN_SCORE <= score <= MAX_SCORE:
                normalized = (score - 1) / 9.0
                logger.warning(
                    "langfuse_evaluator_score_untagged",
                    criterion=criterion,
                    score=score,
                    message="Score found without <score> tags",
                )
                return normalized

        # Failed to parse
        msg = f"Failed to parse score from response for {criterion}: {content[:200]}"
        raise ValueError(msg)

    def _submit_score_to_langfuse(
        self,
        trace_id: str,
        criterion: str,
        score: float,
        reasoning: str,
    ) -> None:
        """Submit evaluation score to Langfuse for analytics.

        Args:
            trace_id: Trace ID to attach score to
            criterion: Evaluation criterion
            score: Normalized score (0.0-1.0)
            reasoning: Evaluation reasoning/comment

        """
        try:
            from app.core.langfuse_config import submit_langfuse_score

            submit_langfuse_score(
                trace_id=trace_id,
                name=f"langfuse_quality_{criterion}",
                value=score,
                comment=f"Langfuse LLM-as-Judge evaluation: {reasoning}",
            )

            logger.debug(
                "langfuse_score_submitted",
                trace_id=trace_id,
                criterion=criterion,
                score=score,
            )

        except Exception as e:  # noqa: BLE001 - Graceful degradation for observability
            logger.warning(
                "langfuse_score_submission_failed",
                trace_id=trace_id,
                criterion=criterion,
                error=str(e),
            )


# Convenience functions for creating evaluators
def create_langfuse_evaluator(criterion: str, model: str | None = None) -> LangfuseEvaluatorService:
    """Create a Langfuse evaluator for a specific criterion.

    Args:
        criterion: Evaluation criterion (relevance, depth, coherence)
        model: Optional model override (default: settings.QUALITY_JUDGE_MODEL)

    Returns:
        LangfuseEvaluatorService instance

    Example:
        >>> evaluator = create_langfuse_evaluator("relevance")
        >>> score = await evaluator.evaluate(trace_id, input, output, "relevance")

    """
    return LangfuseEvaluatorService(model=model)
