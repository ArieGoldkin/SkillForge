"""Agent runner functions with database session management.

This module provides wrapper functions for each agent that manage
their own database sessions, enabling parallel execution as separate
LangGraph nodes via Send API.

Note: GeneratorExit is handled gracefully (returns empty dict) as it
occurs when timeouts cancel tasks. Other exceptions are allowed to
propagate naturally. Each agent node handles its own exceptions and
returns empty findings on error, allowing other agents to continue.

Issue #268: Agent nodes now use ArtifactStore.load() to load content
from artifact refs with section-based loading. Falls back to raw_content
for backward compatibility.
"""

import time

from langchain_core.tools import BaseTool
from langsmith import get_current_run_tree
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.timeout_config import STEP_TIMEOUT
from app.core.types import AnalysisID
from app.domains.analysis.schemas.api import ArtifactSection
from app.domains.analysis.services.context.artifact_store import ArtifactStore
from app.domains.analysis.workflows.agents import (
    run_code_quality_critic,
    run_dependency_mapper,
    run_implementation_planner,
    run_integration_feasibility,
    run_performance_analyst,
    run_security_auditor,
    run_tech_comparator,
    run_trend_validator,
)
from app.domains.analysis.workflows.state import AnalysisState

# Note: AsyncSessionLocal is imported lazily inside each function to avoid
# DATABASE_URL validation at import time (required for CI without database)

logger = get_logger(__name__)


def has_content_available(state: AnalysisState) -> bool:
    """Check if content is available via Handle Pattern or fallback.

    Issue #244: Handle Pattern implementation. Agents should use this
    to check content availability before processing.

    Content is available if:
    1. content_ref exists with a valid URI (Handle Pattern - preferred)
    2. OR raw_content is non-empty (fallback for backward compatibility)

    Args:
        state: Current workflow state

    Returns:
        True if content can be loaded via artifact or fallback

    Example:
        >>> if not has_content_available(state):
        ...     return {"agent_findings": []}  # Skip processing

    """
    # Check Handle Pattern first (preferred)
    content_ref = state.get("content_ref")
    if content_ref and isinstance(content_ref, dict):
        uri = content_ref.get("uri")
        if uri:
            return True

    # Fallback: check raw_content
    raw_content = state.get("raw_content", "")
    return bool(raw_content)


def get_fallback_content(state: AnalysisState) -> str:
    """Get fallback content for artifact loading.

    Issue #244: Used by agent runners when artifact loading fails.
    Returns raw_content if available, empty string otherwise.

    Args:
        state: Current workflow state

    Returns:
        raw_content string or empty string

    """
    return state.get("raw_content", "")


# Agent-specific content section mapping (Issue #268)
# Each agent gets optimized content section to minimize token usage
# Issue #299-304: Increased content for tech_comparator, trend_validator, performance_analyst
# to handle research papers which need more context than just summaries/code blocks
AGENT_SECTION_MAPPING: dict[str, ArtifactSection] = {
    "code_quality_critic": ArtifactSection.FULL,  # Needs full code for antipatterns
    "security_auditor": ArtifactSection.FULL,  # Requires complete code for scanning
    "dependency_mapper": ArtifactSection.FULL,  # Needs all imports and package files
    "performance_analyst": ArtifactSection.FIRST_N,  # Needs more context for research papers
    "implementation_planner": ArtifactSection.FIRST_N,  # Overview, not exhaustive
    "tech_comparator": ArtifactSection.FIRST_N,  # Needs more than summary for articles
    "trend_validator": ArtifactSection.FIRST_N,  # Needs more context for trend analysis
    "integration_feasibility": ArtifactSection.FIRST_N,  # Integration point overview
}

# Max characters for FIRST_N section per agent (Issue #268, #299-304)
AGENT_MAX_CHARS: dict[str, int | None] = {
    "implementation_planner": 10000,  # Overview section
    "integration_feasibility": 8000,  # Integration points
    "tech_comparator": 15000,  # Needs more context for tech identification
    "trend_validator": 15000,  # Needs more context for trend analysis
    "performance_analyst": 12000,  # Performance patterns require context
}


