#!/usr/bin/env python3
"""Regenerate ALL artifacts with updated Mermaid constraints.

This script re-runs the aggregation/synthesis step for existing analyses
to regenerate artifacts with the new diagram constraints.

Usage:
    poetry run python scripts/regenerate_all_artifacts.py --dry-run
    poetry run python scripts/regenerate_all_artifacts.py
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import delete, select

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.analysis import Analysis
from app.models.artifact import Artifact
from app.workflows.analysis import analysis_workflow

logger = get_logger(__name__)


async def get_all_completed_analyses() -> list[dict]:
    """Get all completed analyses with their data."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Analysis).where(
                Analysis.status.in_(["complete", "completed"])
            )
        )
        analyses = result.scalars().all()

        return [
            {
                "id": str(a.id),
                "url": a.url,
                "title": a.title,
                "content_type": a.content_type,
                "raw_content": a.raw_content,
                "content_summary": a.content_summary,
            }
            for a in analyses
        ]


async def delete_artifact(analysis_id: str) -> bool:
    """Delete existing artifact for an analysis."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            delete(Artifact).where(Artifact.analysis_id == UUID(analysis_id))
        )
        await session.commit()
        return result.rowcount > 0


async def regenerate_artifact(analysis: dict, idx: int, total: int) -> dict:
    """Regenerate artifact for a single analysis."""
    start_time = time.time()
    analysis_id = analysis["id"]

    try:
        # Delete existing artifact
        deleted = await delete_artifact(analysis_id)
        if deleted:
            logger.info(f"[{idx + 1}/{total}] Deleted old artifact for {analysis_id}")

        # Prepare state for workflow (skip extraction, go to aggregation)
        initial_state = {
            "analysis_id": analysis_id,
            "url": analysis["url"],
            "content_type": analysis["content_type"] or "article",
            "skill_level": "intermediate",
            "raw_content": analysis["raw_content"] or "",
            "content_summary": analysis["content_summary"] or "",
            # This triggers re-extraction and full workflow
        }

        config = {"configurable": {"thread_id": analysis_id}}

        # Run workflow
        logger.info(f"[{idx + 1}/{total}] Regenerating: {analysis['title'][:50]}...")
        result = await analysis_workflow.ainvoke(initial_state, config)

        elapsed = time.time() - start_time
        logger.info(f"[{idx + 1}/{total}] ✅ Done in {elapsed:.1f}s")

        return {
            "analysis_id": analysis_id,
            "title": analysis["title"],
            "status": "success",
            "elapsed": elapsed,
            "artifact_id": result.get("artifact_id"),
        }

    except Exception as e:
        logger.exception(f"[{idx + 1}/{total}] ❌ Failed: {analysis['title']}")
        return {
            "analysis_id": analysis_id,
            "title": analysis["title"],
            "status": "failed",
            "error": str(e),
        }


async def main(
    dry_run: bool = False,
    limit: int | None = None,
    analysis_ids: list[str] | None = None,
) -> int:
    """Main regeneration function."""
    logger.info("=" * 60)
    logger.info("Regenerating Artifacts with Updated Mermaid Constraints")
    logger.info("=" * 60)

    # Get all completed analyses
    analyses = await get_all_completed_analyses()

    # Filter by specific IDs if provided
    if analysis_ids:
        analyses = [a for a in analyses if a["id"] in analysis_ids]
        logger.info(f"Filtered to {len(analyses)} specific analyses")

    if limit:
        analyses = analyses[:limit]

    logger.info(f"Found {len(analyses)} completed analyses to regenerate")

    if dry_run:
        logger.info("\nDRY RUN - would regenerate:")
        for a in analyses:
            logger.info(f"  - {a['title'][:50]} ({a['id'][:8]}...)")
        return 0

    # Regenerate each
    results = []
    for i, analysis in enumerate(analyses):
        result = await regenerate_artifact(analysis, i, len(analyses))
        results.append(result)

        # Rate limiting between LLM calls
        if i < len(analyses) - 1:
            await asyncio.sleep(3)

    # Summary
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")

    logger.info("")
    logger.info("=" * 60)
    logger.info("REGENERATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Success: {success_count}")
    logger.info(f"  Failed:  {failed_count}")

    if failed_count > 0:
        logger.info("\nFailed:")
        for r in results:
            if r["status"] == "failed":
                logger.info(f"  - {r['title']}: {r.get('error', 'unknown')[:50]}")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Regenerate artifacts with updated Mermaid constraints"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be regenerated"
    )
    parser.add_argument(
        "--limit", type=int, help="Limit number of artifacts to regenerate"
    )
    parser.add_argument(
        "--ids", nargs="+", help="Specific analysis IDs to regenerate"
    )
    args = parser.parse_args()

    exit_code = asyncio.run(
        main(dry_run=args.dry_run, limit=args.limit, analysis_ids=args.ids)
    )
    sys.exit(exit_code)
