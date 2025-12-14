"""Pydantic schema for supervisor structured output."""

from pydantic import BaseModel, Field


class AgentSelection(BaseModel):
    """Structured output for supervisor agent selection.

    Replaces tool calls with direct structured output for faster inference.
    """

    agents: list[str] = Field(
        ...,
        description=(
            "Selected agent names. MINIMUM 3 agents required. Select 3-4 for simple content, "
            "4-6 for tutorials, 6-8 for comprehensive guides. "
            "(e.g., ['implementation_planner', 'dependency_mapper', 'security_auditor'])"
        ),
        min_length=3,
        max_length=8,
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation for agent selection (max 500 chars)",
        max_length=500,
    )
    confidence: float = Field(
        ...,
        description="Confidence score for selection (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
