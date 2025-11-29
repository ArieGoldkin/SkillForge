"""Agent invocation logic with fallback strategies.

This module handles different agent invocation methods:
- Streaming (preferred)
- Async invoke (fallback)
- Sync invoke in thread pool (last resort)
"""

import asyncio
from typing import cast

from langchain_core.runnables import Runnable

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.workflows.agents.streaming import stream_agent_response

logger = get_logger(__name__)


async def invoke_agent(
    agent: Runnable,
    input_messages: dict[str, list[dict[str, str]]],
    analysis_id: AnalysisID,
    agent_type: str,
    timeout: float,
) -> dict[str, object]:
    """Invoke agent with automatic fallback strategy.

    Tries streaming first, then async invoke, then sync invoke.

    Args:
        agent: Agent instance to invoke
        input_messages: Input messages for the agent
        analysis_id: UUID of the analysis
        agent_type: Type of agent for logging
        timeout: Maximum time to wait

    Returns:
        Result dictionary from agent execution

    Raises:
        GeneratorExit: If stream is closed externally
        TimeoutError: If invocation exceeds timeout
        Exception: For other invocation errors

    """
    # Check if agent supports streaming (must be callable, not just present)
    agent_has_streaming = callable(getattr(agent, "astream", None))
    if agent_has_streaming:
        # Stream agent execution (preferred - shows progress)
        return await stream_agent_response(
            agent=agent,
            input_messages=input_messages,
            analysis_id=analysis_id,
            agent_type=agent_type,
            timeout=timeout,
        )
    elif hasattr(agent, "ainvoke"):
        # Fallback: async invoke without streaming
        result = await asyncio.wait_for(
            agent.ainvoke(input_messages),
            timeout=timeout,
        )
        # LangChain returns Any, but we know it's a dict[str, object] for our use case
        return cast(dict[str, object], result)
    else:
        # Fallback: run sync invoke in thread pool
        result = await asyncio.wait_for(
            asyncio.to_thread(agent.invoke, input_messages),
            timeout=timeout,
        )
        # LangChain returns Any, but we know it's a dict[str, object] for our use case
        return cast(dict[str, object], result)


