"""Research analyst agent schemas."""

from pydantic import BaseModel, Field

from app.domains.analysis.workflows.agents.schemas.base import DataAvailabilityMixin


class ResearchFinding(BaseModel):
    """A single research finding with evidence."""

    finding: str = Field(
        description="Key finding from the research",
        min_length=20,
    )
    evidence: str = Field(
        description="Supporting evidence or data for this finding",
        min_length=30,
    )
    significance: str = Field(
        description="Why this finding matters (high/medium/low)",
        pattern="^(high|medium|low)$",
    )


class ResearchAnalysis(DataAvailabilityMixin):
    """Research analyst output schema.

    Analyzes research papers, technical documents, and studies to extract
    key findings, methodology, and insights.

    Issue #299-304: Inherits DataAvailabilityMixin to report data coverage.
    """

    research_topic: str = Field(
        description="Main research topic or question addressed",
        min_length=10,
    )
    key_findings: list[ResearchFinding] = Field(
        description="3-5 key research findings with evidence",
        min_length=3,
        max_length=5,
    )
    methodology: str = Field(
        description="Research methodology used (quantitative, qualitative, mixed, experimental, etc.)",
        min_length=50,
    )
    data_sources: list[str] = Field(
        description="Primary data sources and datasets used",
        min_length=1,
        max_length=10,
    )
    limitations: list[str] = Field(
        description="Study limitations and potential biases",
        min_length=2,
        max_length=5,
    )
    practical_applications: list[str] = Field(
        description="Real-world applications of the research",
        min_length=2,
        max_length=5,
    )
    confidence_score: float = Field(
        description="Confidence in analysis quality (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    recommendation: str = Field(
        description="Overall assessment and recommendation for practitioners",
        min_length=100,
        max_length=500,
    )
