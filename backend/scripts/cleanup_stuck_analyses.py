#!/usr/bin/env python3
"""Cleanup script to mark stuck analyses as failed.

Marks analyses stuck in 'analyzing' or 'pending' status for more than
10 minutes as failed with WORKFLOW_TIMEOUT error code.

Usage:
    poetry run python scripts/cleanup_stuck_analyses.py [--dry-run] [--minutes 10]
"""

import asyncio
import argparse
from datetime import UTC, datetime, timedelta

from app.core.logging import get_logger
from app.db.session import get_session_factory
from app.db.repositories.analysis_repository import AnalysisRepository

logger = get_logger(__name__)


async def cleanup_stuck_analyses(dry_run: bool = False, minutes: int = 10) -> None:
    """Mark stuck analyses as failed.

    Args:
        dry_run: If True, only log what would be done without making changes
        minutes: Number of minutes old to consider an analysis "stuck"
    """
    cutoff_time = datetime.now(UTC) - timedelta(minutes=minutes)
    
    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = AnalysisRepository(session)
        
        # Find stuck analyses
        from sqlalchemy import select, and_, or_
        from app.db.models.analysis import Analysis
        
        query = select(Analysis).where(
            and_(
                or_(Analysis.status == "analyzing", Analysis.status == "pending"),
                Analysis.created_at < cutoff_time,
            )
        )
        
        result = await session.execute(query)
        stuck_analyses = result.scalars().all()
        
        count = len(stuck_analyses)
        logger.info(
            "cleanup_stuck_analyses_found",
            count=count,
            minutes=minutes,
            dry_run=dry_run,
        )
        
        if count == 0:
            logger.info("cleanup_stuck_analyses_none_found")
            return
        
        # Group by status for reporting
        by_status = {}
        for analysis in stuck_analyses:
            status = str(analysis.status)
            by_status[status] = by_status.get(status, 0) + 1
        
        logger.info(
            "cleanup_stuck_analyses_by_status",
            status_breakdown=by_status,
        )
        
        if dry_run:
            logger.info(
                "cleanup_stuck_analyses_dry_run",
                message="DRY RUN: Would mark the following analyses as failed:",
            )
            for analysis in stuck_analyses[:10]:  # Show first 10
                logger.info(
                    "cleanup_stuck_analyses_example",
                    analysis_id=str(analysis.id),
                    status=str(analysis.status),
                    created_at=analysis.created_at.isoformat(),
                    title=analysis.title or "Untitled",
                )
            if count > 10:
                logger.info(
                    "cleanup_stuck_analyses_more",
                    remaining_count=count - 10,
                )
            return
        
        # Mark as failed
        updated_count = 0
        for analysis in stuck_analyses:
            try:
                await repo.mark_failed(
                    analysis_id=analysis.id,
                    error_code="WORKFLOW_TIMEOUT",
                    error_message=(
                        f"Analysis stuck in '{analysis.status}' status "
                        f"for {minutes}+ minutes. Marked as failed by cleanup script."
                    ),
                    failed_at_stage="workflow_execution",
                )
                updated_count += 1
            except Exception as e:
                logger.error(
                    "cleanup_stuck_analyses_failed_to_update",
                    analysis_id=str(analysis.id),
                    error=str(e),
                    exc_info=True,
                )
        
        await session.commit()
        
        logger.info(
            "cleanup_stuck_analyses_complete",
            total_found=count,
            updated=updated_count,
            failed=count - updated_count,
        )


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Cleanup stuck analyses by marking them as failed"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--minutes",
        type=int,
        default=10,
        help="Number of minutes old to consider an analysis 'stuck' (default: 10)",
    )
    
    args = parser.parse_args()
    
    await cleanup_stuck_analyses(dry_run=args.dry_run, minutes=args.minutes)


if __name__ == "__main__":
    asyncio.run(main())
