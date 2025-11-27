"""Workflow task functions for content analysis.

This module contains individual task functions that are orchestrated by
the main analysis workflow. Each task is a self-contained unit of work
that can be executed independently and emits SSE events for progress tracking.

Note: These functions are decorated with @task in analysis.py after import
to avoid circular dependencies. The task() function can be used as a decorator
factory to wrap functions.
"""

import asyncio
from typing import TYPE_CHECKING

from langsmith import traceable

if TYPE_CHECKING:
    pass  # BaseException is a builtin, no import needed

from app.core.logging import get_logger
from app.core.types import AnalysisID, EmbeddingVector
from app.services.embeddings import EmbeddingService
from app.services.extraction.jina_reader import JinaReader
from app.services.sse_helpers import emit_streaming_event
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

# Note: AsyncSessionLocal is imported lazily inside execute_agents() to avoid
# DATABASE_URL validation at import time (required for CI without database)

logger = get_logger(__name__)


@traceable(
    name="extract_content",
    run_type="tool",
    tags=["workflow", "node"],
)
async def extract_content(url: str, analysis_id: AnalysisID) -> dict:
    """Extract content from URL using JinaReader.

    Args:
        url: The URL to extract content from
        analysis_id: Unique identifier for this analysis

    Returns:
        Dictionary with 'raw_content' and 'extraction_metadata'

    Raises:
        JinaReaderError: If extraction fails

    """
    # Emit SSE event: extraction started
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="extraction",
        status="running",
    )

    logger.info("workflow_extraction_started", analysis_id=analysis_id, url=url)
    jina = JinaReader()
    try:
        extracted = await jina.extract_article(url)

        # Emit SSE event: extraction complete
        await emit_streaming_event(
            "progress",
            analysis_id=analysis_id,
            stage="extraction",
            status="complete",
            word_count=extracted.get("word_count", 0),
        )

        logger.info(
            "workflow_extraction_complete",
            analysis_id=analysis_id,
            url=url,
            word_count=extracted.get("word_count", 0),
        )
        return {
            "raw_content": extracted["content"],
            "extraction_metadata": extracted["metadata"],
        }
    except Exception as e:
        # Emit SSE event: extraction failed
        await emit_streaming_event(
            "error",
            analysis_id=analysis_id,
            stage="extraction",
            status="failed",
            error=str(e),
            error_code="EXTRACTION_FAILED",
        )
        logger.error(
            "workflow_extraction_failed",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        raise
    finally:
        await jina.close()


@traceable(
    name="generate_embedding",
    run_type="tool",
    tags=["workflow", "node"],
)
async def generate_embedding(content: str, analysis_id: AnalysisID) -> EmbeddingVector:
    """Generate embedding vector for content.

    Args:
        content: The text content to embed
        analysis_id: Unique identifier for this analysis

    Returns:
        List of floats representing the embedding vector

    Raises:
        EmbeddingError: If embedding generation fails

    """
    # Emit SSE event: embedding generation started
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="embedding",
        status="running",
    )

    logger.info("workflow_embedding_started", content_length=len(content))
    embedding_service = EmbeddingService()
    try:
        embedding_result = await embedding_service.generate_embedding(content)
        embedding: EmbeddingVector = list(embedding_result)

        # Emit SSE event: embedding complete
        await emit_streaming_event(
            "progress",
            analysis_id=analysis_id,
            stage="embedding",
            status="complete",
        )

        logger.info(
            "workflow_embedding_complete",
            embedding_dimensions=len(embedding),
        )
    except Exception as e:
        # Emit SSE event: embedding failed
        await emit_streaming_event(
            "error",
            analysis_id=analysis_id,
            stage="embedding",
            status="failed",
            error=str(e),
            error_code="EMBEDDING_FAILED",
        )
        logger.error(
            "workflow_embedding_failed",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        raise
    finally:
        await embedding_service.close()

    return embedding


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

    # Lazy import to avoid DATABASE_URL validation at module load time
    # This allows the app to be imported in CI environments without a database
    from app.db.session import AsyncSessionLocal

    logger.info(
        "workflow_agents_starting",
        analysis_id=analysis_id,
        selected_agents=selected_agents,
        agent_count=len(selected_agents),
    )

    # Create wrapper functions that manage their own database sessions
    # Each agent gets its own session to avoid concurrency issues
    async def run_tech_comparator_with_session() -> dict[str, object] | BaseException:
        """Run tech comparator with its own database session."""
        async with AsyncSessionLocal() as session:
            try:
                return await run_tech_comparator(content, content_type, analysis_id, session)
            except (RuntimeError, ValueError, TimeoutError) as e:
                return e

    async def run_integration_feasibility_with_session() -> dict[str, object] | BaseException:
        """Run integration feasibility with its own database session."""
        async with AsyncSessionLocal() as session:
            try:
                return await run_integration_feasibility(
                    content, content_type, analysis_id, session
                )
            except (RuntimeError, ValueError, TimeoutError) as e:
                return e

    async def run_implementation_planner_with_session() -> dict[str, object] | BaseException:
        """Run implementation planner with its own database session."""
        async with AsyncSessionLocal() as session:
            try:
                return await run_implementation_planner(content, content_type, analysis_id, session)
            except (RuntimeError, ValueError, TimeoutError) as e:
                return e

    async def run_security_auditor_with_session() -> dict[str, object] | BaseException:
        """Run security auditor with its own database session."""
        async with AsyncSessionLocal() as session:
            try:
                return await run_security_auditor(content, content_type, analysis_id, session)
            except (RuntimeError, ValueError, TimeoutError) as e:
                return e

    async def run_performance_analyst_with_session() -> dict[str, object] | BaseException:
        """Run performance analyst with its own database session."""
        async with AsyncSessionLocal() as session:
            try:
                return await run_performance_analyst(content, content_type, analysis_id, session)
            except (RuntimeError, ValueError, TimeoutError) as e:
                return e

    async def run_code_quality_critic_with_session() -> dict[str, object] | BaseException:
        """Run code quality critic with its own database session."""
        async with AsyncSessionLocal() as session:
            try:
                return await run_code_quality_critic(content, content_type, analysis_id, session)
            except (RuntimeError, ValueError, TimeoutError) as e:
                return e

    async def run_trend_validator_with_session() -> dict[str, object] | BaseException:
        """Run trend validator with its own database session."""
        async with AsyncSessionLocal() as session:
            try:
                return await run_trend_validator(content, content_type, analysis_id, session)
            except (RuntimeError, ValueError, TimeoutError) as e:
                return e

    async def run_dependency_mapper_with_session() -> dict[str, object] | BaseException:
        """Run dependency mapper with its own database session."""
        async with AsyncSessionLocal() as session:
            try:
                return await run_dependency_mapper(content, content_type, analysis_id, session)
            except (RuntimeError, ValueError, TimeoutError) as e:
                return e

    # Create tasks for selected agents (each with its own session)
    agent_tasks = []
    if "tech_comparator" in selected_agents:
        agent_tasks.append(run_tech_comparator_with_session())
    if "integration_feasibility" in selected_agents:
        agent_tasks.append(run_integration_feasibility_with_session())
    if "implementation_planner" in selected_agents:
        agent_tasks.append(run_implementation_planner_with_session())
    if "security_auditor" in selected_agents:
        agent_tasks.append(run_security_auditor_with_session())
    if "performance_analyst" in selected_agents:
        agent_tasks.append(run_performance_analyst_with_session())
    if "code_quality_critic" in selected_agents:
        agent_tasks.append(run_code_quality_critic_with_session())
    if "trend_validator" in selected_agents:
        agent_tasks.append(run_trend_validator_with_session())
    if "dependency_mapper" in selected_agents:
        agent_tasks.append(run_dependency_mapper_with_session())

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
            if isinstance(result, (Exception, BaseException)):
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
