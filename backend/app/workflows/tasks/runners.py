"""Agent runner functions with database session management.

This module provides wrapper functions for each agent that manage
their own database sessions, enabling parallel execution as separate
LangGraph nodes via Send API.

Note: GeneratorExit is handled gracefully (returns empty dict) as it
occurs when timeouts cancel tasks. Other exceptions are allowed to
propagate naturally. Each agent node handles its own exceptions and
returns empty findings on error, allowing other agents to continue.
"""

import time

from langchain_core.tools import BaseTool
from langsmith import get_current_run_tree

from app.core.logging import get_logger
from app.core.timeout_config import STEP_TIMEOUT
from app.core.types import AnalysisID
from app.workflows.agents import (
    run_code_quality_critic,
    run_dependency_mapper,
    run_implementation_planner,
    run_integration_feasibility,
    run_performance_analyst,
    run_security_auditor,
    run_tech_comparator,
    run_trend_validator,
)
from app.workflows.state import AnalysisState

# Note: AsyncSessionLocal is imported lazily inside each function to avoid
# DATABASE_URL validation at import time (required for CI without database)

logger = get_logger(__name__)


async def run_tech_comparator_with_session(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    state: AnalysisState,
) -> dict[str, object]:
    """Run tech comparator with its own database session."""
    from app.db.session import AsyncSessionLocal

    start_time = time.time()

    # Get LangSmith trace ID for correlation if available
    trace_id: str | None = None
    try:
        run_tree = get_current_run_tree()
        if run_tree and hasattr(run_tree, "id"):
            trace_id = str(run_tree.id)
    except Exception:  # noqa: BLE001 - LangSmith may not be available, catch all to continue
        # LangSmith not available or not in trace context - continue without trace_id
        pass

    try:
        async with AsyncSessionLocal() as session:
            return await run_tech_comparator(content, content_type, analysis_id, session, state)
    except GeneratorExit:
        # GeneratorExit occurs when timeout cancels the task - handle gracefully
        duration = time.time() - start_time
        logger.warning(
            "agent_cancelled",
            agent_type="tech_comparator",
            analysis_id=analysis_id,
            exception_type="GeneratorExit",
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,
        )
        return {}  # Return empty dict for graceful degradation
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "agent_failed",
            agent_type="tech_comparator",
            analysis_id=analysis_id,
            error_type=type(e).__name__,
            error=str(e),
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,  # Returns empty dict, doesn't break workflow
            exc_info=True,
        )
        return {}  # Return empty dict on error to allow other agents to continue


async def run_integration_feasibility_with_session(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    state: AnalysisState,
) -> dict[str, object]:
    """Run integration feasibility with its own database session."""
    from app.db.session import AsyncSessionLocal

    start_time = time.time()

    # Get LangSmith trace ID for correlation if available
    trace_id: str | None = None
    try:
        run_tree = get_current_run_tree()
        if run_tree and hasattr(run_tree, "id"):
            trace_id = str(run_tree.id)
    except Exception:  # noqa: BLE001 - LangSmith may not be available, catch all to continue
        # LangSmith not available or not in trace context - continue without trace_id
        pass

    try:
        async with AsyncSessionLocal() as session:
            return await run_integration_feasibility(
                content, content_type, analysis_id, session, state
            )
    except GeneratorExit:
        duration = time.time() - start_time
        logger.warning(
            "agent_cancelled",
            agent_type="integration_feasibility",
            analysis_id=analysis_id,
            exception_type="GeneratorExit",
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,
        )
        return {}
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "agent_failed",
            agent_type="integration_feasibility",
            analysis_id=analysis_id,
            error_type=type(e).__name__,
            error=str(e),
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,
            exc_info=True,
        )
        return {}


async def run_implementation_planner_with_session(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    state: AnalysisState,
) -> dict[str, object]:
    """Run implementation planner with its own database session."""
    from app.db.session import AsyncSessionLocal

    start_time = time.time()

    # Get LangSmith trace ID for correlation if available
    trace_id: str | None = None
    try:
        run_tree = get_current_run_tree()
        if run_tree and hasattr(run_tree, "id"):
            trace_id = str(run_tree.id)
    except Exception:  # noqa: BLE001 - LangSmith may not be available, catch all to continue
        # LangSmith not available or not in trace context - continue without trace_id
        pass

    try:
        async with AsyncSessionLocal() as session:
            return await run_implementation_planner(
                content, content_type, analysis_id, session, state
            )
    except GeneratorExit:
        duration = time.time() - start_time
        logger.warning(
            "agent_cancelled",
            agent_type="implementation_planner",
            analysis_id=analysis_id,
            exception_type="GeneratorExit",
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,
        )
        return {}
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "agent_failed",
            agent_type="implementation_planner",
            analysis_id=analysis_id,
            error_type=type(e).__name__,
            error=str(e),
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,
            exc_info=True,
        )
        return {}


