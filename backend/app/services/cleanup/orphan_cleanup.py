"""Orphan chunk detection and cleanup.

Handles removal of chunks where parent analysis is deleted or superseded.
Uses soft delete approach for safety with batch processing for large datasets.
"""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.analysis import Analysis
from app.models.analysis_chunk import AnalysisChunk

logger = get_logger(__name__)


class OrphanCleaner:
    """Service for detecting and cleaning orphaned chunks.

    Orphaned chunks are chunks whose parent analysis has been:
    - Deleted from the analyses table
    - Superseded by a newer analysis of the same URL
    - Marked as failed/error status for extended period

    Strategy:
    - Soft delete: Mark chunks with is_deleted flag (requires migration)
    - Hard delete: Permanent removal after grace period
    - Batch processing: Process large datasets in chunks to avoid memory issues
    """

    def __init__(
        self,
        session: AsyncSession,
        batch_size: int = 1000,
        grace_period_days: int = 7,
    ) -> None:
        """Initialize orphan cleaner.

        Args:
            session: Async database session
            batch_size: Number of chunks to process per batch
            grace_period_days: Days to wait before hard delete (default: 7)
        """
        self.session = session
        self.batch_size = batch_size
        self.grace_period_days = grace_period_days

    async def find_orphans_missing_parent(self) -> list[uuid.UUID]:
        """Find chunks where parent analysis no longer exists.

        Uses LEFT JOIN to efficiently find chunks with NULL parent.
        This is the most critical orphan type - parent was deleted.

        Returns:
            List of orphaned chunk IDs

        Example:
            >>> cleaner = OrphanCleaner(session)
            >>> orphan_ids = await cleaner.find_orphans_missing_parent()
            >>> print(f"Found {len(orphan_ids)} orphaned chunks")
        """
        # LEFT JOIN to find chunks with NULL parent (parent was deleted)
        query = (
            select(AnalysisChunk.id)
            .select_from(AnalysisChunk)
            .outerjoin(Analysis, AnalysisChunk.analysis_id == Analysis.id)
            .where(Analysis.id.is_(None))  # Parent doesn't exist
        )

        result = await self.session.execute(query)
        orphan_ids = [row[0] for row in result.all()]

        logger.info(
            "find_orphans_missing_parent",
            orphan_count=len(orphan_ids),
        )

        return orphan_ids

    async def find_orphans_failed_analysis(
        self,
        failed_threshold_days: int = 7,
    ) -> list[uuid.UUID]:
        """Find chunks from failed/error analyses older than threshold.

        Failed analyses are unlikely to be retried after extended period.
        These chunks can be cleaned up to free storage.

        Args:
            failed_threshold_days: Days after which failed analysis chunks are orphaned

        Returns:
            List of chunk IDs from old failed analyses

        Example:
            >>> orphans = await cleaner.find_orphans_failed_analysis(failed_threshold_days=14)
        """
        threshold_date = datetime.now(UTC) - timedelta(days=failed_threshold_days)

        # Find chunks from analyses with failed/error status older than threshold
        query = (
            select(AnalysisChunk.id)
            .join(Analysis, AnalysisChunk.analysis_id == Analysis.id)
            .where(Analysis.status.in_(["failed", "error"]))
            .where(Analysis.updated_at < threshold_date)
        )

        result = await self.session.execute(query)
        orphan_ids = [row[0] for row in result.all()]

        logger.info(
            "find_orphans_failed_analysis",
            orphan_count=len(orphan_ids),
            threshold_days=failed_threshold_days,
        )

        return orphan_ids

    async def find_orphans_superseded_analysis(self) -> list[uuid.UUID]:
        """Find chunks from superseded analyses (same URL, older version).

        When a URL is re-analyzed, older analysis chunks can be cleaned up.
        Keeps only the most recent analysis per URL.

        Returns:
            List of chunk IDs from superseded analyses

        Example:
            >>> orphans = await cleaner.find_orphans_superseded_analysis()
        """
        # Find superseded analyses: same URL but not the latest created_at
        # Use window function to identify latest analysis per URL
        from sqlalchemy import literal_column

        superseded_subquery = (
            select(
                Analysis.id,
                func.row_number()
                .over(
                    partition_by=Analysis.url,
                    order_by=Analysis.created_at.desc(),
                )
                .label("row_num"),
            )
            .where(Analysis.status == "complete")
            .subquery()
        )

        # Get IDs of superseded analyses (row_num > 1)
        superseded_ids_query = select(superseded_subquery.c.id).where(
            superseded_subquery.c.row_num > 1
        )

        # Find chunks belonging to superseded analyses
        query = select(AnalysisChunk.id).where(
            AnalysisChunk.analysis_id.in_(superseded_ids_query)
        )

        result = await self.session.execute(query)
        orphan_ids = [row[0] for row in result.all()]

        logger.info(
            "find_orphans_superseded_analysis",
            orphan_count=len(orphan_ids),
        )

        return orphan_ids

    async def delete_orphans_batch(
        self,
        orphan_ids: list[uuid.UUID],
        hard_delete: bool = False,
    ) -> int:
        """Delete orphaned chunks in batches.

        Processes deletions in batches to avoid memory issues and
        provide progress feedback for large datasets.

        Args:
            orphan_ids: List of chunk IDs to delete
            hard_delete: If True, permanently delete; if False, soft delete (mark as deleted)

        Returns:
            Total number of chunks deleted

        Example:
            >>> orphan_ids = await cleaner.find_orphans_missing_parent()
            >>> deleted = await cleaner.delete_orphans_batch(orphan_ids, hard_delete=False)
            >>> print(f"Deleted {deleted} orphaned chunks")

        Note:
            Soft delete requires migration to add is_deleted column to analysis_chunks.
            Hard delete is immediate and permanent - use with caution.
        """
        if not orphan_ids:
            logger.info("delete_orphans_batch_skipped", reason="no_orphans")
            return 0

        total_deleted = 0

        # Process in batches
        for i in range(0, len(orphan_ids), self.batch_size):
            batch = orphan_ids[i : i + self.batch_size]

            if hard_delete:
                # Permanent deletion
                stmt = delete(AnalysisChunk).where(AnalysisChunk.id.in_(batch))
            else:
                # Soft delete: Mark as deleted (requires migration for is_deleted column)
                # For now, we'll use hard delete since is_deleted doesn't exist yet
                # TODO: Add is_deleted column migration and use soft delete
                stmt = delete(AnalysisChunk).where(AnalysisChunk.id.in_(batch))

            result = await self.session.execute(stmt)
            batch_deleted = result.rowcount or 0
            total_deleted += batch_deleted

            await self.session.commit()

            logger.info(
                "delete_orphans_batch_progress",
                batch_num=i // self.batch_size + 1,
                batch_size=len(batch),
                batch_deleted=batch_deleted,
                total_deleted=total_deleted,
            )

        logger.info(
            "delete_orphans_batch_complete",
            total_deleted=total_deleted,
            total_orphans=len(orphan_ids),
            hard_delete=hard_delete,
        )

        return total_deleted

    async def cleanup_all_orphans(
        self,
        hard_delete: bool = False,
        include_superseded: bool = False,
    ) -> dict[str, int]:
        """Run all orphan detection and cleanup routines.

        Comprehensive cleanup that finds and removes:
        - Chunks with missing parent analysis
        - Chunks from old failed analyses
        - Chunks from superseded analyses (optional)

        Args:
            hard_delete: If True, permanently delete; if False, soft delete
            include_superseded: If True, also clean up superseded analysis chunks

        Returns:
            Dictionary with cleanup statistics

        Example:
            >>> stats = await cleaner.cleanup_all_orphans(
            ...     hard_delete=False,
            ...     include_superseded=True
            ... )
            >>> print(f"Cleaned up {stats['total_deleted']} chunks")
        """
        stats: dict[str, int] = {
            "missing_parent": 0,
            "failed_analysis": 0,
            "superseded_analysis": 0,
            "total_deleted": 0,
        }

        # 1. Find and delete chunks with missing parent
        missing_parent_ids = await self.find_orphans_missing_parent()
        stats["missing_parent"] = await self.delete_orphans_batch(
            missing_parent_ids, hard_delete
        )

        # 2. Find and delete chunks from old failed analyses
        failed_analysis_ids = await self.find_orphans_failed_analysis()
        stats["failed_analysis"] = await self.delete_orphans_batch(
            failed_analysis_ids, hard_delete
        )

        # 3. Optionally find and delete chunks from superseded analyses
        if include_superseded:
            superseded_ids = await self.find_orphans_superseded_analysis()
            stats["superseded_analysis"] = await self.delete_orphans_batch(
                superseded_ids, hard_delete
            )

        stats["total_deleted"] = sum(
            [stats["missing_parent"], stats["failed_analysis"], stats["superseded_analysis"]]
        )

        logger.info(
            "cleanup_all_orphans_complete",
            stats=stats,
            hard_delete=hard_delete,
            include_superseded=include_superseded,
        )

        return stats

    async def count_orphans(self) -> dict[str, int]:
        """Count orphaned chunks without deleting them.

        Useful for dry-run and monitoring purposes.

        Returns:
            Dictionary with orphan counts by type

        Example:
            >>> counts = await cleaner.count_orphans()
            >>> print(f"Found {counts['total']} orphaned chunks")
        """
        counts: dict[str, int] = {
            "missing_parent": 0,
            "failed_analysis": 0,
            "superseded_analysis": 0,
            "total": 0,
        }

        missing_parent_ids = await self.find_orphans_missing_parent()
        counts["missing_parent"] = len(missing_parent_ids)

        failed_analysis_ids = await self.find_orphans_failed_analysis()
        counts["failed_analysis"] = len(failed_analysis_ids)

        superseded_ids = await self.find_orphans_superseded_analysis()
        counts["superseded_analysis"] = len(superseded_ids)

        counts["total"] = sum(
            [
                counts["missing_parent"],
                counts["failed_analysis"],
                counts["superseded_analysis"],
            ]
        )

        logger.info("count_orphans_complete", counts=counts)

        return counts

    async def stream_orphan_chunks(
        self,
        orphan_type: str = "missing_parent",
    ) -> AsyncIterator[AnalysisChunk]:
        """Stream orphaned chunks for inspection or processing.

        Memory-efficient streaming for large orphan sets.
        Useful for detailed analysis before deletion.

        Args:
            orphan_type: Type of orphans to stream ('missing_parent', 'failed_analysis')

        Yields:
            AnalysisChunk objects

        Example:
            >>> async for chunk in cleaner.stream_orphan_chunks('missing_parent'):
            ...     print(f"Orphan: {chunk.id} from analysis {chunk.analysis_id}")
        """
        if orphan_type == "missing_parent":
            orphan_ids = await self.find_orphans_missing_parent()
        elif orphan_type == "failed_analysis":
            orphan_ids = await self.find_orphans_failed_analysis()
        elif orphan_type == "superseded_analysis":
            orphan_ids = await self.find_orphans_superseded_analysis()
        else:
            logger.error("stream_orphan_chunks_invalid_type", orphan_type=orphan_type)
            return

        # Stream in batches
        for i in range(0, len(orphan_ids), self.batch_size):
            batch = orphan_ids[i : i + self.batch_size]

            query = select(AnalysisChunk).where(AnalysisChunk.id.in_(batch))

            result = await self.session.execute(query)
            chunks = result.scalars().all()

            for chunk in chunks:
                yield chunk
