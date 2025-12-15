"""Phase 1: Core Synthesis Schema - REQUIRED fields for all analyses.

This schema defines the minimal required output that MUST be generated for every
analysis, regardless of content type. It contains executive summary, key findings,
technical synthesis, and meta-analysis (conflicts, gaps, connections).

Generated in parallel with Phase 2 (learning) and Phase 3 (docs) during multi-phase
synthesis to reduce total LLM processing time from ~90s to ~35s.

Related: Issue #299-304 - Artifact Quality Initiative
"""

from pydantic import BaseModel, Field, field_validator

from app.workflows.tasks.schemas.aggregated_insights import (
    ConflictResolution,
    CoverageGap,
    CrossDomainConnection,
    Synthesis,
)


class CoreSynthesisSchema(BaseModel):
    """Phase 1: Core synthesis output - ALWAYS generated.

    Contains the essential analysis results that every artifact needs:
    - Executive summary for quick scanning
    - Key findings prioritized by impact
    - Technical synthesis from all agents (4 nested fields)
    - Meta-analysis of conflicts, gaps, and cross-domain connections
    - Coverage score indicating agent participation

    This phase completes first (~10-15s) and is shown immediately to users
    while optional learning/docs content generates in parallel.
    """

    executive_summary: str = Field(
        description=(
            "2-3 sentence summary of the entire analysis. "
            "Write as a cohesive paragraph, not a list. "
            "Should answer: What is this? Why does it matter? What's the key takeaway?"
        ),
        min_length=50,
        max_length=500,
    )

    key_findings: list[str] = Field(
        description=(
            "3-7 key findings prioritized by impact. "
            "Each finding should be a single concise sentence or phrase. "
            "Focus on actionable insights, not just observations."
        ),
        min_length=3,
        max_length=7,
    )

    synthesis: Synthesis = Field(
        description=(
            "Synthesized insights from all agents with 4 required fields: "
            "technical_analysis, implementation_guidance, risk_assessment, recommendations. "
            "Each field is markdown-formatted with proper structure (paragraphs, lists, bullets)."
        )
    )

    conflicts_resolved: list[ConflictResolution] = Field(
        description=(
            "List of contradictions detected between agent findings and how they were resolved. "
            "Each conflict includes: conflict description, resolution strategy, "
            "priority agent, and reasoning for prioritization. "
            "Empty list if no conflicts detected."
        ),
        default_factory=list,
    )

    coverage_gaps: list[CoverageGap] = Field(
        description=(
            "Missing analysis perspectives when not all agents contribute. "
            "Each gap identifies: missing agent, missing perspective, impact on analysis. "
            "Helps users understand limitations of the analysis. "
            "Empty list if all relevant agents contributed."
        ),
        default_factory=list,
    )

    cross_domain_connections: list[CrossDomainConnection] = Field(
        description=(
            "Connections identified between different analysis domains (e.g., security + performance). "
            "Each connection specifies: two domains, the relationship/trade-off, agents involved. "
            "Reveals non-obvious insights from multi-agent collaboration. "
            "Empty list if no cross-domain patterns found."
        ),
        default_factory=list,
    )

    coverage_score: float = Field(
        description=(
            "Percentage of potential agents that contributed to this analysis (0.0-1.0). "
            "Formula: (num_contributing_agents / total_relevant_agents). "
            "Lower scores indicate coverage gaps that may affect analysis completeness. "
            "Example: 0.875 = 7 out of 8 agents contributed"
        ),
        ge=0.0,
        le=1.0,
        default=0.0,
    )

    @field_validator("key_findings")
    @classmethod
    def validate_key_findings_count(cls, v: list[str]) -> list[str]:
        """Ensure key_findings has 3-7 items."""
        if not 3 <= len(v) <= 7:
            msg = f"key_findings must have 3-7 items, got {len(v)}"
            raise ValueError(msg)
        return v

    @field_validator("coverage_score")
    @classmethod
    def validate_coverage_score_range(cls, v: float) -> float:
        """Ensure coverage_score is between 0.0 and 1.0."""
        if not 0.0 <= v <= 1.0:
            msg = f"coverage_score must be between 0.0 and 1.0, got {v}"
            raise ValueError(msg)
        return v
