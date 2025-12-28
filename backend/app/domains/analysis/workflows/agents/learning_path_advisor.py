"""Learning Path Advisor Agent for creating personalized learning sequences.

This is a Tier 3 Research agent that:
1. Analyzes current content complexity and learning objectives
2. Compares content requirements to user's existing knowledge (from memory)
3. Identifies skill gaps and prerequisite knowledge
4. Creates a personalized, sequential learning path
5. Estimates time commitments based on user's skill level

This agent uses memory (prior_memory) for personalization - it knows what the user
has already learned from previous analyses and adapts recommendations accordingly.

Issue #418: Uses PromptManager for Langfuse prompt fetching with multi-level caching.
Issue #500: Tier 3 Research agent with memory integration for personalized learning paths.
"""

from collections.abc import Sequence

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.domains.analysis.schemas.agents.learning_path_advisor import (
    LearningPathAdvisorOutput,
)
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
PROMPT_NAME = "analysis-agent-learning-path-advisor"


async def run_learning_path_advisor(  # noqa: PLR0913 - All parameters required for agent execution
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, object]:
    """Run learning path advisor agent to create personalized learning sequences.

    This is a Tier 3 Research agent that uses memory (prior_memory) to create
    personalized learning paths based on user's existing knowledge and skill level.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence
        state: Current workflow state (contains skill_level and prior_memory)
        tools: Optional MCP tools (Tier 3 agents typically don't use external tools)

    Returns:
        Dictionary with agent_type, findings, processing_time_ms

    Raises:
        Exception: If agent execution fails

    """
    # Get skill level and inject instructions
    skill_level = state.get("skill_level", "intermediate")
    skill_instructions = get_skill_level_instructions(skill_level)

    # Issue #500: Get prior memory from state (injected by agent_router for memory-enabled agents)
    prior_memory = state.get("prior_memory", "")

    # Log memory availability for debugging
    if prior_memory:
        logger.info(
            "learning_path_advisor_using_memory",
            analysis_id=str(analysis_id),
            memory_length=len(prior_memory),
            has_memory=True,
        )
    else:
        logger.info(
            "learning_path_advisor_no_memory",
            analysis_id=str(analysis_id),
            has_memory=False,
            message="No prior learning history - path will be based on skill_level only",
        )

    # Issue #300: Get proactive context from state (general memory context)
    proactive_context = state.get("proactive_context", "")

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
        agent_name="learning_path_advisor",
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
    )

    # DEBUG: Log threshold calculation
    logger.info(
        "threshold_calculated_learning_path_advisor",
        analysis_id=analysis_id,
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
        expectation=expectation,
        calculated_threshold=specificity_threshold,
    )

    # Issue #418: Fetch prompt from Langfuse via PromptManager
    # Issue #564: Use get_prompt_with_langfuse_client() for prompt observation linkage
    prompt_manager = get_prompt_manager()
    base_prompt, langfuse_prompt_client = await prompt_manager.get_prompt_with_langfuse_client(
        PROMPT_NAME
    )

    # Build prompt with skill level instructions, grounding, and memory context
    prompt_with_instructions = f"{base_prompt}\n\n{skill_instructions}"

    # If we have prior memory, inject it into the prompt
    if prior_memory:
        memory_section = f"""

PRIOR MEMORY - User's Learning History:
{prior_memory}

Use this memory to personalize the learning path. Reference specific analyses they've
completed, skip concepts they already know, and adjust time estimates based on their
demonstrated expertise. Make connections between this content and their prior learning.
"""
        prompt_with_instructions = f"{prompt_with_instructions}\n{memory_section}"

    # Apply grounding to ensure factual accuracy
    full_prompt = apply_grounding(prompt_with_instructions)

    # Create agent with optional few-shot prompting
    # Tier 3 agents don't typically use tools - they use memory and LLM reasoning
    agent = await create_agent_with_optional_few_shot(
        agent_type="learning_path_advisor",
        content=content,
        system_prompt=full_prompt,
        response_schema=LearningPathAdvisorOutput,
        analysis_id=analysis_id,
        session=session,
        tools=tools,  # Usually None for Tier 3 memory-based agents
    )

    # Issue #564: Attach Langfuse prompt client to agent for observation linkage
    if langfuse_prompt_client:
        agent = agent.with_config(metadata={"langfuse_prompt_client": langfuse_prompt_client})

    if tools:
        logger.info(
            "learning_path_advisor_using_tools",
            analysis_id=str(analysis_id),
            tool_count=len(tools),
            tool_names=[t.name for t in tools],
            message="Tier 3 agent unexpectedly has tools - usually memory-only",
        )

    # Run agent with tracking and persistence
    # Issue #300: Pass proactive context for general memory-enhanced analysis
    # Issue #299-304: Pass content-aware specificity threshold
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="learning_path_advisor",
        session=session,
        proactive_context=proactive_context,
        specificity_threshold=specificity_threshold,
    )
