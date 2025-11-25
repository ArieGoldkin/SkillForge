"""Base utilities for agent implementation.

This module provides shared functionality for all specialized analysis agents,
including agent creation with structured output, database persistence, and
SSE event emission.
"""

import asyncio
import time
from typing import Any
from uuid import UUID

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, before_model, wrap_model_call
from langchain.agents.structured_output import ToolStrategy
from langsmith import traceable
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.types import AnalysisID
from app.models.agent_finding import AgentFinding
from app.services.sse_helpers import emit_streaming_event

logger = get_logger(__name__)


def create_structured_agent(
    system_prompt: str,
    response_schema: type[BaseModel],
    tools: list[Any] | None = None,
) -> Any:
    """Create an agent with structured output using ToolStrategy.

    Args:
        system_prompt: System prompt for the agent
        response_schema: Pydantic model defining the expected output structure
        tools: Optional list of tools for the agent

    Returns:
        Configured agent instance with structured output support

    Note:
        ToolStrategy automatically validates output against response_schema.
        Validation errors are automatically traced by LangSmith when they occur.

    """
    model = get_chat_model()
    agent = create_agent(
        model,
        tools=tools or [],
        system_prompt=system_prompt,
        response_format=ToolStrategy(response_schema),
    )

    # Note: ToolStrategy already validates output against response_schema.
    # Validation errors are automatically captured by LangChain and traced by LangSmith.
    # We don't need to wrap invoke here as ToolStrategy handles validation internally.
    # The validation errors will appear in LangSmith traces automatically.

    return agent


@before_model
def log_agent_before_model(state: Any, runtime: Any) -> Any:
    """Log agent invocation before model call."""
    if hasattr(runtime, "context"):
        context = runtime.context
        agent_type = context.get("agent_type", "unknown")
        analysis_id = context.get("analysis_id", "unknown")
        logger.debug(
            "agent_invoking",
            agent_type=agent_type,
            analysis_id=analysis_id,
            message_count=len(state.get("messages", []) if isinstance(state, dict) else []),
        )
    return None


@wrap_model_call
def retry_agent_model(
    request: ModelRequest,
    handler: Any,
) -> Any:
    """Wrap model calls with retry logic and exponential backoff.

    Retries up to 3 times with exponential backoff for transient failures.
    Handles both sync and async handlers.
    """
    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            # Handler is always sync for wrap_model_call
            return handler(request)
        except Exception as e:
            if attempt == max_attempts - 1:
                # Last attempt failed, re-raise
                logger.exception(
                    "agent_model_call_failed",
                    attempt=attempt + 1,
                    error=str(e),
                )
                raise

            # Exponential backoff: base_delay * (2^attempt)
            base_delay = settings.LLM_RETRY_DELAY_BASE
            wait_time = base_delay * (2**attempt)
            logger.warning(
                "agent_model_call_retry",
                attempt=attempt + 1,
                max_attempts=max_attempts,
                wait_time=wait_time,
                error=str(e),
            )
            time.sleep(wait_time)

    # Should never reach here, but just in case
    msg = "Retry loop exhausted without success"
    raise RuntimeError(msg)


async def save_agent_finding(  # noqa: PLR0913
    session: AsyncSession,
    analysis_id: UUID,
    agent_type: str,
    findings: dict[str, Any],
    confidence_score: float | None = None,
    processing_time_ms: int | None = None,
) -> AgentFinding:
    """Save agent finding to database.

    Args:
        session: Database session
        analysis_id: UUID of the analysis
        agent_type: Type of agent (e.g., "tech_comparator")
        findings: Structured findings dictionary
        confidence_score: Optional confidence score (0.0-1.0)
        processing_time_ms: Optional processing time in milliseconds

    Returns:
        Created AgentFinding instance

    """
    finding = AgentFinding(
        analysis_id=analysis_id,
        agent_type=agent_type,
        findings=findings,
        confidence_score=confidence_score,
        processing_time_ms=processing_time_ms,
    )
    session.add(finding)
    await session.commit()
    await session.refresh(finding)
    return finding


async def emit_agent_progress(
    analysis_id: AnalysisID,
    agent_type: str,
    status: str,
    **kwargs: object,
) -> None:
    """Emit SSE event for agent progress.

    Args:
        analysis_id: UUID of the analysis
        agent_type: Type of agent
        status: Status ("running", "streaming", "complete", "failed")
        **kwargs: Additional event data

    """
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage=agent_type,
        status=status,
        agent_type=agent_type,
        **kwargs,
    )


async def _run_agent_with_tracking_impl(  # noqa: PLR0913
    agent: Any,
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    agent_type: str,
    session: AsyncSession,
    max_content_length: int = 2000,
) -> dict[str, Any]:
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

        # Use async invoke if available, otherwise wrap sync invoke in thread pool
        # This prevents blocking the event loop during LLM calls
        agent_timeout = 120.0  # 120 seconds (2 minutes) max per agent for complex LLM calls
        try:
            if hasattr(agent, "ainvoke"):
                # Async invoke (preferred - non-blocking)
                result = await asyncio.wait_for(
                    agent.ainvoke(input_messages),
                    timeout=agent_timeout,
                )
            else:
                # Fallback: run sync invoke in thread pool to avoid blocking event loop
                result = await asyncio.wait_for(
                    asyncio.to_thread(agent.invoke, input_messages),
                    timeout=agent_timeout,
                )
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
        structured_response = result.get("structured_response")
        if structured_response is None:
            msg = f"Agent {agent_type} did not return structured_response"
            raise RuntimeError(msg)  # noqa: TRY301

        # Convert Pydantic model to dict for storage
        findings = structured_response.model_dump()

        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Save to database
        await save_agent_finding(
            session=session,
            analysis_id=UUID(str(analysis_id)),
            agent_type=agent_type,
            findings=findings,
            processing_time_ms=processing_time_ms,
        )

        # Emit SSE event: agent complete
        await emit_agent_progress(
            analysis_id,
            agent_type,
            "complete",
            processing_time_ms=processing_time_ms,
        )

        logger.info(
            "agent_complete",
            agent_type=agent_type,
            analysis_id=analysis_id,
            processing_time_ms=processing_time_ms,
        )

        return {  # noqa: TRY300
            "agent_type": agent_type,
            "findings": findings,
            "processing_time_ms": processing_time_ms,
        }

    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Emit SSE event: agent failed
        await emit_agent_progress(
            analysis_id,
            agent_type,
            "failed",
            error=str(e),
            error_code=f"{agent_type.upper()}_FAILED",
        )

        logger.exception(
            "agent_failed",
            agent_type=agent_type,
            analysis_id=analysis_id,
            error=str(e),
            processing_time_ms=processing_time_ms,
        )
        raise


async def run_agent_with_tracking(  # noqa: PLR0913
    agent: Any,
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    agent_type: str,
    session: AsyncSession,
    max_content_length: int = 2000,
) -> dict[str, Any]:
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
