"""Quality scoring system for agent output evaluation.

This module provides comprehensive quality assessment for agent outputs,
comparing control (baseline) vs treatment (few-shot enhanced) variants.

Phase 1, Week 3: Quality Comparison Testing
Phase 2: G-Eval LLM-as-Judge Integration

Scoring Approaches:
1. Heuristic scoring (fast, synchronous): Schema validation + structural checks
2. G-Eval scoring (deep, async): LLM-as-Judge with chain-of-thought rubrics

Scoring Dimensions:
- Completeness: Schema compliance, required fields, data depth
- Accuracy: Semantic similarity to golden examples
- Detail Level: Depth of analysis, list lengths, thoroughness
- Structure Quality: Formatting, consistency, pattern adherence
- Token Usage: Input/output token counts for cost analysis

Example:
    >>> from app.shared.services.quality_scorer import score_output_quality
    >>> score = score_output_quality(
    ...     output={"primary_tech": "React", ...},
    ...     golden_example={"output_example": {...}},
    ...     agent_type="tech_comparator",
    ... )
    >>> print(f"Overall quality: {score.overall_score:.2f}")

    # Async with G-Eval:
    >>> from app.shared.services.quality_scorer import GEvalConfig
    >>> config = GEvalConfig(heuristic_weight=0.4, g_eval_weight=0.6)
    >>> score = await score_output_quality_g_eval(
    ...     output={"primary_tech": "React", ...},
    ...     input_content="Compare React and Vue...",
    ...     agent_type="tech_comparator",
    ...     config=config,
    ... )
    >>> print(f"G-Eval quality: {score.overall_score:.2f}")

"""

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from app.core.logging import get_logger

logger = get_logger(__name__)

# Quality scoring thresholds
MIN_LIST_LENGTH = 3  # Target minimum list length
MIN_TEXT_LENGTH = 100  # Minimum chars for detailed text
MIN_SHORT_TEXT_LENGTH = 50  # Minimum for partial credit
MAX_TEXT_LENGTH = 500  # Maximum recommended text length


@dataclass
class QualityScore:
    """Multi-dimensional quality score for agent output.

    Attributes:
        completeness_score: Schema compliance and required fields (0.0-1.0)
        accuracy_score: Similarity to golden example (0.0-1.0)
        detail_score: Depth of analysis (0.0-1.0)
        structure_score: Formatting and consistency (0.0-1.0)
        overall_score: Weighted average of all dimensions (0.0-1.0)
        token_count: Token usage (input + output)
        error_message: Error details if scoring failed

    """

    completeness_score: float
    accuracy_score: float
    detail_score: float
    structure_score: float
    overall_score: float
    token_count: int
    error_message: str | None = None


def _score_completeness(
    output: dict[str, Any],
    schema_class: type[BaseModel] | None,
) -> float:
    """Score output completeness based on schema compliance.

    Checks:
    - Required fields present
    - Lists are non-empty where expected
    - Confidence score present and valid
    - Nested structures populated

    Args:
        output: Agent output dictionary
        schema_class: Expected Pydantic schema (if available)

    Returns:
        Completeness score between 0.0 and 1.0

    """
    if not output:
        return 0.0

    score = 0.0

    # Basic presence check (20%)
    if output:
        score += 0.2

    # Schema validation (40%)
    if schema_class:
        try:
            schema_class.model_validate(output)
            score += 0.4
        except ValidationError as e:
            # Partial credit based on number of errors
            error_count = len(e.errors())
            partial_credit = max(0, 0.4 - (error_count * 0.05))
            score += partial_credit
            logger.debug(
                "completeness_validation_errors",
                error_count=error_count,
                partial_credit=partial_credit,
            )
    else:
        # If no schema, give partial credit for having fields
        score += 0.3

    # Required field checks (20%)
    required_fields = ["confidence_score", "recommendation"]
    present_count = sum(1 for field in required_fields if field in output)
    score += (present_count / len(required_fields)) * 0.2

    # Depth check - lists should have content (20%)
    list_fields = [k for k, v in output.items() if isinstance(v, list)]
    if list_fields:
        non_empty_lists = sum(1 for k in list_fields if output[k])
        score += (non_empty_lists / len(list_fields)) * 0.2
    else:
        score += 0.1  # Partial credit if no lists expected

    return min(score, 1.0)


