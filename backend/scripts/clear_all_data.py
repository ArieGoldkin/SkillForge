#!/usr/bin/env python3
"""Clear all data from the SkillForge database.

This script deletes all data from all tables, useful for development
when you want to start with a clean slate.

⚠️  WARNING: This will permanently delete ALL data from the database!
This includes:
- All analyses
- All artifacts
- All chunks
- All agent findings
- All progress records
- All tutoring sessions
- All agent memories and examples
- All annotation queue items

Usage:
    python scripts/clear_all_data.py

    # Dry run (preview what will be deleted)
    python scripts/clear_all_data.py --dry-run

    # Skip confirmation prompt
    python scripts/clear_all_data.py --yes
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_session_factory
from app.db.models import (
    Analysis,
    AnalysisChunk,
    Artifact,
    AgentFinding,
    AnalysisProgress,
    TutoringSession,
    TutoringMessage,
    AgentMemory,
    AgentExample,
    AnnotationQueue,
)

logger = get_logger(__name__)

# Tables in deletion order (respecting foreign key constraints)
# Delete child tables first, then parent tables
TABLES_TO_CLEAR = [
    # Child tables (depend on other tables)
    (TutoringMessage, "tutoring_messages"),
    (TutoringSession, "tutoring_sessions"),
    (AnalysisChunk, "analysis_chunks"),
    (Artifact, "artifacts"),
    (AgentFinding, "agent_findings"),
    (AnalysisProgress, "analysis_progress"),
    # Parent tables
    (Analysis, "analyses"),
    # Independent tables
    (AgentMemory, "agent_memories"),
    (AgentExample, "agent_examples"),
    (AnnotationQueue, "annotation_queue"),
]


async def get_table_counts(session: AsyncSession) -> dict[str, int]:
    """Get row counts for all tables."""
    counts: dict[str, int] = {}
    for model, table_name in TABLES_TO_CLEAR:
        result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        count = result.scalar() or 0
        counts[table_name] = count
    return counts


async def clear_all_data(session: AsyncSession, dry_run: bool = False) -> dict[str, int]:
    """Clear all data from all tables.

    Args:
        session: Database session
        dry_run: If True, only show what would be deleted without actually deleting

    Returns:
        Dictionary mapping table names to number of rows deleted
    """
    deleted_counts: dict[str, int] = {}

    if dry_run:
        logger.info("dry_run_mode", message="Previewing deletions (no data will be deleted)")

    for model, table_name in TABLES_TO_CLEAR:
        # Get count before deletion
        result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        count_before = result.scalar() or 0

        if count_before > 0:
            if not dry_run:
                # Delete all rows
                await session.execute(delete(model))
                await session.commit()
                logger.info(
                    "table_cleared",
                    table=table_name,
                    rows_deleted=count_before,
                )
            else:
                logger.info(
                    "table_would_be_cleared",
                    table=table_name,
                    rows_would_be_deleted=count_before,
                )

            deleted_counts[table_name] = count_before
        else:
            logger.debug("table_already_empty", table=table_name)

    return deleted_counts


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clear all data from SkillForge database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deletions without actually deleting (safe)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt (use with caution!)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Get session factory
    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            # Get current counts
            counts_before = await get_table_counts(session)
            total_rows = sum(counts_before.values())

            if total_rows == 0:
                print("✅ Database is already empty. Nothing to clear.")
                return

            # Show what will be deleted
            print("\n📊 Current database state:")
            print("=" * 60)
            for table_name, count in sorted(counts_before.items()):
                if count > 0:
                    print(f"  {table_name:30} {count:>10,} rows")
            print("=" * 60)
            print(f"  {'TOTAL':30} {total_rows:>10,} rows\n")

            if args.dry_run:
                print("🔍 DRY RUN MODE - No data will be deleted\n")
                await clear_all_data(session, dry_run=True)
                print("\n✅ Dry run complete. Run without --dry-run to actually delete.")
                return

            # Confirmation prompt
            if not args.yes:
                print("⚠️  WARNING: This will permanently delete ALL data from the database!")
                print("⚠️  This action cannot be undone!\n")
                response = input("Type 'DELETE ALL' to confirm: ")
                if response != "DELETE ALL":
                    print("❌ Cancelled. No data was deleted.")
                    return

            # Clear all data
            print("\n🗑️  Clearing all data...")
            deleted_counts = await clear_all_data(session, dry_run=False)

            # Show results
            print("\n✅ Data cleared successfully!")
            print("=" * 60)
            total_deleted = sum(deleted_counts.values())
            for table_name, count in sorted(deleted_counts.items()):
                if count > 0:
                    print(f"  {table_name:30} {count:>10,} rows deleted")
            print("=" * 60)
            print(f"  {'TOTAL':30} {total_deleted:>10,} rows deleted\n")

            logger.info("clear_all_data_completed", total_rows_deleted=total_deleted)

        except Exception as e:
            logger.error("clear_all_data_failed", error=str(e), exc_info=True)
            await session.rollback()
            print(f"\n❌ Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())


