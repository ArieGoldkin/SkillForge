"""Research analyst agent schemas."""

from pydantic import BaseModel, Field

from app.domains.analysis.schemas.agents.base import DataAvailabilityMixin


class KeyFinding(BaseModel):
    """A key finding from the research analysis."""

    finding: str = Field(
        description=(
            "Single sentence describing a key finding or insight from the content. "
            "Be specific about what was discovered or demonstrated."
        )
    )
    evidence_strength: str = Field(
        description=(
            "Assessment of evidence strength: 'strong' (replicated results, large samples), "
            "'moderate' (single study, reasonable methodology), or 'weak' (anecdotal, small sample)"
        )
    )
    practical_implication: str = Field(
        description=("Single sentence describing how this finding can be applied in practice.")
    )


class ResearchAnalysis(DataAvailabilityMixin):
    """Research analysis output schema.

    Issue #299-304: Inherits DataAvailabilityMixin to report data coverage.
    """

    research_question: str = Field(
        description=(
            "The main research question or problem being addressed. "
            "Write as a single clear question or problem statement."
        )
    )
    methodology_summary: str = Field(
        description=(
            "Summary of the methodology or approach used. "
            "Write as 2-3 sentences covering the key methods, data sources, and analysis approach."
        )
    )
    key_findings: list[KeyFinding] = Field(
        description="List of key findings with evidence strength and practical implications",
        min_length=1,
    )
    limitations: list[str] = Field(
        description=(
            "Limitations, caveats, and potential biases identified. "
            "Each item should be a single sentence describing one limitation."
        ),
        default_factory=list,
    )
    related_work: list[str] = Field(
        description=(
            "Related research, papers, or concepts mentioned or relevant. "
            "Each item should reference a specific work or concept."
        ),
        default_factory=list,
    )
    synthesis: str = Field(
        description=(
            "Synthesis of the main themes, patterns, and connections identified. "
            "Write as 2-3 cohesive sentences revealing insights and novel connections."
        )
    )
    recommendation: str = Field(
        description=(
            "Overall recommendation for practitioners based on this research. "
            "Write as 2-3 cohesive sentences with actionable guidance."
        )
    )
    confidence_score: float = Field(
        description=(
            "Confidence score (0.0-1.0) representing both the quality and certainty "
            "of this research analysis. Consider: accuracy of findings, quality of synthesis, "
            "depth of critical evaluation, and completeness of methodology coverage. "
            "Higher scores indicate more thorough and accurate research assessments."
        ),
        ge=0.0,
        le=1.0,
    )
