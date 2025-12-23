#!/usr/bin/env python3
"""Regenerate golden dataset with full agent analysis pipeline.

This script runs the COMPLETE LangGraph workflow on fixture content,
producing triple-consumer artifacts with:
- TL;DR sections
- AI Assistant prompts
- Core Concepts for tutor
- Exercises & Quizzes
- Mermaid diagrams
- Quality gate validation

Unlike load_golden_dataset.py which creates placeholders, this script
runs real LLM analysis through all 8 specialized agents.

Usage:
    poetry run python scripts/regenerate_with_agents.py [--limit N] [--dry-run]

Options:
    --limit N    Only process first N documents (for testing)
    --dry-run    Show what would be processed without running
    --verbose    Enable debug logging
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.core.logging import get_logger  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.db.models.analysis import Analysis  # noqa: E402
from app.domains.analysis.workflows.analysis import create_analysis_workflow  # noqa: E402

logger = get_logger(__name__)


async def load_fixture_documents() -> list[dict[str, Any]]:
    """Load fixture documents from expanded JSON."""
    fixtures_path = (
        Path(__file__).parent.parent / "tests/smoke/retrieval/fixtures/documents_expanded.json"
    )

    if not fixtures_path.exists():
        msg = f"Fixtures not found: {fixtures_path}"
        raise FileNotFoundError(msg)

    with fixtures_path.open() as f:
        data = json.load(f)

    return data["documents"]


def fixture_to_raw_content(doc: dict[str, Any]) -> str:
    """Convert fixture document to raw content string for workflow."""
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


async def create_analysis_record(
    session: Any,
    doc: dict[str, Any],
) -> Analysis:
    """Create Analysis record for fixture document."""
    analysis_id = uuid4()
    content_type = doc.get("content_type", "article")

    # Create realistic URL based on content type
    url_base = {
        "article": "https://docs.skillforge.dev",
        "tutorial": "https://learn.skillforge.dev",
        "research_paper": "https://papers.skillforge.dev",
    }.get(content_type, "https://content.skillforge.dev")

    analysis = Analysis(
        id=analysis_id,
        url=f"{url_base}/{doc['id']}",
        content_type=content_type,
        status="pending",
        title=doc["title"],
    )
    session.add(analysis)
    await session.flush()

    return analysis


async def run_workflow_on_fixture(
    doc: dict[str, Any],
    analysis: Analysis,
    skill_level: str = "intermediate",
) -> dict[str, Any]:
    """Run the full LangGraph workflow on fixture content.

    This bypasses URL extraction by providing raw_content directly in the
    initial state. The extract node detects this and skips JinaReader.

    The workflow runs:
    1. Extract (passthrough - content already provided)
    2. Fan-out: Embedding + Supervisor + Inject Context (parallel)
    3. Fan-out: Selected agents (parallel via Send API)
    4. Fan-in: Aggregate findings
    5. Quality gate validation
    6. Artifact generation with triple-consumer template
    """
    # Prepare initial state with pre-extracted content
    raw_content = fixture_to_raw_content(doc)
    extraction_metadata = fixture_to_extraction_metadata(doc)

    initial_state = {
        "analysis_id": str(analysis.id),
        "url": analysis.url,
        "content_type": analysis.content_type,
        "skill_level": skill_level,
        "raw_content": raw_content,  # Triggers passthrough in extract node
        "extraction_metadata": extraction_metadata,
    }

    # Config with thread_id for checkpointing
    config = {"configurable": {"thread_id": str(analysis.id)}}

    # Run the workflow (extract node will passthrough since raw_content is set)
    logger.info(f"Running workflow for: {doc['title']}")
    workflow = create_analysis_workflow()
    result = await workflow.ainvoke(initial_state, config)

    return result


async def process_document(
    doc: dict[str, Any],
    doc_idx: int,
    total: int,
) -> dict[str, Any]:
    """Process a single fixture document through the full pipeline."""
    start_time = time.time()
    analysis_id = None

    try:
        # Create analysis record in its own session
        async with AsyncSessionLocal() as session:
            analysis = await create_analysis_record(session, doc)
            analysis_id = str(analysis.id)
            await session.commit()  # Commit immediately so workflow can use it
            logger.info(f"[{doc_idx + 1}/{total}] Created analysis: {analysis_id} - {doc['title']}")

        # Run workflow in a separate context (workflow manages its own sessions)
        result = await run_workflow_on_fixture(doc, analysis)

        elapsed = time.time() - start_time
        logger.info(f"[{doc_idx + 1}/{total}] Completed in {elapsed:.1f}s: {doc['title']}")

        return {
            "analysis_id": analysis_id,
            "title": doc["title"],
            "status": "success",
            "elapsed": elapsed,
            "artifact_id": result.get("artifact_id"),
        }

    except Exception as e:
        logger.exception(f"[{doc_idx + 1}/{total}] Failed: {doc['title']}")
        return {
            "analysis_id": analysis_id,
            "title": doc["title"],
            "status": "failed",
            "error": str(e),
        }


async def main(limit: int | None = None, dry_run: bool = False) -> int:
    """Main regeneration function."""
    logger.info("=" * 60)
    logger.info("Golden Dataset Regeneration with Full Agent Analysis")
    logger.info("=" * 60)

    # Load fixtures
    documents = await load_fixture_documents()

    if limit:
        documents = documents[:limit]

    logger.info(f"Processing {len(documents)} documents")

    if dry_run:
        logger.info("DRY RUN - would process:")
        for i, doc in enumerate(documents):
            logger.info(f"  [{i + 1}] {doc['title']} ({doc.get('content_type', 'article')})")
        return 0

    # Process documents
    results = []
    for i, doc in enumerate(documents):
        result = await process_document(doc, i, len(documents))
        results.append(result)

        # Rate limiting: pause between documents to avoid overwhelming APIs
        if i < len(documents) - 1:
            await asyncio.sleep(2)  # 2 second delay between analyses

    # Summary
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")

    logger.info("")
    logger.info("=" * 60)
    logger.info("REGENERATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Success: {success_count}")
    logger.info(f"  Failed:  {failed_count}")
    logger.info(f"  Total:   {len(results)}")

    if failed_count > 0:
        logger.info("")
        logger.info("Failed documents:")
        for r in results:
            if r["status"] == "failed":
                logger.info(f"  - {r['title']}: {r.get('error', 'unknown error')}")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Regenerate golden dataset with agents")
    parser.add_argument("--limit", type=int, help="Process only first N documents")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    exit_code = asyncio.run(main(limit=args.limit, dry_run=args.dry_run))
    sys.exit(exit_code)
