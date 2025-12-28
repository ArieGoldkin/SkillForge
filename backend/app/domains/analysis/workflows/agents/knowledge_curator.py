"""Knowledge Curator Agent for connecting content to user's knowledge graph.

This is a Tier 3 Research agent that:
1. Uses proactive memory (prior_memory from state) to find related content
2. Identifies connections between current content and user's existing analyses
3. Suggests prerequisites and next steps based on knowledge graph
4. Does NOT use external tools - only memory-based analysis

The agent uses memory injection (prior_memory field) which is proactively
populated by the router before agent execution.

Issue #500: Tier 3 Research agent with proactive memory injection.
Issue #418: Uses PromptManager for Langfuse prompt fetching with multi-level caching.
"""

from collections.abc import Sequence

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.domains.analysis.schemas.agents.knowledge_curator import KnowledgeCuratorOutput
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
PROMPT_NAME = "analysis-agent-knowledge-curator"


async def run_knowledge_curator(  # noqa: PLR0913 - All parameters required for agent execution
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,  # noqa: ARG001 - Standard interface, unused (memory-only)
) -> dict[str, object]:
    """Run knowledge curator agent to connect content to user's knowledge graph.

    This is a Tier 3 Research agent that uses proactive memory injection
    (prior_memory field in state) to find connections to existing analyses.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence
        state: Current workflow state (includes prior_memory for Tier 3)
        tools: Optional MCP tools (NOT used by this agent - memory only)

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

    # Combine memory contexts for comprehensive knowledge graph analysis
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
        agent_name="knowledge_curator",
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
    )

    # DEBUG: Log threshold calculation and memory availability
    logger.info(
        "threshold_calculated_knowledge_curator",
        analysis_id=analysis_id,
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
        expectation=expectation,
        calculated_threshold=specificity_threshold,
        has_prior_memory=bool(prior_memory),
        memory_length=len(prior_memory) if prior_memory else 0,
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
    # Note: Tier 3 agents do NOT use tools - only memory context
    agent = await create_agent_with_optional_few_shot(
        agent_type="knowledge_curator",
        content=content,
        system_prompt=full_prompt,
        response_schema=KnowledgeCuratorOutput,
        analysis_id=analysis_id,
        session=session,
        tools=None,  # No tools for memory-based agent
    )

    # Issue #564: Attach Langfuse prompt client to agent for observation linkage
    if langfuse_prompt_client:
        agent = agent.with_config(metadata={"langfuse_prompt_client": langfuse_prompt_client})

    # Log memory usage - Tier 3 agents should have memory context
    if full_memory_context:
        logger.info(
            "knowledge_curator_using_memory",
            analysis_id=str(analysis_id),
            memory_length=len(full_memory_context),
            has_prior_memory=bool(prior_memory),
            has_proactive_context=bool(proactive_context),
        )
    else:
        logger.warning(
            "knowledge_curator_without_memory",
            analysis_id=str(analysis_id),
            message="Tier 3 agent running without memory context - connections will be limited",
        )

    # Run agent with tracking and persistence
    # Issue #500: Pass memory context (already combined above)
    # Issue #299-304: Pass content-aware specificity threshold
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="knowledge_curator",
        session=session,
        proactive_context=full_memory_context,
        specificity_threshold=specificity_threshold,
    )
