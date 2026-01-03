#!/usr/bin/env python3
"""Regenerate golden dataset artifacts with the NEW workflow system.

This script regenerates all 97 golden dataset artifacts using the updated
LangGraph workflow with:
- Claude Sonnet 4 (instead of old gpt-4o-mini)
- Quality gates with ASPECT_MINIMUMS enforcement
- Triple-consumer format (AI Guide + Exercises + Quizzes)
- Mermaid diagram generation
- Collapsible sections
- Anti-hallucination grounding instructions

The script uses content passthrough mode to inject fixture content directly,
skipping URL extraction while running through the FULL workflow pipeline.

Usage:
    # Dry run (no DB writes)
    poetry run python scripts/regenerate_golden_dataset.py --dry-run

    # Regenerate all 97 artifacts (sequential, safe)
    poetry run python scripts/regenerate_golden_dataset.py

    # Regenerate with parallel batches (faster, uses more API credits)
    poetry run python scripts/regenerate_golden_dataset.py --parallel --batch-size 5

    # Regenerate specific documents only
    poetry run python scripts/regenerate_golden_dataset.py --ids context-engineering,rag-survey

Requirements:
    - Docker backend running on port 8500
    - PostgreSQL with existing schema
    - Valid ANTHROPIC_API_KEY (for Claude Sonnet 4)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

# Import status update helper from workflow runner
from app.api.v1.analysis.workflow_runner import _update_analysis_status
from dotenv import load_dotenv

from app.core.logging import get_logger
from app.db.models.analysis import Analysis
from app.db.session import AsyncSessionLocal
from app.domains.analysis.workflows.analysis import create_analysis_workflow

logger = get_logger(__name__)


class FixtureSourceUrlMissingError(RuntimeError):
    """Fixture document is missing required `source_url`."""


# Constants
FIXTURE_PATH = Path("tests/smoke/retrieval/fixtures/documents_expanded.json")
BACKUP_PATH = Path("data/golden_dataset_backup.json")
OUTPUT_REPORT_PATH = Path("data/golden_dataset_regeneration_report.json")

# Rate limiting (to avoid API rate limits)
DEFAULT_DELAY_SECONDS = 2.0
PARALLEL_BATCH_SIZE = 3


def load_fixture_documents() -> list[dict]:
    """Load golden dataset fixture documents."""
    if not FIXTURE_PATH.exists():
        raise FileNotFoundError(FIXTURE_PATH)

    with FIXTURE_PATH.open() as f:
        data = json.load(f)

    documents = data.get("documents", data)
    logger.info("fixture_documents_loaded", count=len(documents))
    return documents


def build_raw_content(doc: dict) -> str:
    """Convert fixture document sections into raw markdown content.

    This concatenates all sections into a single markdown string,
    preserving structure that the workflow expects.
    """
    title = doc.get("title", "Untitled")
    sections = doc.get("sections", [])

    # Build markdown from sections
    parts = [f"# {title}\n"]

    for section in sections:
        section_title = section.get("title", "")
        section_content = section.get("content", "")

        if section_title:
            parts.append(f"\n## {section_title}\n")
        if section_content:
            parts.append(f"\n{section_content}\n")

    return "\n".join(parts)


def build_extraction_metadata(doc: dict) -> dict[str, Any]:
    """Build extraction metadata from fixture document."""
    return {
        "title": doc.get("title", "Untitled"),
        "content_type": doc.get("content_type", "article"),
        "tags": doc.get("tags", []),
        "language": doc.get("language", "en"),
        "word_count": sum(len(s.get("content", "").split()) for s in doc.get("sections", [])),
        "source": "golden-dataset-regenerated",
        "regenerated_at": datetime.now(UTC).isoformat(),
    }


async def create_analysis_record(doc: dict) -> Analysis:
    """Create a new analysis record in the database."""
    doc_id = doc.get("id", "unknown")
    title = doc.get("title", "Untitled")
    content_type = doc.get("content_type", "article")
    source_url = doc.get("source_url")

    if not source_url:
        logger.error(
            "fixture_document_missing_source_url",
            doc_id=doc_id,
            title=title,
        )
        raise FixtureSourceUrlMissingError

    # Create analysis record - DB generates UUIDs via server_default
    async with AsyncSessionLocal() as session:
        analysis = Analysis(
            url=source_url,
            title=title,
            content_type=content_type,
            status="processing",
        )
        session.add(analysis)
        await session.commit()
        await session.refresh(analysis)

        logger.info(
            "analysis_record_created",
            analysis_id=str(analysis.id),
            title=title,
        )
        return analysis


async def run_workflow_for_document(
    doc: dict,
    analysis_id: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run the full workflow for a fixture document.

    Uses content passthrough mode to inject raw_content directly,
    skipping URL extraction but running through the full pipeline.
    """
    doc_id = doc.get("id", "unknown")
    title = doc.get("title", "Untitled")

    logger.info(
        "workflow_starting",
        doc_id=doc_id,
        title=title,
        analysis_id=analysis_id,
    )

    if dry_run:
        logger.info("dry_run_skipping_workflow", doc_id=doc_id)
        return {
            "status": "dry_run",
            "doc_id": doc_id,
            "title": title,
        }

    # Build initial state with raw_content (passthrough mode)
    raw_content = build_raw_content(doc)
    extraction_metadata = build_extraction_metadata(doc)
    source_url = doc.get("source_url")

    if not source_url:
        logger.error(
            "fixture_document_missing_source_url",
            doc_id=doc_id,
            title=title,
        )
        raise FixtureSourceUrlMissingError

    initial_state = {
        "url": source_url,
        "analysis_id": analysis_id,
        "raw_content": raw_content,  # <-- Triggers passthrough mode
        "extraction_metadata": extraction_metadata,
        "content_type": extraction_metadata.get("content_type", "article"),
        "skill_level": "intermediate",
    }

    # Run the workflow
    start_time = time.time()
    try:
        workflow = create_analysis_workflow()
        result = await workflow.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": analysis_id}},
        )

        duration = time.time() - start_time

        # Check for artifact generation
        artifact_id = result.get("artifact_id")
        quality_scores = result.get("quality_scores", {})

        # FIX: Update analysis status to "complete" after successful workflow
        # This was missing, causing "processing" status to persist
        if artifact_id:
            await _update_analysis_status(UUID(analysis_id), "complete")
            logger.info(
                "analysis_status_updated",
                analysis_id=analysis_id,
                status="complete",
            )

        logger.info(
            "workflow_completed",
            doc_id=doc_id,
            analysis_id=analysis_id,
            artifact_id=str(artifact_id) if artifact_id else None,
            duration_seconds=round(duration, 2),
            quality_scores=quality_scores,
        )

        return {
            "status": "success",
            "doc_id": doc_id,
            "title": title,
            "analysis_id": analysis_id,
            "artifact_id": str(artifact_id) if artifact_id else None,
            "duration_seconds": round(duration, 2),
            "quality_scores": quality_scores,
        }

    except Exception as e:
        duration = time.time() - start_time
        logger.exception(
            "workflow_failed",
            doc_id=doc_id,
            analysis_id=analysis_id,
            error=str(e),
            duration_seconds=round(duration, 2),
        )

        return {
            "status": "failed",
            "doc_id": doc_id,
            "title": title,
            "analysis_id": analysis_id,
            "error": str(e),
            "duration_seconds": round(duration, 2),
        }


