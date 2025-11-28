"""Agent execution with tracking and error handling.

This module handles the execution of agents with progress tracking,
streaming support, error handling, and database persistence.
"""

import time

from langchain_core.runnables import Runnable
from langsmith import traceable
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.workflows.agents.base import emit_agent_progress
from app.workflows.agents.invocation import invoke_agent
from app.workflows.agents.response_processing import extract_structured_response
from app.workflows.agents.result_processing import (
    handle_agent_cancellation,
    handle_agent_error,
    process_agent_result,
)

logger = get_logger(__name__)


async def _run_agent_with_tracking_impl(  # noqa: PLR0913
    agent: Runnable,
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    agent_type: str,
    session: AsyncSession,
    max_content_length: int = 1500,
) -> dict[str, object]:
    """Implement agent execution with tracking.

    This function contains the actual logic. The public `run_agent_with_tracking`
    function wraps this with @traceable for LangSmith instrumentation.

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
    start_time = time.time()

    # Emit SSE event: agent started
    await emit_agent_progress(analysis_id, agent_type, "running")

    logger.info(
        "agent_started",
        agent_type=agent_type,
        analysis_id=analysis_id,
        content_type=content_type,
        content_length=len(content),
    )

    try:
        # Prepare content for agent (limit length for prompt efficiency)
        if len(content) > max_content_length:
            content_preview = content[:max_content_length]
        else:
            content_preview = content
        user_prompt = f"Content Type: {content_type}\n\nContent:\n{content_preview}"

        # Invoke agent with structured output (async with timeout)
        input_messages = {
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ]
        }

        # Invoke agent with automatic fallback strategy
        # This follows LangChain v1.0 best practices for long-running agent calls
        agent_timeout = 120.0  # 120 seconds (2 minutes) max per agent for complex LLM calls

        try:
            final_result = await invoke_agent(
                agent=agent,
                input_messages=input_messages,
                analysis_id=analysis_id,
                agent_type=agent_type,
                timeout=agent_timeout,
            )
        except GeneratorExit:
            # Re-raise GeneratorExit to propagate to outer handler
            # Don't check for structured_response if GeneratorExit occurred
            raise
        except TimeoutError:
            msg = f"Agent {agent_type} exceeded timeout of {agent_timeout}s"
            logger.exception(
                "agent_timeout",
                agent_type=agent_type,
                analysis_id=analysis_id,
                timeout=agent_timeout,
            )
            raise TimeoutError(msg) from None

        # Extract structured response (validated Pydantic model)
        # Only check if we didn't get GeneratorExit (which would have been re-raised above)
        findings = extract_structured_response(final_result, agent_type)

        # Process and persist result
        return await process_agent_result(
            findings=findings,
            analysis_id=analysis_id,
            agent_type=agent_type,
            session=session,
            start_time=start_time,
        )

    except GeneratorExit:
        # Generator was closed externally (timeout, cancellation, etc.)
        await handle_agent_cancellation(
            analysis_id=analysis_id,
            agent_type=agent_type,
            start_time=start_time,
        )
        # Re-raise to propagate to workflow
        raise
    except Exception as e:
        await handle_agent_error(
            error=e,
            analysis_id=analysis_id,
            agent_type=agent_type,
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
    # Use @traceable with dynamic name, tags, and metadata based on agent_type
    traced_func = traceable(
        name=agent_type,
        run_type="chain",
        tags=["agent", agent_type],
        metadata={
            "analysis_id": str(analysis_id),
            "agent_type": agent_type,
            "content_type": content_type,
        },
    )(_run_agent_with_tracking_impl)

    return await traced_func(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type=agent_type,
        session=session,
        max_content_length=max_content_length,
    )
