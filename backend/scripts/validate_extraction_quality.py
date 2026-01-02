#!/usr/bin/env python3
"""Validate extraction quality against golden dataset.

Tests current extractors (JinaReader, ArxivPDFExtractor) against golden dataset URLs
to identify quality issues and generate validation report.

Usage:
    poetry run python scripts/validate_extraction_quality.py [--output validation_report.json]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

# Import extractors after path setup
from app.core.logging import get_logger
from app.shared.services.extraction.arxiv_pdf_extractor import (
    ArxivPDFExtractor,
    is_arxiv_url,
)
from app.shared.services.extraction.jina_reader import JinaReader, JinaReaderError

logger = get_logger(__name__)


def extract_title_from_markdown(markdown_content: str | None) -> str | None:
    """Extract title from markdown content (first # heading).

    Args:
        markdown_content: Markdown text to parse

    Returns:
        Title string or None if not found

    """
    if not markdown_content:
        return None

    lines = markdown_content.split("\n")
    for line in lines[:20]:  # Check first 20 lines
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
        if stripped.startswith("#"):
            # Handle ## or ### by removing all # prefixes
            return re.sub(r"^#+\s*", "", stripped).strip()

    return None


def title_similarity(title1: str | None, title2: str | None) -> float:
    """Calculate similarity between two titles (0.0 to 1.0).

    Args:
        title1: First title
        title2: Second title

    Returns:
        Similarity score between 0.0 and 1.0

    """
    if not title1 or not title2:
        return 0.0

    # Normalize titles: lowercase, remove extra whitespace
    norm1 = " ".join(title1.lower().split())
    norm2 = " ".join(title2.lower().split())

    if norm1 == norm2:
        return 1.0

    # Use SequenceMatcher for fuzzy matching
    return SequenceMatcher(None, norm1, norm2).ratio()


def calculate_quality_score(
    extracted_title: str | None,
    expected_title: str | None,
    extracted_word_count: int,
    expected_word_count: int | None = None,
    extraction_failed: bool = False,
) -> dict[str, Any]:
    """Calculate quality score for an extraction.

    Args:
        extracted_title: Title extracted by extractor
        expected_title: Expected title from golden dataset
        extracted_word_count: Word count of extracted content
        expected_word_count: Expected word count (optional)
        extraction_failed: Whether extraction failed

    Returns:
        Dictionary with quality metrics and overall score

    """
    if extraction_failed:
        return {
            "overall_score": 0.0,
            "title_score": 0.0,
            "content_score": 0.0,
            "title_match": False,
            "content_complete": False,
        }

    # Title quality score (0-100)
    title_sim = title_similarity(extracted_title, expected_title)
    title_score = title_sim * 100.0

    # Content completeness score (0-100)
    content_score = 100.0  # Default to 100% if no expected word count
    if expected_word_count and expected_word_count > 0:
        ratio = min(extracted_word_count / expected_word_count, 1.0)
        content_score = ratio * 100.0

    # Overall score: 40% title, 60% content
    overall_score = (title_score * 0.4) + (content_score * 0.6)

    return {
        "overall_score": round(overall_score, 2),
        "title_score": round(title_score, 2),
        "content_score": round(content_score, 2),
        "title_match": title_sim > 0.9,  # >90% similarity
        "content_complete": (
            content_score >= 80.0 if expected_word_count else True
        ),  # >=80% content
    }


async def validate_extraction(
    url: str,
    expected_title: str | None,
    expected_word_count: int | None = None,
) -> dict[str, Any]:
    """Validate extraction for a single URL.

    Args:
        url: URL to extract
        expected_title: Expected title from golden dataset
        expected_word_count: Expected word count (optional)

    Returns:
        Validation result dictionary

    """
    result: dict[str, Any] = {
        "url": url,
        "expected_title": expected_title,
        "expected_word_count": expected_word_count,
        "extraction_failed": False,
        "error": None,
        "extractor_used": None,
        "extracted_title": None,
        "extracted_word_count": 0,
        "quality": {},
    }

    try:
        # Choose extractor based on URL
        if is_arxiv_url(url):
            extractor = ArxivPDFExtractor()
            result["extractor_used"] = "arxiv_pdf"
        else:
            extractor = JinaReader()
            result["extractor_used"] = "jina_reader"

        # Extract content
        extracted = await extractor.extract_article(url)

        result["extracted_title"] = extracted.get("title")
        result["extracted_word_count"] = extracted.get("word_count", 0)

        # Calculate quality score
        result["quality"] = calculate_quality_score(
            extracted_title=result["extracted_title"],
            expected_title=expected_title,
            extracted_word_count=result["extracted_word_count"],
            expected_word_count=expected_word_count,
            extraction_failed=False,
        )

        # Cleanup
        if hasattr(extractor, "close"):
            await extractor.close()

    except JinaReaderError as e:
        result["extraction_failed"] = True
        result["error"] = str(e)
        result["quality"] = calculate_quality_score(
            extracted_title=None,
            expected_title=expected_title,
            extracted_word_count=0,
            expected_word_count=expected_word_count,
            extraction_failed=True,
        )
    except Exception as e:
        result["extraction_failed"] = True
        result["error"] = f"{type(e).__name__}: {e!s}"
        result["quality"] = calculate_quality_score(
            extracted_title=None,
            expected_title=expected_title,
            extracted_word_count=0,
            expected_word_count=expected_word_count,
            extraction_failed=True,
        )

    return result


async def load_golden_dataset(
    backup_path: Path,
) -> list[dict[str, Any]]:
    """Load golden dataset from backup JSON.

    Args:
        backup_path: Path to golden_dataset_backup.json

    Returns:
        List of URL validation targets with expected titles

    """
    with backup_path.open() as f:
        backup_data = json.load(f)

    analyses = backup_data.get("data", {}).get("analyses", [])
    artifacts = backup_data.get("data", {}).get("artifacts", [])

    # Create mapping: analysis_id -> artifact
    artifact_map = {art["analysis_id"]: art for art in artifacts}

    # Extract validation targets
    targets = []
    for analysis in analyses:
        analysis_id = analysis.get("id")
        url = analysis.get("url")
        stored_title = analysis.get("title")

        if not url:
            continue

        # Get expected title from artifact markdown
        artifact = artifact_map.get(analysis_id)
        expected_title = None
        if artifact:
            markdown = artifact.get("markdown_content")
            expected_title = extract_title_from_markdown(markdown)

        # Fallback to stored title if no markdown title
        if not expected_title and stored_title:
            expected_title = stored_title

        # Get expected word count from artifact metadata (if available)
        expected_word_count = None
        if artifact:
            metadata = artifact.get("artifact_metadata", {})
            if isinstance(metadata, dict):
                expected_word_count = metadata.get("word_count")

        targets.append(
            {
                "analysis_id": analysis_id,
                "url": url,
                "content_type": analysis.get("content_type", "article"),
                "expected_title": expected_title,
                "expected_word_count": expected_word_count,
                "stored_title": stored_title,
            }
        )

    return targets


async def main() -> int:
    """Main validation function."""
    parser = argparse.ArgumentParser(
        description="Validate extraction quality against golden dataset"
    )
    parser.add_argument(
        "--golden-dataset",
        type=Path,
        default=Path(__file__).parent.parent / "data" / "golden_dataset_backup.json",
        help="Path to golden dataset backup JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent.parent / "data" / "validation_report.json",
        help="Path to output validation report",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of URLs to validate (for testing)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed progress",
    )

    args = parser.parse_args()

    if not args.golden_dataset.exists():
        logger.error(f"Golden dataset not found: {args.golden_dataset}")
        return 1

    logger.info(f"Loading golden dataset from: {args.golden_dataset}")

    # Load validation targets
    targets = await load_golden_dataset(args.golden_dataset)

    if args.limit:
        targets = targets[: args.limit]
        logger.info(f"Limited to first {args.limit} URLs for testing")

    logger.info(f"Validating {len(targets)} URLs")

    # Validate each URL
    results = []
    for i, target in enumerate(targets, 1):
        if args.verbose:
            logger.info(
                f"[{i}/{len(targets)}] Validating: {target['url']}",
            )

        result = await validate_extraction(
            url=target["url"],
            expected_title=target["expected_title"],
            expected_word_count=target.get("expected_word_count"),
        )

        # Add metadata
        result["analysis_id"] = target["analysis_id"]
        result["content_type"] = target["content_type"]
        result["stored_title"] = target.get("stored_title")

        results.append(result)

        # Progress update every 10 URLs
        if i % 10 == 0 and not args.verbose:
            logger.info(f"Progress: {i}/{len(targets)} URLs validated")

    # Calculate summary statistics
    total = len(results)
    passed = sum(1 for r in results if r["quality"]["overall_score"] >= 80.0)
    failed = sum(1 for r in results if r["extraction_failed"])
    title_accurate = sum(1 for r in results if r["quality"]["title_match"])
    content_complete = sum(1 for r in results if r["quality"]["content_complete"])

    avg_score = sum(r["quality"]["overall_score"] for r in results) / total if total > 0 else 0.0
    avg_title_score = (
        sum(r["quality"]["title_score"] for r in results) / total if total > 0 else 0.0
    )
    avg_content_score = (
        sum(r["quality"]["content_score"] for r in results) / total if total > 0 else 0.0
    )

    # Group by extractor
    extractor_stats: dict[str, dict[str, Any]] = {}
    for result in results:
        extractor = result["extractor_used"] or "unknown"
        if extractor not in extractor_stats:
            extractor_stats[extractor] = {
                "count": 0,
                "passed": 0,
                "failed": 0,
                "avg_score": 0.0,
            }
        stats = extractor_stats[extractor]
        stats["count"] += 1
        if result["extraction_failed"]:
            stats["failed"] += 1
        elif result["quality"]["overall_score"] >= 80.0:
            stats["passed"] += 1
        stats["avg_score"] += result["quality"]["overall_score"]

    for stats in extractor_stats.values():
        if stats["count"] > 0:
            stats["avg_score"] = round(stats["avg_score"] / stats["count"], 2)

    # Create report
    report = {
        "version": "1.0",
        "summary": {
            "total_urls": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round((passed / total * 100) if total > 0 else 0.0, 2),
            "failure_rate": round((failed / total * 100) if total > 0 else 0.0, 2),
            "title_accuracy": round((title_accurate / total * 100) if total > 0 else 0.0, 2),
            "content_completeness": round(
                (content_complete / total * 100) if total > 0 else 0.0, 2
            ),
            "average_score": round(avg_score, 2),
            "average_title_score": round(avg_title_score, 2),
            "average_content_score": round(avg_content_score, 2),
        },
        "extractor_stats": extractor_stats,
        "results": results,
    }

    # Write report
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Validation report written to: {args.output}")

    # Print summary
    print("\n" + "=" * 60)
    print("EXTRACTION VALIDATION REPORT")
    print("=" * 60)
    print(f"   Total URLs:        {total}")
    print(f"   Passed (>=80%):    {passed} ({passed / total * 100:.1f}%)")
    print(f"   Failed:            {failed} ({failed / total * 100:.1f}%)")
    print(f"   Title Accuracy:    {title_accurate} ({title_accurate / total * 100:.1f}%)")
    print(f"   Content Complete:  {content_complete} ({content_complete / total * 100:.1f}%)")
    print(f"   Average Score:     {avg_score:.1f}/100")
    print(f"   Avg Title Score:   {avg_title_score:.1f}/100")
    print(f"   Avg Content Score: {avg_content_score:.1f}/100")
    print("\nExtractor Stats:")
    for extractor, stats in extractor_stats.items():
        print(f"   {extractor}:")
        print(f"      Count:  {stats['count']}")
        print(f"      Passed: {stats['passed']} ({stats['passed'] / stats['count'] * 100:.1f}%)")
        print(f"      Failed: {stats['failed']} ({stats['failed'] / stats['count'] * 100:.1f}%)")
        print(f"      Avg Score: {stats['avg_score']:.1f}/100")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
