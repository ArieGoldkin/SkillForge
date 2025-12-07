#!/usr/bin/env python3
"""Cleanup script to delete incomplete analyses and related data.

This script deletes analyses that don't have all required fields populated:
- raw_content
- title
- content_embedding

It also cleans up related foreign key records first.
"""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

# Add backend to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import get_settings  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402


async def cleanup_incomplete_analyses():
    """Delete incomplete analyses and related data."""
    settings = get_settings()
    print(f"Connecting to database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'local'}")

    async with AsyncSessionLocal() as session:
        try:
            # 1. Count incomplete analyses first
            result = await session.execute(
                text("""
                    SELECT COUNT(*) as count
                    FROM analyses
                    WHERE raw_content IS NULL OR title IS NULL OR content_embedding IS NULL
                """)
            )
            incomplete_count = result.scalar()
            print(f"\nFound {incomplete_count} incomplete analyses to delete")

            if incomplete_count == 0:
                print("No incomplete analyses found. Nothing to clean up.")
                return

            # 2. Delete agent_findings for incomplete analyses
            print("\n1. Deleting agent_findings for incomplete analyses...")
            result = await session.execute(
                text("""
                    DELETE FROM agent_findings
                    WHERE analysis_id IN (
                        SELECT id FROM analyses
                        WHERE raw_content IS NULL OR title IS NULL OR content_embedding IS NULL
                    )
                """)
            )
            print(f"   Deleted {result.rowcount} agent_findings records")

            # 3. Delete artifacts for incomplete analyses
            print("2. Deleting artifacts for incomplete analyses...")
            result = await session.execute(
                text("""
                    DELETE FROM artifacts
                    WHERE analysis_id IN (
                        SELECT id FROM analyses
                        WHERE raw_content IS NULL OR title IS NULL OR content_embedding IS NULL
                    )
                """)
            )
            print(f"   Deleted {result.rowcount} artifacts records")

            # 4. Delete tutoring_sessions for incomplete analyses
            print("3. Deleting tutoring_sessions for incomplete analyses...")
            result = await session.execute(
                text("""
                    DELETE FROM tutoring_sessions
                    WHERE analysis_id IN (
                        SELECT id FROM analyses
                        WHERE raw_content IS NULL OR title IS NULL OR content_embedding IS NULL
                    )
                """)
            )
            print(f"   Deleted {result.rowcount} tutoring_sessions records")

            # 5. Delete analysis_progress for incomplete analyses
            print("4. Deleting analysis_progress for incomplete analyses...")
            result = await session.execute(
                text("""
                    DELETE FROM analysis_progress
                    WHERE analysis_id IN (
                        SELECT id FROM analyses
                        WHERE raw_content IS NULL OR title IS NULL OR content_embedding IS NULL
                    )
                """)
            )
            print(f"   Deleted {result.rowcount} analysis_progress records")

            # 6. Delete incomplete analyses
            print("5. Deleting incomplete analyses...")
            result = await session.execute(
                text("""
                    DELETE FROM analyses
                    WHERE raw_content IS NULL OR title IS NULL OR content_embedding IS NULL
                """)
            )
            deleted_count = result.rowcount
            print(f"   Deleted {deleted_count} incomplete analyses")

            # Commit all deletions
            await session.commit()
            print("\n✅ Cleanup completed successfully!")

            # 7. Verify cleanup
            print("\n6. Verifying cleanup...")
            result = await session.execute(text("SELECT COUNT(*) as remaining FROM analyses"))
            remaining = result.scalar()
            print(f"   Remaining analyses: {remaining}")

            result = await session.execute(
                text("""
                    SELECT COUNT(*) as fully_populated
                    FROM analyses
                    WHERE raw_content IS NOT NULL
                      AND title IS NOT NULL
                      AND content_embedding IS NOT NULL
                """)
            )
            fully_populated = result.scalar()
            print(f"   Fully populated analyses: {fully_populated}")

        except Exception as e:
            await session.rollback()
            print(f"\n❌ Error during cleanup: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(cleanup_incomplete_analyses())

