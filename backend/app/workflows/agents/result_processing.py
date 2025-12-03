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
from app.workflows.agents.validation import score_agent_output
from app.workflows.agents.validation.specificity_scorer import LOW_SPECIFICITY_WARNING_THRESHOLD

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

    # Extract confidence_score from findings if present
    # This allows agents to include confidence in their response without breaking existing code
    confidence_score: float | None = None
    findings_clean: dict[str, object] = findings
    if isinstance(findings, dict):
        confidence_value = findings.get("confidence_score")
        if isinstance(confidence_value, (int, float)):
            confidence_score = float(confidence_value)
        # Remove confidence_score from findings to avoid duplication in database
        findings_clean = {k: v for k, v in findings.items() if k != "confidence_score"}

    # Validate specificity of output (post-agent, pre-persistence)
    # This runs AFTER agent execution but BEFORE database save
    specificity_score = score_agent_output(findings, agent_type=agent_type)

    # Log specificity metrics for monitoring
    logger.info(
        "agent_specificity_score",
        agent_type=agent_type,
        analysis_id=analysis_id,
        specificity_score=specificity_score.overall_score,
        quality_level=specificity_score.quality_level,
        numeric_count=specificity_score.numeric_value_count,
        vague_count=specificity_score.vague_phrase_count,
        numeric_compliance=specificity_score.numeric_field_compliance,
    )

    # Flag low-specificity outputs
    if specificity_score.overall_score < LOW_SPECIFICITY_WARNING_THRESHOLD:
        logger.warning(
            "low_specificity_output",
            agent_type=agent_type,
            analysis_id=analysis_id,
            specificity_score=specificity_score.overall_score,
            quality_level=specificity_score.quality_level,
            vague_phrases=specificity_score.vague_phrase_count,
            numeric_values=specificity_score.numeric_value_count,
            expected_numeric_count=specificity_score.expected_numeric_count,
            # Include sample vague phrases for debugging
            sample_vague_phrases=[vp.phrase for vp in specificity_score.vague_phrases[:3]],
        )

    # Save to database
    # Normalize analysis_id to UUID (handles strings, UUID objects, and non-UUID strings)
    analysis_uuid = normalize_analysis_id_to_uuid(analysis_id)

    await save_agent_finding(
        session=session,
        analysis_id=analysis_uuid,
        agent_type=agent_type,
        findings=findings_clean,
        confidence_score=confidence_score,
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
        "confidence_score": confidence_score,  # Include at top level for template/validation
        "processing_time_ms": processing_time_ms,
        "specificity_score": specificity_score.overall_score,  # Include for monitoring
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
