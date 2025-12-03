"""Performance analysis agent schemas."""

from pydantic import BaseModel, Field


class PerformanceMetric(BaseModel):
    """Performance metric assessment."""

    metric_name: str = Field(
        description="Metric name (e.g., 'latency', 'throughput', 'memory_usage', 'cpu_usage')"
    )
    current_value: str = Field(description="Current or expected value for this metric")
    target_value: str = Field(description="Recommended target value for optimal performance")
    notes: str = Field(
        description=("Single sentence providing analysis notes and context for this metric.")
    )


class PerformanceAnalysis(BaseModel):
    """Performance analysis output schema."""

    performance_metrics: list[PerformanceMetric] = Field(
        description="Key performance metrics and their assessments",
        default_factory=list,
    )
    bottlenecks: list[str] = Field(
        description=(
            "Identified performance bottlenecks and constraints. "
            "Each item should be a single sentence describing one bottleneck."
        ),
        default_factory=list,
    )
    optimization_opportunities: list[str] = Field(
        description=(
            "Optimization recommendations and opportunities. "
            "Each item should be a single actionable sentence starting with a verb."
        ),
        default_factory=list,
    )
    scaling_considerations: str = Field(
        description=(
            "Scaling strategy and considerations (horizontal vs vertical, caching, etc.). "
            "Write as 2-3 cohesive sentences covering the recommended approach."
        )
    )
    recommendation: str = Field(
        description=(
            "Overall performance recommendation. "
            "Write as 2-3 cohesive sentences summarizing priority optimizations."
        )
    )
    confidence_score: float = Field(
        description=(
            "Confidence score (0.0-1.0) representing both the quality and certainty "
            "of this performance analysis. Consider: accuracy of metric identification, "
            "correctness of bottleneck analysis, completeness of optimization opportunities, "
            "and confidence in scaling recommendations. Higher scores indicate more thorough "
            "and accurate performance assessments."
        ),
        ge=0.0,
        le=1.0,
    )
