#!/usr/bin/env python
"""Sync golden dataset backup to Langfuse.

This script syncs the golden_dataset_backup.json to a Langfuse dataset
for evaluation tracking and experiment management.

Issue #380: Part of Langfuse Phase 2 integration.

Usage:
    # Sync all analyses to Langfuse
    poetry run python scripts/sync_golden_dataset_to_langfuse.py

    # Dry run (show what would be synced)
    poetry run python scripts/sync_golden_dataset_to_langfuse.py --dry-run

    # Limit to N analyses for testing
    poetry run python scripts/sync_golden_dataset_to_langfuse.py --max-items 10

Environment variables required:
    LANGFUSE_ENABLED=true
    LANGFUSE_PUBLIC_KEY=<your-key>
    LANGFUSE_SECRET_KEY=<your-key>
    LANGFUSE_HOST=<your-host>  # Optional, defaults to http://localhost:3000
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables before other imports
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from app.core.langfuse_config import get_langfuse_client  # noqa: E402
from app.core.logging import get_logger  # noqa: E402

logger = get_logger(__name__)

# Dataset configuration
# Issue #410: Semantic versioning for dataset changes
DATASET_NAME = "skillforge_golden_analyses_v1_prod"
DATASET_VERSION = "2.1.0"  # Major.Minor.Patch - increment on schema/content changes
DATASET_DESCRIPTION = """Golden dataset of 98 completed analyses from SkillForge.

Contains real-world technical content analyses (articles, tutorials, research papers)
with canonical URLs for reproducibility. Topics include RAG, LangGraph, API design,
prompt engineering, and ML infrastructure.

Source: golden_dataset_backup.json (v2.0 format)

Version History:
- 2.1.0 (Dec 2025): Added Langfuse sync with semantic versioning
- 2.0.0 (Dec 2025): Initial golden dataset with 98 analyses
"""

# Path to golden dataset backup
GOLDEN_DATASET_PATH = Path(__file__).parent.parent / "data" / "golden_dataset_backup.json"


def check_langfuse_enabled() -> bool:
    """Check if Langfuse is enabled and configured.

    Returns:
        True if Langfuse is enabled and configured, False otherwise.

    """
    langfuse_enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
    if not langfuse_enabled:
        logger.error(
            "langfuse_disabled",
            message="LANGFUSE_ENABLED is not set to 'true'. Set LANGFUSE_ENABLED=true in your environment.",
        )
        return False

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")

    if not public_key or not secret_key:
        logger.error(
            "langfuse_credentials_missing",
            message="LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY not set",
            public_key_set=bool(public_key),
            secret_key_set=bool(secret_key),
        )
        return False

    return True


def compute_item_hash(input_data: dict[str, Any], expected_output: dict[str, Any]) -> str:
    """Compute a unique hash for a dataset item for deduplication.

    Args:
        input_data: Item input data
        expected_output: Item expected output

    Returns:
        SHA256 hash string (first 16 chars)

    """
    content = json.dumps({"input": input_data, "output": expected_output}, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def load_golden_dataset() -> dict[str, Any]:
    """Load the golden dataset backup from JSON.

    Returns:
        Full dataset structure including version, counts, and data

    Raises:
        FileNotFoundError: If backup file doesn't exist
        json.JSONDecodeError: If file is not valid JSON

    """
    if not GOLDEN_DATASET_PATH.exists():
        msg = f"Golden dataset backup not found at {GOLDEN_DATASET_PATH}"
        raise FileNotFoundError(msg)

    with GOLDEN_DATASET_PATH.open() as f:
        return json.load(f)


def format_analysis_item(
    analysis: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Format an analysis for Langfuse dataset item.

    Args:
        analysis: Analysis record from golden dataset

    Returns:
        Tuple of (input, expected_output, metadata)

    """
    input_data = {
        "url": analysis.get("url", ""),
        "content_type": analysis.get("content_type", "article"),
        "title": analysis.get("title", ""),
    }

    # For golden dataset, all analyses are completed
    expected_output = {
        "status": "completed",
    }

    # Issue #410: Include dataset version in item metadata for traceability
    metadata = {
        "analysis_id": analysis.get("id", ""),
        "created_at": analysis.get("created_at", ""),
        "source": "golden_dataset_backup",
        "source_format_version": "v2.0",
        "dataset_version": DATASET_VERSION,
    }

    return input_data, expected_output, metadata


