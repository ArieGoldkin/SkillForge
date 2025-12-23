"""Base utilities for agent implementation.

This module provides shared functionality for all specialized analysis agents,
including agent creation with structured output, database persistence, and
SSE event emission.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast
from uuid import UUID

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.messages import SystemMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_config import get_stage_name
from app.core.config import settings
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.types import AnalysisID
from app.db.models.agent_finding import AgentFinding
from app.db.session import get_session_factory
from app.domains.analysis.constants.error_codes import AgentStatus
from app.shared.services.messaging.sse_helpers import emit_streaming_event

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

logger = get_logger(__name__)


def _create_system_message_with_cache_control(system_prompt: str) -> SystemMessage:
    """Create a SystemMessage with Anthropic prompt caching support.

    Args:
        system_prompt: System prompt text

    Returns:
        SystemMessage with cache_control configured based on settings

    Note:
        Cache control is only added when using Anthropic models.
        - 5m TTL: Default Anthropic ephemeral caching (no beta header needed)
        - 1h TTL: Extended caching (requires beta header in model factory)

    """
    # Check if we should add cache_control for Anthropic models
    provider = settings.resolved_llm_provider()
    if provider != "anthropic":
        # No cache control for non-Anthropic providers
        return SystemMessage(content=system_prompt)

    # Determine cache_control based on configured TTL
    cache_control: dict[str, str] = {"type": "ephemeral"}
    if settings.ANTHROPIC_PROMPT_CACHE_TTL == "1h":
        # Extended 1-hour cache (requires beta header)
        cache_control["ttl"] = "1h"
        logger.debug(
            "system_prompt_cache_control_enabled",
            cache_type="ephemeral",
            ttl="1h",
            provider=provider,
        )
    else:
        # Default 5-minute cache
        logger.debug(
            "system_prompt_cache_control_enabled",
            cache_type="ephemeral",
            ttl="5m",
            provider=provider,
        )

    # Create SystemMessage with cache_control in additional_kwargs
    # Anthropic expects cache_control at the content level for text blocks
    return SystemMessage(
        content=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": cache_control,
            }
        ]
    )


@dataclass
class ToolCallConfig:
    """Configuration for tool-enabled agent behavior.

    Attributes:
        max_tool_calls: Maximum number of tool calls allowed per agent run
        parallel_tool_calls: Whether to allow parallel tool execution

    """

    max_tool_calls: int = 10
    parallel_tool_calls: bool = True


def create_structured_agent(
    system_prompt: str,
    response_schema: type[BaseModel],
    tools: Sequence[BaseTool] | None = None,
    task_type: str | None = None,
) -> Runnable:
    """Create an agent with structured output using ToolStrategy.

    Args:
        system_prompt: System prompt for the agent
        response_schema: Pydantic model defining the expected output structure
        tools: Optional list of tools for the agent
        task_type: Optional task type for model routing (e.g., "synthesis", "agent").
            If provided and in TASK_MODEL_MAP, routes to optimized model.
            If not in map, uses default model (intentional for complex tasks).

    Returns:
        Configured agent instance with structured output support

    Note:
        ToolStrategy automatically validates output against response_schema.
        Validation errors are automatically traced by Langfuse when they occur.
        For Anthropic models, system prompts are automatically cached for cost savings.

    """
    model = get_chat_model(task_type=task_type)
    # Prevent multiple parallel tool calls; we expect exactly one structured response
    # LangChain 1.2.x: Added tool_choice for explicit provider control
    bound_model: Runnable = model.bind_tools(
        tools or [],
        parallel_tool_calls=False,
        tool_choice="auto",  # Explicit tool selection mode
    )

    # Create system message with prompt caching support
    system_message = _create_system_message_with_cache_control(system_prompt)

    # Note: ToolStrategy handles schema validation internally
    # LangChain 1.2.x strict mode is applied via with_structured_output() in other paths
    return create_agent(
        cast("BaseChatModel", bound_model),
        tools=tools or [],
        system_prompt=system_message,
        response_format=ToolStrategy(response_schema),
    )

    # Note: ToolStrategy already validates output against response_schema.
    # Validation errors are automatically captured by LangChain and traced by Langfuse.
    # We don't need to wrap invoke here as ToolStrategy handles validation internally.
    # The validation errors will appear in Langfuse traces automatically.


def _build_tool_enhanced_prompt(
    base_prompt: str,
    tools: Sequence[BaseTool],
    max_tool_calls: int,
) -> str:
    """Enhance system prompt with tool usage guidelines.

    Args:
        base_prompt: Original system prompt for the agent
        tools: List of available MCP tools
        max_tool_calls: Maximum allowed tool invocations

    Returns:
        Enhanced prompt with tool descriptions and usage guidelines

    """
    if not tools:
        return base_prompt

    tool_descriptions = "\n".join(f"- **{tool.name}**: {tool.description}" for tool in tools)

    tool_section = f"""

