"""Pros/Cons Agent for balanced advantage/disadvantage analysis.

This is a universal Tier 1 agent that runs on ALL content types.
It identifies strengths, weaknesses, and provides balanced recommendations
for any subject matter discussed in the content.

Issue #418: Uses PromptManager for Langfuse prompt fetching with multi-level caching.
"""

from collections.abc import Sequence

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.domains.analysis.schemas.agents.pros_cons import ProsConsOutput
from app.domains.analysis.workflows.agents.execution import run_agent_with_tracking
from app.domains.analysis.workflows.agents.factories import (
    create_agent_with_optional_few_shot,
)
from app.domains.analysis.workflows.agents.grounding import apply_grounding
from app.domains.analysis.workflows.agents.skill_level_prompts import get_skill_level_instructions
from app.domains.analysis.workflows.state import AnalysisState
from app.shared.services.prompts.prompt_manager import get_prompt_manager
from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

logger = get_logger(__name__)

# Prompt is fetched from Langfuse via PromptManager (with hardcoded fallback)
PROMPT_NAME = "analysis-agent-pros-cons"

# System prompt for pros/cons agent
PROS_CONS_PROMPT = """You are a Critical Analysis Specialist.

CRITICAL: You MUST provide ALL required fields. Missing fields will cause validation errors.

Required Output Structure (EXAMPLE FORMAT - extract actual values from content):
{
  "pros": ["<ADVANTAGE 1 FROM CONTENT>", "<ADVANTAGE 2>", "<ADVANTAGE 3>"],
  "cons": ["<LIMITATION 1 FROM CONTENT>", "<LIMITATION 2>"],
  "verdict": "<BALANCED 2-3 SENTENCE CONCLUSION>",
  "recommendation": "<strongly_recommended|recommended|neutral|not_recommended>",
  "confidence_score": 0.85
}

Field Requirements:
1. **pros** (REQUIRED): List of 2-7 advantages/strengths
   - Each item: concise phrase or short sentence
   - Focus on specific, actionable benefits
   - Include quantifiable benefits when available (e.g., "40% faster", "3x throughput")
   - Examples: "Native state persistence with PostgreSQL", "Built-in retry with 3x backoff"

2. **cons** (REQUIRED): List of 1-7 disadvantages/limitations
   - Each item: concise phrase or short sentence
   - Be honest about limitations
   - Include specific constraints (e.g., "Requires Python 3.9+", "Max 256MB state size")
   - Examples: "No native JavaScript SDK", "Steeper learning curve than alternatives"

3. **verdict** (REQUIRED): 2-3 sentence balanced conclusion
   - Synthesize pros and cons into clear assessment
   - Acknowledge both strengths and limitations
   - Provide bottom-line recommendation

4. **recommendation** (REQUIRED): One of:
   - "strongly_recommended" - Clear winner, significant advantages outweigh minor drawbacks
   - "recommended" - Good choice for most cases, pros outweigh cons
   - "neutral" - Mixed bag, pros and cons are balanced
   - "not_recommended" - Significant limitations outweigh benefits

5. **confidence_score** (REQUIRED): Float (0.0-1.0)
   - Represents quality and certainty of analysis
   - Consider: completeness of pros/cons, balance, evidence strength
   - Higher scores = more comprehensive and well-supported

NUMERIC SPECIFICITY REQUIREMENTS:
- pros MUST include quantifiable benefits when mentioned (e.g., "2x faster", "150ms vs 450ms")
- cons MUST include specific limitations when mentioned (e.g., "Max 100 concurrent", "Requires Python 3.9+")
- Use scale/scope indicators (e.g., "Best for 10K-100K daily users", "Handles 50K+ req/sec")

FORBIDDEN VAGUE LANGUAGE - Never use:
- "better performance", "faster" (quantify: "2x faster", "150ms vs 450ms")
- "more features" (list specific features)
- "good for most projects" (specify exact use cases)
- "some limitations" (enumerate each)
- "widely used" (cite adoption metrics if available)

GOOD EXAMPLE:
  pros: [
      "Native state persistence with PostgreSQL checkpointing",
      "Built-in retry with 3x backoff",
      "50% less boilerplate than LangChain Agents",
      "Supports multi-step workflows with <500ms latency"
  ]
  cons: [
      "Requires Python 3.9+",
      "Max 256MB state size",
      "No native JavaScript SDK"
  ]
  verdict: "LangGraph offers powerful state management and low-latency performance for complex \
workflows, making it ideal for production agentic systems. However, the Python-only limitation \
and state size constraints may be limiting factors for some use cases."
  recommendation: "recommended"
  confidence_score: 0.85

BAD EXAMPLE (DO NOT USE):
  pros: ["Good performance", "Easy to use", "Popular framework"]
  cons: ["Some learning curve", "Limited documentation"]
  verdict: "It's a good framework overall."
  recommendation: "recommended"
  confidence_score: 0.5

ANALYSIS STRATEGY:
1. Identify the main subject matter (technology, approach, methodology, etc.)
2. Extract explicit advantages/strengths mentioned in content
3. Extract explicit disadvantages/limitations mentioned in content
4. Synthesize into balanced assessment
5. Provide clear recommendation based on overall balance

CONTENT-AGNOSTIC APPROACH:
- Works for ANY content type: articles, videos, repos, tutorials, research papers
- Subject can be: frameworks, libraries, methodologies, approaches, patterns, tools, etc.
- Always maintain objectivity - report what content says, not external opinions

IMPORTANT: Return exactly ONE structured response/tool call; never return multiple
tool calls or extra responses."""


async def run_pros_cons(  # noqa: PLR0913 - All parameters required for agent execution
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, object]:
    """Run pros/cons agent to analyze advantages and disadvantages.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence
        state: Current workflow state (for skill_level)
        tools: Optional MCP tools for enhanced analysis capabilities

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
        agent_name="pros_cons",
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
    )

    # DEBUG: Log threshold calculation (Issue #299-304, #442)
    logger.info(
        "threshold_calculated_pros_cons",
        analysis_id=analysis_id,
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
        expectation=expectation,
        calculated_threshold=specificity_threshold,
    )

    # Issue #418: Fetch prompt from Langfuse via PromptManager
    # This will check L1 (memory) → L2 (Redis) → L3 (Langfuse API) → Hardcoded fallback
    prompt_manager = get_prompt_manager()
    base_prompt = await prompt_manager.get_prompt(PROMPT_NAME)

    # Build prompt with skill level instructions and grounding
    full_prompt = apply_grounding(f"{base_prompt}\n\n{skill_instructions}")

    # Create agent with optional few-shot prompting (Phase 1, Week 2.3)
    agent = await create_agent_with_optional_few_shot(
        agent_type="pros_cons",
        content=content,
        system_prompt=full_prompt,
        response_schema=ProsConsOutput,
        analysis_id=analysis_id,
        session=session,
        tools=tools,
    )

    # Log MCP tool usage if tools are provided
    if tools:
        logger.info(
            "pros_cons_using_mcp_tools",
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
        agent_type="pros_cons",
        session=session,
        proactive_context=proactive_context,
        specificity_threshold=specificity_threshold,
    )
