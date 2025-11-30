"""Aggregated insights schema for synthesis output."""

from pydantic import BaseModel, Field


class ConflictResolution(BaseModel):
    """Conflict resolution details."""

    conflict: str = Field(description="Description of the contradiction between agents")
    resolution: str = Field(description="How the conflict was resolved")
    priority_agent: str = Field(description="Which agent's finding was prioritized")
    reasoning: str = Field(description="Why this agent was prioritized")


class Synthesis(BaseModel):
    """Synthesized insights from all agents."""

    technical_analysis: str = Field(
        description=(
            "Combined technical insights from all agents. "
            "Format as markdown with paragraphs separated by blank lines."
        )
    )
    implementation_guidance: str = Field(
        description=(
            "Unified implementation recommendations. "
            "Format as a markdown numbered list with each step on its own line. "
            "Example:\n1. First step\n2. Second step\n3. Third step"
        )
    )
    risk_assessment: str = Field(
        description=(
            "Consolidated risk analysis. "
            "Format as markdown with bullet points for each risk."
        )
    )
    recommendations: str = Field(
        description=(
            "Final recommendations prioritizing all perspectives. "
            "Format as markdown with bullet points for each recommendation."
        )
    )


class AggregatedInsights(BaseModel):
    """Aggregated insights from all agent findings.

    This schema defines the output structure for the aggregator node,
    which synthesizes findings from all 8 specialized agents into a
    cohesive, actionable narrative.
    """

    executive_summary: str = Field(
        description=(
            "2-3 sentence summary of the entire analysis. "
            "Write as a cohesive paragraph, not a list."
        ),
        min_length=50,
    )
    key_findings: list[str] = Field(
        description=(
            "3-7 key findings prioritized by impact. "
            "Each finding should be a single concise sentence or phrase."
        ),
        min_length=3,
        max_length=7,
    )
    synthesis: Synthesis = Field(description="Synthesized insights from all agents")
    conflicts_resolved: list[ConflictResolution] = Field(
        description="List of conflicts that were detected and resolved",
        default_factory=list,
    )
