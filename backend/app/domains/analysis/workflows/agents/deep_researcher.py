"""Deep Researcher Agent for extended web research with comprehensive search.

This is a Tier 3 Research agent that:
1. Uses proactive memory (prior_memory from state) to build on existing analyses
2. Executes 10+ comprehensive Tavily searches for external research
3. Synthesizes findings across multiple sources to provide depth
4. Identifies knowledge gaps and recommends further reading

The agent combines memory injection (prior_memory) with tool-calling
(tavily_search) to provide the most comprehensive research capabilities.

Issue #500: Tier 3 Research agent with both memory and tools.
Issue #418: Uses PromptManager for Langfuse prompt fetching with multi-level caching.
"""

from collections.abc import Sequence

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.domains.analysis.schemas.agents.deep_researcher import DeepResearcherOutput
from app.domains.analysis.workflows.agents.execution import run_agent_with_tracking
from app.domains.analysis.workflows.agents.factories import (
    create_agent_with_optional_few_shot,
)
from app.domains.analysis.workflows.agents.grounding import apply_grounding
from app.domains.analysis.workflows.agents.skill_level_prompts import (
    get_skill_level_instructions,
)
from app.domains.analysis.workflows.state import AnalysisState
from app.shared.services.prompts.prompt_manager import get_prompt_manager
from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

logger = get_logger(__name__)

# Prompt is fetched from Langfuse via PromptManager (with hardcoded fallback)
PROMPT_NAME = "analysis-agent-deep-researcher"

# Query budget for comprehensive research
DEEP_RESEARCH_QUERY_BUDGET = 10


async def run_deep_researcher(  # noqa: PLR0913 - All parameters required for agent execution
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, object]:
    """Run deep researcher agent for comprehensive external research.

    This is a Tier 3 Research agent that combines proactive memory injection
    with reactive tool-calling (Tavily search) for maximum research depth.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence
        state: Current workflow state (includes prior_memory and skill_level)
        tools: Optional MCP tools (should include tavily_search for Tier 3)

    Returns:
        Dictionary with agent_type, findings, processing_time_ms

    Raises:
        Exception: If agent execution fails

    """
    # Get skill level and inject instructions
    skill_level = state.get("skill_level", "intermediate")
    skill_instructions = get_skill_level_instructions(skill_level)

    # Issue #500: Get proactive memory context from state
    # Router has already injected prior_memory for Tier 3 agents
    prior_memory = state.get("prior_memory", "")

    # Issue #300: Get proactive context from state (general context)
    proactive_context = state.get("proactive_context", "")

    # Combine memory contexts for comprehensive research-aware analysis
    # prior_memory = specific relevant analyses
    # proactive_context = general user preferences, goals, etc.
    full_memory_context = f"{prior_memory}\n\n{proactive_context}".strip()

    # Issue #299-304: Get content-aware specificity threshold
    expectation = state.get("agent_expectation")

    # Issue #299-304, #442: Get content signals for research-aware thresholds
    content_signals_dict: dict[str, object] = state.get("content_signals", {})
    has_comparisons = bool(content_signals_dict.get("has_comparisons", False))
    detected_genre = str(content_signals_dict.get("detected_genre", "unknown"))
    is_research = detected_genre == "research"
    is_conceptual = bool(content_signals_dict.get("has_conceptual_only", False))

    specificity_threshold = get_threshold_for_expectation(
        expectation_str=str(expectation) if expectation is not None else None,
        agent_name="deep_researcher",
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
    )

    # DEBUG: Log threshold calculation and memory/tool availability
    logger.info(
        "threshold_calculated_deep_researcher",
        analysis_id=analysis_id,
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
        expectation=expectation,
        calculated_threshold=specificity_threshold,
        has_prior_memory=bool(prior_memory),
        memory_length=len(prior_memory) if prior_memory else 0,
        has_tools=bool(tools),
        tool_count=len(tools) if tools else 0,
        query_budget=DEEP_RESEARCH_QUERY_BUDGET,
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

    # Create agent with optional few-shot prompting
    # Note: Tier 3 deep_researcher uses BOTH memory AND tools
    agent = await create_agent_with_optional_few_shot(
        agent_type="deep_researcher",
        content=content,
        system_prompt=full_prompt,
        response_schema=DeepResearcherOutput,
        analysis_id=analysis_id,
        session=session,
        tools=tools,
    )

    # Issue #564: Attach Langfuse prompt client to agent for observation linkage
    if langfuse_prompt_client:
        agent = agent.with_config(metadata={"langfuse_prompt_client": langfuse_prompt_client})

    # Log memory and tool usage - Tier 3 deep_researcher should have both
    if full_memory_context:
        logger.info(
            "deep_researcher_using_memory",
            analysis_id=str(analysis_id),
            memory_length=len(full_memory_context),
            has_prior_memory=bool(prior_memory),
            has_proactive_context=bool(proactive_context),
        )
    else:
        logger.warning(
            "deep_researcher_without_memory",
            analysis_id=str(analysis_id),
            message="Tier 3 agent running without memory context - research won't build on prior knowledge",
        )

    if tools:
        logger.info(
            "deep_researcher_using_tools",
            analysis_id=str(analysis_id),
            tool_count=len(tools),
            tool_names=[t.name for t in tools],
            query_budget=DEEP_RESEARCH_QUERY_BUDGET,
        )
    else:
        logger.warning(
            "deep_researcher_without_tools",
            analysis_id=str(analysis_id),
            message="Tier 3 agent expected tools but none provided - research will be limited",
        )

    # Run agent with tracking and persistence
    # Issue #500: Pass memory context for building on prior knowledge
    # Issue #299-304: Pass content-aware specificity threshold
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="deep_researcher",
        session=session,
        proactive_context=full_memory_context,
        specificity_threshold=specificity_threshold,
    )
