"""Aggregated insights schema for synthesis output."""

from pydantic import BaseModel, Field


class GotchaItem(BaseModel):
    """Common pitfall with symptom and quick fix."""

    issue: str = Field(
        description=(
            "Description of the common pitfall or gotcha. "
            "Be specific and technical (e.g., 'Circular imports between modules')"
        )
    )
    symptom: str = Field(
        description=(
            "Observable symptom when this issue occurs. "
            "Should help developers recognize the problem "
            "(e.g., 'ImportError: cannot import name X from Y')"
        )
    )
    quick_fix: str = Field(
        description=(
            "Concrete solution or workaround. "
            "Should be actionable and specific "
            "(e.g., 'Use TYPE_CHECKING import guard and string type hints')"
        )
    )


class QuickReference(BaseModel):
    """Front-loaded critical information for fast scanning.

    This section appears at the top of artifacts to provide instant context
    for developers and AI agents. Designed for 10-15 second scanning per
    research findings (docs/ARTIFACT_RESEARCH_SUMMARY.md).
    """

    primary_technology: str = Field(
        description=(
            "Main technology stack with specific versions. "
            "Format: 'TechName version + optional dependency'. "
            "Example: 'LangGraph 0.6.7 + PostgreSQL 14' or 'React 19 + Next.js 15'"
        ),
        min_length=5,
        max_length=100,
    )
    complexity: str = Field(
        description=(
            "Complexity level with time estimate. "
            "Format: 'Level (Est. X-Y hours)'. "
            "Levels: Beginner (1-2h), Intermediate (3-4h), Advanced (5-8h), Expert (8+h). "
            "Example: 'Intermediate (Est. 3-4 hours)'"
        ),
        min_length=10,
        max_length=60,
    )
    prerequisites: list[str] = Field(
        description=(
            "Required dependencies or knowledge before starting. "
            "Max 4 items, each specific and version-pinned. "
            "Example: 'Python 3.11+', 'PostgreSQL 14+', 'Docker installed'"
        ),
        max_length=4,
    )
    critical_commands: list[str] = Field(
        description=(
            "Essential commands for installation and setup. "
            "Max 6 items, copy-paste ready with exact versions. "
            "Example: 'pip install langgraph==0.6.7', 'docker-compose up -d'"
        ),
        max_length=6,
    )
    files_to_modify: list[str] = Field(
        description=(
            "List of files to create or modify with full paths. "
            "Max 10 items, prioritize most important files first. "
            "Example: 'backend/app/workflows/graph.py', 'backend/app/models/state.py'"
        ),
        max_length=10,
        default_factory=list,
    )
    gotchas: list[GotchaItem] = Field(
        description=(
            "Common pitfalls with symptoms and quick fixes. "
            "Max 5 items, prioritize most frequent or critical issues. "
            "Helps developers avoid common mistakes and debug faster."
        ),
        max_length=5,
        default_factory=list,
    )


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
            "Consolidated risk analysis. Format as markdown with bullet points for each risk."
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

    quick_reference: QuickReference | None = Field(
        description=(
            "Quick Reference section with critical information for fast scanning. "
            "Should be extracted from agent findings to front-load technology, "
            "complexity, commands, files, and common gotchas. "
            "Optional field - if extraction fails, template will skip this section."
        ),
        default=None,
    )
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
