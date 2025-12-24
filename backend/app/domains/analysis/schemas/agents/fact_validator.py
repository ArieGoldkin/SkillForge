"""Fact validation agent schemas."""

from typing import Literal

from pydantic import BaseModel, Field

from app.domains.analysis.schemas.agents.base import DataAvailabilityMixin


class Claim(BaseModel):
    """A factual claim extracted from content with validation status."""

    statement: str = Field(description="The factual claim statement extracted from content")
    source_text: str = Field(
        description="The original text snippet from which this claim was extracted"
    )
    validation_status: Literal["verified", "disputed", "unverified"] = Field(
        description=(
            "Validation status of the claim:\n"
            "- 'verified': Found supporting evidence from credible sources\n"
            "- 'disputed': Found contradicting evidence or concerns\n"
            "- 'unverified': Insufficient evidence to confirm or deny"
        )
    )
    confidence: float = Field(
        description="Confidence in validation status (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    evidence_url: str | None = Field(
        description="URL of external source used for validation (if any)",
        default=None,
    )


class FactValidatorOutput(DataAvailabilityMixin):
    """Fact validation analysis output schema.

    Issue #299-304: Inherits DataAvailabilityMixin to report data coverage.
    """

    claims: list[Claim] = Field(
        description=(
            "List of factual claims extracted from content with validation status. "
            "Focus on objective, verifiable statements about technologies, metrics, "
            "performance, security, or other factual assertions."
        ),
        default_factory=list,
    )
    validation_score: float = Field(
        description=(
            "Overall validation score (0.0-1.0) representing the proportion of "
            "claims that were verified. Higher scores indicate more factual accuracy."
        ),
        ge=0.0,
        le=1.0,
    )
    summary: str = Field(
        description=(
            "Summary of fact validation findings. Write as 2-3 cohesive sentences "
            "covering overall factual accuracy, key verified/disputed claims, and "
            "any reliability concerns."
        )
    )
    confidence_score: float = Field(
        description=(
            "Confidence score (0.0-1.0) representing both the quality and certainty "
            "of this fact validation analysis. Consider: number of claims validated, "
            "quality of evidence sources, thoroughness of verification, and confidence "
            "in validation status assignments. Higher scores indicate more comprehensive "
            "and reliable fact-checking."
        ),
        ge=0.0,
        le=1.0,
    )
