"""Key insights agent schemas."""

from typing import Literal

from pydantic import BaseModel, Field

from app.domains.analysis.schemas.agents.base import DataAvailabilityMixin


class KeyInsight(BaseModel):
    """A single key insight extracted from content."""

    title: str = Field(
        description=(
            "Concise title for this insight (5-10 words). "
            "Should be specific and actionable, not generic."
        )
    )
    description: str = Field(
        description=(
            "Detailed explanation of the insight (2-4 sentences). "
            "Must be specific and evidence-based, extracted directly from content. "
            "Include context about why this insight matters and how to apply it."
        )
    )
    importance: Literal["high", "medium", "low"] = Field(
        description=(
            "Importance level of this insight:\n"
            "- 'high': Critical insight that significantly impacts implementation or understanding\n"
            "- 'medium': Valuable insight that improves quality or efficiency\n"
            "- 'low': Useful detail or minor optimization"
        )
    )
    novelty_score: float = Field(
        description=(
            "Novelty score (0.0-1.0) indicating how unexpected or unique this insight is:\n"
            "- 1.0: Completely novel approach or counter-intuitive finding\n"
            "- 0.7-0.9: Fresh perspective on common problem\n"
            "- 0.4-0.6: Useful clarification of existing practice\n"
            "- 0.0-0.3: Well-known best practice or common knowledge"
        ),
        ge=0.0,
        le=1.0,
    )


class KeyInsightsOutput(DataAvailabilityMixin):
    """Key insights extraction output schema.

    Issue #299-304: Inherits DataAvailabilityMixin to report data coverage.
    This agent runs on ALL content types (Tier 1) and extracts the most important
    takeaways regardless of format (article, video, repo, news).
    """

    insights: list[KeyInsight] = Field(
        description=(
            "List of 3-5 key insights extracted from content. "
            "Prioritize insights by importance (high first), then by novelty. "
            "Each insight must be specific, actionable, and evidence-based. "
            "Avoid generic statements or common knowledge."
        ),
        min_length=3,
        max_length=5,
    )
    summary: str = Field(
        description=(
            "Overall summary of key insights (2-3 sentences). "
            "Synthesize the main themes and explain why these insights matter. "
            "Connect insights to practical application or decision-making."
        )
    )
    confidence_score: float = Field(
        description=(
            "Confidence score (0.0-1.0) representing the quality and certainty "
            "of extracted insights. Consider: specificity of insights, evidence quality, "
            "clarity of content, and completeness of analysis. Higher scores indicate "
            "more reliable and well-supported insights."
        ),
        ge=0.0,
        le=1.0,
    )
