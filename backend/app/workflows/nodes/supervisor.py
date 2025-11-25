"""Supervisor node for routing content analysis to specialized agents.

This module implements the supervisor pattern using LangChain v1.0's create_agent.
The supervisor analyzes extracted content and decides which of 8 specialized
sub-agents should analyze the content.

Architecture:
    - Supervisor agent uses create_agent with 8 tools (one per sub-agent)
    - Each tool represents "select this agent for analysis"
    - Supervisor analyzes content and calls relevant tools
    - Tool calls are parsed to extract selected agents list
    - Returns structured decision: {"agents": [...], "priority": [...]}
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Any, TypedDict

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, before_model, dynamic_prompt, wrap_model_call
from langchain_core.messages import AIMessage
from langsmith import traceable

from app.core.config import settings
from app.core.constants import SUPERVISOR_CONTENT_PREVIEW_LENGTH
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.types import AnalysisID
from app.services.sse_helpers import emit_streaming_event
from app.workflows.nodes.agent_tools import AGENT_TOOLS, TOOL_TO_AGENT_MAP
from app.workflows.nodes.supervisor_config import SUPERVISOR_PROMPT


# Context schema for dynamic prompts and middleware
class SupervisorContext(TypedDict):
    """Runtime context for supervisor agent."""

    content_type: str
    analysis_id: str


@dynamic_prompt
def dynamic_supervisor_prompt(request: ModelRequest) -> str:
    """Generate context-aware system prompt based on content type and environment.

    Adapts the supervisor prompt based on:
    - Content type (article, video, repo) for specialized instructions
    - Analysis context for better routing decisions
    """
    base_prompt = SUPERVISOR_PROMPT

    # Access runtime context if available
    if hasattr(request, "runtime") and hasattr(request.runtime, "context"):
        context = request.runtime.context
        content_type = context.get("content_type", "article")

        # Add content-type-specific instructions
        if content_type == "video":
            base_prompt += (
                "\n\nNote: This is video content. Focus on visual elements, "
                "transcript analysis, and video-specific technologies."
            )
        elif content_type == "repo":
            base_prompt += (
                "\n\nNote: This is repository content. Focus on code structure, "
                "dependencies, and implementation patterns."
            )
        # article is default, no extra instructions needed

    return base_prompt


@before_model
def log_supervisor_before_model(state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
    """Log supervisor agent invocation before model call."""
    if hasattr(runtime, "context"):
        context = runtime.context
        content_type = context.get("content_type", "unknown")
        analysis_id = context.get("analysis_id", "unknown")
        logger.debug(
            "supervisor_agent_invoking",
            analysis_id=analysis_id,
            content_type=content_type,
            message_count=len(state.get("messages", [])),
        )
    return None


@wrap_model_call
async def retry_supervisor_model(
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
            # Handle both sync and async handlers
            if asyncio.iscoroutinefunction(handler):
                return await handler(request)
            return handler(request)
        except (ConnectionError, TimeoutError, ValueError) as e:
            if attempt == max_attempts - 1:
                # Last attempt failed, re-raise
                logger.error(
                    "supervisor_model_call_failed",
                    attempt=attempt + 1,
                    error=str(e),
                    exc_info=True,
                )
                raise

            # Exponential backoff: base_delay * (2^attempt)
            # Default: 1.0s * (1, 2, 4) = 1s, 2s, 4s
            # Test: 0.1s * (1, 2, 4) = 0.1s, 0.2s, 0.4s
            base_delay = settings.LLM_RETRY_DELAY_BASE
            wait_time = base_delay * (2**attempt)
            logger.warning(
                "supervisor_model_call_retry",
                attempt=attempt + 1,
                max_attempts=max_attempts,
                wait_time=wait_time,
                base_delay=base_delay,
                error=str(e),
            )
            await asyncio.sleep(wait_time)

    # Should never reach here, but just in case
    msg = "Retry loop exhausted without success"
    raise RuntimeError(msg)


logger = get_logger(__name__)


class SupervisorAgentManager:
    """Manages supervisor agent instance with lazy initialization."""

    def __init__(self) -> None:
        """Initialize manager with no agent."""
        self._agent: Any | None = None

    def get_agent(self) -> Any:
        """Get or create the supervisor agent instance (lazy initialization).

        Initializes the supervisor agent on first access to avoid import-time
        initialization issues during test discovery.

        Uses dynamic prompts and middleware hooks for:
        - Context-aware prompt generation (content type, analysis context)
        - Request logging before model calls
        - Retry logic with exponential backoff

        Returns:
            The supervisor agent instance

        """
        if self._agent is None:
            _model = get_chat_model()
            self._agent = create_agent(
                _model,
                tools=AGENT_TOOLS,
                middleware=[
                    dynamic_supervisor_prompt,
                    log_supervisor_before_model,
                    retry_supervisor_model,
                ],
                context_schema=SupervisorContext,
            )
        return self._agent


# Module-level manager instance (avoids global variable)
_supervisor_manager = SupervisorAgentManager()


def _get_supervisor_agent() -> Any:
    """Get supervisor agent instance."""
    return _supervisor_manager.get_agent()


def _parse_tool_calls_from_messages(messages: list[Any]) -> list[str]:
    """Extract agent names from tool calls in agent response messages.

    Uses LangChain 1.1.0's unified content_blocks API for parsing, which supports
    reasoning blocks, tool calls, and text content. Falls back to tool_calls for
    compatibility with older message formats.

    Args:
        messages: List of messages from supervisor agent response

    Returns:
        List of agent names that were selected (tools that were called)

    """
    selected_agents: list[str] = []
    for message in messages:
        if not isinstance(message, AIMessage):
            continue

        # Try content_blocks API first (LangChain 1.1.0+ unified interface)
        if hasattr(message, "content_blocks") and message.content_blocks:
            for block in message.content_blocks:
                # Handle tool call blocks from content_blocks
                if isinstance(block, dict):
                    block_type = block.get("type", "")
                    if block_type in {"tool_call", "tool_call_chunk"}:
                        tool_name = block.get("name", "")
                        if tool_name in TOOL_TO_AGENT_MAP:
                            agent_name = TOOL_TO_AGENT_MAP[tool_name]
                            if agent_name not in selected_agents:
                                selected_agents.append(agent_name)

        # Fallback to tool_calls for compatibility
        elif message.tool_calls:
            for tool_call in message.tool_calls:
                tool_name = (
                    tool_call.get("name", "")
                    if isinstance(tool_call, dict)
                    else getattr(tool_call, "name", "")
                )
                if tool_name in TOOL_TO_AGENT_MAP:
                    agent_name = TOOL_TO_AGENT_MAP[tool_name]
                    if agent_name not in selected_agents:
                        selected_agents.append(agent_name)

    return selected_agents


def _raise_no_messages_error(analysis_id: AnalysisID, used_streaming: bool) -> None:
    """Raise error when supervisor returns no messages."""
    logger.error(
        "supervisor_no_messages_received",
        analysis_id=analysis_id,
        used_streaming=used_streaming,
    )
    msg = "Supervisor agent returned no messages"
    raise RuntimeError(msg)


async def _stream_supervisor_response(
    supervisor_agent: Any,
    input_messages: dict[str, Any],
    supervisor_context: SupervisorContext,
    agent_config: dict[str, Any],
    analysis_id: AnalysisID,
) -> dict[str, Any] | None:
    """Stream supervisor agent response and accumulate result.

    Returns:
        Final result dict if streaming succeeds, None if it fails

    """
    accumulated_content = ""
    token_chunk_buffer = ""
    last_emit_time = asyncio.get_event_loop().time()
    batch_interval = 0.1  # Emit batched chunks every 100ms
    min_chunk_size = 10  # Minimum characters before emitting
    final_result = None

    # Type: LangGraph's astream() returns AsyncIterator[dict[str, Any] | Any]
    # Note: AsyncIterator doesn't guarantee aclose(), but AsyncGenerator does
    # We check with hasattr() at runtime
    stream: AsyncIterator[dict[str, Any]] | None = None
    try:
        stream = supervisor_agent.astream(
            input_messages,
            stream_mode="values",
            context=supervisor_context,
            config=agent_config,
        )

        try:
            async for chunk in stream:
                final_result = chunk

                # Early exit: break immediately if we have a complete result with tool calls
                # This prevents waiting for unnecessary streaming chunks
                if chunk.get("messages"):
                    messages = chunk["messages"]
                    latest_message = messages[-1]
                    if hasattr(latest_message, "tool_calls") and latest_message.tool_calls:
                        # Tool calls indicate agent decision is complete, can break early
                        # The finally block will handle proper cleanup via aclose()
                        break

                    # Extract latest message for token streaming (batched)
                    if hasattr(latest_message, "content") and latest_message.content:
                        # Accumulate content
                        new_content = latest_message.content[len(accumulated_content) :]
                        if new_content:
                            accumulated_content = latest_message.content
                            token_chunk_buffer += new_content

                            # Emit batched chunks periodically to reduce SSE overhead
                            current_time = asyncio.get_event_loop().time()
                            time_since_last_emit = current_time - last_emit_time

                            if (
                                len(token_chunk_buffer) >= min_chunk_size
                                or time_since_last_emit >= batch_interval
                            ):
                                await emit_streaming_event(
                                    "progress",
                                    analysis_id=analysis_id,
                                    stage="supervisor",
                                    status="streaming",
                                    token_chunk=token_chunk_buffer,
                                    accumulated_content=accumulated_content,
                                )
                                token_chunk_buffer = ""
                                last_emit_time = current_time

            # Emit any remaining buffered chunks
            if token_chunk_buffer:
                await emit_streaming_event(
                    "progress",
                    analysis_id=analysis_id,
                    stage="supervisor",
                    status="streaming",
                    token_chunk=token_chunk_buffer,
                    accumulated_content=accumulated_content,
                )
        except GeneratorExit:
            # GeneratorExit is raised when Python's garbage collector closes the generator
            # This is expected behavior when breaking from async for loop early
            # We handle it silently - Python handles cleanup automatically per PEP 525
            # Do NOT call aclose() here as it causes double-close and LangSmith error logs
            pass
    except GeneratorExit:
        # GeneratorExit is not an error - it's Python cleaning up the generator
        # Handle silently and continue to fallback
        return None
    except (ConnectionError, TimeoutError, ValueError) as e:
        # Log error but allow fallback to invoke
        logger.warning(
            "supervisor_streaming_error",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        return None

    return final_result


async def _invoke_supervisor_fallback(
    supervisor_agent: Any,
    input_messages: dict[str, Any],
    supervisor_context: SupervisorContext,
    agent_config: dict[str, Any],
    analysis_id: AnalysisID,
) -> dict[str, Any]:
    """Invoke supervisor agent synchronously as fallback.

    Returns:
        Result dict with messages

    """
    logger.info(
        "supervisor_fallback_to_invoke",
        analysis_id=analysis_id,
        reason="streaming_not_available_or_failed",
    )
    # Use async invoke if available, otherwise wrap sync invoke in thread pool
    supervisor_timeout = 120.0  # 120 seconds (2 minutes) max for supervisor
    try:
        if hasattr(supervisor_agent, "ainvoke"):
            # Async invoke (preferred - non-blocking)
            result = await asyncio.wait_for(
                supervisor_agent.ainvoke(
                    input_messages,
                    context=supervisor_context,
                    config=agent_config,
                ),
                timeout=supervisor_timeout,
            )
        else:
            # Fallback: run sync invoke in thread pool to avoid blocking event loop
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    supervisor_agent.invoke,
                    input_messages,
                    context=supervisor_context,
                    config=agent_config,
                ),
                timeout=supervisor_timeout,
            )
    except TimeoutError:
        msg = f"Supervisor agent exceeded timeout of {supervisor_timeout}s"
        logger.exception(
            "supervisor_timeout",
            analysis_id=analysis_id,
            timeout=supervisor_timeout,
        )
        raise TimeoutError(msg) from None
    return result


@traceable(
    name="supervisor_route",
    run_type="chain",
    tags=["workflow", "supervisor"],
)
async def supervisor_route(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
) -> dict[str, Any]:
    """Supervisor decides which agents should analyze the content.

    Uses a LangChain agent to analyze the content and select relevant
    specialized agents by calling their corresponding tools.

    Args:
        content: The extracted text content to analyze
        content_type: Content type (article, video, repo)
        analysis_id: Unique identifier for this analysis

    Returns:
        Dictionary with supervisor_decision containing:
            - agents: List of selected agent names
            - priority: List of priority scores (0.9 for all, simplified)
            - reasoning: Optional brief explanation

    Raises:
        Exception: If supervisor agent invocation fails

    """
    # Emit SSE event: supervisor started
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="supervisor",
        status="running",
    )

    logger.info(
        "workflow_supervisor_started",
        analysis_id=analysis_id,
        content_type=content_type,
        content_length=len(content),
    )

    try:
        # Prepare content for supervisor (limit to constant for prompt efficiency)
        content_preview = (
            content[:SUPERVISOR_CONTENT_PREVIEW_LENGTH]
            if len(content) > SUPERVISOR_CONTENT_PREVIEW_LENGTH
            else content
        )
        user_prompt = f"Content Type: {content_type}\n\nContent:\n{content_preview}"

        # Invoke supervisor agent with streaming (lazy initialization)
        supervisor_agent = _get_supervisor_agent()

        # Stream agent response for real-time token streaming
        # Collect final state for parsing tool calls
        input_messages = {
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ]
        }

        # Stream agent progress and accumulate final result
        # Pass context for dynamic prompts and middleware
        # Also support runtime model configuration via config parameter
        supervisor_context = SupervisorContext(
            content_type=content_type,
            analysis_id=str(analysis_id),
        )

        # Create config for agent invocation (supports runtime model switching)
        agent_config = {"configurable": {}}

        # Note: Runtime model switching can be done via config["configurable"]["model"]
        # Example: config={"configurable": {"model": "gpt-5-nano"}} for cost optimization

        # Try streaming first, fallback to invoke if needed
        final_result = await _stream_supervisor_response(
            supervisor_agent,
            input_messages,
            supervisor_context,
            agent_config,
            analysis_id,
        )

        # Fallback to invoke if streaming not supported or failed
        if final_result is None:
            result = await _invoke_supervisor_fallback(
                supervisor_agent,
                input_messages,
                supervisor_context,
                agent_config,
                analysis_id,
            )
            messages = result.get("messages", [])
        else:
            messages = final_result.get("messages", [])

        # Validate that we have messages before parsing
        if not messages:
            _raise_no_messages_error(analysis_id, final_result is not None)
            return {"supervisor_decision": {}}  # Unreachable, but satisfies type checker

        # Extract tool calls from response messages
        selected_agents = _parse_tool_calls_from_messages(messages)

        # Create supervisor decision
        supervisor_decision = {
            "agents": selected_agents,
            "priority": [0.9] * len(selected_agents),  # Simplified: all agents same priority
            "reasoning": f"Selected {len(selected_agents)} agent(s) based on content analysis",
        }

        # Emit SSE event: supervisor complete
        await emit_streaming_event(
            "progress",
            analysis_id=analysis_id,
            stage="supervisor",
            status="complete",
            agent_count=len(selected_agents),
            selected_agents=selected_agents,
        )

        logger.info(
            "workflow_supervisor_complete",
            analysis_id=analysis_id,
            selected_agents=selected_agents,
            agent_count=len(selected_agents),
        )
    except Exception as e:
        # Emit SSE event: supervisor failed
        await emit_streaming_event(
            "error",
            analysis_id=analysis_id,
            stage="supervisor",
            status="failed",
            error=str(e),
            error_code="SUPERVISOR_FAILED",
        )

        logger.error(
            "workflow_supervisor_failed",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        raise
    else:
        return {"supervisor_decision": supervisor_decision}
