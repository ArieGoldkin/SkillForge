"""Agent execution task for parallel agent processing.

This module handles the execution of multiple agents in parallel with
proper error isolation, timeout handling, and GeneratorExit support.
"""

import asyncio
from typing import TYPE_CHECKING

from langsmith import traceable

if TYPE_CHECKING:
    pass  # BaseException and GeneratorExit are builtins, no import needed

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.workflows.tasks.agent_runners import (
    run_code_quality_critic_with_session,
    run_dependency_mapper_with_session,
    run_implementation_planner_with_session,
    run_integration_feasibility_with_session,
    run_performance_analyst_with_session,
    run_security_auditor_with_session,
    run_tech_comparator_with_session,
    run_trend_validator_with_session,
)

logger = get_logger(__name__)


@traceable(
    name="execute_agents",
    run_type="chain",
    tags=["workflow", "node"],
)
async def execute_agents(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    selected_agents: list[str],
) -> list[dict[str, object]]:
    """Execute selected agents in parallel.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        selected_agents: List of agent names to execute

    Returns:
        List of agent findings dictionaries

    """
    if not selected_agents:
        logger.debug("workflow_no_agents_selected", analysis_id=analysis_id)
        return []

    logger.info(
        "workflow_agents_starting",
        analysis_id=analysis_id,
        selected_agents=selected_agents,
        agent_count=len(selected_agents),
    )

    # Create tasks for selected agents (each with its own session)
    agent_tasks = []
    if "tech_comparator" in selected_agents:
        agent_tasks.append(run_tech_comparator_with_session(content, content_type, analysis_id))
    if "integration_feasibility" in selected_agents:
        agent_tasks.append(
            run_integration_feasibility_with_session(content, content_type, analysis_id)
        )
    if "implementation_planner" in selected_agents:
        agent_tasks.append(
            run_implementation_planner_with_session(content, content_type, analysis_id)
        )
    if "security_auditor" in selected_agents:
        agent_tasks.append(run_security_auditor_with_session(content, content_type, analysis_id))
    if "performance_analyst" in selected_agents:
        agent_tasks.append(run_performance_analyst_with_session(content, content_type, analysis_id))
    if "code_quality_critic" in selected_agents:
        agent_tasks.append(run_code_quality_critic_with_session(content, content_type, analysis_id))
    if "trend_validator" in selected_agents:
        agent_tasks.append(run_trend_validator_with_session(content, content_type, analysis_id))
    if "dependency_mapper" in selected_agents:
        agent_tasks.append(run_dependency_mapper_with_session(content, content_type, analysis_id))

    if not agent_tasks:
        logger.warning(
            "workflow_no_valid_agents",
            analysis_id=analysis_id,
            selected_agents=selected_agents,
        )
        return []

    # Execute agents in parallel with timeout and error isolation
    # Each agent manages its own database session independently
    agent_timeout = 120.0  # 120 seconds (2 minutes) per agent for complex LLM calls
    try:
        # asyncio.gather returns a tuple, convert to list for type consistency
        # return_exceptions=True means results can be Exception or BaseException
        # Note: mypy has issues with asyncio.gather return types, but runtime is correct
        findings_tuple = await asyncio.wait_for(
            asyncio.gather(*agent_tasks, return_exceptions=True),  # type: ignore[arg-type]
            timeout=agent_timeout * len(agent_tasks),  # Total timeout for all agents
        )
        # Convert tuple to list - mypy sees BaseException but we filter it below
        findings_list = list(findings_tuple)  # type: ignore[arg-type]

        # Filter out exceptions and collect successful results
        # Note: return_exceptions=True means results can be Exception or BaseException
        agent_findings: list[dict[str, object]] = []
        for i, result in enumerate(findings_list):
            if isinstance(result, GeneratorExit):
                agent_name = selected_agents[i] if i < len(selected_agents) else "unknown"
                logger.warning(
                    "workflow_agent_cancelled",
                    analysis_id=analysis_id,
                    agent_type=agent_name,
                    reason="Generator closed externally",
                )
            elif isinstance(result, (Exception, BaseException)):
                agent_name = selected_agents[i] if i < len(selected_agents) else "unknown"
                logger.error(
                    "workflow_agent_failed",
                    analysis_id=analysis_id,
                    agent_type=agent_name,
                    error=str(result),
                    exc_info=True,
                )
            elif isinstance(result, dict):
                agent_findings.append(result)

        logger.info(
            "workflow_agents_complete",
            analysis_id=analysis_id,
            successful_count=len(agent_findings),
            total_count=len(agent_tasks),
        )
    except TimeoutError:
        logger.exception(
            "workflow_agents_timeout",
            analysis_id=analysis_id,
            timeout=agent_timeout * len(agent_tasks),
            agent_count=len(agent_tasks),
        )
        # Return any findings that completed before timeout
        return []
    else:
        return agent_findings
