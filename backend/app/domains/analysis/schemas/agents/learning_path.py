"""Learning path agent schemas."""

from pydantic import BaseModel, Field

from app.domains.analysis.schemas.agents.base import DataAvailabilityMixin


class LearningModule(BaseModel):
    """A module in the learning path."""

    module_number: int = Field(description="Module sequence number", ge=1)
    title: str = Field(description="Short title for this module (3-6 words)")
    learning_objective: str = Field(
        description=(
            "What the learner will be able to do after completing this module. "
            "Start with a verb (e.g., 'Implement...', 'Understand...', 'Design...')."
        )
    )
    topics: list[str] = Field(
        description="Key topics covered in this module (3-5 items)",
        min_length=1,
    )
    estimated_time: str = Field(
        description="Estimated time to complete (e.g., '2-3 hours', '1 day')"
    )
    practical_exercise: str = Field(
        description=(
            "Hands-on exercise or project for this module. "
            "Single sentence describing what to build or practice."
        )
    )


class LearningPath(DataAvailabilityMixin):
    """Learning path output schema.

    Issue #299-304: Inherits DataAvailabilityMixin to report data coverage.
    """

    topic: str = Field(description="Main topic or skill this learning path covers")
    target_audience: str = Field(
        description=(
            "Description of who this path is for. "
            "Single sentence specifying skill level and background."
        )
    )
    prerequisites: list[str] = Field(
        description=(
            "Required knowledge or skills before starting. "
            "Each item should be a specific skill or concept."
        ),
        default_factory=list,
    )
    modules: list[LearningModule] = Field(
        description="Ordered list of learning modules from beginner to advanced",
        min_length=1,
    )
    resources: list[str] = Field(
        description=(
            "Recommended resources (books, courses, documentation, tools). "
            "Each item should include the resource name and type."
        ),
        default_factory=list,
    )
    total_estimated_time: str = Field(
        description=(
            "Total estimated time to complete the entire path (e.g., '20-30 hours', '2 weeks')"
        )
    )
    mastery_indicators: list[str] = Field(
        description=(
            "How to verify mastery of this topic. "
            "Each item should describe a specific skill demonstration."
        ),
        default_factory=list,
    )
    recommendation: str = Field(
        description=(
            "Overall learning recommendation and approach. "
            "Write as 2-3 cohesive sentences with guidance on how to approach this path."
        )
    )
    confidence_score: float = Field(
        description=(
            "Confidence score (0.0-1.0) representing both the quality and certainty "
            "of this learning path. Consider: completeness of modules, pedagogical quality, "
            "logical progression, and practicality of exercises. "
            "Higher scores indicate more comprehensive and well-structured learning paths."
        ),
        ge=0.0,
        le=1.0,
    )
