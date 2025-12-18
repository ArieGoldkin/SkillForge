"""Agent execution with tracking and error handling.

This module handles the execution of agents with progress tracking,
streaming support, error handling, and database persistence.

Redis semantic caching is integrated at the model factory level (get_chat_model),
providing automatic caching for all LLM calls without explicit cache management here.
"""

import os
import time
from dataclasses import dataclass

from langchain_core.runnables import Runnable
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.timeout_config import AGENT_TIMEOUT
from app.core.types import AnalysisID
from app.domains.analysis.workflows.agents.base import emit_agent_progress
from app.domains.analysis.workflows.agents.invocation import invoke_agent
from app.domains.analysis.workflows.agents.prompt_builders import build_agent_user_prompt
from app.domains.analysis.workflows.agents.response_processing import extract_structured_response
from app.domains.analysis.workflows.agents.result_processing import (
    handle_agent_cancellation,
    handle_agent_error,
    process_agent_result,
)
from app.domains.analysis.workflows.agents.validation import score_agent_output

logger = get_logger(__name__)

# Specificity validation configuration
# Can be overridden via environment variable for testing (set to 0.0 to disable)


def get_specificity_min_score() -> float:
    """Get specificity minimum score from environment or default.

    Returns:
        Minimum specificity score (0.0-1.0). 0.0 disables validation.

    """
    return float(os.environ.get("SPECIFICITY_MIN_SCORE", "0.70"))


def get_specificity_max_retries() -> int:
    """Get maximum specificity retries from environment or default.

    Returns:
        Maximum number of retries (default: 1)

    """
    return int(os.environ.get("SPECIFICITY_MAX_RETRIES", "1"))


@dataclass
class AgentExecutionParams:
    """Parameters for agent execution.

    Groups agent execution parameters to reduce function complexity.
    """

    agent: Runnable
    content: str
    content_type: str
    analysis_id: AnalysisID
    agent_type: str
    proactive_context: str = ""  # Issue #300: Proactive memory context


@dataclass
class AgentExecutionConfig:
    """Configuration for agent execution.

    Groups agent execution configuration to reduce function complexity.

    Issue #299-304: Added specificity_threshold to allow content-aware threshold adjustment.
    """

    session: AsyncSession
    max_content_length: int = 12000
    timeout: float = AGENT_TIMEOUT
    specificity_threshold: float | None = None  # None = use default from env