def _score_accuracy(
    output: dict[str, Any],
    golden_output: dict[str, Any] | None,
) -> float:
    """Score output accuracy compared to golden example.

    Uses structural similarity since we don't have semantic embeddings:
    - Key overlap (30%)
    - Value type matching (20%)
    - List length similarity (20%)
    - Confidence score similarity (30%)

    Args:
        output: Agent output dictionary
        golden_output: Golden example output (if available)

    Returns:
        Accuracy score between 0.0 and 1.0

    """
    if not golden_output:
        # No golden reference, use confidence score as proxy
        return float(output.get("confidence_score", 0.7))

    score = 0.0

    # Key overlap (30%)
    output_keys = set(output.keys())
    golden_keys = set(golden_output.keys())
    if golden_keys:
        key_overlap = len(output_keys & golden_keys) / len(golden_keys)
        score += key_overlap * 0.3

    # Value type matching (20%)
    matching_types = sum(
        1
        for k in output_keys & golden_keys
        if type(output[k]) == type(golden_output[k])  # noqa: E721 - Intentional type check
    )
    if golden_keys:
        type_match = matching_types / len(golden_keys)
        score += type_match * 0.2

    # List length similarity (20%)
    list_keys = [k for k in output_keys & golden_keys if isinstance(output[k], list)]
    if list_keys:
        length_similarities = []
        for k in list_keys:
            output_len = len(output[k])
            golden_len = len(golden_output[k])
            if golden_len > 0:
                # Ratio capped at 1.0 (longer lists aren't necessarily better)
                length_sim = min(output_len / golden_len, 1.0)
                length_similarities.append(length_sim)
        if length_similarities:
            avg_length_sim = sum(length_similarities) / len(length_similarities)
            score += avg_length_sim * 0.2
    else:
        score += 0.1  # Partial credit if no lists

    # Confidence score similarity (30%)
    output_conf = float(output.get("confidence_score", 0.5))
    golden_conf = float(golden_output.get("confidence_score", 0.8))
    conf_diff = abs(output_conf - golden_conf)
    conf_similarity = 1.0 - conf_diff
    score += conf_similarity * 0.3

    return min(score, 1.0)


