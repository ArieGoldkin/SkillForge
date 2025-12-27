"""Tech Comparator Agent for technology comparison analysis.

This agent identifies the primary technology discussed in content and compares
it to relevant alternatives, providing pros, cons, use cases, and recommendations.

Issue #418: Uses PromptManager for Langfuse prompt fetching with multi-level caching.
"""

from collections.abc import Sequence

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.domains.analysis.schemas.agents.tech_comparator import TechComparison
from app.domains.analysis.workflows.agents.execution import run_agent_with_tracking
from app.domains.analysis.workflows.agents.factories import (
    create_tech_comparator_agent_with_few_shot,
)
from app.domains.analysis.workflows.agents.grounding import apply_grounding
from app.domains.analysis.workflows.agents.skill_level_prompts import get_skill_level_instructions
from app.domains.analysis.workflows.state import AnalysisState
from app.shared.services.prompts.prompt_manager import get_prompt_manager
from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

logger = get_logger(__name__)

# Prompt is fetched from Langfuse via PromptManager (with hardcoded fallback)
PROMPT_NAME = "analysis-agent-tech-comparator"

# System prompt for tech comparator agent
TECH_COMPARATOR_PROMPT = """You are a Technical Comparison Specialist.

CRITICAL: You MUST provide ALL required fields. Missing fields will cause validation errors.

Required Output Structure (EXAMPLE FORMAT - extract actual values from content):
{
  "primary_tech": "<PRIMARY TECH FROM CONTENT>",
  "alternatives": ["<ALT 1 FROM CONTENT>", "<ALT 2>", "<ALT 3>"],
  "comparison": {
    "<PRIMARY TECH>": {
      "pros": ["<ACTUAL PROS FROM CONTENT>"],
      "cons": ["<ACTUAL CONS FROM CONTENT>"],
      "use_cases": ["<ACTUAL USE CASES FROM CONTENT>"]
    }
  },
  "recommendation": "<RECOMMENDATION BASED ON CONTENT>"
}

Field Requirements:
1. **primary_tech** (REQUIRED): String - primary technology name with version (
    e.g., "LangGraph 0.6.7"
)
2. **alternatives** (REQUIRED): List of 2-3 alternative technology names with versions
3. **comparison** (REQUIRED): Dictionary mapping tech names to comparison entries
   - MUST include entry for primary_tech
   - MUST include entry for each alternative
   - Each entry: {"pros": [], "cons": [], "use_cases": []}
4. **recommendation** (REQUIRED): String with clear recommendation
5. **confidence_score** (REQUIRED): Float (0.0-1.0) - confidence in quality and certainty
   of this comparison. Consider: accuracy of identification, completeness of analysis,
   relevance of alternatives, and confidence in recommendation.

NUMERIC SPECIFICITY REQUIREMENTS:
- primary_tech MUST include version (e.g., "LangGraph 0.6.7", "React 18.2.0")
- alternatives MUST include versions (e.g., "LangChain Agents 0.1.0")
- pros MUST include quantifiable benefits (e.g., "40% faster cold start", "3x better throughput")
- cons MUST include specific limitations (
    e.g., "Max 100 concurrent executions", "No TypeScript support"
)
- use_cases MUST include scale (e.g., "Best for 10K-100K daily users", "Handles 50K+ req/sec")

FORBIDDEN VAGUE LANGUAGE - Never use:
- "better performance", "faster" (quantify: "2x faster", "150ms vs 450ms")
- "more features", "richer ecosystem" (list specific features)
- "good for most projects", "suitable for many use cases" (specify exact use cases)
- "some limitations", "a few drawbacks" (enumerate each)
- "popular choice", "widely used" (cite adoption metrics)

GOOD EXAMPLE:
  primary_tech: "LangGraph 0.6.7"
  pros: [
      "Native state persistence with PostgreSQL checkpointing",
      "Built-in retry with 3x backoff",
      "50% less boilerplate than LangChain Agents",
  ]
  cons: ["Requires Python 3.9+", "Max 256MB state size", "No native JavaScript SDK"]
  use_cases: [
      "Multi-step agentic workflows processing 1K-50K tasks/day",
      "RAG pipelines with <500ms latency requirements",
  ]

BAD EXAMPLE (DO NOT USE):
  primary_tech: "LangGraph"
  pros: ["Good performance", "Easy to use", "Popular framework"]
  cons: ["Some learning curve", "Limited documentation"]
  use_cases: ["Various AI applications", "Building agents"]

IMPORTANT: The "comparison" field must include entries for primary_tech AND all alternatives.
Do not omit any required fields. Return exactly ONE structured response/tool call; never
return multiple tool calls or extra responses.

COMPARISON STRATEGY:
- If multiple frameworks are detected (e.g., Django vs FastAPI), treat them as the primary subjects.
- Focus on "Build vs Buy" if applicable.
- Highlight "Standard vs Modern" approaches (e.g., Redux vs Zustand)."""


