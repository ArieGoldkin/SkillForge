"""Knowledge curator agent schemas."""

from typing import Literal

from pydantic import BaseModel, Field

from app.domains.analysis.schemas.agents.base import DataAvailabilityMixin


class KnowledgeConnection(BaseModel):
    """A connection to related analyzed content in the knowledge base."""

    related_analysis_id: str = Field(description="ID of the related analysis in the knowledge base")
    relationship_type: Literal[
        "prerequisite",
        "builds_upon",
        "alternative",
        "complementary",
        "contradicts",
        "extends",
    ] = Field(
        description=(
            "Type of relationship:\n"
            "- 'prerequisite': Should be learned before current content\n"
            "- 'builds_upon': Current content extends this\n"
            "- 'alternative': Different approach to same problem\n"
            "- 'complementary': Works well together\n"
            "- 'contradicts': Presents conflicting approach or information\n"
            "- 'extends': Advanced topic that builds on current content"
        )
    )
    relevance: float = Field(
        description="Relevance score for this connection (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )


class RecommendedContent(BaseModel):
    """Recommended content for the user to explore next."""

    title: str = Field(description="Title or topic of the recommended content")
    reason: str = Field(
        description=(
            "Single sentence explaining why this is recommended and how it "
            "relates to the current content."
        )
    )
    priority: Literal["low", "medium", "high"] = Field(
        description=(
            "Priority level for this recommendation:\n"
            "- 'low': Optional, nice to have\n"
            "- 'medium': Recommended for deeper understanding\n"
            "- 'high': Strongly recommended, fills critical gaps"
        )
    )


class KnowledgeCuratorOutput(DataAvailabilityMixin):
    """Knowledge curator analysis output schema.

    Issue #299-304: Inherits DataAvailabilityMixin to report data coverage.

    This agent connects content to the user's existing knowledge base,
    identifies prerequisites, and recommends related learning.
    """

    connections: list[KnowledgeConnection] = Field(
        description=(
            "List of connections to related analyzed content in the knowledge base. "
            "Each connection should specify the relationship type and relevance. "
            "Empty if no related content found."
        ),
        default_factory=list,
    )
    prerequisites: list[str] = Field(
        description=(
            "Concepts or topics the user should understand before diving into this content. "
            "Each item should be a single concept or topic (e.g., 'async/await in Python', "
            "'REST API design principles'). Empty if content is beginner-friendly."
        ),
        default_factory=list,
    )
    builds_upon: list[str] = Field(
        description=(
            "Concepts or topics that this content extends or builds upon. "
            "Each item should be a foundational concept that this content assumes "
            "knowledge of or extends with more advanced techniques."
        ),
        default_factory=list,
    )
    recommended_next: list[RecommendedContent] = Field(
        description=(
            "Recommended content to explore next, in priority order. "
            "Include both prerequisite gaps and natural next steps for deepening knowledge."
        ),
        default_factory=list,
    )
    knowledge_graph_position: str = Field(
        description=(
            "Description of where this content fits in the user's learning journey. "
            "Write as 2-3 sentences covering skill level, topic area, and how it "
            "connects to the broader knowledge graph."
        )
    )
    summary: str = Field(
        description=(
            "Summary of knowledge curation findings. Write as 2-3 cohesive sentences "
            "covering connections found, prerequisites identified, and recommended "
            "learning path progression."
        )
    )
    confidence_score: float = Field(
        description=(
            "Confidence score (0.0-1.0) representing both the quality and certainty "
            "of this knowledge curation analysis. Consider: accuracy of prerequisite "
            "identification, relevance of connections found, appropriateness of "
            "recommendations, and understanding of user's knowledge level. Higher scores "
            "indicate more accurate and helpful curation."
        ),
        ge=0.0,
        le=1.0,
    )
