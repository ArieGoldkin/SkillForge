"""Agent runner functions with database session management.

This module provides wrapper functions for each agent that manage
their own database sessions, enabling parallel execution.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # BaseException is a builtin, no import needed

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

# Note: AsyncSessionLocal is imported lazily inside each function to avoid
# DATABASE_URL validation at import time (required for CI without database)


async def run_tech_comparator_with_session(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
) -> dict[str, object] | BaseException:
    """Run tech comparator with its own database session."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        try:
            return await run_tech_comparator(content, content_type, analysis_id, session)
        except (RuntimeError, ValueError, TimeoutError) as e:
            return e


async def run_integration_feasibility_with_session(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
) -> dict[str, object] | BaseException:
    """Run integration feasibility with its own database session."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        try:
            return await run_integration_feasibility(content, content_type, analysis_id, session)
        except (RuntimeError, ValueError, TimeoutError) as e:
            return e


async def run_implementation_planner_with_session(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
) -> dict[str, object] | BaseException:
    """Run implementation planner with its own database session."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        try:
            return await run_implementation_planner(content, content_type, analysis_id, session)
        except (RuntimeError, ValueError, TimeoutError) as e:
            return e


async def run_security_auditor_with_session(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
) -> dict[str, object] | BaseException:
    """Run security auditor with its own database session."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        try:
            return await run_security_auditor(content, content_type, analysis_id, session)
        except (RuntimeError, ValueError, TimeoutError) as e:
            return e


async def run_performance_analyst_with_session(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
) -> dict[str, object] | BaseException:
    """Run performance analyst with its own database session."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        try:
            return await run_performance_analyst(content, content_type, analysis_id, session)
        except (RuntimeError, ValueError, TimeoutError) as e:
            return e


async def run_code_quality_critic_with_session(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
) -> dict[str, object] | BaseException:
    """Run code quality critic with its own database session."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        try:
            return await run_code_quality_critic(content, content_type, analysis_id, session)
        except (RuntimeError, ValueError, TimeoutError) as e:
            return e


async def run_trend_validator_with_session(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
) -> dict[str, object] | BaseException:
    """Run trend validator with its own database session."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        try:
            return await run_trend_validator(content, content_type, analysis_id, session)
        except (RuntimeError, ValueError, TimeoutError) as e:
            return e


async def run_dependency_mapper_with_session(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
) -> dict[str, object] | BaseException:
    """Run dependency mapper with its own database session."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        try:
            return await run_dependency_mapper(content, content_type, analysis_id, session)
        except (RuntimeError, ValueError, TimeoutError) as e:
            return e
