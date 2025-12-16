"""Code reviewer agent schemas."""

from pydantic import BaseModel, Field

from app.domains.analysis.workflows.agents.schemas.base import DataAvailabilityMixin


class CodeIssue(BaseModel):
    """A single code quality issue with suggested fix."""

    severity: str = Field(
        description="Issue severity level (critical/high/medium/low)",
        pattern="^(critical|high|medium|low)$",
    )
    category: str = Field(
        description="Issue category (performance, security, maintainability, readability, etc.)",
        min_length=5,
    )
    description: str = Field(
        description="Clear description of the issue",
        min_length=20,
    )
    location: str = Field(
        description="Where the issue occurs (file, function, line range)",
        min_length=5,
    )
    suggested_fix: str = Field(
        description="Recommended fix or improvement",
        min_length=20,
    )


class CodeReview(DataAvailabilityMixin):
    """Code reviewer output schema.

    Analyzes code quality, identifies issues, and suggests improvements
    across security, performance, maintainability, and style dimensions.

    Issue #299-304: Inherits DataAvailabilityMixin to report data coverage.
    """

    code_summary: str = Field(
        description="Brief summary of what the code does",
        min_length=50,
        max_length=200,
    )
    strengths: list[str] = Field(
        description="2-4 positive aspects of the code",
        min_length=2,
        max_length=4,
    )
    issues: list[CodeIssue] = Field(
        description="3-8 code quality issues found",
        min_length=1,
        max_length=10,
    )
    best_practices_violations: list[str] = Field(
        description="Best practices not followed",
        min_length=1,
        max_length=5,
    )
    refactoring_suggestions: list[str] = Field(
        description="High-level refactoring recommendations",
        min_length=1,
        max_length=5,
    )
    test_coverage_assessment: str = Field(
        description="Assessment of test coverage quality (if tests present)",
        min_length=30,
    )
    overall_quality: str = Field(
        description="Overall code quality rating (excellent/good/fair/poor)",
        pattern="^(excellent|good|fair|poor)$",
    )
    confidence_score: float = Field(
        description="Confidence in review quality (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    recommendation: str = Field(
        description="Summary recommendation for next steps",
        min_length=100,
        max_length=500,
    )
