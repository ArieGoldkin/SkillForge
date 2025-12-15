#!/usr/bin/env python3
"""Re-render all artifacts using the updated Jinja2 template.

This script regenerates artifact markdown WITHOUT re-running LLM analysis.
It uses existing aggregated_insights data from the database and applies
the new template with:
- fix_bullets filter for proper list rendering
- slugify filter for clickable See also/Related links

Usage:
    poetry run python scripts/rerender_artifacts.py --dry-run
    poetry run python scripts/rerender_artifacts.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import select

from app.core.logging import get_logger
from app.core.template_utils import render_jinja_template
from app.db.session import AsyncSessionLocal
from app.models.analysis import Analysis
from app.models.artifact import Artifact

logger = get_logger(__name__)


async def rerender_all_artifacts(dry_run: bool = False) -> dict:
    """Re-render all artifacts using updated template.

    Args:
        dry_run: If True, don't save changes to database

    Returns:
        Summary of results

    """
    results = {
        "total": 0,
        "success": 0,
        "skipped": 0,
        "errors": [],
    }

    async with AsyncSessionLocal() as db:
        # Get all artifacts with their analyses
        query = select(Artifact).join(Analysis)
        result = await db.execute(query)
        artifacts = result.scalars().all()

        results["total"] = len(artifacts)
        print(f"\n{'=' * 60}")
        print(f"Re-rendering {len(artifacts)} artifacts with updated template")
        print(f"Dry run: {dry_run}")
        print(f"{'=' * 60}\n")

        for i, artifact in enumerate(artifacts):
            try:
                # Get the analysis
                analysis_query = select(Analysis).where(
                    Analysis.id == artifact.analysis_id
                )
                analysis_result = await db.execute(analysis_query)
                analysis = analysis_result.scalar_one_or_none()

                if not analysis:
                    print(f"[{i+1}/{len(artifacts)}] ⚠️  No analysis for artifact {artifact.id}")
                    results["skipped"] += 1
                    continue

                # Get data from artifact_metadata (where aggregated_insights is stored)
                metadata = artifact.artifact_metadata or {}
                aggregated_insights = metadata.get("aggregated_insights", {})

                # If no aggregated_insights in metadata, check if we can extract from
                # the existing markdown content (skip re-render if no source data)
                if not aggregated_insights:
                    print(f"[{i+1}/{len(artifacts)}] ⚠️  No insights in metadata for {artifact.id}")
                    results["skipped"] += 1
                    continue

                # Build template context from metadata
                template_context = {
                    "document_title": metadata.get("title", analysis.title) or "Untitled",
                    "source_url": metadata.get("source_url", analysis.url) or "",
                    "analysis_date": metadata.get(
                        "analysis_date",
                        analysis.created_at.isoformat() if analysis.created_at else "",
                    ),
                    "aggregated_insights": aggregated_insights,
                    "agent_findings": metadata.get("agent_findings", []),
                    "coverage_score": metadata.get("coverage_score", 0),
                    "average_confidence": metadata.get("average_confidence", 0),
                    "agents_involved": metadata.get("agents_involved", []),
                }

                # Render new markdown
                new_markdown = render_jinja_template("artifact.j2", template_context)

                # Check if content changed
                old_len = len(artifact.markdown_content or "")
                new_len = len(new_markdown)

                if not dry_run:
                    artifact.markdown_content = new_markdown
                    await db.commit()

                title_short = (analysis.title or "Untitled")[:40]
                print(
                    f"[{i+1}/{len(artifacts)}] ✅ {title_short}... "
                    f"({old_len} → {new_len} chars)"
                )
                results["success"] += 1

            except Exception as e:
                print(f"[{i+1}/{len(artifacts)}] ❌ Error: {e}")
                results["errors"].append({"id": str(artifact.id), "error": str(e)})

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Re-render all artifacts using updated template"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't save changes to database",
    )
    args = parser.parse_args()

    results = asyncio.run(rerender_all_artifacts(dry_run=args.dry_run))

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total artifacts: {results['total']}")
    print(f"Success: {results['success']}")
    print(f"Skipped: {results['skipped']}")
    print(f"Errors: {len(results['errors'])}")

    if results["errors"]:
        print("\nErrors:")
        for err in results["errors"]:
            print(f"  - {err['id']}: {err['error']}")

    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
