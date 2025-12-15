"""Security audit agent schemas."""

from typing import Literal

from pydantic import BaseModel, Field

from app.workflows.agents.schemas.base import DataAvailabilityMixin


class SecurityRisk(BaseModel):
    """Security risk identified in content analysis."""

    risk_type: str = Field(
        description="Type of risk (e.g., 'authentication', 'data_exposure', 'injection', 'xss')"
    )
    severity: Literal["low", "medium", "high", "critical"] = Field(
        description="Risk severity level based on potential impact and exploitability"
    )
    description: str = Field(
        description=(
            "Single sentence describing the security risk. "
            "Be specific about the vulnerability and its potential impact."
        )
    )
    mitigation: str = Field(
        description=(
            "Single actionable sentence describing the recommended mitigation. "
            "Start with a verb (e.g., 'Implement...', 'Validate...', 'Encrypt...')."
        )
    )


class SecurityAudit(DataAvailabilityMixin):
    """Security audit analysis output schema.

    Issue #299-304: Inherits DataAvailabilityMixin to report data coverage.
    """

    security_risks: list[SecurityRisk] = Field(
        description="List of identified security risks and vulnerabilities",
        default_factory=list,
    )
    best_practices: list[str] = Field(
        description=(
            "Security best practices to follow (e.g., 'Use HTTPS', 'Implement CSRF protection'). "
            "Each item should be a single concise sentence or phrase."
        ),
        default_factory=list,
    )
    compliance_notes: list[str] = Field(
        description=(
            "Compliance considerations (OWASP Top 10, GDPR, PCI-DSS, etc.). "
            "Each item should be a single sentence referencing the compliance standard."
        ),
        default_factory=list,
    )
    recommendation: str = Field(
        description=(
            "Overall security recommendation and priority actions. "
            "Write as 2-3 cohesive sentences summarizing critical fixes and their priority."
        )
    )
    confidence_score: float = Field(
        description=(
            "Confidence score (0.0-1.0) representing both the quality and certainty "
            "of this security audit. Consider: accuracy of risk identification, "
            "severity assessment correctness, completeness of mitigations, and confidence "
            "in compliance notes. Higher scores indicate more thorough and accurate audits."
        ),
        ge=0.0,
        le=1.0,
    )
