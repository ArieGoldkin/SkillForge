#!/usr/bin/env python3
"""Database cleanup script for SkillForge embedding pipeline.

This script can be run:
1. As a cron job for scheduled cleanup
2. Manually for one-off cleanup operations
3. As part of maintenance workflows

Usage:
    # Health check (read-only)
    python scripts/cleanup.py --check

    # Preview cleanup (dry run)
    python scripts/cleanup.py --dry-run

    # Execute orphan cleanup only
    python scripts/cleanup.py --orphans

    # Execute TTL cleanup only
    python scripts/cleanup.py --ttl

    # Full cleanup
    python scripts/cleanup.py --full

    # Full cleanup with superseded analyses
    python scripts/cleanup.py --full --include-superseded

    # Generate report
    python scripts/cleanup.py --report output.md

Examples:
    # Daily cron job (health check only)
    0 2 * * * cd /app && python scripts/cleanup.py --check

    # Weekly orphan cleanup
    0 3 * * 0 cd /app && python scripts/cleanup.py --orphans

    # Monthly full cleanup
    0 4 1 * * cd /app && python scripts/cleanup.py --full --include-superseded
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_async_session
from app.services.cleanup import CleanupService

logger = get_logger(__name__)


async def main() -> None:
    """Main cleanup script entry point."""
    parser = argparse.ArgumentParser(
        description="SkillForge database cleanup utility",
        epilog="For more information, see backend/app/services/cleanup/README.md",
    )

    # Cleanup operations
    operations = parser.add_mutually_exclusive_group(required=True)
    operations.add_argument(
        "--check",
        action="store_true",
        help="Health check only (read-only, no deletions)",
    )
    operations.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview cleanup without executing (dry run)",
    )
    operations.add_argument(
        "--orphans",
        action="store_true",
        help="Clean up orphaned chunks only",
    )
    operations.add_argument(
        "--ttl",
        action="store_true",
        help="Clean up expired analyses only (TTL-based)",
    )
    operations.add_argument(
        "--full",
        action="store_true",
        help="Full cleanup (orphans + TTL)",
    )
    operations.add_argument(
        "--report",
        type=str,
        metavar="FILE",
        help="Generate Markdown report (e.g., cleanup_report.md)",
    )

    # Options
    parser.add_argument(
        "--include-superseded",
        action="store_true",
        help="Include superseded analyses in cleanup (use with --full)",
    )
    parser.add_argument(
        "--hard-delete",
        action="store_true",
        help="Use hard delete (permanent) instead of soft delete",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for processing (default: 1000)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logger.info("verbose_mode_enabled")

    logger.info(
        "cleanup_script_started",
        operation=next(
            (
                k
                for k, v in vars(args).items()
                if v is True and k not in ["verbose", "include_superseded", "hard_delete"]
            ),
            "unknown",
        ),
    )

    # Get database session
    async for session in get_async_session():
        try:
            # Initialize cleanup service
            service = CleanupService(session, batch_size=args.batch_size)

            # Execute requested operation
            if args.check:
                await run_health_check(service)
            elif args.dry_run:
                await run_dry_run(service, args.include_superseded)
            elif args.orphans:
                await run_orphan_cleanup(service, args.include_superseded, args.hard_delete)
            elif args.ttl:
                await run_ttl_cleanup(service)
            elif args.full:
                await run_full_cleanup(service, args.include_superseded, args.hard_delete)
            elif args.report:
                await generate_report(service, args.report)

            logger.info("cleanup_script_completed")

        except Exception as e:
            logger.error("cleanup_script_failed", error=str(e), exc_info=True)
            sys.exit(1)


async def run_health_check(service: CleanupService) -> None:
    """Run health check and print results."""
    print("Running health check...\n")

    health = await service.health_check()

    status_emoji = "✅" if health["healthy"] else "⚠️"
    print(f"{status_emoji} Overall Status: {'Healthy' if health['healthy'] else 'Issues Found'}")
    print(f"\nIssue Counts:")
    print(f"  • Orphan chunks: {health['orphan_chunks']}")
    print(f"  • Expired analyses: {health['expired_analyses']}")
    print(f"  • Integrity issues: {health['integrity_issues']}")
    print(f"  • Total issues: {health['total_issues']}")

    if not health["healthy"]:
        print("\nRun with --dry-run to preview cleanup")

    sys.exit(0 if health["healthy"] else 1)


async def run_dry_run(
    service: CleanupService,
    include_superseded: bool,
) -> None:
    """Run cleanup preview (dry run)."""
    print("Running cleanup preview (dry run)...\n")

    result = await service.run_full_cleanup(
        include_orphans=True,
        include_expired=True,
        include_superseded=include_superseded,
        dry_run=True,
    )

    summary = result["summary"]
    print("Cleanup Preview:")
    print(f"  • Orphaned chunks: {summary['orphans_cleaned']}")
    print(f"  • Expired analyses: {summary['analyses_expired']}")
    print(f"  • Total items: {summary['total_items_affected']}")

    if summary["integrity_issues"] > 0:
        print(f"\n⚠️  Found {summary['integrity_issues']} integrity issues")
        print("    Run with --report to see details")

    print("\nRun without --dry-run to execute cleanup")


async def run_orphan_cleanup(
    service: CleanupService,
    include_superseded: bool,
    hard_delete: bool,
) -> None:
    """Run orphan cleanup."""
    print("Running orphan cleanup...\n")

    result = await service.orphan_cleaner.cleanup_all_orphans(
        hard_delete=hard_delete,
        include_superseded=include_superseded,
    )

    print("Orphan Cleanup Results:")
    print(f"  • Missing parent: {result['missing_parent']} chunks")
    print(f"  • Failed analysis: {result['failed_analysis']} chunks")
    print(f"  • Superseded analysis: {result['superseded_analysis']} chunks")
    print(f"  • Total deleted: {result['total_deleted']} chunks")
    print(f"  • Delete type: {'Hard delete (permanent)' if hard_delete else 'Soft delete'}")


async def run_ttl_cleanup(service: CleanupService) -> None:
    """Run TTL-based cleanup."""
    print("Running TTL cleanup...\n")

    result = await service.ttl_cleaner.delete_expired_analyses()

    print("TTL Cleanup Results:")
    for status, count in result.items():
        if status != "total":
            print(f"  • {status}: {count} analyses")
    print(f"  • Total deleted: {result['total']} analyses")


async def run_full_cleanup(
    service: CleanupService,
    include_superseded: bool,
    hard_delete: bool,
) -> None:
    """Run full cleanup."""
    print("Running full cleanup...\n")

    result = await service.run_full_cleanup(
        include_orphans=True,
        include_expired=True,
        include_superseded=include_superseded,
        hard_delete=hard_delete,
        dry_run=False,
    )

    summary = result["summary"]
    print("Full Cleanup Results:")
    print(f"  • Orphaned chunks: {summary['orphans_cleaned']}")
    print(f"  • Expired analyses: {summary['analyses_expired']}")
    print(f"  • Total items: {summary['total_items_affected']}")

    if summary["integrity_issues"] > 0:
        print(f"\n⚠️  Found {summary['integrity_issues']} integrity issues")
        print("    Run with --report to see details")


async def generate_report(service: CleanupService, output_file: str) -> None:
    """Generate and save cleanup report."""
    print(f"Generating cleanup report: {output_file}\n")

    report = await service.generate_cleanup_report_markdown()

    with open(output_file, "w") as f:
        f.write(report)

    print(f"✅ Report saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