async def _run_agent_with_tracking_impl(
    params: AgentExecutionParams,
    config: AgentExecutionConfig,
) -> dict[str, object]:
    """Implement agent execution with tracking.

    This function contains the actual logic. The public `run_agent_with_tracking`
    function wraps this with @traceable for Langfuse instrumentation.

    Redis semantic caching is automatically enabled for all agents via the model
    factory (get_chat_model). No explicit cache management needed here.

    Redis semantic caching is automatically enabled for all agents via the model
    factory (get_chat_model). No explicit cache management needed here.

    Args:
        params: Agent execution parameters
        config: Agent execution configuration

    Returns:
        Dictionary with agent_type, findings, confidence_score, processing_time_ms

    Raises:
        Exception: If agent execution fails

    """
    start_time = time.time()

    # Emit SSE event: agent started
    await emit_agent_progress(params.analysis_id, params.agent_type, "running")

    logger.info(
        "agent_started",
        agent_type=params.agent_type,
        analysis_id=params.analysis_id,
        content_type=params.content_type,
        content_length=len(params.content),
    )

    try:
        # Build user prompt using prompt builder
        # Issue #300: Include proactive context from memory recall
        # Note: Redis semantic caching is integrated at model level (no manual cache management)
        user_prompt = build_agent_user_prompt(
            content=params.content,
            content_type=params.content_type,
            max_length=config.max_content_length,
            proactive_context=params.proactive_context,
        )

        # Invoke agent with structured output (async with timeout)
        input_messages = {
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ]
        }

        attempts = 0
        findings = None
        specificity_score = None
        max_retries = get_specificity_max_retries()
        # Issue #299-304: Use content-aware threshold if provided, otherwise default
        min_score = (
            config.specificity_threshold
            if config.specificity_threshold is not None
            else get_specificity_min_score()
        )

        # DEBUG: Log threshold being used (Issue #299-304)
        logger.info(
            "threshold_being_used_in_execution",
            agent_type=params.agent_type,
            analysis_id=params.analysis_id,
            config_threshold=config.specificity_threshold,
            final_min_score=min_score,
            used_config=config.specificity_threshold is not None,
        )

        while attempts <= max_retries:
            try:
                final_result = await invoke_agent(
                    agent=params.agent,
                    input_messages=input_messages,
                    analysis_id=params.analysis_id,
                    agent_type=params.agent_type,
                    timeout=config.timeout,
                )
            except TimeoutError as exc:
                # LangGraph's RunnableConfig timeout raises TimeoutError directly
                logger.exception(
                    "timeout_error",
                    context=f"Agent {params.agent_type} execution",
                    timeout=config.timeout,
                    agent_type=params.agent_type,
                    analysis_id=params.analysis_id,
                )
                msg = f"Agent {params.agent_type} execution exceeded timeout of {config.timeout}s"
                raise TimeoutError(msg) from exc

            # Extract structured response (validated Pydantic model)
            findings = extract_structured_response(final_result, params.agent_type)

            # Validate specificity; retry once if below threshold
            # Skip validation if threshold is 0.0 (disabled for tests)
            if min_score > 0.0:
                specificity_score = score_agent_output(
                    findings,
                    agent_type=params.agent_type,
                )
                if specificity_score.overall_score >= min_score:
                    break

                if attempts >= max_retries:
                    logger.error(
                        "agent_specificity_below_threshold",
                        agent_type=params.agent_type,
                        analysis_id=params.analysis_id,
                        specificity_score=specificity_score.overall_score,
                        threshold=min_score,
                        retries=attempts,
                    )
                    error_message = (
                        "Specificity score "
                        f"{specificity_score.overall_score} "
                        f"below threshold {min_score}"
                    )
                    raise ValueError(error_message)

                attempts += 1
                logger.warning(
                    "agent_specificity_retry",
                    agent_type=params.agent_type,
                    analysis_id=params.analysis_id,
                    attempt=attempts,
                    specificity_score=specificity_score.overall_score,
                    threshold=min_score,
                )
            else:
                # Validation disabled (min_score = 0.0), proceed without checking
                break

        # Process and persist result
        return await process_agent_result(
            findings=findings or {},
            analysis_id=params.analysis_id,
            agent_type=params.agent_type,
            session=config.session,
            start_time=start_time,
        )

    except GeneratorExit:
        # Handle task cancellation (e.g., workflow interrupted)
        await handle_agent_cancellation(
            analysis_id=params.analysis_id,
            agent_type=params.agent_type,
            start_time=start_time,
        )
        # Re-raise to propagate to workflow
        raise
    except Exception as e:
        await handle_agent_error(
            error=e,
            analysis_id=params.analysis_id,
            agent_type=params.agent_type,
            start_time=start_time,
        )
        raise


async def run_agent_with_tracking(  # noqa: PLR0913
    agent: Runnable,
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    agent_type: str,
    session: AsyncSession,
    max_content_length: int = 12000,
    proactive_context: str = "",
    specificity_threshold: float | None = None,
) -> dict[str, object]:
    """Run an agent with progress tracking, error handling, and database persistence.

    Note: This function is NOT traced with @robust_traceable because the calling
    node (e.g., tech_comparator_node) is already traced. Adding tracing here would
    create duplicate traces in Langfuse.

    Note: This function accepts 9 parameters for backward compatibility with existing callers.
    Internally, parameters are grouped into AgentExecutionParams and AgentExecutionConfig
    dataclasses to reduce complexity. Future refactoring could change the signature to accept
    dataclasses directly.

    Args:
        agent: Agent instance to run
        content: Content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: UUID of the analysis
        agent_type: Type of agent for logging and storage
        session: Database session for persistence
        max_content_length: Maximum content length to send to agent
        proactive_context: Formatted memory context from past analyses (Issue #300)
        specificity_threshold: Optional threshold override (Issue #299-304).
            If None, uses default from SPECIFICITY_MIN_SCORE env var (0.70).
            Lower thresholds (e.g., 0.55) for conceptual-only content.

    Returns:
        Dictionary with agent_type, findings, confidence_score, processing_time_ms

    Raises:
        Exception: If agent execution fails

    """
    # Group parameters into dataclasses to reduce function complexity
    params = AgentExecutionParams(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type=agent_type,
        proactive_context=proactive_context,
    )
    config = AgentExecutionConfig(
        session=session,
        max_content_length=max_content_length,
        specificity_threshold=specificity_threshold,
    )

    # Call implementation directly - no tracing here since the node wrapper already traces
    return await _run_agent_with_tracking_impl(params=params, config=config)
