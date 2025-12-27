"""Status update service for analysis records with locking and transition validation.

Issue #441: Implements database-level locking (SELECT FOR UPDATE) and status
transition validation to prevent race conditions and invalid state changes.
"""

import asyncio
from collections.abc import Mapping

from sqlalchemy import select

from app.core.branded_ids import AnalysisID
from app.core.logging import get_logger
from app.db.models.analysis import Analysis
from app.db.session import AsyncSessionLocal

logger = get_logger(__name__)

# Per-analysis locks to prevent concurrent updates
_locks: dict[str, asyncio.Lock] = {}
_locks_lock = asyncio.Lock()  # Protects _locks dict itself


async def _get_lock(analysis_id: AnalysisID) -> asyncio.Lock:
    """Get or create a lock for the given analysis_id.

    Thread-safe lock creation using a global lock to protect the locks dict.

    Args:
        analysis_id: UUID of the analysis

    Returns:
        asyncio.Lock for this analysis

    """
    analysis_id_str = str(analysis_id)
    async with _locks_lock:
        if analysis_id_str not in _locks:
            _locks[analysis_id_str] = asyncio.Lock()
        return _locks[analysis_id_str]


# Valid status transitions
# Format: {from_status: {to_status1, to_status2, ...}}  # noqa: ERA001
# Note: All intermediate states allow "complete" transition for fast-track completion
# when workflow finishes before DB status updates (Issue #441)
VALID_TRANSITIONS: Mapping[str, set[str]] = {
    # Normal workflow progression (with fast-track to complete)
    "pending": {"extracting", "complete", "failed", "cancelled"},
    "extracting": {"analyzing", "complete", "extraction_failed", "failed", "cancelled"},
    "analyzing": {
        "generating_artifact",
        "complete",  # Fast-track when workflow completes quickly
        "analysis_failed",
        "quality_gate_failed",
        "failed",
        "cancelled",
    },
    "generating_artifact": {"complete", "artifact_failed", "failed", "cancelled"},
    # Failure states (allow retry via transition to pending)
    "extraction_failed": {"failed", "cancelled", "pending"},  # +pending for retry
    "analysis_failed": {"failed", "cancelled", "pending"},  # +pending for retry
    "artifact_failed": {"failed", "cancelled", "pending"},  # +pending for retry
    "quality_gate_failed": {"failed", "cancelled", "pending"},  # +pending for retry
    "failed": {"cancelled", "pending"},  # +pending for retry
    # Complete allows rerun (skip extraction, go straight to analyzing)
    "complete": {"analyzing"},  # +analyzing for rerun
    # Cancelled is terminal (no transitions allowed)
    "cancelled": set(),
}


def _is_valid_transition(from_status: str, to_status: str) -> bool:
    """Check if status transition is valid.

    Args:
        from_status: Current status
        to_status: Desired new status

    Returns:
        True if transition is valid, False otherwise

    """
    allowed = VALID_TRANSITIONS.get(from_status, set())
    return to_status in allowed


class StatusUpdater:
    """Service for updating analysis status in database with locking and validation."""

    async def update(self, analysis_id: AnalysisID, status: str) -> None:
        """Update analysis status in database with locking and transition validation.

        Uses database-level locking (SELECT FOR UPDATE) and validates status transitions
        to prevent race conditions and invalid state changes.

        Args:
            analysis_id: UUID of the analysis to update
            status: New status value (e.g., "complete", "failed", "artifact_failed")

        Raises:
            ValueError: If status transition is invalid

        """
        # Get per-analysis lock to prevent concurrent updates
        lock = await _get_lock(analysis_id)

        async with lock:
            try:
                async with AsyncSessionLocal() as db_session:
                    # Use SELECT FOR UPDATE to lock the row at database level
                    result = await db_session.execute(
                        select(Analysis).where(Analysis.id == analysis_id).with_for_update()
                    )
                    analysis = result.scalar_one_or_none()

                    if not analysis:
                        logger.warning(
                            "workflow_task_status_update_analysis_not_found",
                            analysis_id=str(analysis_id),
                            status=status,
                        )
                        return

                    # Validate status transition
                    # Convert SQLAlchemy Column to string for type checking
                    current_status = str(analysis.status)
                    if not _is_valid_transition(current_status, status):
                        error_msg = f"Invalid status transition: {current_status} -> {status}"
                        allowed = VALID_TRANSITIONS.get(current_status, set())
                        logger.error(
                            "workflow_task_status_transition_invalid",
                            analysis_id=str(analysis_id),
                            from_status=current_status,
                            to_status=status,
                            allowed_transitions=list(allowed),
                        )
                        raise ValueError(error_msg)

                    # Update status
                    analysis.status = status
                    await db_session.commit()

                    logger.info(
                        "workflow_task_status_updated",
                        analysis_id=str(analysis_id),
                        from_status=current_status,
                        to_status=status,
                    )
            except ValueError:
                # Re-raise ValueError (invalid transition)
                raise
            except Exception as db_error:
                logger.error(
                    "workflow_task_status_update_failed",
                    analysis_id=str(analysis_id),
                    status=status,
                    error=str(db_error),
                    exc_info=True,
                )
                raise
