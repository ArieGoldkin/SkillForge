"""Pros/Cons agent schemas."""

from typing import Literal

from pydantic import Field

from app.domains.analysis.schemas.agents.base import DataAvailabilityMixin


class ProsConsOutput(DataAvailabilityMixin):
    """Balanced pros/cons analysis output schema.

    Issue #299-304: Inherits DataAvailabilityMixin to report data coverage.
    Universal Tier 1 agent - runs on ALL content types.
    """

    pros: list[str] = Field(
        description=(
            "List of advantages, strengths, or benefits of the subject matter. "
            "Each item should be a single concise phrase or short sentence. "
            "Focus on specific, actionable benefits. Include quantifiable benefits "
            "when available (e.g., '40% faster cold start', '3x better throughput'). "
            "Minimum 2 items, maximum 7 items."
        ),
        min_length=2,
        max_length=7,
    )
    cons: list[str] = Field(
        description=(
            "List of disadvantages, limitations, or drawbacks of the subject matter. "
            "Each item should be a single concise phrase or short sentence. "
            "Be honest about limitations. Include specific constraints when available "
            "(e.g., 'Max 100 concurrent executions', 'Requires Python 3.9+'). "
            "Minimum 1 item, maximum 7 items."
        ),
        min_length=1,
        max_length=7,
    )
    verdict: str = Field(
        description=(
            "Balanced conclusion synthesizing the pros/cons analysis. "
            "Write as 2-3 cohesive sentences explaining the overall assessment. "
            "Should acknowledge both strengths and limitations while providing "
            "a clear bottom-line recommendation."
        )
    )
    recommendation: Literal["strongly_recommended", "recommended", "neutral", "not_recommended"] = (
        Field(
            description=(
                "Overall recommendation based on the pros/cons analysis:\n"
                "- 'strongly_recommended': Clear winner, significant advantages outweigh minor drawbacks\n"
                "- 'recommended': Good choice for most cases, pros outweigh cons\n"
                "- 'neutral': Mixed bag, pros and cons are balanced\n"
                "- 'not_recommended': Significant limitations outweigh benefits"
            )
        )
    )
    confidence_score: float = Field(
        description=(
            "Confidence score (0.0-1.0) representing both the quality and certainty "
            "of this pros/cons analysis. Consider: completeness of pros/cons identification, "
            "balance of analysis, evidence strength, and confidence in recommendation. "
            "Higher scores indicate more comprehensive and well-supported analysis."
        ),
        ge=0.0,
        le=1.0,
    )
