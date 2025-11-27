"""Tech comparator agent schemas."""

from pydantic import BaseModel, Field


class TechComparisonEntry(BaseModel):
    """Comparison details for a single technology."""

    pros: list[str] = Field(
        description="List of advantages and strengths of this technology",
        default_factory=list,
    )
    cons: list[str] = Field(
        description="List of disadvantages and limitations of this technology",
        default_factory=list,
    )
    use_cases: list[str] = Field(
        description="List of recommended use cases and scenarios for this technology",
        default_factory=list,
    )


class TechComparison(BaseModel):
    """Technology comparison analysis output schema."""

    primary_tech: str = Field(description="Primary technology/framework identified in the content")
    alternatives: list[str] = Field(
        description="2-3 relevant alternative technologies to compare against",
        min_length=1,
        max_length=5,
    )
    comparison: dict[str, TechComparisonEntry] = Field(
        description=(
            "REQUIRED: Comparison table with pros, cons, and use_cases for each technology. "
            "MUST include an entry for primary_tech and each alternative. "
            "Each entry contains three lists: pros (advantages), "
            "cons (disadvantages), and use_cases (recommended scenarios)."
        )
    )
    recommendation: str = Field(description="Recommendation based on the comparison analysis")
