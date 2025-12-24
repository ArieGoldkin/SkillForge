"""Alternatives Finder agent schemas.

This Tier 2 Validation agent identifies technologies/tools mentioned in content,
uses Tavily search to find alternatives/competitors, and returns ranked alternatives
with comparison notes.

Issue #436: MCP tool integration for all agents.
"""

from pydantic import BaseModel, Field

from app.domains.analysis.schemas.agents.base import DataAvailabilityMixin


class Alternative(BaseModel):
    """Single alternative/competitor with comparison notes."""

    name: str = Field(
        description=(
            "Name of the alternative technology, tool, or framework. "
            "Be specific and include version if mentioned (e.g., 'Vue.js 3.x', 'Angular 17', 'Svelte 5'). "
            "Use official names/capitalization."
        )
    )
    description: str = Field(
        description=(
            "Brief description of what this alternative does and its key differentiator. "
            "One to two sentences maximum. Focus on unique selling points "
            "(e.g., 'Lightweight compiler-based framework with minimal runtime overhead', "
            "'Enterprise-grade with built-in TypeScript and comprehensive CLI tooling')."
        )
    )
    comparison_notes: str = Field(
        description=(
            "How this alternative compares to the subject (advantages, disadvantages, tradeoffs). "
            "Be specific about differences in performance, complexity, ecosystem, use cases. "
            "2-3 sentences. Include quantifiable metrics when available "
            "(e.g., 'Smaller bundle size (25KB vs 45KB)', 'Steeper learning curve but better TypeScript support')."
        )
    )
    relevance_score: float = Field(
        description=(
            "Relevance score (0.0-1.0) indicating how similar/comparable this alternative is. "
            "1.0 = direct competitor/drop-in replacement, "
            "0.7-0.9 = strong alternative with different tradeoffs, "
            "0.5-0.7 = viable option for similar use cases, "
            "< 0.5 = loosely related or niche alternative."
        ),
        ge=0.0,
        le=1.0,
    )
    url: str | None = Field(
        description=(
            "Official website or documentation URL for the alternative. "
            "Prefer official docs over GitHub repos. "
            "Set to None if no reliable URL found during search."
        ),
        default=None,
    )


class AlternativesFinderOutput(DataAvailabilityMixin):
    """Alternatives Finder analysis output schema.

    Tier 2 Validation agent that identifies and compares alternatives
    to technologies/tools mentioned in content.

    Issue #299-304: Inherits DataAvailabilityMixin to report data coverage.
    """

    subject: str = Field(
        description=(
            "The main technology/tool/framework being discussed in the content. "
            "Be specific with version numbers if mentioned "
            "(e.g., 'React 19', 'FastAPI 0.104.x', 'LangGraph 0.6.x'). "
            "This is what we're finding alternatives for."
        )
    )
    alternatives: list[Alternative] = Field(
        description=(
            "List of 3-7 viable alternatives/competitors ranked by relevance score (highest first). "
            "Include direct competitors, adjacent solutions, and niche alternatives. "
            "Prioritize alternatives mentioned in content, then use Tavily to find current options. "
            "Each alternative should offer distinct value propositions or tradeoffs."
        ),
        min_length=1,
        max_length=7,
    )
    recommendation: str = Field(
        description=(
            "High-level recommendation on when to consider alternatives vs sticking with the subject. "
            "Consider use case alignment, maturity, ecosystem, learning curve. "
            "3-4 sentences providing actionable guidance "
            "(e.g., 'React 19 remains the best choice for large-scale SPAs with complex state. "
            "Consider Svelte 5 if bundle size is critical, or Vue 3 for faster onboarding. "
            "For static sites, explore Astro with React islands for optimal performance.')."
        )
    )
    confidence_score: float = Field(
        description=(
            "Confidence score (0.0-1.0) representing the quality and completeness of alternatives analysis. "
            "Consider: accuracy of subject identification, relevance of alternatives found, "
            "quality of comparison notes, reliability of search results, and recency of information. "
            "Higher scores indicate comprehensive analysis with well-researched alternatives. "
            "Score 0.8+ means all alternatives are highly relevant with accurate comparisons."
        ),
        ge=0.0,
        le=1.0,
    )
