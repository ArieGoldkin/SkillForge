"""Freshness checker agent schemas.

Tier 2 Validation agent that detects version references and checks
against package registries (npm, PyPI) to flag outdated content.
"""

from pydantic import BaseModel, Field

from app.domains.analysis.schemas.agents.base import DataAvailabilityMixin


class VersionCheck(BaseModel):
    """Version comparison result for a single package."""

    package_name: str = Field(
        description="Name of the package or framework (e.g., 'react', 'fastapi', 'python')"
    )
    mentioned_version: str = Field(
        description="Version mentioned in content (e.g., '18.2.0', '3.11', 'latest')"
    )
    latest_version: str = Field(
        description=(
            "Latest stable version from package registry. "
            "Set to 'unknown' if registry unavailable or package not found."
        )
    )
    is_outdated: bool = Field(
        description=(
            "Whether the mentioned version is outdated. "
            "False if mentioned_version is 'latest' or matches latest_version."
        )
    )
    versions_behind: int = Field(
        description=(
            "Estimate of how many major/minor versions behind. "
            "0 if current or version comparison not possible."
        ),
        ge=0,
    )
    ecosystem: str = Field(
        description="Package ecosystem (npm, pypi, language, framework, other)",
        default="other",
    )


class FreshnessCheckerOutput(DataAvailabilityMixin):
    """Freshness checker analysis output schema.

    Tier 2 Validation agent that checks version freshness
    against package registries.

    Inherits DataAvailabilityMixin to report data coverage.
    """

    content_date: str | None = Field(
        description=(
            "Publication or update date if detected in content. "
            "Format: YYYY-MM-DD or YYYY-MM or YYYY. "
            "Set to null if no date found."
        ),
        default=None,
    )
    version_checks: list[VersionCheck] = Field(
        description=(
            "List of version checks performed on packages/frameworks mentioned in content. "
            "Include only items with explicit version numbers or 'latest' references. "
            "Skip generic technology mentions without versions."
        ),
        default_factory=list,
    )
    is_outdated: bool = Field(
        description=(
            "Overall assessment: true if content references outdated versions "
            "or is from more than 18 months ago. "
            "False if all versions are current or no version info available."
        )
    )
    freshness_score: float = Field(
        description=(
            "Freshness score from 0.0 (completely outdated) to 1.0 (completely fresh). "
            "Consider: recency of content_date, percentage of current versions, "
            "severity of version gaps (major vs minor behind). "
            "Examples: 1.0 = all current, 0.8 = 1-2 minor behind, 0.5 = some major behind, "
            "0.2 = multiple major versions behind or >2 years old."
        ),
        ge=0.0,
        le=1.0,
    )
    recommendations: list[str] = Field(
        description=(
            "List of 1-5 concise recommendations for updating content. "
            "Each recommendation should reference specific packages and target versions. "
            "Examples: 'Update React from 16.x to 19.x for concurrent features', "
            "'Migrate to Python 3.12 for performance improvements'. "
            "Empty list if content is fresh or no actionable updates found."
        ),
        default_factory=list,
    )
    confidence_score: float = Field(
        description=(
            "Confidence in freshness assessment (0.0-1.0). "
            "Consider: availability of version data, reliability of package registries, "
            "clarity of version mentions in content. "
            "High confidence (0.8+) requires explicit versions and successful registry checks. "
            "Low confidence (0.3-) when no versions mentioned or registries unavailable."
        ),
        ge=0.0,
        le=1.0,
    )
