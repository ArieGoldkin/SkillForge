"""TTL-based cleanup for draft analyses.

Handles expiration of old draft analyses with cascade to chunks.
Implements configurable retention policies by status.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.analysis import Analysis
from app.db.models.analysis_chunk import AnalysisChunk

logger = get_logger(__name__)


class TTLCleaner:
    """Service for TTL-based cleanup of old draft analyses.

    Implements retention policies:
    - Draft: 7 days default
    - Failed/Error: 30 days default
    - Pending: 1 day default (likely stuck)
    - Complete: Never expire (keep indefinitely)

    Cleanup cascades to chunks via foreign key ON DELETE CASCADE.
    """

    def __init__(
        self,
        session: AsyncSession,
        batch_size: int = 100,
    ) -> None:
        """Initialize TTL cleaner.

        Args:
            session: Async database session
            batch_size: Number of analyses to delete per batch

        """
        self.session = session
        self.batch_size = batch_size

        # Default TTL policies by status (in days)
        self.ttl_policies: dict[str, int] = {
            "draft": 7,
            "pending": 1,  # Likely stuck workflows
            "failed": 30,
            "error": 30,
            # "complete": None,  # Never expire completed analyses
        }

    def set_ttl_policy(self, status: str, days: int | None) -> None:
        """Set custom TTL policy for a status.

        Args:
            status: Analysis status ('draft', 'pending', 'failed', 'error')
            days: Number of days to retain, or None for no expiration

        Example:
            >>> cleaner.set_ttl_policy("draft", 14)  # Keep drafts for 14 days
            >>> cleaner.set_ttl_policy("complete", None)  # Never expire complete

        """
        if days is None:
            self.ttl_policies.pop(status, None)
        else:
            self.ttl_policies[status] = days

        logger.info(
            "ttl_policy_updated",
            status=status,
            days=days,
        )

    async def find_expired_analyses(
        self,
        status: str | None = None,
        dry_run: bool = True,
    ) -> list[tuple[uuid.UUID, str, datetime]]:
        """Find analyses that have expired based on TTL policies.

        Args:
            status: Optional status filter (checks only this status)
            dry_run: If True, only return what would be deleted

        Returns:
            List of tuples (analysis_id, status, updated_at)

        Example:
            >>> cleaner = TTLCleaner(session)
            >>> expired = await cleaner.find_expired_analyses(status="draft")
            >>> print(f"Found {len(expired)} expired draft analyses")

        """
        expired: list[tuple[uuid.UUID, str, datetime]] = []

        # Determine which statuses to check
        statuses_to_check = [status] if status else list(self.ttl_policies.keys())

        for check_status in statuses_to_check:
            ttl_days = self.ttl_policies.get(check_status)
            if ttl_days is None:
                continue

            threshold_date = datetime.now(UTC) - timedelta(days=ttl_days)

            query = select(Analysis.id, Analysis.status, Analysis.updated_at).where(
                Analysis.status == check_status,
                Analysis.updated_at < threshold_date,
            )

            result = await self.session.execute(query)
            rows = result.all()

            for analysis_id, analysis_status, updated_at in rows:
                expired.append((analysis_id, analysis_status, updated_at))

        logger.info(
            "find_expired_analyses",
            expired_count=len(expired),
            status_filter=status,
        )

        return expired

    async def delete_expired_analyses(
        self,
        status: str | None = None,
        cascade_to_chunks: bool = True,
    ) -> dict[str, int]:
        """Delete expired analyses based on TTL policies.

        Args:
            status: Optional status filter (delete only this status)
            cascade_to_chunks: If True, also delete associated chunks
                               (automatic via ON DELETE CASCADE)

        Returns:
            Dictionary with deletion statistics by status

        Example:
            >>> stats = await cleaner.delete_expired_analyses(status="draft")
            >>> print(f"Deleted {stats['draft']} draft analyses")

        Note:
            Chunks are automatically deleted via foreign key ON DELETE CASCADE.
            No need to manually delete chunks if cascade_to_chunks=True.

        """
        stats: dict[str, int] = {}

        # Find expired analyses
        expired_analyses = await self.find_expired_analyses(status=status)

        if not expired_analyses:
            logger.info("delete_expired_analyses_skipped", reason="no_expired")
            return stats

        # Group by status for statistics
        by_status: dict[str, list[uuid.UUID]] = {}
        for analysis_id, analysis_status, _ in expired_analyses:
            if analysis_status not in by_status:
                by_status[analysis_status] = []
            by_status[analysis_status].append(analysis_id)

        # Delete in batches by status
        for analysis_status, analysis_ids in by_status.items():
            deleted_count = 0

            for i in range(0, len(analysis_ids), self.batch_size):
                batch = analysis_ids[i : i + self.batch_size]

                # Delete analyses (chunks cascade automatically)
                stmt = delete(Analysis).where(Analysis.id.in_(batch))
                result = await self.session.execute(stmt)
                batch_deleted = result.rowcount or 0  # type: ignore[attr-defined]
                deleted_count += batch_deleted

                await self.session.commit()

                logger.info(
                    "delete_expired_batch",
                    status=analysis_status,
                    batch_num=i // self.batch_size + 1,
                    batch_size=len(batch),
                    batch_deleted=batch_deleted,
                )

            stats[analysis_status] = deleted_count

        # Calculate total
        stats["total"] = sum(stats.values())

        logger.info(
            "delete_expired_analyses_complete",
            stats=stats,
            cascade_to_chunks=cascade_to_chunks,
        )

        return stats

    async def count_expired_by_status(self) -> dict[str, int]:
        """Count expired analyses by status without deleting them.

        Returns:
            Dictionary mapping status to count of expired analyses

        Example:
            >>> counts = await cleaner.count_expired_by_status()
            >>> print(f"Expired drafts: {counts.get('draft', 0)}")

        """
        counts: dict[str, int] = {}

        for status, ttl_days in self.ttl_policies.items():
            if ttl_days is None:
                continue

            threshold_date = datetime.now(UTC) - timedelta(days=ttl_days)

            query = select(func.count(Analysis.id)).where(
                Analysis.status == status,
                Analysis.updated_at < threshold_date,
            )

            result = await self.session.execute(query)
            count = result.scalar_one()
            counts[status] = count

        counts["total"] = sum(counts.values())

        logger.info("count_expired_by_status", counts=counts)

        return counts

    async def get_expired_chunk_count(
        self,
        analysis_ids: list[uuid.UUID],
    ) -> int:
        """Count chunks that will be deleted with expired analyses.

        Args:
            analysis_ids: List of analysis IDs to check

        Returns:
            Total number of chunks that will be deleted

        Example:
            >>> expired = await cleaner.find_expired_analyses()
            >>> expired_ids = [a[0] for a in expired]
            >>> chunk_count = await cleaner.get_expired_chunk_count(expired_ids)
            >>> print(f"Will delete {chunk_count} chunks")

        """
        if not analysis_ids:
            return 0

        query = select(func.count(AnalysisChunk.id)).where(
            AnalysisChunk.analysis_id.in_(analysis_ids)
        )

        result = await self.session.execute(query)
        count = result.scalar_one()

        logger.info(
            "get_expired_chunk_count",
            analysis_count=len(analysis_ids),
            chunk_count=count,
        )

        return count

    async def cleanup_with_preview(
        self,
        status: str | None = None,
        confirm: bool = False,
    ) -> dict[str, int | dict]:
        """Preview or execute TTL cleanup with detailed statistics.

        Args:
            status: Optional status filter
            confirm: If False, preview only; if True, execute deletion

        Returns:
            Dictionary with preview/execution statistics

        Example:
            >>> # Preview what will be deleted
            >>> preview = await cleaner.cleanup_with_preview(confirm=False)
            >>> print(f"Would delete {preview['analyses_to_delete']} analyses")
            >>>
            >>> # Execute deletion
            >>> result = await cleaner.cleanup_with_preview(confirm=True)
            >>> print(f"Deleted {result['analyses_deleted']} analyses")

        """
        # Find expired analyses
        expired_analyses = await self.find_expired_analyses(status=status)
        expired_ids = [a[0] for a in expired_analyses]

        # Count chunks that will be deleted
        chunk_count = await self.get_expired_chunk_count(expired_ids)

        # Group by status
        by_status: dict[str, int] = {}
        for _, analysis_status, _ in expired_analyses:
            by_status[analysis_status] = by_status.get(analysis_status, 0) + 1

        result: dict[str, int | dict] = {
            "analyses_to_delete": len(expired_analyses),
            "chunks_to_delete": chunk_count,
            "by_status": by_status,
            "executed": confirm,
        }

        if confirm:
            # Execute deletion
            deletion_stats = await self.delete_expired_analyses(status=status)
            result["analyses_deleted"] = deletion_stats.get("total", 0)
            result["deletion_stats"] = deletion_stats
        else:
            logger.info("cleanup_preview_only", stats=result)

        return result

    async def extend_ttl_for_analysis(
        self,
        analysis_id: uuid.UUID,
        extension_days: int = 7,
    ) -> bool:
        """Extend TTL for a specific analysis by updating its timestamp.

        Useful for:
        - User-requested retention extension
        - Active work in progress
        - Important draft analyses

        Args:
            analysis_id: Analysis ID to extend
            extension_days: Days to extend from now (default: 7)

        Returns:
            True if extended, False if analysis not found

        Example:
            >>> extended = await cleaner.extend_ttl_for_analysis(analysis_id, extension_days=14)

        """
        from sqlalchemy import update

        # Update updated_at to now to reset TTL
        stmt = (
            update(Analysis).where(Analysis.id == analysis_id).values(updated_at=datetime.now(UTC))
        )

        result = await self.session.execute(stmt)
        await self.session.commit()

        extended = (result.rowcount or 0) > 0  # type: ignore[attr-defined]

        logger.info(
            "extend_ttl_for_analysis",
            analysis_id=analysis_id,
            extension_days=extension_days,
            extended=extended,
        )

        return extended

    async def get_ttl_status_report(self) -> dict:
        """Generate comprehensive TTL status report.

        Returns:
            Dictionary with TTL policy status and expiration counts

        Example:
            >>> report = await cleaner.get_ttl_status_report()
            >>> print(report["policies"])
            >>> print(report["expired_counts"])

        """
        report: dict[str, dict | str] = {
            "policies": self.ttl_policies.copy(),
            "expired_counts": await self.count_expired_by_status(),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Add next expiration dates
        next_expirations: dict[str, datetime] = {}
        for status, ttl_days in self.ttl_policies.items():
            if ttl_days is None:
                continue

            # Find oldest non-expired analysis for this status
            threshold_date = datetime.now(UTC) - timedelta(days=ttl_days)

            query = (
                select(Analysis.updated_at)
                .where(
                    Analysis.status == status,
                    Analysis.updated_at >= threshold_date,
                )
                .order_by(Analysis.updated_at.asc())
                .limit(1)
            )

            result = await self.session.execute(query)
            oldest = result.scalar_one_or_none()

            if oldest:
                expiration_date = oldest + timedelta(days=ttl_days)
                next_expirations[status] = expiration_date

        report["next_expirations"] = next_expirations

        logger.info("ttl_status_report_generated", report=report)

        return report
