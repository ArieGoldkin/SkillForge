"""Performance Analyst Agent for performance evaluation.

This agent evaluates performance trade-offs, identifies bottlenecks,
and provides optimization recommendations for latency, memory, throughput, and scaling.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import AnalysisID
from app.workflows.agents.base import create_structured_agent
from app.workflows.agents.execution import run_agent_with_tracking
from app.workflows.agents.grounding import apply_grounding
from app.workflows.agents.schemas.performance_analyst import PerformanceAnalysis
from app.workflows.agents.skill_level_prompts import get_skill_level_instructions
from app.workflows.state import AnalysisState

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

NUMERIC SPECIFICITY REQUIREMENTS:
- current_value MUST include a number with unit (e.g., "650ms", "2000 req/sec", "4GB")
- target_value MUST include a number with unit (e.g., "<200ms", ">8000 req/sec", "<=2GB")
- bottlenecks MUST include specific numbers (e.g., "N+1 queries causing 23 queries/request")
- optimization_opportunities MUST include expected improvement (e.g., "reduce by 70%", "save 450ms")
- scaling_considerations MUST include specific numbers (e.g., "3-5 instances", "2 vCPU, 4GB RAM")

FORBIDDEN VAGUE LANGUAGE - Never use:
- "appropriate", "suitable", "reasonable", "adequate", "proper"
- "fast", "slow", "high", "low" without numbers (e.g., say "450ms" not "slow")
- "improve", "optimize", "enhance" without measurable targets
- "several", "many", "few", "some", "various"
- "might", "could", "should" for recommendations (be definitive)

GOOD EXAMPLE:
  current_value: "650ms p99 latency"
  target_value: "<200ms p99 latency"
  bottleneck: "Database queries consume 450ms/request due to N+1 problem (23 queries/request)"
  opportunity: "Add Redis cache with 300s TTL to achieve 90% hit ratio, reducing latency by 70%"

BAD EXAMPLE (DO NOT USE):
  current_value: "slow"
  target_value: "fast"
  bottleneck: "Database queries are slow"
  opportunity: "Implement appropriate caching for better performance"

FRAMEWORK-SPECIFIC CHECKS (Apply if detected):
- FastAPI/Starlette: Check for blocking code in async routes, Pydantic validation overhead.
- Django: Check for N+1 queries (select_related/prefetch_related), middleware overhead.
- React/Next.js: Check for excessive re-renders (useMemo/useCallback), large bundle sizes.
- Node.js: Check for event loop blocking, memory leaks.
- Databases: Check for missing indexes, inefficient joins, connection pooling.

Provide actionable, measurable recommendations."""


async def run_performance_analyst(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
) -> dict[str, object]:
    """Run performance analyst agent.

    Args:
        content: Analyzed content
        content_type: Type of content
        analysis_id: Analysis ID
        session: Database session
        state: Current workflow state (for skill_level)

    Returns:
        Agent findings dict

    """
    # Get skill level and inject instructions
    skill_level = state.get("skill_level", "intermediate")
    skill_instructions = get_skill_level_instructions(skill_level)

    # Issue #300: Get proactive context from state
    proactive_context = state.get("proactive_context", "")

    # Build prompt with skill level instructions
    full_prompt = apply_grounding(f"{PERFORMANCE_ANALYST_PROMPT}\n\n{skill_instructions}")

    # Create agent
    agent = create_structured_agent(
        system_prompt=full_prompt,
        response_schema=PerformanceAnalysis,
    )

    # Run agent with tracking and persistence
    # Issue #300: Pass proactive context for memory-enhanced analysis
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="performance_analyst",
        session=session,
        proactive_context=proactive_context,
    )
