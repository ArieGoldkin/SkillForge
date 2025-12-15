"""Tech comparator agent schemas."""

from pydantic import BaseModel, Field

from app.workflows.agents.schemas.base import DataAvailabilityMixin


class TechComparisonEntry(BaseModel):
    """Comparison details for a single technology."""

    pros: list[str] = Field(
        description=(
            "List of advantages and strengths of this technology. "
            "Each item should be a single concise phrase or short sentence."
        ),
        default_factory=list,
    )
    cons: list[str] = Field(
        description=(
            "List of disadvantages and limitations of this technology. "
            "Each item should be a single concise phrase or short sentence."
        ),
        default_factory=list,
    )
    use_cases: list[str] = Field(
        description=(
            "List of recommended use cases and scenarios for this technology. "
            "Each item should be a single concise phrase describing the scenario."
        ),
        default_factory=list,
    )


class TechComparison(DataAvailabilityMixin):
    """Technology comparison analysis output schema.

    Issue #299-304: Inherits DataAvailabilityMixin to report data coverage.
    """

    primary_tech: str = Field(description="Primary technology/framework identified in the content")
    alternatives: list[str] = Field(
        description="2-3 relevant alternative technologies to compare against",
        min_length=1,
        max_length=5,
    )
    comparison: dict[str, TechComparisonEntry] = Field(
        default_factory=dict,
        description=(
            "Comparison table with pros, cons, and use_cases for each technology. "
            "Include an entry for primary_tech and each alternative. "
            "Each entry contains three lists: pros (advantages), "
            "cons (disadvantages), and use_cases (recommended scenarios). "
            "Example: {'LangGraph': {'pros': ['...'], 'cons': ['...'], 'use_cases': ['...']}, "
            "'LangChain Agents': {'pros': ['...'], 'cons': ['...'], 'use_cases': ['...']}}."
        ),
        examples=[
            {
                "LangGraph": {
                    "pros": ["Low-level control", "Durable execution"],
                    "cons": ["Steeper learning curve"],
                    "use_cases": ["Long-running agents", "Stateful workflows"],
                },
                "LangChain Agents": {
                    "pros": ["High-level abstraction", "Easy to use"],
                    "cons": ["Less control"],
                    "use_cases": ["Quick prototypes", "Simple agents"],
                },
            }
        ],
    )
    recommendation: str = Field(
        description=(
            "Recommendation based on the comparison analysis. "
            "Write as 2-3 cohesive sentences explaining which technology to choose and why."
        )
    )
    confidence_score: float = Field(
        description=(
            "Confidence score (0.0-1.0) representing both the quality and certainty "
            "of this technology comparison. Consider: accuracy of technology identification, "
            "completeness of pros/cons, relevance of alternatives, and confidence in "
            "recommendation. Higher scores indicate more accurate and comprehensive comparisons."
        ),
        ge=0.0,
        le=1.0,
    )
