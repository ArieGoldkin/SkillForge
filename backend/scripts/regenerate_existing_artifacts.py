#!/usr/bin/env python3
"""Regenerate existing artifacts with updated template.

This script:
1. Identifies unique fixture documents from existing analyses
2. Deletes existing analyses/artifacts for those fixtures
3. Re-runs the full LLM workflow to generate fresh artifacts

Usage:
    poetry run python scripts/regenerate_existing_artifacts.py --dry-run
    poetry run python scripts/regenerate_existing_artifacts.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import delete, select, update

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.analysis import Analysis
from app.models.analysis_chunk import AnalysisChunk
from app.models.artifact import Artifact
from app.domains.analysis.workflows.analysis import analysis_workflow

logger = get_logger(__name__)


async def load_fixture_documents() -> list[dict[str, Any]]:
    """Load fixture documents from expanded JSON."""
    fixtures_path = (
        Path(__file__).parent.parent
        / "tests/smoke/retrieval/fixtures/documents_expanded.json"
    )

    if not fixtures_path.exists():
        msg = f"Fixtures not found: {fixtures_path}"
        raise FileNotFoundError(msg)

    with fixtures_path.open() as f:
        data = json.load(f)

    return data["documents"]


def fixture_to_raw_content(doc: dict[str, Any]) -> str:
    """Convert fixture document to raw content string."""
    parts = [f"# {doc['title']}", ""]

    for section in doc.get("sections", []):
        title = section.get("title", "")
        content = section.get("content", "")
        if title:
            parts.append(f"## {title}")
            parts.append("")
        parts.append(content)
        parts.append("")

    return "\n".join(parts)


def fixture_to_extraction_metadata(doc: dict[str, Any]) -> dict[str, Any]:
    """Create extraction metadata from fixture document."""
    raw_content = fixture_to_raw_content(doc)
    return {
        "title": doc["title"],
        "content_type": doc.get("content_type", "article"),
        "word_count": len(raw_content.split()),
        "language": doc.get("language", "en"),
        "source": "golden-dataset-fixture",
        "tags": doc.get("tags", []),
    }


async def get_existing_fixture_ids() -> list[str]:
    """Get unique fixture IDs from existing analyses."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Analysis.url).where(Analysis.url.like("%docs.skillforge.dev%"))
        )
        urls = [row[0] for row in result.all()]

    # Extract fixture IDs from URLs like https://docs.skillforge.dev/chain-of-thought
    fixture_ids = set()
    for url in urls:
        if "docs.skillforge.dev/" in url:
            fixture_id = url.split("/")[-1]
            fixture_ids.add(fixture_id)

    return list(fixture_ids)


async def cleanup_existing_data(fixture_ids: list[str], dry_run: bool = False) -> int:
    """Delete existing analyses/artifacts for the given fixture IDs."""
    deleted_count = 0

    async with AsyncSessionLocal() as session:
        for fixture_id in fixture_ids:
            url_pattern = f"%docs.skillforge.dev/{fixture_id}"

            # Get analysis IDs
            result = await session.execute(
                select(Analysis.id).where(Analysis.url.like(url_pattern))
            )
            analysis_ids = [row[0] for row in result.all()]

            if not analysis_ids:
                continue

            logger.info(
                f"Found {len(analysis_ids)} analyses for fixture '{fixture_id}'"
            )

            if not dry_run:
                # Delete chunks for these analyses
                for aid in analysis_ids:
                    await session.execute(
                        delete(AnalysisChunk).where(AnalysisChunk.analysis_id == aid)
                    )

                # Delete artifacts for these analyses
                for aid in analysis_ids:
                    await session.execute(
                        delete(Artifact).where(Artifact.analysis_id == aid)
                    )

                # Delete analyses
                await session.execute(
                    delete(Analysis).where(Analysis.id.in_(analysis_ids))
                )

                await session.commit()

            deleted_count += len(analysis_ids)

    return deleted_count


