"""Performance Analyst Agent for performance evaluation.

This agent evaluates performance trade-offs, identifies bottlenecks,
and provides optimization recommendations for latency, memory, throughput, and scaling.

Issue #418: Uses PromptManager for Langfuse prompt fetching with multi-level caching.
"""

from collections.abc import Sequence

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.domains.analysis.schemas.agents.performance_analyst import PerformanceAnalysis
from app.domains.analysis.workflows.agents.base import create_structured_agent
from app.domains.analysis.workflows.agents.execution import run_agent_with_tracking
from app.domains.analysis.workflows.agents.grounding import apply_grounding
from app.domains.analysis.workflows.agents.skill_level_prompts import get_skill_level_instructions
from app.domains.analysis.workflows.state import AnalysisState
from app.shared.services.prompts.prompt_manager import get_prompt_manager
from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

logger = get_logger(__name__)

# Prompt is fetched from Langfuse via PromptManager (with hardcoded fallback)
PROMPT_NAME = "analysis-agent-performance-analyst"

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


async def run_performance_analyst(  # noqa: PLR0913 - All parameters required for agent execution
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, object]:
    """Run performance analyst agent.

    Args:
        content: Analyzed content
        content_type: Type of content
        analysis_id: Analysis ID
        session: Database session
        state: Current workflow state (for skill_level)
        tools: Optional MCP tools for enhanced performance analysis

    Returns:
        Agent findings dict

    """
    # Get skill level and inject instructions
    skill_level = state.get("skill_level", "intermediate")
    skill_instructions = get_skill_level_instructions(skill_level)

    # Issue #300: Get proactive context from state
    proactive_context = state.get("proactive_context", "")

    # Issue #299-304: Get content-aware specificity threshold
    # Read from flat field injected by build_scoped_context()
    expectation = state.get("agent_expectation")
    specificity_threshold = get_threshold_for_expectation(
        str(expectation) if expectation is not None else None
    )

    # Issue #418: Fetch prompt from Langfuse via PromptManager
    # This will check L1 (memory) → L2 (Redis) → L3 (Langfuse API) → Hardcoded fallback
    prompt_manager = get_prompt_manager()
    base_prompt = await prompt_manager.get_prompt(PROMPT_NAME)

    # Build prompt with skill level instructions
    full_prompt = apply_grounding(f"{base_prompt}\n\n{skill_instructions}")

    # Create agent with structured output
    # Handles both tool-enabled and non-tool variants
    agent = create_structured_agent(
        system_prompt=full_prompt,
        response_schema=PerformanceAnalysis,
        tools=tools,
    )

    if tools:
        logger.info(
            "performance_analyst_using_mcp_tools",
            analysis_id=str(analysis_id),
            tool_count=len(tools),
            tool_names=[t.name for t in tools],
        )

    # Run agent with tracking and persistence
    # Issue #300: Pass proactive context for memory-enhanced analysis
    # Issue #299-304: Pass content-aware specificity threshold
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="performance_analyst",
        session=session,
        proactive_context=proactive_context,
        specificity_threshold=specificity_threshold,
    )
