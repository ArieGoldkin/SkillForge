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

from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage

from app.core.config import settings
from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.services.sse_helpers import emit_streaming_event
from app.workflows.nodes.agent_tools import AGENT_TOOLS, TOOL_TO_AGENT_MAP
from app.workflows.nodes.supervisor_config import SUPERVISOR_PROMPT

logger = get_logger(__name__)

# Initialize supervisor agent
_model = init_chat_model(f"ollama:{settings.OLLAMA_MODEL}")
_supervisor_agent: Any = create_agent(
    _model,
    tools=AGENT_TOOLS,
    system_prompt=SUPERVISOR_PROMPT,
)


def _parse_tool_calls_from_messages(messages: list[Any]) -> list[str]:
    """Extract agent names from tool calls in agent response messages.

    Args:
        messages: List of messages from supervisor agent response

    Returns:
        List of agent names that were selected (tools that were called)

    """
    selected_agents: list[str] = []
    for message in messages:
        if isinstance(message, AIMessage) and message.tool_calls:
            for tool_call in message.tool_calls:
                tool_name = tool_call.get("name", "")
                if tool_name in TOOL_TO_AGENT_MAP:
                    agent_name = TOOL_TO_AGENT_MAP[tool_name]
                    if agent_name not in selected_agents:
                        selected_agents.append(agent_name)
    return selected_agents


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
        # Prepare content for supervisor (limit to 2000 chars for prompt efficiency)
        content_preview = content[:2000] if len(content) > 2000 else content
        user_prompt = f"Content Type: {content_type}\n\nContent:\n{content_preview}"

        # Invoke supervisor agent
        result = _supervisor_agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": user_prompt,
                    }
                ]
            }
        )

        # Extract tool calls from response messages
        messages = result.get("messages", [])
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

        return {"supervisor_decision": supervisor_decision}

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
