"""Code quality review agent schemas."""

from typing import Literal

from pydantic import BaseModel, Field

from app.workflows.agents.schemas.base import DataAvailabilityMixin


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
    description: str = Field(
        description=(
            "Single sentence describing the code quality issue. "
            "Be specific about the file or component affected."
        )
    )
    suggestion: str = Field(
        description=(
            "Single actionable sentence describing the recommended fix. "
            "Start with a verb (e.g., 'Refactor...', 'Extract...', 'Replace...')."
        )
    )


class CodeQualityReview(DataAvailabilityMixin):
    """Code quality review output schema.

    Issue #299-304: Inherits DataAvailabilityMixin to report data coverage.
    """

    code_issues: list[CodeIssue] = Field(
        description="Identified code quality issues and violations",
        default_factory=list,
    )
    best_practices: list[str] = Field(
        description=(
            "Code quality best practices to follow (SOLID, DRY, clean code principles). "
            "Each item should be a single concise sentence or phrase."
        ),
        default_factory=list,
    )
    maintainability_score: float = Field(
        description="Maintainability score from 0.0 (poor) to 1.0 (excellent)",
        ge=0.0,
        le=1.0,
    )
    refactoring_suggestions: list[str] = Field(
        description=(
            "Refactoring recommendations to improve code quality. "
            "Each item should start with a verb (e.g., 'Extract method...', 'Rename...')."
        ),
        default_factory=list,
    )
    recommendation: str = Field(
        description=(
            "Overall code quality recommendation. "
            "Write as 2-3 cohesive sentences summarizing the assessment and priority actions."
        )
    )
    confidence_score: float = Field(
        description=(
            "Confidence score (0.0-1.0) representing both the quality and certainty "
            "of this code quality review. Consider: accuracy of issue identification, "
            "correctness of maintainability score, completeness of refactoring suggestions, "
            "and confidence in best practices recommendations. Higher scores indicate "
            "more thorough and accurate code quality assessments."
        ),
        ge=0.0,
        le=1.0,
    )