async def run_security_auditor_with_session(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    state: AnalysisState,
) -> dict[str, object]:
    """Run security auditor with its own database session."""
    from app.db.session import AsyncSessionLocal

    start_time = time.time()

    # Get LangSmith trace ID for correlation if available
    trace_id: str | None = None
    try:
        run_tree = get_current_run_tree()
        if run_tree and hasattr(run_tree, "id"):
            trace_id = str(run_tree.id)
    except Exception:  # noqa: BLE001 - LangSmith may not be available, catch all to continue
        # LangSmith not available or not in trace context - continue without trace_id
        pass

    # Load MCP tools for security auditor if enabled
    tools: list[BaseTool] = []
    try:
        from app.services.mcp import MCPClientPool, ToolRegistry, get_mcp_settings

        registry = ToolRegistry()
        if registry.is_tool_enabled("security_auditor"):
            settings = get_mcp_settings()
            if settings.enabled:
                pool = MCPClientPool(settings.get_enabled_servers())
                capabilities = registry.get_capabilities("security_auditor")
                tools = await pool.get_tools_for_capabilities(capabilities)
                logger.info(
                    "loaded_mcp_tools_for_security_auditor",
                    analysis_id=str(analysis_id),
                    tool_count=len(tools),
                    capabilities=capabilities,
                )
    except Exception as e:  # noqa: BLE001 - Graceful degradation for any MCP loading error
        # Graceful degradation - continue without tools if MCP loading fails
        logger.warning(
            "mcp_tool_loading_failed",
            agent_type="security_auditor",
            analysis_id=str(analysis_id),
            error=str(e),
        )
        tools = []

    try:
        async with AsyncSessionLocal() as session:
            return await run_security_auditor(
                content, content_type, analysis_id, session, state, tools=tools
            )
    except GeneratorExit:
        duration = time.time() - start_time
        logger.warning(
            "agent_cancelled",
            agent_type="security_auditor",
            analysis_id=analysis_id,
            exception_type="GeneratorExit",
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,
        )
        return {}
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "agent_failed",
            agent_type="security_auditor",
            analysis_id=analysis_id,
            error_type=type(e).__name__,
            error=str(e),
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,
            exc_info=True,
        )
        return {}


async def run_performance_analyst_with_session(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    state: AnalysisState,
) -> dict[str, object]:
    """Run performance analyst with its own database session."""
    from app.db.session import AsyncSessionLocal

    start_time = time.time()

    # Get LangSmith trace ID for correlation if available
    trace_id: str | None = None
    try:
        run_tree = get_current_run_tree()
        if run_tree and hasattr(run_tree, "id"):
            trace_id = str(run_tree.id)
    except Exception:  # noqa: BLE001 - LangSmith may not be available, catch all to continue
        # LangSmith not available or not in trace context - continue without trace_id
        pass

    try:
        async with AsyncSessionLocal() as session:
            return await run_performance_analyst(content, content_type, analysis_id, session, state)
    except GeneratorExit:
        duration = time.time() - start_time
        logger.warning(
            "agent_cancelled",
            agent_type="performance_analyst",
            analysis_id=analysis_id,
            exception_type="GeneratorExit",
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,
        )
        return {}
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "agent_failed",
            agent_type="performance_analyst",
            analysis_id=analysis_id,
            error_type=type(e).__name__,
            error=str(e),
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,
            exc_info=True,
        )
        return {}


async def run_code_quality_critic_with_session(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    state: AnalysisState,
) -> dict[str, object]:
    """Run code quality critic with its own database session."""
    from app.db.session import AsyncSessionLocal

    start_time = time.time()

    # Get LangSmith trace ID for correlation if available
    trace_id: str | None = None
    try:
        run_tree = get_current_run_tree()
        if run_tree and hasattr(run_tree, "id"):
            trace_id = str(run_tree.id)
    except Exception:  # noqa: BLE001 - LangSmith may not be available, catch all to continue
        # LangSmith not available or not in trace context - continue without trace_id
        pass

    try:
        async with AsyncSessionLocal() as session:
            return await run_code_quality_critic(content, content_type, analysis_id, session, state)
    except GeneratorExit:
        duration = time.time() - start_time
        logger.warning(
            "agent_cancelled",
            agent_type="code_quality_critic",
            analysis_id=analysis_id,
            exception_type="GeneratorExit",
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,
        )
        return {}
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "agent_failed",
            agent_type="code_quality_critic",
            analysis_id=analysis_id,
            error_type=type(e).__name__,
            error=str(e),
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,
            exc_info=True,
        )
        return {}


