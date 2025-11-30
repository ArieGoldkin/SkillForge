"""Security audit agent schemas."""

from typing import Literal

from pydantic import BaseModel, Field


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


class SecurityAudit(BaseModel):
    """Security audit analysis output schema."""

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
