"""Migrate existing analysis status values to new granular status system.

Finds analyses with status='complete' but no artifact,
and updates them to status='artifact_failed'.

Usage:
    poetry run python scripts/migrate_status_values.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.models.analysis import Analysis
from app.db.models.artifact import Artifact
from app.db.session import AsyncSessionLocal
from app.domains.analysis.schemas.api import AnalysisStatus

logger = get_logger(__name__)


async def migrate_statuses() -> None:
    """Migrate existing status values to new granular system."""
    async with AsyncSessionLocal() as db:
        # Find analyses marked complete but no artifact
        stmt = (
            select(Analysis)
            .where(Analysis.status == "complete")
            .where(
                ~select(Artifact.analysis_id)
                .where(Artifact.analysis_id == Analysis.id)
                .exists()
            )
        )

        result = await db.execute(stmt)
        analyses = result.scalars().all()

        print(f"Found {len(analyses)} analyses to migrate")

        if len(analyses) == 0:
            print("✅ No analyses need migration")
            return

        for analysis in analyses:
            print(
                f"Migrating {analysis.id} from 'complete' to 'artifact_failed' "
                f"(URL: {analysis.url[:60]}...)"
            )
            analysis.status = AnalysisStatus.ARTIFACT_FAILED.value
            analysis.error_code = "incomplete_workflow"
            analysis.error_message = (
                "Analysis marked complete but no artifact exists (migrated to granular status)"
            )
            analysis.failed_at_stage = "artifact_generation"

        await db.commit()
        print(f"✅ Migrated {len(analyses)} analyses to 'artifact_failed' status")


if __name__ == "__main__":
    asyncio.run(migrate_statuses())

