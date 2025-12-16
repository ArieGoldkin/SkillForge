"""Pydantic schemas for agent examples and selection results.

Used for Few-Shot Prompting (Phase 1 - Week 1.2).
"""

from uuid import UUID

from pydantic import BaseModel, Field


class AgentExample(BaseModel):
    """A single agent example for few-shot prompting.

    Represents a high-quality example that can be injected into prompts
    to improve agent output quality.

    Example:
        >>> example = AgentExample(
        ...     id=uuid4(),
        ...     agent_type="tech_comparator",
        ...     input_summary="Comparing React vs Vue for state management",
        ...     output_example={"key_differences": [...], "recommendation": "..."},
        ...     quality_score=0.95,
        ... )
        >>> example.agent_type
        'tech_comparator'

    """

    id: UUID = Field(..., description="Unique example ID")
    agent_type: str = Field(..., description="Agent type (e.g., 'tech_comparator')")
    input_summary: str = Field(..., description="Brief summary of input content")
    input_content_preview: str | None = Field(
        None, description="First 2000 chars of content (optional)"
    )
    output_example: dict = Field(..., description="Example agent output (JSON)")
    context_note: str | None = Field(None, description="Additional context or notes")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Quality score (0-1)")
    content_type: str | None = Field(None, description="Content type (article, video, repo)")
    difficulty_level: str | None = Field(
        None, description="Difficulty (beginner, intermediate, advanced)"
    )
    similarity_distance: float | None = Field(
        None, description="Cosine distance from query (lower = more similar)"
    )

    class Config:
        """Pydantic config."""

        from_attributes = True


class ExampleSelectionResult(BaseModel):
    """Result from example selection query.

    Contains selected examples and metadata about the selection process.

    Example:
        >>> result = ExampleSelectionResult(
        ...     examples=[example1, example2],
        ...     total_candidates=10,
        ...     selection_strategy="semantic_similarity",
        ... )
        >>> len(result.examples)
        2

    """

    examples: list[AgentExample] = Field(
        ..., description="Selected examples (ordered by relevance)"
    )
    total_candidates: int = Field(..., description="Total examples available for this agent type")
    selection_strategy: str = Field(
        ..., description="Strategy used (semantic_similarity or quality_based)"
    )
    avg_quality_score: float | None = Field(
        None, description="Average quality score of selected examples"
    )
    avg_similarity_distance: float | None = Field(
        None, description="Average cosine distance (semantic search only)"
    )
