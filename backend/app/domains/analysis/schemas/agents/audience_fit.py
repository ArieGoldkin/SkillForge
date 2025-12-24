"""Audience fit agent schemas."""

from typing import Literal

from pydantic import BaseModel, Field

from app.domains.analysis.schemas.agents.base import DataAvailabilityMixin


class Audience(BaseModel):
    """Audience profile with relevance assessment."""

    name: str = Field(
        description=(
            "Name of the audience segment (e.g., 'Backend Engineers with 2-5 years Python experience', "
            "'Frontend Developers migrating to React 19', 'Tech Leads evaluating RAG architectures')"
        )
    )
    experience_level: Literal["beginner", "intermediate", "advanced", "expert"] = Field(
        description=(
            "Required experience level for this audience segment:\n"
            "- 'beginner': 0-1 years in the domain, learning fundamentals\n"
            "- 'intermediate': 2-4 years, comfortable with core concepts\n"
            "- 'advanced': 5-7 years, deep expertise in specific areas\n"
            "- 'expert': 8+ years, thought leader or specialist"
        )
    )
    relevance_score: float = Field(
        description=(
            "How relevant this content is for this audience (0.0-1.0). "
            "Consider: topic alignment, depth match, prerequisite coverage, practical applicability. "
            "0.0 = not relevant, 0.5 = moderately relevant, 1.0 = highly relevant"
        ),
        ge=0.0,
        le=1.0,
    )
    why_relevant: str = Field(
        description=(
            "Explain why this content is relevant for this audience. "
            "Include: what they'll learn, how it fits their needs, specific benefits. "
            "Write as 1-2 concise sentences."
        )
    )


class AudienceFitOutput(DataAvailabilityMixin):
    """Audience fit analysis output schema.

    Issue #299-304: Inherits DataAvailabilityMixin to report data coverage.
    """

    primary_audience: Audience = Field(
        description=(
            "The main target audience for this content. Identify the audience segment "
            "that will benefit most from this material based on topic, depth, and prerequisites."
        )
    )
    secondary_audiences: list[Audience] = Field(
        description=(
            "Additional audience segments who would benefit from this content. "
            "List 1-3 secondary audiences with lower relevance scores than primary. "
            "Each should represent a distinct segment with different needs or experience levels."
        ),
        min_length=0,
        max_length=3,
        default_factory=list,
    )
    prerequisites: list[str] = Field(
        description=(
            "Required knowledge, skills, or experience needed to understand this content. "
            "Each item should be a single concise phrase or sentence. Examples:\n"
            "- 'Basic understanding of HTTP and REST APIs'\n"
            "- 'Familiarity with Python async/await syntax'\n"
            "- '2+ years experience with React hooks'\n"
            "List 1-5 most important prerequisites."
        ),
        min_length=1,
        max_length=5,
    )
    not_suitable_for: list[str] = Field(
        description=(
            "Audience segments or scenarios where this content is NOT suitable. "
            "Help readers avoid wasting time if content doesn't match their needs. Examples:\n"
            "- 'Complete beginners with no programming experience'\n"
            "- 'Teams using JavaScript (content is Python-specific)'\n"
            "- 'Production systems (examples are for learning only)'\n"
            "List 0-3 most important unsuitable cases."
        ),
        min_length=0,
        max_length=3,
        default_factory=list,
    )
    confidence_score: float = Field(
        description=(
            "Confidence score (0.0-1.0) representing both the quality and certainty "
            "of this audience analysis. Consider: clarity of target audience indicators "
            "in content, completeness of prerequisite information, accuracy of experience "
            "level assessment, and confidence in relevance scores. Higher scores indicate "
            "more accurate and comprehensive audience fit analysis."
        ),
        ge=0.0,
        le=1.0,
    )