async def regenerate_document(
    doc: dict,
    dry_run: bool = False,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
) -> dict[str, Any]:
    """Regenerate a single document through the workflow."""
    doc_id = doc.get("id", "unknown")
    title = doc.get("title", "Untitled")

    print(f"  Processing: {title}...")

    try:
        # Create analysis record
        if not dry_run:
            analysis = await create_analysis_record(doc)
            analysis_id = str(analysis.id)
        else:
            analysis_id = f"dry-run-{doc_id}"

        # Run workflow
        result = await run_workflow_for_document(doc, analysis_id, dry_run)

        # Rate limit delay
        if not dry_run and delay_seconds > 0:
            await asyncio.sleep(delay_seconds)

        return result

    except Exception as e:
        logger.exception(
            "document_regeneration_failed",
            doc_id=doc_id,
            error=str(e),
        )
        return {
            "status": "error",
            "doc_id": doc_id,
            "title": title,
            "error": str(e),
        }


async def regenerate_all_sequential(
    documents: list[dict],
    dry_run: bool = False,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
) -> list[dict[str, Any]]:
    """Regenerate all documents sequentially (safer, slower)."""
    results = []
    total = len(documents)

    for i, doc in enumerate(documents):
        print(f"\n[{i + 1}/{total}] ", end="")
        result = await regenerate_document(doc, dry_run, delay_seconds)
        results.append(result)

        # Progress report
        success = sum(1 for r in results if r.get("status") == "success")
        failed = sum(1 for r in results if r.get("status") == "failed")
        print(f"    Status: {result.get('status')} | Progress: {success} success, {failed} failed")

    return results


