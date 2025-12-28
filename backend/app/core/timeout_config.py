"""Timeout configuration constants and helpers for LangGraph.

This module centralizes timeout values and provides helpers for
creating RunnableConfig for LangGraph execution.

Issue #536: Consolidated timeout architecture with tiered strategy.

## Tiered Timeout Architecture

We use a **tiered timeout strategy** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: Workflow-Level (WORKFLOW_TIMEOUT = 900s)             │
│  └── Total workflow budget, external monitoring                 │
│                                                                 │
│  LAYER 2: Node-Level (STEP_TIMEOUT = 300s)                     │
│  └── LangGraph's built-in per-node timeout                     │
│  └── Set on compiled graph: graph.step_timeout = STEP_TIMEOUT  │
│  └── Single source of truth for node execution limits          │
│                                                                 │
│  LAYER 3: Operation-Level (asyncio.timeout)                    │
│  └── For discrete async operations INSIDE nodes                │
│  └── ✅ OK: LLM calls, DB queries, HTTP requests               │
│  └── ❌ FORBIDDEN: Around async generators (PEP 789 violation) │
│                                                                 │
│  LAYER 4: Bulkhead (see bulkhead.py)                           │
│  └── Concurrency control, separate concern from timeout        │
└─────────────────────────────────────────────────────────────────┘
```

## When to Use `asyncio.timeout()`

`asyncio.timeout()` is **acceptable** for discrete async operations that:
1. Don't contain `yield` statements (no generators)
2. Complete with a single `await` (no streaming)
3. Need sub-node granularity (e.g., individual LLM calls)

**Examples of CORRECT usage:**
```python
# ✅ OK - discrete LLM call, no generator
async with asyncio.timeout(LLM_CALL_TIMEOUT):
    result = await llm.ainvoke(messages)

# ✅ OK - discrete DB query
async with asyncio.timeout(DB_QUERY_TIMEOUT):
    rows = await session.execute(query)
```

**Examples of FORBIDDEN usage (PEP 789 violation):**
```python
# ❌ FORBIDDEN - yield inside timeout scope
async with asyncio.timeout(30):
    async for chunk in stream:  # Generator!
        yield chunk  # PEP 789 violation!

# ❌ FORBIDDEN - astream creates generator
async with asyncio.timeout(30):
    async for event in agent.astream(input):  # Generator!
        process(event)
```

## GeneratorExit Handling

`GeneratorExit` is a `BaseException` (not `Exception`) that occurs when:
- LangGraph's `step_timeout` cancels a node execution
- An async generator is closed/cancelled

**Best Practice**: Handle `GeneratorExit` only at workflow boundaries:
- Orchestrator level: Log and update status appropriately
- Node level: Let it propagate (LangGraph handles cleanup)
- Avoid excessive try/except GeneratorExit blocks

## Timeout Constants

All timeout values are centralized here for consistency:

**Active (used in code):**
- `STEP_TIMEOUT`: Node-level timeout on compiled graph (300s)
- `LLM_CALL_TIMEOUT`: Per-LLM invocation timeout (60s)
- `SYNTHESIS_TIMEOUT`: Aggregation synthesis timeout (180s)
- `COMPRESSION_TIMEOUT`: Finding compression timeout (30s)
- `CONTEXT_INJECTION_TIMEOUT`: Proactive memory fetch (30s)
- `EVALUATOR_TIMEOUT`: Quality gate evaluator (30s)
- `RERANKER_TIMEOUT`: Search reranking (configurable)

**Reference (for documentation):**
- `WORKFLOW_TIMEOUT`: Entire workflow budget (900s)
- `STREAMING_TIMEOUT`: Streaming operations (120s)

## Retry Configuration

Retry handling is managed by LangChain's built-in `max_retries` parameter.
Configured via `settings.LLM_MAX_RETRIES` at model initialization.

## References

- LangGraph `step_timeout`: https://python.langchain.com/docs/how_to/migrate_agent/
- PEP 789: https://peps.python.org/pep-0789/ (yield in cancellation scopes)
- AnyIO structured concurrency: https://anyio.readthedocs.io/en/stable/why.html
"""

import os

from langchain_core.runnables import RunnableConfig

# =============================================================================
# LAYER 1: Workflow-Level Timeout
# =============================================================================
# Total budget for entire workflow execution
WORKFLOW_TIMEOUT: float = 900.0  # 15 minutes

# =============================================================================
# LAYER 2: Node-Level Timeout (LangGraph step_timeout)
# =============================================================================
# Single source of truth for node execution limits
# Set on compiled graph: graph.step_timeout = STEP_TIMEOUT
# Override via SKILLFORGE_STEP_TIMEOUT env var for complex regeneration tasks
_step_timeout_env = os.environ.get("SKILLFORGE_STEP_TIMEOUT")
STEP_TIMEOUT: float = float(_step_timeout_env) if _step_timeout_env else 300.0  # 5 min

# =============================================================================
# LAYER 3: Operation-Level Timeouts (asyncio.timeout for discrete awaits)
# =============================================================================
# These are safe to use with asyncio.timeout() because they wrap discrete
# await calls, not generators. See module docstring for PEP 789 compliance.

# Per-LLM invocation timeout (used in invocation.py)
# Triggers fallback model if primary hangs
LLM_CALL_TIMEOUT: float = 60.0  # 1 minute per LLM call

# Alias for backward compatibility
AGENT_TIMEOUT: float = LLM_CALL_TIMEOUT

# Aggregation synthesis timeout (3 phases x 60s each)
# Issue #299-304: Increased to allow detailed schema processing
SYNTHESIS_TIMEOUT: float = 180.0  # 3 minutes total, ~60s per phase

# Per-phase timeout for synthesis (SYNTHESIS_TIMEOUT // 3)
SYNTHESIS_PHASE_TIMEOUT: float = SYNTHESIS_TIMEOUT / 3  # 60s per phase

# Finding compression timeout (fast operation)
# Used in compress_findings.py for LLM compression calls
COMPRESSION_TIMEOUT: float = 30.0  # 30 seconds

# Proactive memory context injection timeout
# Used in inject_context_node.py for vector similarity search
CONTEXT_INJECTION_TIMEOUT: float = 30.0  # 30 seconds

# Quality gate evaluator timeout
# Prevents one slow evaluator from consuming entire step_timeout budget
EVALUATOR_TIMEOUT: float = 30.0  # 30 seconds per evaluator

# MCP tool operation timeout (used in mcp/client.py)
MCP_OPERATION_TIMEOUT: float = 30.0  # 30 seconds

# =============================================================================
# Reference Timeouts (not actively used, for documentation)
# =============================================================================
# Streaming operations - reference value
STREAMING_TIMEOUT: float = 120.0  # 2 minutes


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
