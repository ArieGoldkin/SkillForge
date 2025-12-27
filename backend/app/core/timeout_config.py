"""Timeout configuration constants and helpers for LangGraph.

This module centralizes timeout values and provides helpers for
creating RunnableConfig for LangGraph execution.

## Timeout Strategy

We use a **single timeout strategy** following LangGraph best practices:

**Graph-level timeout (`step_timeout`)**: Set on the compiled graph (90s)
- LangGraph's built-in mechanism for node-level timeouts
- Single source of truth for all timeout handling
- Cancels tasks when exceeded, which can cause `GeneratorExit` in async generators
- This is expected behavior and handled gracefully at the node level

**Why not use `asyncio.timeout()`?**
- Using both `asyncio.timeout()` and `step_timeout` creates nested timeouts
- Yielding inside `asyncio.timeout()` cancellation scope violates PEP 789
- LangGraph's `step_timeout` is the recommended approach per official documentation
- Simpler code with single timeout mechanism

## GeneratorExit Handling

`GeneratorExit` is a `BaseException` (not `Exception`) that occurs when:
- LangGraph's `step_timeout` cancels a node execution
- An async generator is closed/cancelled

**Best Practice**: Handle `GeneratorExit` gracefully at the node level:
- In node functions: Catch and return empty findings for graceful degradation
- In runner functions: Catch and return empty dict for graceful degradation
- Don't convert to `TimeoutError` - handle as cancellation per Python best practices

This allows the workflow to continue even when individual agents timeout,
providing graceful degradation rather than complete failure.

**Note**: With proper timeout strategy (step_timeout only), `GeneratorExit` should
rarely occur. The handling in nodes serves as a safety net.

## Timeout Constants

The following constants are provided for reference/documentation:
- `AGENT_TIMEOUT`: Reference value (not used in code - step_timeout handles it)
- `SYNTHESIS_TIMEOUT`: Reference value (not used in code - step_timeout handles it)
- `STREAMING_TIMEOUT`: Reference value (not used in code - step_timeout handles it)
- `STEP_TIMEOUT`: **Active** - Used on compiled graph (90s)
- `WORKFLOW_TIMEOUT`: Reference value for entire workflow duration

## Retry Configuration

Retry handling is managed by LangChain's built-in `max_retries` parameter in `init_chat_model()`.
This is configured via `settings.LLM_MAX_RETRIES` and applied at model initialization.
LangChain handles retry logic internally with proper async behavior (no blocking operations).

## References

- LangGraph `step_timeout`: https://python.langchain.com/docs/how_to/migrate_agent/
- PEP 789: https://peps.python.org/pep-0789/ (avoiding yield in cancellation scopes)
"""

import os

from langchain_core.runnables import RunnableConfig

# Agent execution timeout (in seconds)
AGENT_TIMEOUT: float = 60.0  # 60 seconds (1 minute) - LLM calls should complete faster

# LLM synthesis timeout (in seconds)
# Issue #299-304: Increased from 90s to 180s to allow 60s per phase (3 phases)
# The detailed schema prompts require more LLM processing time
SYNTHESIS_TIMEOUT: float = 180.0  # 180 seconds (3 minutes) - allow 60s per phase

# Streaming timeout (in seconds)
STREAMING_TIMEOUT: float = 120.0  # 120 seconds (2 minutes) - streaming should be faster

# Graph step timeout (in seconds) - set on compiled graph
# This is the single source of truth for timeout handling
# Override via SKILLFORGE_STEP_TIMEOUT env var for complex regeneration tasks
_step_timeout_env = os.environ.get("SKILLFORGE_STEP_TIMEOUT")
STEP_TIMEOUT: float = float(_step_timeout_env) if _step_timeout_env else 300.0  # Default 5 min

# Workflow-level timeout (in seconds) - for entire workflow
WORKFLOW_TIMEOUT: float = 900.0  # 900 seconds (15 minutes) - entire workflow should complete faster

# Issue #536: Per-evaluator timeout for quality gate (in seconds)
# EXCEPTION TO THE asyncio.timeout() RULE - See docstring for why this is acceptable:
# 1. Wraps non-generator async call (no yield, no PEP 789 violation)
# 2. Provides graceful degradation (neutral score on timeout, not failure)
# 3. Prevents one slow evaluator from consuming entire step_timeout budget
EVALUATOR_TIMEOUT: float = 30.0  # 30 seconds per evaluator call


def create_runnable_config(
    thread_id: str | None = None,
    metadata: dict[str, str] | None = None,
    tags: list[str] | None = None,
    langfuse_prompt: object | None = None,
) -> RunnableConfig:
    """Create RunnableConfig for LangGraph execution.

    Note: Python RunnableConfig does not support timeout parameter.
    Timeout handling is managed by `step_timeout` on the compiled graph.
    This is the recommended approach per LangGraph best practices.

    This function also integrates Langfuse CallbackHandler for LLM observability,
    enabling token count tracking and cost visibility in the Langfuse dashboard.

    Args:
        thread_id: Optional thread ID for checkpointing
        metadata: Optional metadata dict for tracing (e.g., agent_type, analysis_id)
        tags: Optional list of tags for categorization (e.g., ["agent", "tech_comparator"])
        langfuse_prompt: Optional Langfuse TextPromptClient for prompt-to-generation linkage
            (Issue #564: Links prompts to generations in Langfuse UI)

    Returns:
        RunnableConfig with thread_id, metadata, tags, and Langfuse callbacks if enabled

    Example:
        >>> config = create_runnable_config(
        ...     thread_id="abc-123",
        ...     metadata={"agent_type": "tech_comparator", "analysis_id": "abc-123"},
        ...     tags=["agent", "tech_comparator"],
        ... )
        >>> config["configurable"]["thread_id"]  # "abc-123"
        >>> config["metadata"]["agent_type"]  # "tech_comparator"
        >>> config["tags"]  # ["agent", "tech_comparator"]
        >>> # If Langfuse enabled, config["callbacks"] contains CallbackHandler

    """
    from app.core.langfuse_service import get_langfuse_service

    config: RunnableConfig = {}

    # Add Langfuse callback for LLM token/cost tracking
    service = get_langfuse_service()
    if service:
        callback = service.get_callback_handler()
        if callback:
            config["callbacks"] = [callback]

    # Issue #564: Link prompt to generation via metadata
    # The langfuse_prompt in metadata is automatically picked up by the CallbackHandler
    # and links the generation to the prompt version in Langfuse UI
    if langfuse_prompt is not None:
        # Copy metadata to avoid modifying caller's dict, then add langfuse_prompt
        config["metadata"] = dict(metadata) if metadata else {}
        config["metadata"]["langfuse_prompt"] = langfuse_prompt
    elif metadata:
        config["metadata"] = metadata

    if tags:
        config["tags"] = tags

    if thread_id:
        config["configurable"] = {"thread_id": thread_id}

    return config