def _score_detail_level(
    output: dict[str, Any],
    agent_type: str,
) -> float:
    """Score depth and thoroughness of analysis.

    Checks:
    - List lengths (more detailed lists = higher score)
    - Text field lengths (longer descriptions = higher score)
    - Nested structure depth
    - Agent-specific detail metrics

    Args:
        output: Agent output dictionary
        agent_type: Type of agent for agent-specific checks

    Returns:
        Detail score between 0.0 and 1.0

    """
    score = 0.0

    # List length metrics (40%)
    list_fields = {k: v for k, v in output.items() if isinstance(v, list)}
    if list_fields:
        # Average list length (target: 3-5 items)
        avg_length = sum(len(v) for v in list_fields.values()) / len(list_fields)
        if avg_length >= MIN_LIST_LENGTH:
            score += min(avg_length / 5, 1.0) * 0.4
        else:
            score += (avg_length / MIN_LIST_LENGTH) * 0.2

    # Text field depth (30%)
    text_fields = [
        k
        for k, v in output.items()
        if isinstance(v, str) and k not in ["primary_tech", "estimated_time"]
    ]
    if text_fields:
        # Average text length (target: 100+ chars for descriptions)
        avg_text_len = sum(len(output[k]) for k in text_fields) / len(text_fields)
        if avg_text_len >= MIN_TEXT_LENGTH:
            score += min(avg_text_len / 200, 1.0) * 0.3
        else:
            score += (avg_text_len / MIN_TEXT_LENGTH) * 0.15

    # Agent-specific detail checks (30%)
    if agent_type == "tech_comparator":
        # Check comparison table depth
        comparison = output.get("comparison", {})
        if comparison:
            total_items = sum(
                len(entry.get("pros", [])) + len(entry.get("cons", []))
                for entry in comparison.values()
            )
            score += min(total_items / 15, 1.0) * 0.3

    elif agent_type == "security_auditor":
        # Check risk count and mitigation detail
        risks = output.get("security_risks", [])
        if risks:
            risk_score = min(len(risks) / 5, 1.0) * 0.15
            # Check mitigation detail
            has_mitigation = sum(1 for r in risks if r.get("mitigation"))
            mitigation_score = (has_mitigation / len(risks)) * 0.15 if risks else 0
            score += risk_score + mitigation_score

    elif agent_type == "implementation_planner":
        # Check step count and prerequisite detail
        steps = output.get("steps", [])
        prereqs = output.get("prerequisites", [])
        step_score = min(len(steps) / 8, 1.0) * 0.15
        prereq_score = min(len(prereqs) / 5, 1.0) * 0.15
        score += step_score + prereq_score

    else:
        # Generic depth check for other agent types
        total_fields = len(output)
        score += min(total_fields / 10, 1.0) * 0.3

    return min(score, 1.0)


def _score_structure_quality(  # noqa: PLR0912 - Complex agent-specific checks needed
    output: dict[str, Any],
    agent_type: str,
) -> float:
    """Score formatting, consistency, and structural patterns.

    Checks:
    - Consistent field naming
    - Proper capitalization
    - List item consistency
    - Recommendation structure
    - Agent-specific patterns

    Args:
        output: Agent output dictionary
        agent_type: Type of agent for pattern checks

    Returns:
        Structure score between 0.0 and 1.0

    """
    score = 0.0

    # Recommendation present and well-formed (30%)
    recommendation = output.get("recommendation", "")
    if recommendation:
        # Check length (should be 2-3 sentences, ~100-500 chars)
        rec_len = len(recommendation)
        if MIN_TEXT_LENGTH <= rec_len <= MAX_TEXT_LENGTH:
            score += 0.3
        elif rec_len > MIN_SHORT_TEXT_LENGTH:
            score += 0.15

    # Confidence score present and valid (20%)
    conf_score = output.get("confidence_score")
    if conf_score is not None and 0.0 <= conf_score <= 1.0:
        score += 0.2

    # List items non-empty and consistent (30%)
    list_fields = {k: v for k, v in output.items() if isinstance(v, list)}
    if list_fields:
        # Check that lists don't have empty strings or None
        clean_lists = sum(1 for v in list_fields.values() if all(item for item in v if item))
        score += (clean_lists / len(list_fields)) * 0.3

    # Agent-specific pattern checks (20%)
    if agent_type == "tech_comparator":
        # Check comparison structure
        comparison = output.get("comparison", {})
        if comparison:
            # Each entry should have pros, cons, use_cases
            complete_entries = sum(
                1
                for entry in comparison.values()
                if "pros" in entry and "cons" in entry and "use_cases" in entry
            )
            if comparison:
                score += (complete_entries / len(comparison)) * 0.2

    elif agent_type == "security_auditor":
        # Check risk structure
        risks = output.get("security_risks", [])
        if risks:
            complete_risks = sum(
                1
                for risk in risks
                if all(k in risk for k in ["severity", "description", "mitigation"])
            )
            score += (complete_risks / len(risks)) * 0.2

    elif agent_type == "implementation_planner":
        # Check step structure and numbering
        steps = output.get("steps", [])
        if steps:
            # Check sequential numbering
            expected_nums = list(range(1, len(steps) + 1))
            actual_nums = [s.get("step", 0) for s in steps]
            if actual_nums == expected_nums:
                score += 0.2
            else:
                score += 0.1

    else:
        # Generic structure check
        score += 0.15

    return min(score, 1.0)


