"""Assessment schemas for tutor workflow."""

from pydantic import BaseModel, Field


class ReadinessAssessment(BaseModel):
    """Readiness assessment result.

    Attributes:
        user_ready: Whether user is ready to proceed
        confidence_score: Confidence in assessment (0.0-1.0)
        reasoning: Explanation of assessment
        suggested_action: Suggested next action

    """

    user_ready: bool = Field(..., description="Whether user is ready to proceed")
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in assessment (0.0-1.0)",
    )
    reasoning: str = Field(..., description="Explanation of assessment")
    suggested_action: str | None = Field(
        None,
        description="Suggested next action (e.g., 'rephrase', 'move_on')",
    )
