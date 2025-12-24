"""Community pulse agent schemas."""

from typing import Literal

from pydantic import BaseModel, Field

from app.domains.analysis.schemas.agents.base import DataAvailabilityMixin


class CommunityConcern(BaseModel):
    """A concern or issue raised by the community."""

    issue: str = Field(description="Brief description of the concern or issue (1-2 sentences)")
    frequency: Literal["rare", "occasional", "common", "widespread"] = Field(
        description=(
            "How frequently this concern is raised:\n"
            "- 'rare': Mentioned by isolated individuals\n"
            "- 'occasional': Mentioned sporadically\n"
            "- 'common': Mentioned regularly by multiple sources\n"
            "- 'widespread': Mentioned consistently across many sources"
        )
    )
    severity: Literal["low", "medium", "high", "critical"] = Field(
        description=(
            "Severity impact of this concern:\n"
            "- 'low': Minor inconvenience or cosmetic issue\n"
            "- 'medium': Affects usability or requires workarounds\n"
            "- 'high': Significant blocker or pain point\n"
            "- 'critical': Fundamental flaw or dealbreaker"
        )
    )


class Discussion(BaseModel):
    """A notable community discussion or thread."""

    source: str = Field(
        description="Platform where discussion occurred (e.g., 'Reddit', 'HackerNews', 'GitHub')"
    )
    title: str = Field(description="Title or topic of the discussion")
    url: str = Field(description="URL to the discussion")
    sentiment: Literal["positive", "neutral", "negative", "mixed"] = Field(
        description="Overall sentiment of the discussion"
    )


class GitHubMetrics(BaseModel):
    """GitHub activity metrics for the project."""

    stars_trend: Literal["increasing", "stable", "decreasing"] = Field(
        description="Trend in GitHub stars over recent time period"
    )
    issues_open: int = Field(
        description="Number of currently open issues",
        ge=0,
    )
    pr_velocity: Literal["low", "moderate", "high"] = Field(
        description=(
            "Pull request velocity:\n"
            "- 'low': Few PRs, slow merge times\n"
            "- 'moderate': Regular PRs, reasonable merge times\n"
            "- 'high': Active development, frequent merges"
        )
    )


class CommunityPulseOutput(DataAvailabilityMixin):
    """Community pulse analysis output schema.

    Issue #299-304: Inherits DataAvailabilityMixin to report data coverage.

    This agent assesses community sentiment, adoption trends, and discussions
    around the technology or content topic.
    """

    adoption_trend: Literal["rising", "stable", "declining", "emerging"] = Field(
        description=(
            "Overall adoption trend:\n"
            "- 'rising': Growing adoption, increasing mentions and usage\n"
            "- 'stable': Steady adoption, consistent usage\n"
            "- 'declining': Decreasing adoption, fewer mentions\n"
            "- 'emerging': Very new, early adoption phase"
        )
    )
    sentiment_score: float = Field(
        description=(
            "Community sentiment score from -1.0 (very negative/critical) to "
            "1.0 (very positive/enthusiastic). 0.0 is neutral."
        ),
        ge=-1.0,
        le=1.0,
    )
    community_concerns: list[CommunityConcern] = Field(
        description=(
            "List of concerns or issues raised by the community. "
            "Focus on recurring themes and significant pain points."
        ),
        default_factory=list,
    )
    notable_discussions: list[Discussion] = Field(
        description=(
            "Notable community discussions or threads. Include diverse perspectives "
            "and high-engagement discussions that reveal community sentiment."
        ),
        default_factory=list,
    )
    github_activity: GitHubMetrics | None = Field(
        description=(
            "GitHub activity metrics if the content relates to an open-source project. "
            "Omit if not applicable or data unavailable."
        ),
        default=None,
    )
    summary: str = Field(
        description=(
            "Summary of community pulse findings. Write as 2-3 cohesive sentences "
            "covering overall sentiment, adoption trend, key concerns, and "
            "community health indicators."
        )
    )
    confidence_score: float = Field(
        description=(
            "Confidence score (0.0-1.0) representing both the quality and certainty "
            "of this community pulse analysis. Consider: diversity of sources consulted, "
            "recency of discussions, signal-to-noise ratio in community feedback, and "
            "completeness of sentiment assessment. Higher scores indicate more comprehensive "
            "and reliable community analysis."
        ),
        ge=0.0,
        le=1.0,
    )
