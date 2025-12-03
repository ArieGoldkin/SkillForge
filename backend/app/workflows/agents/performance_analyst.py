"""Performance Analyst Agent for performance evaluation.

This agent evaluates performance trade-offs, identifies bottlenecks,
and provides optimization recommendations for latency, memory, throughput, and scaling.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import AnalysisID
from app.workflows.agents.base import create_structured_agent
from app.workflows.agents.execution import run_agent_with_tracking
from app.workflows.agents.schemas.performance_analyst import PerformanceAnalysis

# System prompt for performance analyst agent
PERFORMANCE_ANALYST_PROMPT = """You are a Performance Analysis Specialist. Your task is to:
1. Evaluate performance characteristics (latency, throughput, memory, CPU)
2. Identify performance bottlenecks and constraints
3. Recommend optimization opportunities
4. Provide scaling considerations (horizontal vs vertical, caching strategies)
5. Assess performance trade-offs and implications

Focus on:
- Response time and latency metrics
- Throughput and concurrency limits
- Memory usage and optimization
- Database query performance
- Caching strategies (CDN, Redis, in-memory)
- Horizontal vs vertical scaling approaches
- Load balancing considerations
- Performance monitoring and profiling

CRITICAL: You MUST include:
- performance_metrics: List of key metrics with current/target values
- bottlenecks: List of identified performance bottlenecks
- optimization_opportunities: List of optimization recommendations
- scaling_considerations: Scaling strategy and approach
- recommendation: Overall performance recommendation
- confidence_score: Float (0.0-1.0) representing your confidence in the quality and certainty
  of this performance analysis. Consider: accuracy of metric identification, correctness of
  bottleneck analysis, completeness of optimization opportunities, and confidence in scaling
  recommendations.

Provide actionable, measurable recommendations."""


async def run_performance_analyst(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
) -> dict[str, object]:
    """Run performance analyst agent to evaluate performance characteristics.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence

    Returns:
        Dictionary with agent_type, findings, processing_time_ms

    Raises:
        Exception: If agent execution fails

    """
    # Create agent with structured output
    agent = create_structured_agent(
        system_prompt=PERFORMANCE_ANALYST_PROMPT,
        response_schema=PerformanceAnalysis,
    )

    # Run agent with tracking and persistence
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="performance_analyst",
        session=session,
    )
