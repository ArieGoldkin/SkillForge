"""Implementation planner agent schemas."""

from pydantic import BaseModel, Field


class ImplementationStep(BaseModel):
    """Single implementation step schema."""

    step: int = Field(description="Step number", ge=1)
    action: str = Field(description="Action to perform in this step")
    files: list[str] = Field(
        description="Files to create or modify in this step",
        default_factory=list,
    )


class ImplementationPlan(BaseModel):
    """Step-by-step implementation guide output schema."""

    prerequisites: list[str] = Field(
        description="Required dependencies, setup steps, and prerequisites"
    )
    steps: list[ImplementationStep] = Field(
        description="Numbered implementation steps with actions and file modifications"
    )
    testing_strategy: str = Field(
        description="Testing approach, recommendations, and validation steps"
    )
    estimated_time: str = Field(
        description="Estimated implementation time (e.g., '2-3 hours', '1 day')"
    )
