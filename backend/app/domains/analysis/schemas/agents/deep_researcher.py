"""Deep researcher agent schemas."""

from pydantic import BaseModel, Field

from app.domains.analysis.schemas.agents.base import DataAvailabilityMixin


class ResearchFinding(BaseModel):
    """A research finding from deep investigation."""

    topic: str = Field(description="The specific topic or question this finding addresses")
    summary: str = Field(
        description=(
            "Summary of the finding. Write as 2-3 sentences covering what was "
            "discovered, key insights, and implications."
        )
    )
    sources: list[str] = Field(
        description=(
            "List of source URLs or references used for this finding. "
            "Each should be a credible, verifiable source."
        ),
        min_length=1,
    )
    confidence: float = Field(
        description="Confidence in this finding based on source quality and consensus (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )


class DeepResearcherOutput(DataAvailabilityMixin):
    """Deep researcher analysis output schema.

    Issue #299-304: Inherits DataAvailabilityMixin to report data coverage.

    This agent performs comprehensive external research using Tavily search
    to fill knowledge gaps and provide depth beyond the source content.
    """

    research_findings: list[ResearchFinding] = Field(
        description=(
            "List of research findings from deep investigation. Each finding should "
            "address a specific aspect of the topic with credible external sources. "
            "Focus on areas where the original content lacks detail or where "
            "additional context would be valuable."
        ),
        default_factory=list,
    )
    knowledge_gaps: list[str] = Field(
        description=(
            "Areas needing more research or where information is unavailable. "
            "Each item should be a single sentence describing one gap or limitation "
            "in available information."
        ),
        default_factory=list,
    )
    source_quality_assessment: str = Field(
        description=(
            "Overall assessment of the quality and reliability of sources found. "
            "Write as 2-3 sentences covering source diversity, credibility, "
            "recency, and any concerns about information quality."
        )
    )
    search_queries_used: list[str] = Field(
        description=(
            "List of Tavily search queries executed during research. "
            "Documents the research strategy and scope."
        ),
        default_factory=list,
    )
    summary: str = Field(
        description=(
            "Summary of deep research findings. Write as 2-3 cohesive sentences "
            "covering key discoveries, overall source quality, and how the research "
            "complements the original content."
        )
    )
    confidence_score: float = Field(
        description=(
            "Confidence score (0.0-1.0) representing both the quality and certainty "
            "of this deep research analysis. Consider: number and quality of sources found, "
            "consensus among sources, completeness of knowledge gaps identified, and "
            "relevance of findings to the topic. Higher scores indicate more comprehensive "
            "and reliable research."
        ),
        ge=0.0,
        le=1.0,
    )
