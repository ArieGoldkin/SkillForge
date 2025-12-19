"""Annotation queue repository for database operations.

This module implements the repository pattern for annotation queue database operations,
following the mandatory architecture pattern defined in cursor rules.
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Protocol

from fastapi import Depends
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.annotation_queue import AnnotationQueue
from app.db.session import get_db

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = get_logger(__name__)


class IAnnotationRepository(Protocol):
    """Protocol interface for annotation queue repository operations."""

    async def queue_for_review(
        self,
        artifact_id: uuid.UUID,
        reason: str,
        trace_id: str | None = None,
        metadata: "Mapping[str, object] | None" = None,
    ) -> AnnotationQueue:
        """Add an artifact to the annotation queue."""
        ...

    async def get_pending_annotations(
        self, limit: int = 50, offset: int = 0
    ) -> list[AnnotationQueue]:
        """Get pending annotation queue items."""
        ...

    async def mark_as_reviewed(self, queue_id: int) -> AnnotationQueue | None:
        """Mark an annotation queue item as reviewed."""
        ...

    async def check_if_queued(self, artifact_id: uuid.UUID) -> bool:
        """Check if an artifact is already in the pending queue."""
        ...

    async def get_queue_count(self) -> int:
        """Get count of pending annotation queue items."""
        ...


class AnnotationRepository:
    """Repository implementation for annotation queue database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session

        """
        self.session = session

    async def queue_for_review(
        self,
        artifact_id: uuid.UUID,
        reason: str,
        trace_id: str | None = None,
        metadata: "Mapping[str, object] | None" = None,
    ) -> AnnotationQueue:
        """Add an artifact to the annotation queue.

        Args:
            artifact_id: ID of the artifact to queue
            reason: Reason for queuing (e.g., 'low_quality', 'flagged_by_user')
            trace_id: Optional Langfuse trace ID for linking feedback
            metadata: Optional additional context (quality scores, user info, etc.)

        Returns:
            Created annotation queue entry

        """
        annotation = AnnotationQueue(
            artifact_id=artifact_id,
            reason=reason,
            trace_id=trace_id,
            status="pending",
            metadata=dict(metadata) if metadata else None,
        )
        self.session.add(annotation)
        await self.session.commit()
        await self.session.refresh(annotation)

        logger.info(
            "annotation_queued",
            queue_id=annotation.id,
            artifact_id=str(artifact_id),
            reason=reason,
            trace_id=trace_id,
        )

        return annotation

    async def get_pending_annotations(
        self, limit: int = 50, offset: int = 0
    ) -> list[AnnotationQueue]:
        """Get pending annotation queue items.

        Args:
            limit: Maximum number of items to return
            offset: Number of items to skip (for pagination)

        Returns:
            List of pending annotation queue items, ordered by creation date (oldest first)

        """
        result = await self.session.execute(
            select(AnnotationQueue)
            .where(AnnotationQueue.status == "pending")
            .order_by(AnnotationQueue.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def mark_as_reviewed(self, queue_id: int) -> AnnotationQueue | None:
        """Mark an annotation queue item as reviewed.

        Args:
            queue_id: ID of the queue item to mark as reviewed

        Returns:
            Updated annotation queue entry, or None if not found

        """
        await self.session.execute(
            update(AnnotationQueue)
            .where(AnnotationQueue.id == queue_id)
            .values(status="reviewed", reviewed_at=datetime.now(UTC))
        )
        await self.session.commit()

        # Fetch and return updated entry
        result = await self.session.execute(
            select(AnnotationQueue).where(AnnotationQueue.id == queue_id)
        )
        updated_annotation = result.scalar_one_or_none()

        logger.info("annotation_reviewed", queue_id=queue_id)

        return updated_annotation

    async def check_if_queued(self, artifact_id: uuid.UUID) -> bool:
        """Check if an artifact is already in the pending queue.

        Args:
            artifact_id: ID of the artifact to check

        Returns:
            True if artifact is already queued with status 'pending', False otherwise

        """
        result = await self.session.execute(
            select(AnnotationQueue)
            .where(AnnotationQueue.artifact_id == artifact_id)
            .where(AnnotationQueue.status == "pending")
        )
        return result.scalar_one_or_none() is not None

    async def get_queue_count(self) -> int:
        """Get count of pending annotation queue items.

        Returns:
            Number of pending items in the queue

        """
        result = await self.session.execute(
            select(func.count())
            .select_from(AnnotationQueue)
            .where(AnnotationQueue.status == "pending")
        )
        count = result.scalar_one()
        return int(count) if count is not None else 0


def get_annotation_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IAnnotationRepository:
    """Dependency injection function for annotation queue repository."""
    return AnnotationRepository(session=db)
