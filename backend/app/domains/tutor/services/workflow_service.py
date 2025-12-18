"""Workflow continuation service for tutor.

Extracts workflow continuation logic from API endpoints.
"""

import uuid

from app.core.logging import get_logger
from app.domains.tutor.repositories import ITutorRepository
from app.domains.tutor.workflows.state import TutorState

logger = get_logger(__name__)


async def continue_workflow_after_message(
    session_id: uuid.UUID,
    state: TutorState,
    repo: ITutorRepository,
) -> None:
    """Continue workflow after user sends message.

    Runs assess_readiness node and updates session state.
    Note: assess_readiness already updates session state in database,
    so we just need to call it.

    Args:
        session_id: Session UUID
        state: Current tutor state
        repo: Tutor repository

    """
    try:
        from app.domains.tutor.workflows.nodes.assess_readiness import assess_readiness

        # Run assessment (node already updates session state in DB)
        assessment_result = await assess_readiness(state)

        logger.info(
            "tutor_workflow_continued",
            session_id=str(session_id),
            user_ready=assessment_result.get("user_ready", False),
        )

    except Exception as e:
        logger.error(
            "tutor_workflow_continuation_failed",
            session_id=str(session_id),
            error=str(e),
            exc_info=True,
        )