async def run_trend_validator_with_session(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    state: AnalysisState,
) -> dict[str, object]:
    """Run trend validator with its own database session."""
    from app.db.session import AsyncSessionLocal

    start_time = time.time()

    # Get LangSmith trace ID for correlation if available
    trace_id: str | None = None
    try:
        run_tree = get_current_run_tree()
        if run_tree and hasattr(run_tree, "id"):
            trace_id = str(run_tree.id)
    except Exception:  # noqa: BLE001 - LangSmith may not be available, catch all to continue
        # LangSmith not available or not in trace context - continue without trace_id
        pass

    try:
        async with AsyncSessionLocal() as session:
            return await run_trend_validator(content, content_type, analysis_id, session, state)
    except GeneratorExit as gen_exit:
        # GeneratorExit occurs when async generator is closed prematurely
        # This can happen during LangGraph's internal streaming cleanup or timeout cancellation
        duration = time.time() - start_time
        logger.error(
            "agent_generator_exit_runner",
            agent_type="trend_validator",
            analysis_id=analysis_id,
            exception_type="GeneratorExit",
            error_message=str(gen_exit),
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            exc_info=True,  # Include full stack trace for debugging
            context="run_trend_validator_with_session",
            note=(
                "GeneratorExit caught in runner function. "
                "This occurs when LangGraph's pregel module closes an async generator. "
                "Check LangGraph streaming and timeout configuration."
            ),
        )
        return {}
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "agent_failed",
            agent_type="trend_validator",
            analysis_id=analysis_id,
            error_type=type(e).__name__,
            error=str(e),
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,
            exc_info=True,
        )
        return {}


async def run_dependency_mapper_with_session(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    state: AnalysisState,
) -> dict[str, object]:
    """Run dependency mapper with its own database session."""
    from app.db.session import AsyncSessionLocal

    start_time = time.time()

    # Get LangSmith trace ID for correlation if available
    trace_id: str | None = None
    try:
        run_tree = get_current_run_tree()
        if run_tree and hasattr(run_tree, "id"):
            trace_id = str(run_tree.id)
    except Exception:  # noqa: BLE001 - LangSmith may not be available, catch all to continue
        # LangSmith not available or not in trace context - continue without trace_id
        pass

    # Load MCP tools for dependency mapper if enabled
    tools: list[BaseTool] = []
    try:
        from app.services.mcp import MCPClientPool, ToolRegistry, get_mcp_settings

        registry = ToolRegistry()
        if registry.is_tool_enabled("dependency_mapper"):
            settings = get_mcp_settings()
            if settings.enabled:
                pool = MCPClientPool(settings.get_enabled_servers())
                capabilities = registry.get_capabilities("dependency_mapper")
                tools = await pool.get_tools_for_capabilities(capabilities)
                logger.info(
                    "loaded_mcp_tools_for_dependency_mapper",
                    analysis_id=str(analysis_id),
                    tool_count=len(tools),
                    capabilities=capabilities,
                )
    except Exception as e:  # noqa: BLE001 - Graceful degradation for any MCP loading error
        # Graceful degradation - continue without tools if MCP loading fails
        logger.warning(
            "mcp_tool_loading_failed",
            agent_type="dependency_mapper",
            analysis_id=str(analysis_id),
            error=str(e),
        )
        tools = []

    try:
        async with AsyncSessionLocal() as session:
            return await run_dependency_mapper(
                content, content_type, analysis_id, session, state, tools=tools
            )
    except GeneratorExit:
        duration = time.time() - start_time
        logger.warning(
            "agent_cancelled",
            agent_type="dependency_mapper",
            analysis_id=analysis_id,
            exception_type="GeneratorExit",
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,
        )
        return {}
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "agent_failed",
            agent_type="dependency_mapper",
            analysis_id=analysis_id,
            error_type=type(e).__name__,
            error=str(e),
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,
            exc_info=True,
        )
        return {}
