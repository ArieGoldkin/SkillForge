"""Execution validation helpers.

Issue #507 Refactoring: Extracted from execution.py to reduce function complexity.
These helpers validate agent output quality before the self-correction loop.

Usage:
    from app.domains.analysis.workflows.agents.validation.execution_helpers import (
        validate_findings_count,
        validate_specificity_score,
        ValidationCheckResult,
    )
"""

from dataclasses import dataclass
from typing import Any

from app.core.logging import get_logger
from app.domains.analysis.workflows.agents.validation.specificity_scorer import (
    SpecificityScore,
    score_agent_output,
)

logger = get_logger(__name__)


@dataclass
class ValidationCheckResult:
    """Result of a validation check.

    Attributes:
        passed: Whether the validation passed
        should_retry: Whether to retry the agent invocation
        should_fail: Whether to raise an error (exhausted retries)
        error_message: Error message if should_fail is True
        score: Optional score value for specificity checks

    """

    passed: bool
    should_retry: bool
    should_fail: bool
    error_message: str | None = None
    score: SpecificityScore | None = None


def validate_findings_count(  # noqa: PLR0913
    agent_type: str,
    analysis_id: str,
    insights_count: int,
    min_findings: int,
    current_attempt: int,
    max_retries: int,
) -> ValidationCheckResult:
    """Validate that agent produced minimum required findings.

    Issue #507: Catches agents that return valid structure but zero useful content.

    Args:
        agent_type: Type of agent for logging
        analysis_id: Analysis ID for logging
        insights_count: Number of insights found in output
        min_findings: Minimum required findings
        current_attempt: Current retry attempt (0-indexed)
        max_retries: Maximum allowed retries

    Returns:
        ValidationCheckResult indicating next action

    """
    # If min_findings is 0, validation is disabled
    if min_findings <= 0:
        return ValidationCheckResult(passed=True, should_retry=False, should_fail=False)

    # Check if findings meet minimum threshold
    if insights_count >= min_findings:
        return ValidationCheckResult(passed=True, should_retry=False, should_fail=False)

    # Findings below threshold - check if we can retry
    if current_attempt >= max_retries:
        logger.error(
            "agent_empty_findings_exhausted",
            agent_type=agent_type,
            analysis_id=analysis_id,
            insights_count=insights_count,
            min_required=min_findings,
            retries=current_attempt,
        )
        return ValidationCheckResult(
            passed=False,
            should_retry=False,
            should_fail=True,
            error_message=(
                f"Agent produced {insights_count} findings (minimum {min_findings} required)"
            ),
        )

    # Can retry
    logger.warning(
        "agent_empty_findings_retry",
        agent_type=agent_type,
        analysis_id=analysis_id,
        attempt=current_attempt + 1,
        insights_count=insights_count,
        min_required=min_findings,
    )
    return ValidationCheckResult(passed=False, should_retry=True, should_fail=False)


def validate_specificity_score(  # noqa: PLR0913
    findings: dict[str, Any],
    agent_type: str,
    analysis_id: str,
    min_score: float,
    current_attempt: int,
    max_retries: int,
) -> ValidationCheckResult:
    """Validate agent output specificity score.

    Args:
        findings: Agent output dictionary
        agent_type: Type of agent for logging
        analysis_id: Analysis ID for logging
        min_score: Minimum specificity score threshold (0.0-1.0)
        current_attempt: Current retry attempt (0-indexed)
        max_retries: Maximum allowed retries

    Returns:
        ValidationCheckResult with score if validation ran

    """
    # Skip validation if threshold is 0.0 (disabled for tests)
    if min_score <= 0.0:
        return ValidationCheckResult(passed=True, should_retry=False, should_fail=False)

    # Score the output
    specificity_score = score_agent_output(findings, agent_type=agent_type)

    # Check if score meets threshold
    if specificity_score.overall_score >= min_score:
        return ValidationCheckResult(
            passed=True,
            should_retry=False,
            should_fail=False,
            score=specificity_score,
        )

    # Score below threshold - check if we can retry
    if current_attempt >= max_retries:
        logger.error(
            "agent_specificity_below_threshold",
            agent_type=agent_type,
            analysis_id=analysis_id,
            specificity_score=specificity_score.overall_score,
            threshold=min_score,
            retries=current_attempt,
        )
        return ValidationCheckResult(
            passed=False,
            should_retry=False,
            should_fail=True,
            error_message=(
                f"Specificity score {specificity_score.overall_score} below threshold {min_score}"
            ),
            score=specificity_score,
        )

    # Can retry
    logger.warning(
        "agent_specificity_retry",
        agent_type=agent_type,
        analysis_id=analysis_id,
        attempt=current_attempt + 1,
        specificity_score=specificity_score.overall_score,
        threshold=min_score,
    )
    return ValidationCheckResult(
        passed=False,
        should_retry=True,
        should_fail=False,
        score=specificity_score,
    )
