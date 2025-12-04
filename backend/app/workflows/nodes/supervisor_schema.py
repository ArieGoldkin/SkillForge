"""Pydantic schema for supervisor structured output."""

from pydantic import BaseModel, Field


class AgentSelection(BaseModel):
    """Structured output for supervisor agent selection.

    Replaces tool calls with direct structured output for faster inference.
    """

    agents: list[str] = Field(
        ...,
        description="Selected agent names. Select 1-2 for simple content, 3-4 for tutorials, 4-6 for comprehensive guides. (e.g., ['tech_comparator', 'security_auditor'])",
        min_length=1,
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
