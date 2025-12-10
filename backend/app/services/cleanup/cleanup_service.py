"""Main cleanup service orchestrating all cleanup operations.

Provides unified interface for:
- Orphan cleanup
- Integrity checks
- TTL-based expiration

Designed for use in:
- Scheduled cron jobs
- Manual admin operations
- Health check endpoints
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.services.cleanup.integrity_checks import VectorIntegrityChecker
from app.services.cleanup.orphan_cleanup import OrphanCleaner
from app.services.cleanup.ttl_cleanup import TTLCleaner

logger = get_logger(__name__)


class CleanupService:
    """Unified service for all database cleanup operations.

    Orchestrates orphan cleanup, integrity checks, and TTL-based expiration.
    Provides comprehensive cleanup with detailed reporting.
    """

    def __init__(
        self,
        session: AsyncSession,
        batch_size: int = 1000,
    ) -> None:
        """Initialize cleanup service.

        Args:
            session: Async database session
            batch_size: Default batch size for operations
        """
        self.session = session
        self.batch_size = batch_size

        # Initialize component services
        self.orphan_cleaner = OrphanCleaner(session, batch_size=batch_size)
        self.integrity_checker = VectorIntegrityChecker(session, batch_size=batch_size)
        self.ttl_cleaner = TTLCleaner(session, batch_size=batch_size)

    async def run_full_cleanup(
        self,
        include_orphans: bool = True,
        include_expired: bool = True,
        include_superseded: bool = False,
        hard_delete: bool = False,
        dry_run: bool = False,
    ) -> dict[str, dict]:
        """Run comprehensive cleanup operation.

        Args:
            include_orphans: Clean up orphaned chunks
            include_expired: Clean up expired analyses
            include_superseded: Clean up superseded analyses
            hard_delete: Use hard delete (permanent) vs soft delete
            dry_run: Preview only, don't actually delete

        Returns:
            Dictionary with detailed cleanup statistics

        Example:
            >>> service = CleanupService(session)
            >>> # Preview cleanup
            >>> preview = await service.run_full_cleanup(dry_run=True)
            >>> print(f"Would delete {preview['total_items_affected']} items")
            >>>
            >>> # Execute cleanup
            >>> result = await service.run_full_cleanup(dry_run=False)
        """
        logger.info(
            "full_cleanup_started",
            include_orphans=include_orphans,
            include_expired=include_expired,
            include_superseded=include_superseded,
            hard_delete=hard_delete,
            dry_run=dry_run,
        )

        report: dict[str, dict] = {
            "orphan_cleanup": {},
            "ttl_cleanup": {},
            "integrity_checks": {},
            "summary": {},
        }

        # 1. Orphan cleanup
        if include_orphans:
            if dry_run:
                orphan_counts = await self.orphan_cleaner.count_orphans()
                report["orphan_cleanup"] = {
                    "dry_run": True,
                    "counts": orphan_counts,
                }
            else:
                orphan_stats = await self.orphan_cleaner.cleanup_all_orphans(
                    hard_delete=hard_delete,
                    include_superseded=include_superseded,
                )
                report["orphan_cleanup"] = {
                    "dry_run": False,
                    "stats": orphan_stats,
                }

        # 2. TTL-based cleanup
        if include_expired:
            ttl_result = await self.ttl_cleaner.cleanup_with_preview(
                confirm=not dry_run
            )
            report["ttl_cleanup"] = ttl_result

        # 3. Run integrity checks (always safe, read-only)
        integrity_report = await self.integrity_checker.run_all_checks()
        report["integrity_checks"] = integrity_report

        # 4. Calculate summary
        orphan_total = 0
        if include_orphans and report["orphan_cleanup"]:
            if dry_run:
                orphan_total = report["orphan_cleanup"]["counts"].get("total", 0)
            else:
                orphan_total = report["orphan_cleanup"]["stats"].get("total_deleted", 0)

        expired_total = report["ttl_cleanup"].get("analyses_to_delete", 0)
        if not dry_run:
            expired_total = report["ttl_cleanup"].get("analyses_deleted", 0)

        integrity_issues = sum(
            len(v) if isinstance(v, list) else 0
            for v in integrity_report.values()
        )

        report["summary"] = {
            "dry_run": dry_run,
            "orphans_cleaned": orphan_total,
            "analyses_expired": expired_total,
            "integrity_issues": integrity_issues,
            "total_items_affected": orphan_total + expired_total,
        }

        logger.info(
            "full_cleanup_complete",
            summary=report["summary"],
        )

        return report

    async def health_check(self) -> dict[str, bool | int]:
        """Run health check to identify issues without cleanup.

        Returns:
            Dictionary with health status and issue counts

        Example:
            >>> health = await service.health_check()
            >>> if not health['healthy']:
            ...     print(f"Found {health['total_issues']} issues")
        """
        logger.info("health_check_started")

        # Count orphans
        orphan_counts = await self.orphan_cleaner.count_orphans()

        # Count expired analyses
        expired_counts = await self.ttl_cleaner.count_expired_by_status()

        # Run integrity checks
        integrity_report = await self.integrity_checker.run_all_checks()
        integrity_issues = sum(
            len(v) if isinstance(v, list) else 0
            for v in integrity_report.values()
        )

        total_issues = (
            orphan_counts["total"]
            + expired_counts["total"]
            + integrity_issues
        )

        health_status = {
            "healthy": total_issues == 0,
            "total_issues": total_issues,
            "orphan_chunks": orphan_counts["total"],
            "expired_analyses": expired_counts["total"],
            "integrity_issues": integrity_issues,
            "details": {
                "orphans": orphan_counts,
                "expired": expired_counts,
                "integrity": {
                    k: len(v) if isinstance(v, list) else 0
                    for k, v in integrity_report.items()
                },
            },
        }

        logger.info(
            "health_check_complete",
            healthy=health_status["healthy"],
            total_issues=total_issues,
        )

        return health_status

    async def generate_cleanup_report_markdown(
        self,
        include_recommendations: bool = True,
    ) -> str:
        """Generate comprehensive cleanup report in Markdown format.

        Args:
            include_recommendations: Include cleanup recommendations

        Returns:
            Markdown-formatted report string

        Example:
            >>> report = await service.generate_cleanup_report_markdown()
            >>> with open('cleanup_report.md', 'w') as f:
            ...     f.write(report)
        """
        from datetime import UTC, datetime

        lines = [
            "# Database Cleanup Report",
            "",
            f"Generated at: {datetime.now(UTC).isoformat()}",
            "",
        ]

        # Health check summary
        health = await self.health_check()
        status_emoji = "✅" if health["healthy"] else "⚠️"
        lines.extend(
            [
                "## Health Status",
                "",
                f"{status_emoji} **Overall Status**: {'Healthy' if health['healthy'] else 'Issues Found'}",
                f"- Total Issues: {health['total_issues']}",
                f"- Orphan Chunks: {health['orphan_chunks']}",
                f"- Expired Analyses: {health['expired_analyses']}",
                f"- Integrity Issues: {health['integrity_issues']}",
                "",
            ]
        )

        # Orphan details
        if health["orphan_chunks"] > 0:
            orphan_details = health["details"]["orphans"]
            lines.extend(
                [
                    "## Orphan Chunks",
                    "",
                    f"Total orphaned chunks: **{orphan_details['total']}**",
                    "",
                    "Breakdown:",
                    f"- Missing parent: {orphan_details['missing_parent']}",
                    f"- Failed analysis: {orphan_details['failed_analysis']}",
                    f"- Superseded analysis: {orphan_details['superseded_analysis']}",
                    "",
                ]
            )

        # Expired analyses details
        if health["expired_analyses"] > 0:
            expired_details = health["details"]["expired"]
            lines.extend(
                [
                    "## Expired Analyses",
                    "",
                    f"Total expired analyses: **{expired_details['total']}**",
                    "",
                    "Breakdown by status:",
                ]
            )
            for status, count in expired_details.items():
                if status != "total" and count > 0:
                    lines.append(f"- {status}: {count}")
            lines.append("")

        # Integrity issues details
        if health["integrity_issues"] > 0:
            integrity_details = health["details"]["integrity"]
            lines.extend(
                [
                    "## Integrity Issues",
                    "",
                    f"Total integrity issues: **{health['integrity_issues']}**",
                    "",
                    "Issues found:",
                ]
            )
            for issue_type, count in integrity_details.items():
                if count > 0:
                    lines.append(f"- {issue_type.replace('_', ' ').title()}: {count}")
            lines.append("")

        # Recommendations
        if include_recommendations and not health["healthy"]:
            lines.extend(
                [
                    "## Recommendations",
                    "",
                ]
            )

            if health["orphan_chunks"] > 0:
                lines.extend(
                    [
                        "### Orphan Cleanup",
                        "```python",
                        "# Preview orphan cleanup",
                        "service = CleanupService(session)",
                        "preview = await service.run_full_cleanup(dry_run=True)",
                        "",
                        "# Execute cleanup",
                        "await service.run_full_cleanup(",
                        "    include_orphans=True,",
                        "    hard_delete=False,  # Use soft delete for safety",
                        ")",
                        "```",
                        "",
                    ]
                )

            if health["expired_analyses"] > 0:
                lines.extend(
                    [
                        "### TTL Cleanup",
                        "```python",
                        "# Clean up expired analyses",
                        "await service.run_full_cleanup(",
                        "    include_expired=True,",
                        "    dry_run=False,",
                        ")",
                        "```",
                        "",
                    ]
                )

            if health["integrity_issues"] > 0:
                lines.extend(
                    [
                        "### Integrity Issues",
                        "Vector integrity issues require manual investigation:",
                        "```python",
                        "# Generate detailed integrity report",
                        "report = await integrity_checker.generate_integrity_report_markdown()",
                        "```",
                        "",
                    ]
                )

        lines.extend(
            [
                "---",
                "",
                "For more information, see:",
                "- `/backend/app/services/cleanup/README.md`",
                "- `/backend/scripts/cleanup.py`",
            ]
        )

        return "\n".join(lines)

    async def schedule_cleanup(
        self,
        cleanup_type: str = "full",
    ) -> dict:
        """Execute scheduled cleanup based on type.

        Designed for use in cron jobs or scheduled tasks.

        Args:
            cleanup_type: Type of cleanup ('full', 'orphans', 'ttl', 'health')

        Returns:
            Dictionary with cleanup results

        Example:
            >>> # In cron job
            >>> result = await service.schedule_cleanup(cleanup_type='orphans')
        """
        logger.info("schedule_cleanup_started", cleanup_type=cleanup_type)

        if cleanup_type == "full":
            result = await self.run_full_cleanup(
                include_orphans=True,
                include_expired=True,
                hard_delete=False,
                dry_run=False,
            )
        elif cleanup_type == "orphans":
            stats = await self.orphan_cleaner.cleanup_all_orphans(hard_delete=False)
            result = {"orphan_cleanup": stats}
        elif cleanup_type == "ttl":
            stats = await self.ttl_cleaner.delete_expired_analyses()
            result = {"ttl_cleanup": stats}
        elif cleanup_type == "health":
            health = await self.health_check()
            result = {"health_check": health}
        else:
            logger.error("schedule_cleanup_invalid_type", cleanup_type=cleanup_type)
            result = {"error": f"Invalid cleanup type: {cleanup_type}"}

        logger.info("schedule_cleanup_complete", cleanup_type=cleanup_type)

        return result
