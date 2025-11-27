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
    description: str = Field(description="Detailed description of the security risk")
    mitigation: str = Field(description="Recommended mitigation strategy or solution")


class SecurityAudit(BaseModel):
    """Security audit analysis output schema."""

    security_risks: list[SecurityRisk] = Field(
        description="List of identified security risks and vulnerabilities",
        default_factory=list,
    )
    best_practices: list[str] = Field(
        description=(
            "Security best practices to follow (e.g., 'Use HTTPS', 'Implement CSRF protection')"
        ),
        default_factory=list,
    )
    compliance_notes: list[str] = Field(
        description="Compliance considerations (OWASP Top 10, GDPR, PCI-DSS, etc.)",
        default_factory=list,
    )
    recommendation: str = Field(description="Overall security recommendation and priority actions")
