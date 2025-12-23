#!/usr/bin/env python3
"""Batch analyze multiple URLs with the full LLM workflow.

Usage:
    SKILLFORGE_STEP_TIMEOUT=600 poetry run python scripts/batch_analyze_urls.py
"""

from __future__ import annotations

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
from app.db.models.analysis import Analysis
from app.db.models.analysis_chunk import AnalysisChunk
from app.db.models.artifact import Artifact
from app.shared.services.extraction import JinaReader
from app.domains.analysis.workflows.analysis import create_analysis_workflow

logger = get_logger(__name__)

# URLs to analyze - Using arXiv directly (HuggingFace only has abstracts)
URLS_TO_ANALYZE = [
    # ACE Paper - Agentic Context Engineering for self-improving LLMs
    {"url": "https://arxiv.org/abs/2510.04618", "type": "research_paper"},  # ACE: Evolving Contexts
    # AI Coding resources - arXiv HTML versions have full content
    {
        "url": "https://arxiv.org/abs/2508.11126",
        "type": "research_paper",
    },  # AI Agentic Programming Survey
    {
        "url": "https://arxiv.org/abs/2511.04427",
        "type": "research_paper",
    },  # AI-Assisted Coding Study
    {"url": "https://arxiv.org/abs/2510.12399", "type": "research_paper"},  # Vibe Coding Survey
    {"url": "https://arxiv.org/abs/2511.18538", "type": "research_paper"},  # AI Coding Paper
    {"url": "https://github.com/ghuntley/how-to-build-a-coding-agent", "type": "tutorial"},
    {"url": "https://www.turingpost.com/p/aisoftwarestack", "type": "article"},
]

# Issue #299-304: Comparison content for tech_comparator quality improvement
# TEMP: Testing threshold fix with single URL
COMPARISON_URLS = [
    # Framework Comparison (known to work)
    {"url": "https://www.datacamp.com/blog/langchain-vs-llamaindex", "type": "article"},
]

# Full list (commented out for testing)
# COMPARISON_URLS = [
#     # Framework Comparisons
#     {"url": "https://www.datacamp.com/blog/langchain-vs-llamaindex", "type": "article"},
#     {"url": "https://medium.com/@bijit211987/qdrant-vs-pinecone-a-comprehensive-comparison-of-vector-databases-b55d0b36b6a5", "type": "article"},
#     {"url": "https://www.merge.dev/blog/rest-vs-graphql", "type": "article"},
#     {"url": "https://aws.amazon.com/compare/the-difference-between-grpc-and-rest/", "type": "article"},
#     # Database Comparisons
#     {"url": "https://www.mongodb.com/resources/compare/mongodb-postgresql", "type": "article"},
#     {"url": "https://aws.amazon.com/elasticache/redis-vs-memcached/", "type": "article"},  # Replaced 404 redis.io URL
#     # ML/AI Framework Comparisons
#     {"url": "https://neptune.ai/blog/mlflow-vs-kubeflow-vs-prefect-differences", "type": "article"},
#     {"url": "https://www.confident-ai.com/blog/the-definitive-guide-to-evaluating-and-comparing-llms", "type": "article"},
#     # Infrastructure Comparisons
#     {"url": "https://www.confluent.io/learn/kafka-vs-rabbitmq/", "type": "article"},
#     {"url": "https://circleci.com/blog/gitlab-ci-cd-vs-github-actions/", "type": "article"},
# ]


async def load_fixture(fixture_id: str) -> dict[str, Any] | None:
    """Load a fixture document by ID."""
    fixtures_path = (
        Path(__file__).parent.parent / "tests/smoke/retrieval/fixtures/documents_expanded.json"
    )

    with fixtures_path.open() as f:
        data = json.load(f)

    for doc in data["documents"]:
        if doc["id"] == fixture_id:
            return doc
    return None


