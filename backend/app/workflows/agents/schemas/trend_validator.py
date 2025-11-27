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
        description="Evidence for trend status (adoption, community activity, etc.)"
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
        description="Modern alternatives if technology is legacy or declining",
        default_factory=list,
    )
    future_outlook: str = Field(description="Future outlook and predictions for the technology")
    recommendation: str = Field(description="Recommendation based on trend analysis")
