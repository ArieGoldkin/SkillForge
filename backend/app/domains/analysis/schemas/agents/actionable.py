"""Actionable agent schemas.

This agent extracts concrete next steps and learning resources from any content type,
providing immediate actions, follow-up tasks, and relevant resources.
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.domains.analysis.schemas.agents.base import DataAvailabilityMixin


class Action(BaseModel):
    """Single actionable step with context and time estimate."""

    step_number: int = Field(
        description=(
            "Sequential step number (1, 2, 3...). "
            "Used to order actions in a logical learning or implementation sequence."
        ),
        ge=1,
    )
    action: str = Field(
        description=(
            "Clear, actionable step written as an imperative. "
            "Be specific and concrete (e.g., 'Install LangGraph 0.6.7 with pip install langgraph', "
            "'Create FastAPI endpoint at /api/v1/analyze with async handler'). "
            "Avoid vague instructions like 'learn about' or 'understand'."
        )
    )
    expected_outcome: str = Field(
        description=(
            "What the user will achieve after completing this action. "
            "Be concrete and measurable (e.g., 'A working endpoint that returns 200 OK with JSON response', "
            "'Understanding of HNSW indexing tradeoffs between recall and speed'). "
            "Helps users verify they completed the step correctly."
        )
    )
    time_estimate: str = Field(
        description=(
            "Realistic time estimate for completing this action. "
            "Use specific durations like '15 minutes', '1 hour', '2-3 hours', '1 day'. "
            "Consider setup time, learning curve, and potential blockers."
        ),
        examples=["15 minutes", "1 hour", "2-3 hours", "1 day", "30 minutes"],
    )


class Resource(BaseModel):
    """Learning or reference resource with metadata."""

    name: str = Field(
        description=(
            "Clear, descriptive name of the resource. "
            "Include version numbers if applicable (e.g., 'LangGraph 0.6.7 Documentation', "
            "'FastAPI Tutorial - Async Operations'). "
            "Should help users decide if this resource is worth exploring."
        )
    )
    url: str | None = Field(
        description=(
            "Direct URL to the resource if available. "
            "Prefer official documentation or high-quality sources. "
            "Set to None if resource is mentioned in content but no URL provided."
        ),
        default=None,
    )
    resource_type: Literal["documentation", "tutorial", "tool", "library", "course"] = Field(
        description=(
            "Type of resource:\n"
            "- 'documentation': Official docs, API references, guides\n"
            "- 'tutorial': Step-by-step learning materials, how-tos\n"
            "- 'tool': CLI tools, IDEs, development utilities\n"
            "- 'library': Code libraries, frameworks, packages\n"
            "- 'course': Structured learning courses, video series"
        )
    )
    relevance: str = Field(
        description=(
            "Brief explanation of why this resource is relevant to the content. "
            "Connect it to specific actions or outcomes (e.g., 'Essential for understanding "
            "state persistence in multi-agent workflows', 'Provides benchmarks for comparing "
            "HNSW vs IVF indexing performance'). "
            "One sentence maximum."
        )
    )


class ActionableOutput(DataAvailabilityMixin):
    """Actionable next steps analysis output schema.

    Universal agent (Tier 1) that extracts practical next steps from any content type.
    Provides immediate actions (do right now), follow-up actions (do later), and
    relevant learning resources.

    Issue #299-304: Inherits DataAvailabilityMixin to report data coverage.
    """

    immediate_actions: list[Action] = Field(
        description=(
            "1-3 high-impact actions the user should take immediately after reading this content. "
            "Prioritize quick wins and foundational steps (e.g., install tools, set up environment, "
            "run first example). Each action should be completable within a few hours and build "
            "momentum for follow-up actions. Ordered by logical sequence (step_number)."
        ),
        min_length=1,
        max_length=3,
    )
    follow_up_actions: list[Action] = Field(
        description=(
            "Up to 5 actions for deeper learning or implementation. "
            "These build on immediate actions and may take longer (days to weeks). "
            "Include advanced topics, optimization, production deployment, etc. "
            "Ordered by logical sequence or increasing difficulty (step_number)."
        ),
        default_factory=list,
        max_length=5,
    )
    resources: list[Resource] = Field(
        description=(
            "Up to 5 high-quality resources for learning and implementation. "
            "Prioritize official documentation, well-maintained tutorials, and tools mentioned "
            "in the content. Include a mix of resource types (documentation, tutorials, tools). "
            "Each resource should directly support one or more actions."
        ),
        default_factory=list,
        max_length=5,
    )
    quick_win: str = Field(
        description=(
            "Single most impactful action the user can take right now (within 30 minutes). "
            "This should be the easiest, highest-value step from immediate_actions. "
            "Written as a complete sentence with expected outcome (e.g., 'Install LangGraph 0.6.7 "
            "and run the hello-world example to see state persistence in action - takes 15 minutes "
            "and validates your environment is ready'). "
            "Designed to overcome inertia and build confidence."
        )
    )
    confidence_score: float = Field(
        description=(
            "Confidence score (0.0-1.0) representing the quality and actionability of these recommendations. "
            "Consider: clarity of actions (specific vs vague), feasibility of time estimates, "
            "quality/availability of resources, and alignment with user's likely skill level. "
            "Higher scores indicate more concrete, well-supported, achievable action plans. "
            "Score 0.8+ means all actions are specific with clear outcomes and realistic timelines."
        ),
        ge=0.0,
        le=1.0,
    )