def fixture_to_content(doc: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Convert fixture to raw content and metadata."""
    parts = [f"# {doc['title']}", ""]
    for section in doc.get("sections", []):
        if section.get("title"):
            parts.append(f"## {section['title']}")
            parts.append("")
        parts.append(section.get("content", ""))
        parts.append("")

    raw_content = "\n".join(parts)
    metadata = {
        "title": doc["title"],
        "content_type": doc.get("content_type", "article"),
        "word_count": len(raw_content.split()),
        "source": "fixture",
    }
    return raw_content, metadata


async def cleanup_existing(url: str, actual_url: str | None = None) -> None:
    """Remove existing analysis for a URL using EXACT match (safe).

    Args:
        url: The original URL (e.g., fixture:context-engineering)
        actual_url: The resolved URL (e.g., https://docs.skillforge.dev/context-engineering)
    """
    async with AsyncSessionLocal() as session:
        # Determine the actual URL to clean up
        if actual_url:
            target_url = actual_url
        elif url.startswith("fixture:"):
            fixture_id = url.split(":")[1]
            target_url = f"https://docs.skillforge.dev/{fixture_id}"
        else:
            target_url = url

        # EXACT match only - no patterns!
        result = await session.execute(
            select(Analysis.id, Analysis.title).where(Analysis.url == target_url)
        )
        rows = result.all()

        if not rows:
            logger.debug(f"No existing analysis found for: {target_url[:50]}")
            return

        # Safety: Only clean up entries with exact URL match
        old_ids = [row[0] for row in rows]
        titles = [row[1] for row in rows]

        logger.info(f"Found {len(old_ids)} existing entries to clean up:")
        for title in titles:
            logger.info(f"  - {title[:50] if title else 'Untitled'}")

        for aid in old_ids:
            await session.execute(delete(AnalysisChunk).where(AnalysisChunk.analysis_id == aid))
            await session.execute(delete(Artifact).where(Artifact.analysis_id == aid))
        await session.execute(delete(Analysis).where(Analysis.id.in_(old_ids)))
        await session.commit()
        logger.info(f"Cleaned up {len(old_ids)} existing entries for: {target_url[:50]}")


async def analyze_url(url_info: dict[str, Any], idx: int, total: int) -> dict[str, Any]:
    """Analyze a single URL through the full workflow."""
    url = url_info["url"]
    content_type = url_info["type"]

    start_time = time.time()
    analysis_id = str(uuid4())

    try:
        # Clean up existing
        await cleanup_existing(url)

        # Get content
        if url.startswith("fixture:"):
            fixture_id = url.split(":")[1]
            doc = await load_fixture(fixture_id)
            if not doc:
                raise ValueError(f"Fixture not found: {fixture_id}")

            raw_content, extraction_metadata = fixture_to_content(doc)
            actual_url = f"https://docs.skillforge.dev/{fixture_id}"
            title = doc["title"]
        else:
            logger.info(f"[{idx + 1}/{total}] Extracting content from: {url[:60]}")
            reader = JinaReader()
            extraction_result = await reader.extract_article(url)
            # ExtractionResult is a dict, not a dataclass
            raw_content = extraction_result.get("content", "")
            extraction_metadata = {
                "title": extraction_result.get("title", ""),
                "description": extraction_result.get("description", ""),
                "word_count": len(raw_content.split()) if raw_content else 0,
            }
            actual_url = url
            title = extraction_result.get("title") or "Untitled"

            if not raw_content or len(raw_content) < 100:
                raise ValueError(f"Failed to extract content from {url}")

        # Create analysis record
        async with AsyncSessionLocal() as session:
            analysis = Analysis(
                id=UUID(analysis_id),
                url=actual_url,
                content_type=content_type,
                status="pending",
                title=title,
            )
            session.add(analysis)
            await session.commit()

        logger.info(f"[{idx + 1}/{total}] Running workflow for: {title[:50]}")

        # Run workflow
        initial_state = {
            "analysis_id": analysis_id,
            "url": actual_url,
            "content_type": content_type,
            "skill_level": "intermediate",
            "raw_content": raw_content,
            "extraction_metadata": extraction_metadata,
        }

        workflow = create_analysis_workflow()
        result = await workflow.ainvoke(initial_state, {"configurable": {"thread_id": analysis_id}})

        # Update status
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(Analysis).where(Analysis.id == UUID(analysis_id)).values(status="complete")
            )
            await session.commit()

        elapsed = time.time() - start_time
        logger.info(f"[{idx + 1}/{total}] ✅ Completed in {elapsed:.1f}s: {title[:40]}")

        return {
            "url": url,
            "title": title,
            "status": "success",
            "elapsed": elapsed,
            "artifact_id": result.get("artifact_id"),
        }

    except Exception as e:
        elapsed = time.time() - start_time
        logger.exception(f"[{idx + 1}/{total}] ❌ Failed: {url[:50]}")
        return {
            "url": url,
            "status": "failed",
            "error": str(e),
            "elapsed": elapsed,
        }


async def verify_no_golden_overlap(urls_to_check: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    """Verify URLs don't overlap with golden dataset (safety check)."""
    # Load golden dataset metadata
    metadata_path = Path(__file__).parent.parent / "data/golden_dataset_metadata.json"
    if not metadata_path.exists():
        logger.warning("Golden dataset metadata not found - skipping overlap check")
        return True, []

    with metadata_path.open() as f:
        metadata = json.load(f)

    golden_urls = set(metadata.get("urls", []))
    conflicts = []

    for url_info in urls_to_check:
        url = url_info["url"]
        if url.startswith("fixture:"):
            fixture_id = url.split(":")[1]
            check_url = f"https://docs.skillforge.dev/{fixture_id}"
        else:
            check_url = url

        if check_url in golden_urls:
            conflicts.append(check_url)

    return len(conflicts) == 0, conflicts


async def main() -> int:
    """Main batch analysis function."""
    # Parse args
    dry_run = "--dry-run" in sys.argv
    use_comparison = "--comparison" in sys.argv

    # Select URL list based on CLI args
    urls_to_process = COMPARISON_URLS if use_comparison else URLS_TO_ANALYZE
    url_set_name = "Comparison URLs" if use_comparison else "Default URLs"

    logger.info("=" * 60)
    logger.info("Batch URL Analysis" + (" (DRY RUN)" if dry_run else ""))
    logger.info("=" * 60)
    logger.info(f"URL Set: {url_set_name}")
    logger.info(f"URLs to analyze: {len(urls_to_process)}")

    # Safety check: verify no golden dataset overlap
    safe, conflicts = await verify_no_golden_overlap(urls_to_process)
    if conflicts:
        logger.warning("⚠️  Found URLs that overlap with golden dataset:")
        for c in conflicts:
            logger.warning(f"  - {c}")
        logger.warning("These URLs will be RE-ANALYZED, replacing golden data.")
        if not dry_run:
            logger.info("Proceeding in 5 seconds... (Ctrl+C to cancel)")
            await asyncio.sleep(5)

    if dry_run:
        logger.info("")
        logger.info("DRY RUN - Would process these URLs:")
        for i, url_info in enumerate(urls_to_process):
            logger.info(f"  {i + 1}. [{url_info['type']}] {url_info['url'][:60]}")
        logger.info("")
        logger.info("No changes made. Remove --dry-run to execute.")
        return 0

    results = []
    for i, url_info in enumerate(urls_to_process):
        result = await analyze_url(url_info, i, len(urls_to_process))
        results.append(result)

        # Rate limiting between analyses
        if i < len(urls_to_process) - 1:
            await asyncio.sleep(2)

    # Summary
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")

    logger.info("")
    logger.info("=" * 60)
    logger.info("BATCH ANALYSIS COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Success: {success_count}")
    logger.info(f"  Failed:  {failed_count}")

    if failed_count > 0:
        logger.info("")
        logger.info("Failed URLs:")
        for r in results:
            if r["status"] == "failed":
                logger.info(f"  - {r['url'][:50]}: {r.get('error', 'unknown')[:50]}")

    logger.info("")
    logger.info("Successful artifacts:")
    for r in results:
        if r["status"] == "success":
            logger.info(f"  ✅ {r.get('title', 'Unknown')[:40]} -> {r.get('artifact_id')}")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