## Available Tools

You have access to the following tools for real-time data lookup:

{tool_descriptions}

## Tool Usage Guidelines

1. **Verify claims:** Use tools to check specific versions, CVEs, package metadata
2. **Be efficient:** Maximum {max_tool_calls} tool calls allowed - prioritize wisely
3. **Handle failures gracefully:** If a tool fails, note the gap in your findings
4. **Cite sources:** Reference tool results (e.g., "Per npm registry, v3.0.0...")
5. **Don't over-rely:** Trust your training for concepts; use tools for current facts

IMPORTANT: After your tool calls, you MUST produce a structured response matching
the expected schema. Tool usage is for research - your final output must be structured.
"""

    return base_prompt + tool_section


def create_tool_enabled_agent(
    system_prompt: str,
    response_schema: type[BaseModel],
    tools: Sequence[BaseTool],
    tool_call_config: ToolCallConfig | None = None,
    task_type: str | None = None,
) -> Runnable:
    """Create an agent with MCP tool access and structured output.

    This factory creates agents that can call external MCP tools (GitHub, npm, PyPI)
    during their reasoning process while still producing validated structured output.

    Args:
        system_prompt: Base system prompt for the agent
        response_schema: Pydantic model defining expected output structure
        tools: List of MCP tools (pre-filtered by ToolRegistry)
        tool_call_config: Optional configuration for tool behavior
        task_type: Optional task type for model routing (e.g., "agent").
            If provided and in TASK_MODEL_MAP, routes to optimized model.

    Returns:
        Configured agent with tool calling and structured output support

    Raises:
        ValueError: If tools sequence is empty

    Example:
        >>> from app.shared.services.mcp import MCPClientPool, ToolRegistry
        >>> registry = ToolRegistry()
        >>> tools = await pool.get_tools_for_capabilities(
        ...     registry.get_capabilities("security_auditor")
        ... )
        >>> agent = create_tool_enabled_agent(
        ...     system_prompt="Analyze security...",
        ...     response_schema=SecurityAudit,
        ...     tools=tools,
        ... )

    Note:
        Unlike create_structured_agent(), this factory:
        - Enables parallel_tool_calls for efficiency
        - Enhances the prompt with tool usage guidelines
        - Requires at least one tool (use create_structured_agent for no-tool agents)

    """
    if not tools:
        msg = "tools must not be empty; use create_structured_agent() for agents without tools"
        raise ValueError(msg)

    config = tool_call_config or ToolCallConfig()

    # Enhance prompt with tool information
    enhanced_prompt = _build_tool_enhanced_prompt(
        base_prompt=system_prompt,
        tools=tools,
        max_tool_calls=config.max_tool_calls,
    )

    logger.info(
        "creating_tool_enabled_agent",
        tool_count=len(tools),
        tool_names=[t.name for t in tools],
        max_tool_calls=config.max_tool_calls,
        parallel_tool_calls=config.parallel_tool_calls,
    )

    model = get_chat_model(task_type=task_type)
    # Enable parallel tool calls for MCP tools (efficiency)
    # LangChain 1.2.x: Added tool_choice for explicit provider control
    bound_model: Runnable = model.bind_tools(
        list(tools),
        parallel_tool_calls=config.parallel_tool_calls,
        tool_choice="auto",  # Explicit tool selection mode
    )

    # Create system message with prompt caching support
    system_message = _create_system_message_with_cache_control(enhanced_prompt)

    # Note: ToolStrategy handles schema validation internally
    # LangChain 1.2.x strict mode is applied via with_structured_output() in other paths
    return create_agent(
        cast("BaseChatModel", bound_model),
        tools=list(tools),
        system_prompt=system_message,
        response_format=ToolStrategy(response_schema),
    )


async def save_agent_finding(  # noqa: PLR0913
    session: AsyncSession,
    analysis_id: UUID,
    agent_type: str,
    findings: dict[str, object],
    confidence_score: float | None = None,
    processing_time_ms: int | None = None,
    status: str = AgentStatus.SUCCESS,
    error_code: str | None = None,
    error_message: str | None = None,
) -> AgentFinding:
    """Save agent finding to database.

    Args:
        session: Database session
        analysis_id: UUID of the analysis
        agent_type: Type of agent (e.g., "tech_comparator")
        findings: Structured findings dictionary
        confidence_score: Optional confidence score (0.0-1.0)
        processing_time_ms: Optional processing time in milliseconds
        status: Execution status (default: "success")
        error_code: Optional error code if status is "failed" or "skipped"
        error_message: Optional error message if status is "failed" or "skipped"

    Returns:
        Created AgentFinding instance

    Raises:
        ValueError: If Analysis record does not exist (foreign key constraint)

    """
    # Verify Analysis exists before saving finding (prevents foreign key violations)
    from sqlalchemy import select

    from app.db.models.analysis import Analysis

    result = await session.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        error_msg = (
            f"Analysis record with id={analysis_id} does not exist. "
            "Analysis must be created before agents can save findings."
        )
        raise ValueError(error_msg)

    finding = AgentFinding(
        analysis_id=analysis_id,
        agent_type=agent_type,
        findings=findings,
        confidence_score=confidence_score,
        processing_time_ms=processing_time_ms,
        status=status,
        error_code=error_code,
        error_message=error_message,
    )
    session.add(finding)
    await session.commit()
    await session.refresh(finding)
    return finding


async def record_agent_execution(  # noqa: PLR0913
    analysis_id: AnalysisID,
    agent_type: str,
    status: str,
    findings: dict[str, object] | None = None,
    confidence_score: float | None = None,
    processing_time_ms: int | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    """Record agent execution to database with automatic session management.

    This is a convenience wrapper around save_agent_finding() that handles
    its own database session and error logging. Use this function from agent
    nodes to reduce boilerplate.

    Args:
        analysis_id: AnalysisID (str representation of UUID)
        agent_type: Type of agent (e.g., "tech_comparator")
        status: Execution status ("success", "failed", "skipped")
        findings: Optional structured findings dictionary
        confidence_score: Optional confidence score (0.0-1.0)
        processing_time_ms: Optional processing time in milliseconds
        error_code: Optional error code if status is "failed" or "skipped"
        error_message: Optional error message if status is "failed" or "skipped"

    Note:
        - Creates its own database session (no session parameter needed)
        - Catches and logs database errors without crashing the workflow
        - For success status, findings dict is required
        - For failed/skipped status, findings can be None (empty dict will be used)

    Example:
        >>> # Success case
        >>> await record_agent_execution(
        ...     analysis_id=analysis_id,
        ...     agent_type="tech_comparator",
        ...     status=AgentStatus.SUCCESS,
        ...     findings={"comparison": "..."},
        ...     confidence_score=0.85,
        ...     processing_time_ms=1234,
        ... )
        >>>
        >>> # Failure case
        >>> await record_agent_execution(
        ...     analysis_id=analysis_id,
        ...     agent_type="tech_comparator",
        ...     status=AgentStatus.FAILED,
        ...     error_code="TECH_COMPARATOR_FAILED",
        ...     error_message="LLM API timeout",
        ...     processing_time_ms=5000,
        ... )

    """
    # Use empty dict for findings if not provided (for failures/skipped)
    findings_to_save = findings if findings is not None else {}

    # Convert analysis_id to UUID if it's a string
    analysis_uuid = UUID(analysis_id) if isinstance(analysis_id, str) else analysis_id

    # Get database session
    session_factory = get_session_factory()
    try:
        async with session_factory() as session:
            await save_agent_finding(
                session=session,
                analysis_id=analysis_uuid,
                agent_type=agent_type,
                findings=findings_to_save,
                confidence_score=confidence_score,
                processing_time_ms=processing_time_ms,
                status=status,
                error_code=error_code,
                error_message=error_message,
            )
            logger.info(
                "agent_execution_recorded",
                agent_type=agent_type,
                analysis_id=str(analysis_id),
                status=status,
                error_code=error_code,
                processing_time_ms=processing_time_ms,
            )
    except Exception as e:
        # Log database errors but don't crash the workflow
        logger.error(
            "failed_to_record_agent_execution",
            agent_type=agent_type,
            analysis_id=str(analysis_id),
            status=status,
            error=str(e),
            exc_info=True,
        )


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
        analysis_id=str(analysis_id),  # Convert UUID to string for JSON serialization
        stage=stage_name,
        status=status,
        agent_type=agent_type,  # Keep agent_type in details for debugging
        **kwargs,
    )


async def handle_agent_node_error(
    error: BaseException,  # BaseException to handle GeneratorExit (not Exception subclass)
    analysis_id: AnalysisID,
    agent_type: str,
    duration: float,
    trace_id: str | None,
) -> dict[str, object]:
    """Handle errors in agent node execution and return appropriate result.

    This helper centralizes error handling logic to reduce return statements
    in agent nodes (PLR0911 compliance).

    Args:
        error: Exception that occurred
        analysis_id: UUID of the analysis
        agent_type: Type of agent (e.g., "code_quality_critic")
        duration: Execution duration in seconds
        trace_id: Optional Langfuse trace ID

    Returns:
        Dictionary with empty agent_findings list

    """
    from app.core.timeout_config import STEP_TIMEOUT
    from app.domains.analysis.constants.error_codes import (
        AGENT_CANCELLED,
        AGENT_LLM_ERROR,
        AGENT_TIMEOUT,
    )
    from app.domains.analysis.services.persistence.error_recorder import error_recorder

    processing_time_ms = int(duration * 1000)
    error_type = type(error).__name__

    # Handle specific exception types
    if isinstance(error, GeneratorExit):
        # GeneratorExit during execution (cancellation/timeout)
        logger.warning(
            "agent_node_cancelled",
            agent_type=agent_type,
            analysis_id=str(analysis_id),
            exception_type="GeneratorExit",
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,
        )
        await record_agent_execution(
            analysis_id=analysis_id,
            agent_type=agent_type,
            status=AgentStatus.FAILED,
            error_code=AGENT_CANCELLED,
            error_message="Agent execution cancelled",
            processing_time_ms=processing_time_ms,
        )
        return {"agent_findings": []}

    if isinstance(error, TimeoutError):
        # Agent execution exceeded timeout
        error_code = f"{agent_type.upper()}_TIMEOUT"
        error_message = "Agent execution timed out"

        await emit_agent_progress(
            analysis_id,
            agent_type,
            "failed",
            error=error_message,
            error_code=error_code,
            processing_time_ms=processing_time_ms,
        )

        # Record error to database
        await error_recorder.record(
            analysis_id=analysis_id,
            error_code=error_code,
            error_message=error_message,
            stage=agent_type,
        )

        await record_agent_execution(
            analysis_id=analysis_id,
            agent_type=agent_type,
            status=AgentStatus.FAILED,
            error_code=AGENT_TIMEOUT,
            error_message=str(error)[:2000],
            processing_time_ms=processing_time_ms,
        )

        logger.warning(
            f"{agent_type}_timeout",
            analysis_id=str(analysis_id),
            duration_seconds=duration,
            timeout_seconds=STEP_TIMEOUT,
        )
        return {"agent_findings": []}

    if isinstance(error, ValueError):
        # Specificity validation failed
        error_code = f"{agent_type.upper()}_SPECIFICITY_FAILED"
        error_message = f"Specificity validation failed: {error!r}"

        await emit_agent_progress(
            analysis_id,
            agent_type,
            "failed",
            error=error_message,
            error_code=error_code,
            processing_time_ms=processing_time_ms,
        )

        # Record error to database
        await error_recorder.record(
            analysis_id=analysis_id,
            error_code=error_code,
            error_message=str(error),
            stage=agent_type,
        )

        await record_agent_execution(
            analysis_id=analysis_id,
            agent_type=agent_type,
            status=AgentStatus.FAILED,
            error_code=AGENT_LLM_ERROR,
            error_message=str(error)[:2000],
            processing_time_ms=processing_time_ms,
        )

        logger.warning(
            f"{agent_type}_specificity_failed",
            analysis_id=str(analysis_id),
            error=str(error),
            duration_seconds=duration,
        )
        return {"agent_findings": []}

    # Unexpected errors (database, LLM API, etc.)
    error_code = f"{agent_type.upper()}_FAILED"
    error_message = str(error)

    await emit_agent_progress(
        analysis_id,
        agent_type,
        "failed",
        error=error_message,
        error_code=error_code,
        processing_time_ms=processing_time_ms,
    )

    # Record error to database
    await error_recorder.record(
        analysis_id=analysis_id,
        error_code=error_code,
        error_message=error_message,
        stage=agent_type,
    )

    await record_agent_execution(
        analysis_id=analysis_id,
        agent_type=agent_type,
        status=AgentStatus.FAILED,
        error_code=AGENT_LLM_ERROR,
        error_message=str(error)[:2000],
        processing_time_ms=processing_time_ms,
    )

    logger.error(
        "agent_node_failed",
        agent_type=agent_type,
        analysis_id=str(analysis_id),
        error_type=error_type,
        error=error_message,
        duration_seconds=duration,
        step_timeout=STEP_TIMEOUT,
        trace_id=trace_id,
        handled_gracefully=True,  # Returns empty findings, doesn't break workflow
        exc_info=error,  # Pass exception object for traceback logging
    )
    return {"agent_findings": []}
