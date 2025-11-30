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
    notes: str = Field(
        description="Single sentence explaining the compatibility assessment."
    )


class IntegrationFeasibility(BaseModel):
    """Integration feasibility analysis output schema."""

    compatibility: dict[str, CompatibilityScore] = Field(
        default_factory=dict,
        description=(
            "Compatibility scores for 2-3 technology stacks. "
            "Include entries like 'nextjs', 'fastapi', 'react', 'docker', etc. "
            "Each entry should have a 'score' (0.0-1.0) and 'notes' string. "
            "Example: {'react': {'score': 0.9, 'notes': 'Native support'}, "
            "'nextjs': {'score': 0.85, 'notes': 'SSR compatible'}}."
        ),
        examples=[
            {
                "react": {"score": 0.9, "notes": "Native support"},
                "nextjs": {"score": 0.85, "notes": "SSR compatible"},
            }
        ],
    )
    migration_effort: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="Migration effort level",
    )
    breaking_changes: list[str] = Field(
        default_factory=list,
        description=(
            "Potential breaking changes. "
            "Each item should be a single sentence describing one breaking change."
        ),
    )
    integration_steps: list[str] = Field(
        default_factory=list,
        description=(
            "Integration steps to follow. "
            "Each item should be a single actionable sentence starting with a verb."
        ),
    )