def sync_to_langfuse(
    dry_run: bool = False,
    max_items: int | None = None,
) -> dict[str, Any]:
    """Sync golden dataset analyses to Langfuse.

    Args:
        dry_run: If True, just show what would be synced
        max_items: Maximum number of items to sync (None = all)

    Returns:
        Dict with sync results

    """
    # Load golden dataset
    print(f"\nLoading golden dataset from {GOLDEN_DATASET_PATH}")
    dataset = load_golden_dataset()

    version = dataset.get("version", "unknown")
    counts = dataset.get("counts", {})
    analyses = dataset.get("data", {}).get("analyses", [])

    print(f"  Version: {version}")
    print(f"  Total analyses: {counts.get('analyses', len(analyses))}")
    print(f"  Total artifacts: {counts.get('artifacts', 0)}")

    if max_items:
        analyses = analyses[:max_items]
        print(f"  Limiting to: {max_items} items")

    if dry_run:
        print(f"\n[DRY RUN] Would sync {len(analyses)} analyses to Langfuse")
        print(f"  Dataset name: {DATASET_NAME}")
        print("\n  Sample items:")
        for i, analysis in enumerate(analyses[:3]):
            print(f"    {i + 1}. {analysis.get('title', 'N/A')[:50]}...")
            print(f"       URL: {analysis.get('url', 'N/A')[:60]}...")
        return {
            "status": "dry_run",
            "total": len(analyses),
        }

    # Get Langfuse client
    if not check_langfuse_enabled():
        return {"status": "error", "message": "Langfuse not enabled or configured"}

    langfuse = get_langfuse_client()
    if not langfuse:
        return {"status": "error", "message": "Langfuse client not initialized"}

    # Create or get existing dataset
    # Issue #410: Include semantic version in dataset metadata
    print(f"\nCreating/updating Langfuse dataset: {DATASET_NAME} (v{DATASET_VERSION})")
    try:
        langfuse.create_dataset(
            name=DATASET_NAME,
            description=DATASET_DESCRIPTION,
            metadata={
                "dataset_version": DATASET_VERSION,
                "source_version": version,
                "synced_at": datetime.now(UTC).isoformat(),
                "analysis_count": len(analyses),
                "schema": "golden_analysis_v2",
            },
        )
        print(f"  Dataset created/found: {DATASET_NAME}")
    except Exception as e:
        logger.warning("dataset_creation_warning", error=str(e))
        print(f"  Dataset may already exist: {e}")

    # Track sync results
    uploaded = 0
    skipped = 0
    failed = 0
    seen_hashes: set[str] = set()

    print(f"\nSyncing {len(analyses)} analyses...")

    for i, analysis in enumerate(analyses):
        analysis_id = analysis.get("id", f"unknown_{i}")
        title = analysis.get("title", "Untitled")[:40]

        try:
            # Format item
            input_data, expected_output, metadata = format_analysis_item(analysis)

            # Check for duplicates (idempotent uploads)
            item_hash = compute_item_hash(input_data, expected_output)
            if item_hash in seen_hashes:
                skipped += 1
                continue
            seen_hashes.add(item_hash)

            # Create dataset item
            langfuse.create_dataset_item(
                dataset_name=DATASET_NAME,
                input=input_data,
                expected_output=expected_output,
                metadata=metadata,
            )

            uploaded += 1
            if (i + 1) % 10 == 0 or i == len(analyses) - 1:
                print(
                    f"  Progress: {i + 1}/{len(analyses)} ({uploaded} uploaded, {skipped} skipped)"
                )

        except Exception as e:
            failed += 1
            logger.warning(
                "analysis_sync_failed",
                analysis_id=analysis_id,
                error=str(e),
            )
            print(f"  FAILED: {title}... - {e}")

    # Flush to ensure all items are sent
    langfuse.flush()

    # Summary
    print(f"\n{'=' * 50}")
    print("SYNC COMPLETE")
    print("=" * 50)
    print(f"  Uploaded: {uploaded}")
    print(f"  Skipped:  {skipped} (duplicates)")
    print(f"  Failed:   {failed}")
    print(f"  Total:    {len(analyses)}")

    return {
        "status": "success",
        "dataset_name": DATASET_NAME,
        "uploaded": uploaded,
        "skipped": skipped,
        "failed": failed,
        "total": len(analyses),
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sync golden dataset backup to Langfuse",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without uploading",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        help="Maximum number of items to sync",
    )

    args = parser.parse_args()

    result = sync_to_langfuse(
        dry_run=args.dry_run,
        max_items=args.max_items,
    )

    print(f"\nResult: {result['status']}")
    if result["status"] == "error":
        sys.exit(1)


if __name__ == "__main__":
    main()
