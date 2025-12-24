"""Source credibility agent schemas."""

from typing import Literal

from pydantic import BaseModel, Field

from app.domains.analysis.schemas.agents.base import DataAvailabilityMixin


class CredibilitySignal(BaseModel):
    """Individual credibility signal for source assessment."""

    signal_type: str = Field(
        description=(
            "Type of credibility signal (e.g., 'domain_authority', 'author_credentials', "
            "'citation_count', 'publication_venue', 'github_stars', 'maintenance_activity')"
        )
    )
    value: str = Field(
        description=(
            "Signal value or description. Use specific values when available "
            "(e.g., '1.2M GitHub stars', 'Published in peer-reviewed journal', "
            "'Active commits in last 30 days', 'Author: John Doe, PhD from MIT'). "
            "For missing signals, use descriptive text (e.g., 'No author information', "
            "'Domain registered <1 year ago')."
        )
    )
    weight: float = Field(
        description=(
            "Contribution to overall credibility score (0.0-1.0). "
            "Higher weight = stronger signal. Examples: "
            "- Official documentation/repos: 0.9-1.0 "
            "- Peer-reviewed research: 0.8-1.0 "
            "- Established tech blogs: 0.6-0.8 "
            "- Personal blogs with expertise: 0.4-0.6 "
            "- Unknown sources: 0.1-0.3"
        ),
        ge=0.0,
        le=1.0,
    )


class SourceCredibilityOutput(DataAvailabilityMixin):
    """Source credibility analysis output schema.

    Tier 2 Validation agent that assesses source trustworthiness based on:
    - Domain authority and reputation
    - Author credentials and expertise
    - Publication venue and editorial standards
    - Citation patterns and external references
    - GitHub repository metrics (if applicable)
    - Content recency and maintenance activity

    Issue #299-304: Inherits DataAvailabilityMixin to report data coverage.
    """

    source_url: str = Field(description="The source URL being evaluated for credibility")
    credibility_score: float = Field(
        description=(
            "Overall credibility score (0.0-1.0) representing trustworthiness. "
            "Scoring guidelines:\n"
            "- 0.9-1.0: Official documentation, peer-reviewed research, established authorities\n"
            "- 0.7-0.9: Well-known tech blogs, active maintainers, verified experts\n"
            "- 0.5-0.7: Established personal blogs, medium authority domains\n"
            "- 0.3-0.5: New/unknown sources, minimal verification\n"
            "- 0.0-0.3: Suspicious patterns, unreliable sources, spam signals"
        ),
        ge=0.0,
        le=1.0,
    )
    signals: list[CredibilitySignal] = Field(
        description=(
            "List of 2-10 credibility signals identified from the source. "
            "Include both positive signals (reputation, citations, expertise) "
            "and negative signals (red flags, missing verification, spam patterns). "
            "Each signal contributes to the overall credibility_score through its weight."
        ),
        min_length=2,
        max_length=10,
    )
    risk_factors: list[str] = Field(
        description=(
            "List of 0-5 risk factors or red flags identified. Examples:\n"
            "- 'Content farm with excessive ads'\n"
            "- 'No author attribution or credentials'\n"
            "- 'Outdated information (>3 years old)'\n"
            "- 'Contradicts official documentation'\n"
            "- 'Suspicious domain registration patterns'\n"
            "Empty list if no significant risks identified."
        ),
        default_factory=list,
        max_length=5,
    )
    recommendation: Literal["trustworthy", "moderate", "caution", "unreliable"] = Field(
        description=(
            "Overall trust recommendation based on credibility assessment:\n"
            "- 'trustworthy': High confidence source (score 0.8+), safe to reference\n"
            "- 'moderate': Generally reliable (score 0.5-0.8), cross-check key claims\n"
            "- 'caution': Low confidence (score 0.3-0.5), verify with authoritative sources\n"
            "- 'unreliable': Not recommended (score <0.3), avoid using as reference"
        )
    )
    confidence_score: float = Field(
        description=(
            "Confidence score (0.0-1.0) representing certainty of this credibility assessment. "
            "Consider: number of signals identified, clarity of authority markers, "
            "availability of verification data (author info, citations, repo stats). "
            "Higher scores indicate more confident credibility evaluation."
        ),
        ge=0.0,
        le=1.0,
    )
