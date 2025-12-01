"""Trend validation agent schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class TrendAssessment(BaseModel):
    """Trend assessment for a technology or pattern."""

    category: str = Field(
        description="Trend category (e.g., 'framework', 'language', 'pattern', 'tool')"
    )
    trend_status: Literal["emerging", "current", "stable", "declining", "legacy"] = Field(
        description="Current trend status in 2025 technology landscape"
    )
    evidence: str = Field(
        description=(
            "Single sentence providing evidence for trend status "
            "(e.g., GitHub stars, community activity, industry adoption)."
        )
    )
    adoption_rate: str = Field(
        description="Adoption rate description (e.g., 'growing', 'stable', 'declining')"
    )


class TrendValidation(BaseModel):
    """Trend validation analysis output schema."""

    trend_assessments: list[TrendAssessment] = Field(
        description="Trend assessments for different aspects of the technology",
        default_factory=list,
    )
    modern_alternatives: list[str] = Field(
        description=(
            "Modern alternatives if technology is legacy or declining. "
            "Each item should be a single concise phrase naming the alternative."
        ),
        default_factory=list,
    )
    future_outlook: str = Field(
        description=(
            "Future outlook and predictions for the technology. "
            "Write as 2-3 cohesive sentences covering expected trajectory and timeline."
        )
    )
    recommendation: str = Field(
        description=(
            "Recommendation based on trend analysis. "
            "Write as 2-3 cohesive sentences advising whether to adopt, wait, or avoid."
        )
    )
