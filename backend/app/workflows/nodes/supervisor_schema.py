"""Pydantic schema for supervisor structured output."""

from pydantic import BaseModel, Field


class AgentSelection(BaseModel):
    """Structured output for supervisor agent selection.

    Replaces tool calls with direct structured output for faster inference.
    """

    agents: list[str] = Field(
        ...,
        description="Selected agent names (e.g., ['tech_comparator', 'security_auditor'])",
        min_length=0,
        max_length=8,
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation for agent selection (max 100 chars)",
        max_length=100,
    )
    confidence: float = Field(
        ...,
        description="Confidence score for selection (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )

