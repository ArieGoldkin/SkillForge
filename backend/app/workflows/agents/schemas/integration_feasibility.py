"""Integration feasibility agent schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class CompatibilityScore(BaseModel):
    """Compatibility assessment for a technology stack."""

    score: float = Field(
        description="Score 0.0-1.0",
        ge=0.0,
        le=1.0,
    )
    notes: str = Field(description="Compatibility notes")


class IntegrationFeasibility(BaseModel):
    """Integration feasibility analysis output schema."""

    compatibility: dict[str, CompatibilityScore] = Field(
        description=(
            "REQUIRED: Compatibility scores for 2-3 technology stacks. "
            "MUST include entries like 'nextjs', 'fastapi', 'react', 'docker', etc. "
            "Each entry MUST have a 'score' (0.0-1.0) and 'notes' string. "
            "Example: {'react': {'score': 0.9, 'notes': 'Native support'}, "
            "'nextjs': {'score': 0.85, 'notes': 'SSR compatible'}}"
        )
    )
    migration_effort: Literal["low", "medium", "high"] = Field(description="Migration effort level")
    breaking_changes: list[str] = Field(description="Potential breaking changes")
    integration_steps: list[str] = Field(description="Integration steps")