def _estimate_token_count(output: dict[str, Any]) -> int:
    """Estimate total token count for output.

    Uses simple character-based approximation (4 chars ≈ 1 token).

    Args:
        output: Agent output dictionary

    Returns:
        Estimated token count

    """
    import json

    try:
        output_str = json.dumps(output)
        return len(output_str) // 4
    except Exception:  # noqa: BLE001 - Graceful fallback
        return 0


def score_output_quality(
    output: dict[str, Any],
    golden_example: dict[str, Any] | None,
    agent_type: str,
    schema_class: type[BaseModel] | None = None,
) -> QualityScore:
    """Score output quality on multiple dimensions.

    Main entry point for quality scoring. Combines multiple scoring
    dimensions into a comprehensive quality assessment.

    Weighting:
    - Completeness: 30%
    - Accuracy: 30%
    - Detail: 20%
    - Structure: 20%

    Args:
        output: Agent output dictionary to score
        golden_example: Golden example record (with output_example field)
        agent_type: Type of agent (e.g., 'tech_comparator')
        schema_class: Optional Pydantic schema for validation

    Returns:
        QualityScore with all dimensions and overall score

    Example:
        >>> score = score_output_quality(
        ...     output={"primary_tech": "React", "confidence_score": 0.85},
        ...     golden_example={"output_example": {...}},
        ...     agent_type="tech_comparator",
        ... )
        >>> print(f"Quality: {score.overall_score:.2%}")

    """
    try:
        # Extract golden output if available
        golden_output = None
        if golden_example:
            golden_output = golden_example.get("output_example")

        # Score each dimension
        completeness = _score_completeness(output, schema_class)
        accuracy = _score_accuracy(output, golden_output)
        detail = _score_detail_level(output, agent_type)
        structure = _score_structure_quality(output, agent_type)

        # Weighted average (30% + 30% + 20% + 20%)
        overall = completeness * 0.30 + accuracy * 0.30 + detail * 0.20 + structure * 0.20

        # Estimate token usage
        token_count = _estimate_token_count(output)

        logger.debug(
            "quality_score_calculated",
            agent_type=agent_type,
            completeness=completeness,
            accuracy=accuracy,
            detail=detail,
            structure=structure,
            overall=overall,
            token_count=token_count,
        )

        return QualityScore(
            completeness_score=completeness,
            accuracy_score=accuracy,
            detail_score=detail,
            structure_score=structure,
            overall_score=overall,
            token_count=token_count,
        )

    except Exception as e:
        logger.error(
            "quality_scoring_failed",
            agent_type=agent_type,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        return QualityScore(
            completeness_score=0.0,
            accuracy_score=0.0,
            detail_score=0.0,
            structure_score=0.0,
            overall_score=0.0,
            token_count=0,
            error_message=str(e),
        )


# ============================================================================
# G-Eval LLM-as-Judge Scoring (Phase 2)
# ============================================================================


@dataclass
class GEvalConfig:
    """Configuration for G-Eval scoring.

    Groups related parameters to reduce function argument count.

    Attributes:
        schema_class: Optional Pydantic schema for validation
        heuristic_weight: Weight for heuristic score (default 0.3)
        g_eval_weight: Weight for G-Eval score (default 0.7)

    """

    schema_class: type[BaseModel] | None = None
    heuristic_weight: float = 0.3
    g_eval_weight: float = 0.7


@dataclass
class GEvalQualityScore:
    """Quality score with G-Eval LLM-as-Judge dimensions.

    Extends QualityScore with G-Eval specific fields:
    - reasoning: Per-criterion chain-of-thought reasoning
    - confidence: LLM confidence in the evaluation
    - scoring_method: 'g_eval' or 'heuristic'
    """

    completeness_score: float
    accuracy_score: float
    detail_score: float
    structure_score: float
    overall_score: float
    token_count: int
    reasoning: dict[str, str]
    confidence: float
    scoring_method: str
    error_message: str | None = None


async def score_output_quality_g_eval(
    output: dict[str, Any],
    input_content: str,
    agent_type: str,
    config: GEvalConfig | None = None,
) -> GEvalQualityScore:
    """Score output quality using G-Eval LLM-as-Judge.

    Combines heuristic scoring (fast) with G-Eval (deep) for
    comprehensive quality assessment.

    Args:
        output: Agent output dictionary to score
        input_content: Original input that generated the output
        agent_type: Type of agent (e.g., 'tech_comparator')
        config: Optional GEvalConfig for schema, weights, etc.

    Returns:
        GEvalQualityScore with blended dimensions

    Example:
        >>> score = await score_output_quality_g_eval(
        ...     output={"recommendation": "Use React", ...},
        ...     input_content="Compare React vs Vue for our project",
        ...     agent_type="tech_comparator",
        ... )
        >>> print(f"G-Eval quality: {score.overall_score:.2%}")
        >>> print(f"Reasoning: {score.reasoning.get('completeness')}")

    """
    from app.core.tracing import get_current_trace_id
    from app.shared.services.g_eval import g_eval_score

    # Use default config if not provided
    if config is None:
        config = GEvalConfig()

    try:
        # Fast path: Heuristic scoring
        heuristic_score = score_output_quality(
            output=output,
            golden_example=None,
            agent_type=agent_type,
            schema_class=config.schema_class,
        )

        # Get current trace ID for Langfuse score submission
        trace_id = get_current_trace_id()

        # Deep path: G-Eval LLM scoring
        g_eval_result = await g_eval_score(
            input_content=input_content,
            output=output,
            agent_type=agent_type,
            trace_id=trace_id,
        )

        # Blend scores
        completeness = (
            heuristic_score.completeness_score * config.heuristic_weight
            + g_eval_result.completeness * config.g_eval_weight
        )
        accuracy = (
            heuristic_score.accuracy_score * config.heuristic_weight
            + g_eval_result.accuracy * config.g_eval_weight
        )
        detail = (
            heuristic_score.detail_score * config.heuristic_weight
            + g_eval_result.depth * config.g_eval_weight
        )
        structure = (
            heuristic_score.structure_score * config.heuristic_weight
            + g_eval_result.coherence * config.g_eval_weight
        )

        # Overall is weighted average
        overall = completeness * 0.30 + accuracy * 0.30 + detail * 0.20 + structure * 0.20

        logger.info(
            "g_eval_quality_scored",
            agent_type=agent_type,
            heuristic_overall=heuristic_score.overall_score,
            g_eval_overall=g_eval_result.overall,
            blended_overall=overall,
            confidence=g_eval_result.confidence,
        )

        return GEvalQualityScore(
            completeness_score=completeness,
            accuracy_score=accuracy,
            detail_score=detail,
            structure_score=structure,
            overall_score=overall,
            token_count=heuristic_score.token_count,
            reasoning=g_eval_result.reasoning,
            confidence=g_eval_result.confidence,
            scoring_method="g_eval",
        )

    except Exception as e:
        logger.error(
            "g_eval_scoring_failed",
            agent_type=agent_type,
            error=str(e),
            exc_info=True,
        )
        # Fallback to heuristic only
        heuristic_score = score_output_quality(
            output=output,
            golden_example=None,
            agent_type=agent_type,
            schema_class=config.schema_class,
        )
        return GEvalQualityScore(
            completeness_score=heuristic_score.completeness_score,
            accuracy_score=heuristic_score.accuracy_score,
            detail_score=heuristic_score.detail_score,
            structure_score=heuristic_score.structure_score,
            overall_score=heuristic_score.overall_score,
            token_count=heuristic_score.token_count,
            reasoning={},
            confidence=0.0,
            scoring_method="heuristic_fallback",
            error_message=str(e),
        )