async def _load_content_from_artifact(
    session: AsyncSession,
    state: AnalysisState,
    agent_type: str,
    fallback_content: str,
) -> str:
    """Load content from artifact store with fallback to raw_content.

    Issue #268: Agents use ArtifactStore for section-based loading.
    Falls back to raw_content for backward compatibility.

    Args:
        session: Database session
        state: Analysis state containing content_ref
        agent_type: Agent type for section mapping
        fallback_content: Fallback content if artifact loading fails

    Returns:
        Loaded content from artifact or fallback

    """
    content_ref = state.get("content_ref")
    if not content_ref or not isinstance(content_ref, dict):
        # Backward compatibility: use raw_content
        logger.debug(
            "artifact_load_fallback",
            agent_type=agent_type,
            reason="no_content_ref",
        )
        return fallback_content

    uri = content_ref.get("uri")
    if not uri:
        logger.debug(
            "artifact_load_fallback",
            agent_type=agent_type,
            reason="no_uri_in_content_ref",
        )
        return fallback_content

    try:
        store = ArtifactStore(session)
        section = AGENT_SECTION_MAPPING.get(agent_type, ArtifactSection.FULL)
        max_chars = AGENT_MAX_CHARS.get(agent_type)

        loaded = await store.load(uri=uri, section=section, max_chars=max_chars)

        logger.info(
            "artifact_content_loaded",
            agent_type=agent_type,
            section=section.value,
            content_length=len(loaded),
            analysis_id=state.get("analysis_id"),
        )
        return loaded

    except Exception as e:  # noqa: BLE001
        # Graceful degradation: fall back to raw_content on any error
        logger.warning(
            "artifact_load_error",
            agent_type=agent_type,
            error=str(e),
            error_type=type(e).__name__,
            fallback="using_raw_content",
        )
        return fallback_content


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
            # Issue #268: Load content from artifact if content_ref available
            loaded_content = await _load_content_from_artifact(
                session=session,
                state=state,
                agent_type="tech_comparator",
                fallback_content=content,
            )

            return await run_tech_comparator(
                loaded_content, content_type, analysis_id, session, state
            )
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
            # Issue #268: Load content from artifact if content_ref available
            loaded_content = await _load_content_from_artifact(
                session=session,
                state=state,
                agent_type="integration_feasibility",
                fallback_content=content,
            )

            return await run_integration_feasibility(
                loaded_content, content_type, analysis_id, session, state
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
            # Issue #268: Load content from artifact if content_ref available
            loaded_content = await _load_content_from_artifact(
                session=session,
                state=state,
                agent_type="implementation_planner",
                fallback_content=content,
            )

            return await run_implementation_planner(
                loaded_content, content_type, analysis_id, session, state
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
        from app.shared.services.mcp import MCPClientPool, ToolRegistry, get_mcp_settings

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
            # Issue #268: Load content from artifact if content_ref available
            loaded_content = await _load_content_from_artifact(
                session=session,
                state=state,
                agent_type="security_auditor",
                fallback_content=content,
            )

            return await run_security_auditor(
                loaded_content, content_type, analysis_id, session, state, tools=tools
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
            # Issue #268: Load content from artifact if content_ref available
            loaded_content = await _load_content_from_artifact(
                session=session,
                state=state,
                agent_type="performance_analyst",
                fallback_content=content,
            )

            return await run_performance_analyst(
                loaded_content, content_type, analysis_id, session, state
            )
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
            # Issue #268: Load content from artifact if content_ref available
            loaded_content = await _load_content_from_artifact(
                session=session,
                state=state,
                agent_type="code_quality_critic",
                fallback_content=content,
            )

            return await run_code_quality_critic(
                loaded_content, content_type, analysis_id, session, state
            )
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
            # Issue #268: Load content from artifact if content_ref available
            loaded_content = await _load_content_from_artifact(
                session=session,
                state=state,
                agent_type="trend_validator",
                fallback_content=content,
            )

            return await run_trend_validator(
                loaded_content, content_type, analysis_id, session, state
            )
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
        from app.shared.services.mcp import MCPClientPool, ToolRegistry, get_mcp_settings

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
            # Issue #268: Load content from artifact if content_ref available
            loaded_content = await _load_content_from_artifact(
                session=session,
                state=state,
                agent_type="dependency_mapper",
                fallback_content=content,
            )

            return await run_dependency_mapper(
                loaded_content, content_type, analysis_id, session, state, tools=tools
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
