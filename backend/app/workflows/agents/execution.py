"""Agent execution with tracking and error handling.

This module handles the execution of agents with progress tracking,
streaming support, error handling, and database persistence.
"""

import os
import time
from dataclasses import dataclass

from langchain_core.runnables import Runnable
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.timeout_config import AGENT_TIMEOUT
from app.core.types import AnalysisID
from app.workflows.agents.base import emit_agent_progress
from app.workflows.agents.invocation import invoke_agent
from app.workflows.agents.prompt_builders import build_agent_user_prompt
from app.workflows.agents.response_processing import extract_structured_response
from app.workflows.agents.result_processing import (
    handle_agent_cancellation,
    handle_agent_error,
    process_agent_result,
)
from app.workflows.agents.validation import score_agent_output
from app.workflows.utils.timeout_handling import handle_timeout_error

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


@dataclass
class AgentExecutionConfig:
    """Configuration for agent execution.

    Groups agent execution configuration to reduce function complexity.
    """

    session: AsyncSession
    max_content_length: int = 12000
    timeout: float = AGENT_TIMEOUT


async def _run_agent_with_tracking_impl(
    params: AgentExecutionParams,
    config: AgentExecutionConfig,
) -> dict[str, object]:
    """Implement agent execution with tracking.

    This function contains the actual logic. The public `run_agent_with_tracking`
    function wraps this with @traceable for LangSmith instrumentation.

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
        user_prompt = build_agent_user_prompt(
            content=params.content,
            content_type=params.content_type,
            max_length=config.max_content_length,
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
        min_score = get_specificity_min_score()

        while attempts <= max_retries:
            try:
                final_result = await invoke_agent(
                    agent=params.agent,
                    input_messages=input_messages,
                    analysis_id=params.analysis_id,
                    agent_type=params.agent_type,
                    timeout=config.timeout,
                )
            except (TimeoutError, GeneratorExit) as exc:
                # GeneratorExit should not occur with RunnableConfig timeout,
                # but kept as safety net for edge cases
                raise handle_timeout_error(
                    exc=exc,
                    context=f"Agent {params.agent_type} execution",
                    timeout=config.timeout,
                    logger=logger,
                    agent_type=params.agent_type,
                    analysis_id=params.analysis_id,
                ) from None

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
        # GeneratorExit should not occur with RunnableConfig timeout,
        # but kept as safety net for edge cases
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
) -> dict[str, object]:
    """Run an agent with progress tracking, error handling, and database persistence.

    Note: This function is NOT traced with @robust_traceable because the calling
    node (e.g., tech_comparator_node) is already traced. Adding tracing here would
    create duplicate traces in LangSmith.

    Note: This function accepts 7 parameters for backward compatibility with existing callers.
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
    )
    config = AgentExecutionConfig(
        session=session,
        max_content_length=max_content_length,
    )

    # Call implementation directly - no tracing here since the node wrapper already traces
    return await _run_agent_with_tracking_impl(params=params, config=config)
