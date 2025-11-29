"""Agent execution with tracking and error handling.

This module handles the execution of agents with progress tracking,
streaming support, error handling, and database persistence.
"""

import time
from dataclasses import dataclass

from langchain_core.runnables import Runnable
from langsmith import traceable
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
from app.workflows.utils.timeout_handling import handle_timeout_error

logger = get_logger(__name__)


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
    max_content_length: int = 1500
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

        try:
            final_result = await invoke_agent(
                agent=params.agent,
                input_messages=input_messages,
                analysis_id=params.analysis_id,
                agent_type=params.agent_type,
                timeout=config.timeout,
            )
        except (TimeoutError, GeneratorExit) as exc:
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

        # Process and persist result
        return await process_agent_result(
            findings=findings,
            analysis_id=params.analysis_id,
            agent_type=params.agent_type,
            session=config.session,
            start_time=start_time,
        )

    except GeneratorExit:
        # Generator was closed externally (timeout, cancellation, etc.)
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
    max_content_length: int = 1500,
) -> dict[str, object]:
    """Run an agent with progress tracking, error handling, and database persistence.

    This function is wrapped with @traceable to create LangSmith traces for each agent execution.

    Note: This function accepts 7 parameters for backward compatibility with existing callers.
    Internally, parameters are grouped into AgentExecutionParams and AgentExecutionConfig dataclasses
    to reduce complexity. Future refactoring could change the signature to accept dataclasses directly.

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

    # Use @traceable on the wrapper function, not the internal one
    # This avoids LangSmith trying to serialize dataclass arguments
    # The internal function (_run_agent_with_tracking_impl) is not traced
    # to avoid serialization issues with dataclass arguments
    traced_wrapper = traceable(
        name=agent_type,
        run_type="chain",
        tags=["agent", agent_type],
        metadata={
            "analysis_id": str(analysis_id),
            "agent_type": agent_type,
            "content_type": content_type,
        },
    )

    @traced_wrapper
    async def traced_run() -> dict[str, object]:
        """Traced wrapper that calls the internal implementation."""
        return await _run_agent_with_tracking_impl(params=params, config=config)

    return await traced_run()