async def regenerate_all_parallel(
    documents: list[dict],
    batch_size: int = PARALLEL_BATCH_SIZE,
    dry_run: bool = False,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
) -> list[dict[str, Any]]:
    """Regenerate documents in parallel batches (faster, uses more API credits)."""
    results = []
    total = len(documents)

    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch = documents[batch_start:batch_end]

        print(
            f"\n[Batch {batch_start // batch_size + 1}] Processing {len(batch)} documents ({batch_start + 1}-{batch_end}/{total})..."
        )

        # Run batch in parallel
        tasks = [
            regenerate_document(doc, dry_run, 0)  # No delay within batch
            for doc in batch
        ]
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)

        # Progress report
        success = sum(1 for r in results if r.get("status") == "success")
        failed = sum(1 for r in results if r.get("status") == "failed")
        print(f"    Batch complete | Total progress: {success} success, {failed} failed")

        # Delay between batches
        if batch_end < total and delay_seconds > 0:
            print(f"    Waiting {delay_seconds}s before next batch...")
            await asyncio.sleep(delay_seconds)

    return results


def save_report(results: list[dict[str, Any]], output_path: Path) -> None:
    """Save regeneration report to JSON file."""
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "total": len(results),
        "success": sum(1 for r in results if r.get("status") == "success"),
        "failed": sum(1 for r in results if r.get("status") == "failed"),
        "dry_run": sum(1 for r in results if r.get("status") == "dry_run"),
        "results": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(report, f, indent=2)

    print(f"\nReport saved to: {output_path}")


def print_summary(results: list[dict[str, Any]]) -> None:
    """Print summary of regeneration results."""
    total = len(results)
    success = sum(1 for r in results if r.get("status") == "success")
    failed = sum(1 for r in results if r.get("status") == "failed")
    dry_run = sum(1 for r in results if r.get("status") == "dry_run")

    print("\n" + "=" * 60)
    print("REGENERATION SUMMARY")
    print("=" * 60)
    print(f"Total documents:  {total}")
    print(f"Success:          {success}")
    print(f"Failed:           {failed}")
    print(f"Dry run:          {dry_run}")
    print("=" * 60)

    # Show failed documents
    if failed > 0:
        print("\nFailed documents:")
        for r in results:
            if r.get("status") == "failed":
                print(f"  - {r.get('title')}: {r.get('error', 'Unknown error')}")

    # Calculate average duration
    durations = [r.get("duration_seconds", 0) for r in results if r.get("duration_seconds")]
    if durations:
        avg_duration = sum(durations) / len(durations)
        total_duration = sum(durations)
        print(f"\nAverage duration: {avg_duration:.2f}s")
        print(f"Total duration:   {total_duration:.2f}s ({total_duration / 60:.1f}m)")


async def main() -> None:
    """Main entry point for golden dataset regeneration."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Regenerate golden dataset with NEW workflow system"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without making any changes",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run in parallel batches (faster, uses more API credits)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=PARALLEL_BATCH_SIZE,
        help=f"Batch size for parallel mode (default: {PARALLEL_BATCH_SIZE})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help=f"Delay between documents/batches in seconds (default: {DEFAULT_DELAY_SECONDS})",
    )
    parser.add_argument(
        "--ids",
        type=str,
        help="Comma-separated list of document IDs to regenerate (e.g., context-engineering,rag-survey)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(OUTPUT_REPORT_PATH),
        help=f"Output report path (default: {OUTPUT_REPORT_PATH})",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("GOLDEN DATASET REGENERATION")
    print("=" * 60)
    print(f"Mode:        {'Parallel' if args.parallel else 'Sequential'}")
    print(f"Dry run:     {args.dry_run}")
    print(f"Batch size:  {args.batch_size}")
    print(f"Delay:       {args.delay}s")
    print("=" * 60)

    # Load fixture documents
    documents = load_fixture_documents()

    # Filter by IDs if specified
    if args.ids:
        ids = [id.strip() for id in args.ids.split(",")]
        documents = [d for d in documents if d.get("id") in ids]
        print(f"Filtered to {len(documents)} documents: {ids}")

    print(f"\nTotal documents to process: {len(documents)}")

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made\n")

    # Confirm before proceeding
    if not args.dry_run:
        print("\n⚠️  This will regenerate artifacts using API credits!")
        response = input("Continue? [y/N]: ")
        if response.lower() != "y":
            print("Aborted.")
            return

    # Run regeneration
    if args.parallel:
        results = await regenerate_all_parallel(
            documents,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            delay_seconds=args.delay,
        )
    else:
        results = await regenerate_all_sequential(
            documents,
            dry_run=args.dry_run,
            delay_seconds=args.delay,
        )

    # Save report
    save_report(results, Path(args.output))

    # Print summary
    print_summary(results)


if __name__ == "__main__":
    asyncio.run(main())
