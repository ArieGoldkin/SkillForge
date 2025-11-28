"""Base utilities for agent implementation.

This module provides shared functionality for all specialized analysis agents,
including agent creation with structured output, database persistence, and
SSE event emission.
"""

import time
from collections.abc import Callable, Sequence
from uuid import UUID

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentState,
    ModelRequest,
    ModelResponse,
    before_model,
    wrap_model_call,
)
from langchain.agents.structured_output import ToolStrategy
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_config import get_stage_name
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
    tools: Sequence[BaseTool] | None = None,
) -> Runnable:
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
def log_agent_before_model(
    state: AgentState,
    runtime: object,
) -> None:
    """Log agent invocation before model call."""
    if hasattr(runtime, "context"):
        context = runtime.context
        agent_type = context.get("agent_type", "unknown")
        analysis_id = context.get("analysis_id", "unknown")
        message_count = (
            len(state.get("messages", []))  # type: ignore[union-attr]
            if isinstance(state, dict)
            else 0
        )
        logger.debug(
            "agent_invoking",
            agent_type=agent_type,
            analysis_id=analysis_id,
            message_count=message_count,
        )
    return None


@wrap_model_call
def retry_agent_model(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
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
    findings: dict[str, object],
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

    Raises:
        ValueError: If Analysis record does not exist (foreign key constraint)

    """
    # Verify Analysis exists before saving finding (prevents foreign key violations)
    from sqlalchemy import select

    from app.models.analysis import Analysis

    result = await session.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise ValueError(
            f"Analysis record with id={analysis_id} does not exist. "
            "Analysis must be created before agents can save findings."
        )

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
    # Get stage name from agent config (single source of truth)
    stage_name = get_stage_name(agent_type)
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage=stage_name,
        status=status,
        agent_type=agent_type,  # Keep agent_type in details for debugging
        **kwargs,
    )
