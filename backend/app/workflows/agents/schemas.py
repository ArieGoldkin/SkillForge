"""Pydantic schemas for agent structured outputs.

This module defines the output schemas for all specialized analysis agents.
These schemas are used with ToolStrategy to ensure type-safe, validated
structured output from agents.
"""

from typing import Literal

from pydantic import BaseModel, Field


class TechComparisonEntry(BaseModel):
    """Comparison details for a single technology."""

    pros: list[str] = Field(
        description="List of advantages and strengths of this technology",
        default_factory=list,
    )
    cons: list[str] = Field(
        description="List of disadvantages and limitations of this technology",
        default_factory=list,
    )
    use_cases: list[str] = Field(
        description="List of recommended use cases and scenarios for this technology",
        default_factory=list,
    )


class TechComparison(BaseModel):
    """Technology comparison analysis output schema."""

    primary_tech: str = Field(description="Primary technology/framework identified in the content")
    alternatives: list[str] = Field(
        description="2-3 relevant alternative technologies to compare against",
        min_length=1,
        max_length=5,
    )
    comparison: dict[str, TechComparisonEntry] = Field(
        description=(
            "REQUIRED: Comparison table with pros, cons, and use_cases for each technology. "
            "MUST include an entry for primary_tech and each alternative. "
            "Each entry contains three lists: pros (advantages), "
            "cons (disadvantages), and use_cases (recommended scenarios)."
        )
    )
    recommendation: str = Field(description="Recommendation based on the comparison analysis")


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
