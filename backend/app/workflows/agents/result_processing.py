"""Result processing and persistence for agent execution.

This module handles saving agent results to the database and emitting
SSE events for completion, cancellation, and errors.
"""

import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.core.utils import normalize_analysis_id_to_uuid
from app.workflows.agents.base import emit_agent_progress, save_agent_finding

logger = get_logger(__name__)


async def process_agent_result(
    findings: dict[str, object],
    analysis_id: AnalysisID,
    agent_type: str,
    session: AsyncSession,
    start_time: float,
) -> dict[str, object]:
    """Process and persist successful agent result.

    Args:
        findings: Extracted findings from structured response
        analysis_id: UUID of the analysis
        agent_type: Type of agent
        session: Database session
        start_time: Start time for processing time calculation

    Returns:
        Result dictionary with agent_type, findings, processing_time_ms

    """
    # Calculate processing time
    processing_time_ms = int((time.time() - start_time) * 1000)

    # Save to database
    # Normalize analysis_id to UUID (handles strings, UUID objects, and non-UUID strings)
    analysis_uuid = normalize_analysis_id_to_uuid(analysis_id)

    await save_agent_finding(
        session=session,
        analysis_id=analysis_uuid,
        agent_type=agent_type,
        findings=findings,
        processing_time_ms=processing_time_ms,
    )

    # Emit SSE event: agent complete
    await emit_agent_progress(
        analysis_id,
        agent_type,
        "complete",
        processing_time_ms=processing_time_ms,
    )

    logger.info(
        "agent_complete",
        agent_type=agent_type,
        analysis_id=analysis_id,
        processing_time_ms=processing_time_ms,
    )

    return {
        "agent_type": agent_type,
        "findings": findings,
        "processing_time_ms": processing_time_ms,
    }


async def handle_agent_cancellation(
    analysis_id: AnalysisID,
    agent_type: str,
    start_time: float,
) -> None:
    """Handle agent cancellation (GeneratorExit).

    Args:
        analysis_id: UUID of the analysis
        agent_type: Type of agent
        start_time: Start time for processing time calculation

    """
    processing_time_ms = int((time.time() - start_time) * 1000)
    logger.warning(
        "agent_generator_closed",
        agent_type=agent_type,
        analysis_id=analysis_id,
        processing_time_ms=processing_time_ms,
    )
    # Emit SSE event for cancellation
    await emit_agent_progress(
        analysis_id,
        agent_type,
        "cancelled",
        error="Agent execution was interrupted",
        error_code=f"{agent_type.upper()}_CANCELLED",
    )


async def handle_agent_error(
    error: Exception,
    analysis_id: AnalysisID,
    agent_type: str,
    start_time: float,
) -> None:
    """Handle agent execution error.

    Args:
        error: Exception that occurred
        analysis_id: UUID of the analysis
        agent_type: Type of agent
        start_time: Start time for processing time calculation

    """
    processing_time_ms = int((time.time() - start_time) * 1000)

    # Emit SSE event: agent failed
    await emit_agent_progress(
        analysis_id,
        agent_type,
        "failed",
        error=str(error),
        error_code=f"{agent_type.upper()}_FAILED",
    )

    logger.exception(
        "agent_failed",
        agent_type=agent_type,
        analysis_id=analysis_id,
        error=str(error),
        processing_time_ms=processing_time_ms,
    )