async def regenerate_fixture(
    doc: dict[str, Any],
    idx: int,
    total: int,
) -> dict[str, Any]:
    """Regenerate a single fixture through the full workflow."""
    start_time = time.time()
    analysis_id = None
    content_type = doc.get("content_type", "article")

    url_base = {
        "article": "https://docs.skillforge.dev",
        "tutorial": "https://learn.skillforge.dev",
        "research_paper": "https://papers.skillforge.dev",
    }.get(content_type, "https://content.skillforge.dev")

    try:
        # Create analysis record
        async with AsyncSessionLocal() as session:
            analysis = Analysis(
                id=uuid4(),
                url=f"{url_base}/{doc['id']}",
                content_type=content_type,
                status="pending",
                title=doc["title"],
            )
            session.add(analysis)
            await session.commit()
            analysis_id = str(analysis.id)
            logger.info(f"[{idx + 1}/{total}] Created analysis: {analysis_id}")

        # Prepare workflow state
        raw_content = fixture_to_raw_content(doc)
        extraction_metadata = fixture_to_extraction_metadata(doc)

        initial_state = {
            "analysis_id": analysis_id,
            "url": f"{url_base}/{doc['id']}",
            "content_type": content_type,
            "skill_level": "intermediate",
            "raw_content": raw_content,
            "extraction_metadata": extraction_metadata,
        }

        config = {"configurable": {"thread_id": analysis_id}}

        # Run workflow
        logger.info(f"[{idx + 1}/{total}] Running workflow for: {doc['title']}")
        result = await analysis_workflow.ainvoke(initial_state, config)

        # Update analysis status to complete
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(Analysis)
                .where(Analysis.id == UUID(analysis_id))
                .values(status="complete")
            )
            await session.commit()

        elapsed = time.time() - start_time
        logger.info(
            f"[{idx + 1}/{total}] ✅ Completed in {elapsed:.1f}s: {doc['title']}"
        )

        return {
            "analysis_id": analysis_id,
            "title": doc["title"],
            "status": "success",
            "elapsed": elapsed,
            "artifact_id": result.get("artifact_id"),
        }

    except Exception as e:
        logger.exception(f"[{idx + 1}/{total}] ❌ Failed: {doc['title']}")
        return {
            "analysis_id": analysis_id,
            "title": doc["title"],
            "status": "failed",
            "error": str(e),
        }


async def main(dry_run: bool = False) -> int:
    """Main regeneration function."""
    logger.info("=" * 60)
    logger.info("Regenerating Existing Artifacts with Updated Template")
    logger.info("=" * 60)

    # Load all fixtures
    all_fixtures = await load_fixture_documents()
    fixture_map = {doc["id"]: doc for doc in all_fixtures}

    # Get existing fixture IDs
    existing_ids = await get_existing_fixture_ids()
    logger.info(f"Found {len(existing_ids)} unique fixtures to regenerate: {existing_ids}")

    if not existing_ids:
        logger.info("No existing fixtures found. Nothing to regenerate.")
        return 0

    # Get fixture documents to regenerate
    docs_to_regenerate = []
    for fid in existing_ids:
        if fid in fixture_map:
            docs_to_regenerate.append(fixture_map[fid])
        else:
            logger.warning(f"Fixture '{fid}' not found in documents_expanded.json")

    logger.info(f"Will regenerate {len(docs_to_regenerate)} documents")

    if dry_run:
        logger.info("DRY RUN - would regenerate:")
        for doc in docs_to_regenerate:
            logger.info(f"  - {doc['title']} ({doc['id']})")
        return 0

    # Cleanup existing data
    logger.info("Cleaning up existing analyses and artifacts...")
    deleted = await cleanup_existing_data(existing_ids, dry_run=False)
    logger.info(f"Deleted {deleted} existing records")

    # Regenerate
    results = []
    for i, doc in enumerate(docs_to_regenerate):
        result = await regenerate_fixture(doc, i, len(docs_to_regenerate))
        results.append(result)

        # Rate limiting
        if i < len(docs_to_regenerate) - 1:
            await asyncio.sleep(2)

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
        logger.info("")
        logger.info("Failed documents:")
        for r in results:
            if r["status"] == "failed":
                logger.info(f"  - {r['title']}: {r.get('error', 'unknown')}")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Regenerate existing artifacts with updated template"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be regenerated"
    )
    args = parser.parse_args()

    exit_code = asyncio.run(main(dry_run=args.dry_run))
    sys.exit(exit_code)
