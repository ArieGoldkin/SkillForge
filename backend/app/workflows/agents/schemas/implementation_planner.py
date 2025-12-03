"""Implementation planner agent schemas."""

from pydantic import BaseModel, Field


class ImplementationStep(BaseModel):
    """Single implementation step schema."""

    step: int = Field(description="Step number", ge=1)
    action: str = Field(
        description=(
            "Single sentence describing the action to perform in this step. "
            "Start with a verb (e.g., 'Create...', 'Configure...', 'Implement...')."
        )
    )
    files: list[str] = Field(
        description="Files to create or modify in this step",
        default_factory=list,
    )


class ImplementationPlan(BaseModel):
    """Step-by-step implementation guide output schema."""

    prerequisites: list[str] = Field(
        description=(
            "Required dependencies, setup steps, and prerequisites. "
            "Each item should be a single concise sentence or phrase."
        )
    )
    steps: list[ImplementationStep] = Field(
        description="Numbered implementation steps with actions and file modifications"
    )
    testing_strategy: str = Field(
        description=(
            "Testing approach, recommendations, and validation steps. "
            "Write as 2-3 cohesive sentences covering unit tests, integration tests, "
            "and manual validation."
        )
    )
    estimated_time: str = Field(
        description="Estimated implementation time (e.g., '2-3 hours', '1 day')"
    )
    confidence_score: float = Field(
        description=(
            "Confidence score (0.0-1.0) representing both the quality and certainty "
            "of this implementation plan. Consider: completeness of steps, clarity of "
            "instructions, accuracy of prerequisites, and confidence in time estimates. "
            "Higher scores indicate more complete, accurate, and actionable plans."
        ),
        ge=0.0,
        le=1.0,
    )
