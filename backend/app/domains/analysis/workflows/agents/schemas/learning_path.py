"""Learning path designer agent schemas."""

from pydantic import BaseModel, Field

from app.domains.analysis.workflows.agents.schemas.base import DataAvailabilityMixin


class LearningModule(BaseModel):
    """A single learning module in the path."""

    module_number: int = Field(
        description="Sequential module number (1, 2, 3, ...)",
        ge=1,
    )
    title: str = Field(
        description="Module title",
        min_length=10,
        max_length=100,
    )
    description: str = Field(
        description="What will be learned in this module",
        min_length=50,
        max_length=300,
    )
    duration_hours: int = Field(
        description="Estimated time to complete (in hours)",
        ge=1,
        le=200,
    )
    prerequisites: list[str] = Field(
        description="Required knowledge or prior modules",
        default_factory=list,
    )
    learning_objectives: list[str] = Field(
        description="2-4 specific learning objectives",
        min_length=2,
        max_length=4,
    )
    resources: list[str] = Field(
        description="Recommended learning resources (articles, videos, docs)",
        min_length=2,
        max_length=8,
    )


class LearningPath(DataAvailabilityMixin):
    """Learning path designer output schema.

    Creates structured learning paths with modules, objectives, and resources
    tailored to the learner's skill level and goals.

    Issue #299-304: Inherits DataAvailabilityMixin to report data coverage.
    """

    topic: str = Field(
        description="Main learning topic or skill",
        min_length=10,
        max_length=100,
    )
    target_audience: str = Field(
        description="Who this path is designed for (beginner/intermediate/advanced)",
        min_length=10,
    )
    total_duration_hours: int = Field(
        description="Total estimated time to complete the full path (in hours)",
        ge=1,
        le=500,
    )
    modules: list[LearningModule] = Field(
        description="4-8 sequential learning modules",
        min_length=3,
        max_length=10,
    )
    prerequisites: list[str] = Field(
        description="Prerequisites before starting this path",
        min_length=1,
        max_length=5,
    )
    learning_outcomes: list[str] = Field(
        description="What learner will achieve by completing the path",
        min_length=3,
        max_length=5,
    )
    assessment_methods: list[str] = Field(
        description="Ways to assess progress and mastery",
        min_length=2,
        max_length=5,
    )
    confidence_score: float = Field(
        description="Confidence in path design quality (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    recommendation: str = Field(
        description="Overall recommendation and next steps for learner",
        min_length=100,
        max_length=500,
    )
