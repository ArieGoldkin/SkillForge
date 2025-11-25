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
from app.core.constants import SSE_EVENT_THROTTLE_CHARS, SSE_EVENT_THROTTLE_MS
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.types import AnalysisID
from app.core.utils import normalize_analysis_id_to_uuid
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


async def _run_agent_with_tracking_impl(  # noqa: PLR0913, PLR0915
    agent: Any,
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    agent_type: str,
    session: AsyncSession,
    max_content_length: int = 1500,
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

        # Stream agent execution for real-time progress visibility
        # This follows LangChain v1.0 best practices for long-running agent calls
        agent_timeout = 120.0  # 120 seconds (2 minutes) max per agent for complex LLM calls
        accumulated_content = ""
        final_result: dict[str, Any] | None = None

        try:
            # Check if agent supports streaming (must be callable, not just present)
            agent_has_streaming = callable(getattr(agent, "astream", None))
            if agent_has_streaming:
                # Stream agent execution (preferred - shows progress)
                # Use stream_mode="values" to get state updates after each step
                async def stream_with_timeout():
                    nonlocal final_result, accumulated_content
                    last_event_time = 0.0
                    last_event_chars = 0

                    async for chunk in agent.astream(
                        input_messages,
                        stream_mode="values",
                    ):
                        # Check for structured_response early (robustness)
                        # Preserve chunk with structured_response,
                        # even if later chunks don't have it
                        if isinstance(chunk, dict) and chunk.get("structured_response"):
                            # Found structured_response - preserve this chunk
                            # Continue streaming for progress updates, but keep this result
                            # This handles cases where structured_response appears
                            # in intermediate chunks
                            final_result = chunk
                        elif final_result is None or not (
                            isinstance(final_result, dict)
                            and final_result.get("structured_response")
                        ):
                            # Update final_result only if we haven't found structured_response yet
                            # This ensures we preserve the chunk with structured_response
                            final_result = chunk

                        # Extract content from messages for progress updates
                        if isinstance(chunk, dict) and chunk.get("messages"):
                            messages = chunk["messages"]
                            if messages:
                                latest_message = messages[-1]
                                # Extract text content for streaming preview
                                if hasattr(latest_message, "content") and latest_message.content:
                                    new_content = latest_message.content[len(accumulated_content) :]
                                    if new_content:
                                        accumulated_content = latest_message.content

                    # Throttle SSE events to prevent overwhelming frontend
                    # Emit only if enough time has passed OR
                    # enough characters accumulated
                                        current_time = time.time()
                                        chars_since_last = (
                                            len(accumulated_content) - last_event_chars
                                        )
                                        time_since_last_ms = (current_time - last_event_time) * 1000

                                        should_emit = (
                                            time_since_last_ms >= SSE_EVENT_THROTTLE_MS
                                            or chars_since_last >= SSE_EVENT_THROTTLE_CHARS
                                        )

                                        if should_emit:
                                            # Emit SSE so frontend sees progress
                                            await emit_agent_progress(
                                                analysis_id,
                                                agent_type,
                                                "streaming",
                                                token_preview=accumulated_content[
                                                    -100:
                                                ],  # Last 100 chars
                                            )
                                            # Update throttling tracking
                                            last_event_time = current_time
                                            last_event_chars = len(accumulated_content)

                # Stream with timeout
                try:
                    await asyncio.wait_for(
                        stream_with_timeout(),
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
            elif hasattr(agent, "ainvoke"):
                # Fallback: async invoke without streaming
                result = await asyncio.wait_for(
                    agent.ainvoke(input_messages),
                    timeout=agent_timeout,
                )
                final_result = result
            else:
                # Fallback: run sync invoke in thread pool
                result = await asyncio.wait_for(
                    asyncio.to_thread(agent.invoke, input_messages),
                    timeout=agent_timeout,
                )
                final_result = result
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
        if final_result is None:
            msg = f"Agent {agent_type} returned no result"
            raise RuntimeError(msg)  # noqa: TRY301
        if not isinstance(final_result, dict):
            msg = f"Agent {agent_type} returned invalid result type: {type(final_result)}"
            raise TypeError(msg)  # noqa: TRY301
        structured_response = final_result.get("structured_response")
        if structured_response is None:
            msg = f"Agent {agent_type} did not return structured_response"
            raise RuntimeError(msg)  # noqa: TRY301

        # Convert Pydantic model to dict for storage
        findings = structured_response.model_dump()

        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Save to database
        # Normalize analysis_id to UUID (handles strings, UUID objects, and non-UUID strings)
        analysis_uuid = normalize_analysis_id_to_uuid(analysis_id)

        await save_agent_finding(
            session=session,
            analysis_id=analysis_uuid,
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
    max_content_length: int = 1500,
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
