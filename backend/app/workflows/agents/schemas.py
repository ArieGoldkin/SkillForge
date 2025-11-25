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
        description="Compatibility score from 0.0 (incompatible) to 1.0 (fully compatible)",
        ge=0.0,
        le=1.0,
    )
    notes: str = Field(description="Detailed notes explaining the compatibility assessment")


class IntegrationFeasibility(BaseModel):
    """Integration feasibility analysis output schema."""

    compatibility: dict[str, CompatibilityScore] = Field(
        description=(
            "REQUIRED: Compatibility scores and notes for modern development stacks. "
            "MUST include at least 2-3 stack assessments "
            "(e.g., 'nextjs', 'fastapi', 'postgresql', 'react', 'docker'). "
            "Each entry contains a score (0.0-1.0) indicating compatibility level "
            "and notes explaining the assessment."
        )
    )
    migration_effort: Literal["low", "medium", "high"] = Field(
        description="Estimated migration effort level"
    )
    breaking_changes: list[str] = Field(
        description="List of potential breaking changes when integrating"
    )
    integration_steps: list[str] = Field(
        description="Step-by-step integration guidance and recommendations"
    )


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
