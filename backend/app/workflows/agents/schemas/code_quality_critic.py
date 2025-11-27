"""Code quality review agent schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class CodeIssue(BaseModel):
    """Code quality issue identified in analysis."""

    issue_type: str = Field(
        description=(
            "Type of issue (e.g., 'antipattern', 'code_smell', 'violation', 'technical_debt')"
        )
    )
    severity: Literal["low", "medium", "high"] = Field(
        description="Issue severity level based on impact on maintainability"
    )
    description: str = Field(description="Description of the code quality issue")
    suggestion: str = Field(description="Recommended fix or improvement")


class CodeQualityReview(BaseModel):
    """Code quality review output schema."""

    code_issues: list[CodeIssue] = Field(
        description="Identified code quality issues and violations",
        default_factory=list,
    )
    best_practices: list[str] = Field(
        description=("Code quality best practices to follow (SOLID, DRY, clean code principles)"),
        default_factory=list,
    )
    maintainability_score: float = Field(
        description="Maintainability score from 0.0 (poor) to 1.0 (excellent)",
        ge=0.0,
        le=1.0,
    )
    refactoring_suggestions: list[str] = Field(
        description="Refactoring recommendations to improve code quality",
        default_factory=list,
    )
    recommendation: str = Field(description="Overall code quality recommendation")
