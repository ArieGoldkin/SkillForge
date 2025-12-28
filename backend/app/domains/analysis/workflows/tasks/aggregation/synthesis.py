"""LLM synthesis functions for aggregating agent findings.

This module handles LLM-based synthesis of agent findings into
coherent aggregated insights.

Issue #299-304: Implements LangGraph-native resilience patterns:
- Model fallback chain via LangChain's with_fallbacks()
- Heartbeat events during long LLM synthesis
- Graceful degradation instead of hanging forever

Issue #414: Migrated SYNTHESIS_SYSTEM_PROMPT to Jinja2 template.
"""

import time
from typing import TYPE_CHECKING

from app.core.config import settings
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.types import AnalysisID
from app.domains.analysis.schemas.tasks.aggregated_insights import AggregatedInsights
from app.domains.analysis.workflows.agents.base import create_structured_agent
from app.shared.services.messaging.sse_helpers import emit_streaming_event
from app.shared.services.prompts.prompt_manager import get_prompt_manager

if TYPE_CHECKING:
    from langchain_core.runnables import Runnable

logger = get_logger(__name__)

# Heartbeat interval for SSE events during synthesis (seconds)
SYNTHESIS_HEARTBEAT_INTERVAL: float = 5.0


async def get_synthesis_system_prompt() -> str:
    """Get synthesis system prompt from PromptManager.

    Issue #414: Uses Jinja2 template instead of hardcoded string.

    Returns:
        Synthesis system prompt string

    """
    prompt_manager = get_prompt_manager()
    return await prompt_manager.get_prompt(name="synthesis-system")


async def create_synthesis_agent() -> "Runnable":
    """Create structured agent for LLM synthesis.

    Issue #414: Now fetches system prompt from PromptManager.

    Returns:
        Structured agent instance configured for synthesis

    Note:
        Uses task_type="synthesis" for model routing observability.
        Synthesis intentionally uses the default model (not routed to cheaper models)
        because it performs complex multi-agent aggregation requiring high quality.

    """
    system_prompt = await get_synthesis_system_prompt()
    return create_structured_agent(
        system_prompt=system_prompt,
        response_schema=AggregatedInsights,
        task_type="synthesis",
    )


def create_fallback_synthesis_model() -> "Runnable":
    """Create a lighter fallback model for synthesis when primary fails.

    Uses LLM_FALLBACK_MODEL (default: gemini-2.5-flash) configured in settings.
    This model is used via LangChain's with_fallbacks() pattern.

    Returns:
        Fallback model with structured output for AggregatedInsights

    """
    fallback_model = get_chat_model(config={"configurable": {"model": settings.LLM_FALLBACK_MODEL}})
    # Bind structured output schema to fallback model
    return fallback_model.with_structured_output(AggregatedInsights)


async def create_synthesis_agent_with_fallback() -> "Runnable":
    """Create synthesis agent with fallback chain for resilience.

    Issue #299-304: Implements LangChain's with_fallbacks() pattern.
    If primary model fails (timeout, error, etc.), automatically
    falls back to lighter model for graceful degradation.

    Issue #414: Now async to support PromptManager.

    Fallback Chain:
    1. Primary: Full synthesis agent (current LLM_MODEL)
    2. Fallback: Lighter model (LLM_FALLBACK_MODEL)

    Returns:
        Synthesis agent with fallback chain attached

    """
    primary_agent = await create_synthesis_agent()
    fallback_model = create_fallback_synthesis_model()

    logger.info(
        "synthesis_agent_with_fallback_created",
        primary_model=settings.LLM_MODEL,
        fallback_model=settings.LLM_FALLBACK_MODEL,
    )

    # Attach fallback chain - catches all exceptions including TimeoutError
    return primary_agent.with_fallbacks(
        fallbacks=[fallback_model],
        exceptions_to_handle=(Exception, TimeoutError, GeneratorExit),
    )


async def _emit_synthesis_heartbeat(
    analysis_id: AnalysisID,
    start_time: float,
    message: str = "LLM synthesis in progress...",
) -> None:
    """Emit heartbeat SSE event during synthesis.

    Issue #299-304: Keeps frontend informed during long LLM operations.
    Prevents "stuck at synthesizing" appearance by showing progress.

    Args:
        analysis_id: UUID of the analysis
        start_time: When synthesis started (for elapsed time)
        message: Progress message to display

    """
    elapsed = time.time() - start_time
    await emit_streaming_event(
        "progress",
        analysis_id=str(analysis_id),
        stage="aggregation",
        status="synthesizing",
        message=message,
        elapsed_seconds=round(elapsed, 1),
    )


async def synthesize_with_llm(
    validated_findings: list[dict[str, object]],
    conflicts: list[dict[str, str]],
    confidence_scores: dict[str, float],
    analysis_id: AnalysisID,
    source_context: dict[str, object] | None = None,
) -> dict[str, object]:
    """Synthesize agent findings using multi-phase parallel execution.

    Issue #299-304: Replaces monolithic 50-80K token synthesis with 3 parallel phases:
    - Phase 0: Compress findings (8-16K tokens using fast LLM)
    - Phase 1 (Core): REQUIRED - basic synthesis, conflicts, coverage (~15-25K tokens)
    - Phase 2 (Learning): OPTIONAL - concepts, exercises, quizzes (~15-25K tokens)
    - Phase 3 (Docs): OPTIONAL - TLDR, diagrams, glossary, AI prompts (~15-25K tokens)

    Issue #487: Now includes source_context for LLM grounding to prevent hallucinations.

    Phases 1-3 run in parallel after compression. Phase 1 failure fails the whole synthesis.
    Phases 2-3 failures result in graceful degradation (empty but valid structures).

    Args:
        validated_findings: List of validated agent findings
        conflicts: List of detected conflicts
        confidence_scores: Dictionary of agent confidence scores
        analysis_id: UUID of the analysis
        source_context: Optional source content for LLM grounding (Issue #487)
            Expected keys: title, summary, key_terms from source_content_extractor

    Returns:
        Dictionary with aggregated insights from multi-phase synthesis

    Raises:
        Exception: If Phase 1 (Core) fails - other phases fail gracefully

    """
    # Issue #299-304: Use multi-phase parallel synthesis
    from app.domains.analysis.workflows.tasks.aggregation.synthesis_phased import (
        synthesize_with_llm_phased,
    )

    return await synthesize_with_llm_phased(
        validated_findings=validated_findings,
        conflicts=conflicts,
        confidence_scores=confidence_scores,
        analysis_id=analysis_id,
        source_context=source_context,
    )