async def run_tech_comparator(  # noqa: PLR0913 - All parameters required for agent execution
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, object]:
    """Run tech comparator agent to analyze and compare technologies.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence
        state: Current workflow state (for skill_level)
        tools: Optional MCP tools for enhanced technology comparison

    Returns:
        Dictionary with agent_type, findings, processing_time_ms

    Raises:
        Exception: If agent execution fails

    """
    # Get skill level and inject instructions
    skill_level = state.get("skill_level", "intermediate")
    skill_instructions = get_skill_level_instructions(skill_level)

    # Issue #300: Get proactive context from state
    proactive_context = state.get("proactive_context", "")

    # Issue #299-304: Get content-aware specificity threshold
    # Read from flat field injected by build_scoped_context()
    expectation = state.get("agent_expectation")

    # Issue #299-304, #442: Get content signals for comparison/research-aware thresholds
    content_signals_dict: dict[str, object] = state.get("content_signals", {})
    has_comparisons = bool(content_signals_dict.get("has_comparisons", False))
    # Issue #442: Detect research/conceptual content for very low thresholds
    detected_genre = str(content_signals_dict.get("detected_genre", "unknown"))
    is_research = detected_genre == "research"
    is_conceptual = bool(content_signals_dict.get("has_conceptual_only", False))

    specificity_threshold = get_threshold_for_expectation(
        expectation_str=str(expectation) if expectation is not None else None,
        agent_name="tech_comparator",
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
    )

    # DEBUG: Log threshold calculation (Issue #299-304, #442)
    logger.info(
        "threshold_calculated_tech_comparator",
        analysis_id=analysis_id,
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
        expectation=expectation,
        calculated_threshold=specificity_threshold,
    )

    # Issue #418: Fetch prompt from Langfuse via PromptManager
    # This will check L1 (memory) → L2 (Redis) → L3 (Langfuse API) → Hardcoded fallback
    # Issue #564: Use get_prompt_with_langfuse_client() for prompt observation linkage
    prompt_manager = get_prompt_manager()
    base_prompt, langfuse_prompt_client = await prompt_manager.get_prompt_with_langfuse_client(
        PROMPT_NAME
    )

    # Build prompt with skill level instructions and grounding
    full_prompt = apply_grounding(f"{base_prompt}\n\n{skill_instructions}")

    # Create agent with optional few-shot prompting (Phase 1, Week 2.3)
    # Handles both tool-enabled and non-tool variants
    agent = await create_tech_comparator_agent_with_few_shot(
        content=content,
        system_prompt=full_prompt,
        response_schema=TechComparison,
        analysis_id=analysis_id,
        session=session,
        tools=tools,
    )

    # Issue #564: Attach Langfuse prompt client to agent for observation linkage
    if langfuse_prompt_client:
        agent = agent.with_config(metadata={"langfuse_prompt_client": langfuse_prompt_client})

    if tools:
        logger.info(
            "tech_comparator_using_mcp_tools",
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
        agent_type="tech_comparator",
        session=session,
        proactive_context=proactive_context,
        specificity_threshold=specificity_threshold,
    )
