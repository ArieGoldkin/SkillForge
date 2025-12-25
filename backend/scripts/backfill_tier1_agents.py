#!/usr/bin/env python3
"""Backfill Tier 1 agents on old completed analyses.

This script identifies analyses that were completed before the Tier 1 agent fix
(December 25, 2025) and are missing findings from universal agents (key_insights,
pros_cons, audience_fit, actionable). It then reruns these analyses to backfill
the missing agent findings.

Usage:
    # Preview eligible analyses without executing
    poetry run python scripts/backfill_tier1_agents.py --dry-run

    # Execute reruns with default rate limiting (2/minute)
    poetry run python scripts/backfill_tier1_agents.py

    # Process only first 10 analyses (for testing)
    poetry run python scripts/backfill_tier1_agents.py --limit 10

    # Custom cutoff date
    poetry run python scripts/backfill_tier1_agents.py --before "2025-12-24"

Rate Limiting:
    - Default: 30 seconds between reruns (2/minute)
    - Configurable with --rate-limit-seconds
    - Prevents API/workflow overload

Safety:
    - Only processes analyses with status='complete'
    - Checks for missing Tier 1 agent findings
    - Uses existing /analyze/{id}/rerun API endpoint
    - Displays summary and requires confirmation before proceeding
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

from app.core.config import settings  # noqa: E402
from app.core.logging import get_logger  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402

logger = get_logger(__name__)

# Tier 1 (Universal) agents that should be present in all analyses
TIER_1_AGENTS = ["key_insights", "pros_cons", "audience_fit", "actionable"]

# Default cutoff date (before Tier 1 fix was deployed)
DEFAULT_CUTOFF_DATE = "2025-12-25"

# Rate limiting (2 requests per minute = 30 seconds between requests)
DEFAULT_RATE_LIMIT_SECONDS = 30


async def find_eligible_analyses(
    cutoff_date: str,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Find analyses eligible for Tier 1 backfill.

    Criteria:
    - status = 'complete'
    - created_at < cutoff_date
    - Missing findings from at least one Tier 1 agent

    Args:
        cutoff_date: ISO date string (e.g., "2025-12-25")
        limit: Optional limit on number of analyses to return

    Returns:
        List of dicts with analysis_id, url, title, created_at, missing_agents

    """
    # Convert cutoff_date string to datetime for database query
    from datetime import UTC

    cutoff_dt = datetime.fromisoformat(cutoff_date).replace(tzinfo=UTC)

    async with AsyncSessionLocal() as session:
        # Find all complete analyses before cutoff date using raw SQL
        query = text("""
            SELECT id, url, title, created_at
            FROM analyses
            WHERE status = 'complete'
              AND created_at < :cutoff_date
            ORDER BY created_at ASC
        """)

        result = await session.execute(query, {"cutoff_date": cutoff_dt})
        analyses = result.fetchall()

        eligible = []
        for analysis in analyses:
            analysis_id = analysis.id

            # Get existing agent findings for this analysis
            findings_query = text("""
                SELECT agent_type
                FROM agent_findings
                WHERE analysis_id = :analysis_id
                  AND status = 'success'
            """)

            findings_result = await session.execute(findings_query, {"analysis_id": analysis_id})
            existing_agents = {row.agent_type for row in findings_result.fetchall()}

            # Check which Tier 1 agents are missing
            missing_agents = [agent for agent in TIER_1_AGENTS if agent not in existing_agents]

            # Only include if missing at least one Tier 1 agent
            if missing_agents:
                eligible.append(
                    {
                        "analysis_id": str(analysis_id),
                        "url": str(analysis.url),
                        "title": str(analysis.title) if analysis.title else "Untitled",
                        "created_at": analysis.created_at.isoformat(),
                        "missing_agents": missing_agents,
                        "missing_count": len(missing_agents),
                    }
                )

            # Apply limit if specified
            if limit and len(eligible) >= limit:
                break

        return eligible


async def rerun_analysis_via_api(
    analysis_id: str,
    base_url: str,
) -> dict[str, Any]:
    """Trigger analysis rerun via API endpoint.

    Args:
        analysis_id: UUID of analysis to rerun
        base_url: Base URL for API (e.g., "http://localhost:8500")

    Returns:
        Dict with status, response_data, and error (if any)

    """
    url = f"{base_url}{settings.API_V1_PREFIX}/analyze/{analysis_id}/rerun"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url)

            if response.status_code in {200, 201}:
                return {
                    "status": "success",
                    "response_data": response.json(),
                    "error": None,
                }
            return {
                "status": "failed",
                "response_data": None,
                "error": f"HTTP {response.status_code}: {response.text}",
            }
    except Exception as e:
        return {
            "status": "failed",
            "response_data": None,
            "error": str(e),
        }


def print_summary(
    eligible: list[dict[str, Any]],
    dry_run: bool,
    cutoff_date: str,
) -> None:
    """Print summary of eligible analyses.

    Args:
        eligible: List of eligible analysis dicts
        dry_run: Whether this is a dry run
        cutoff_date: Cutoff date used for filtering

    """
    print("\n" + "=" * 70)
    print("TIER 1 AGENT BACKFILL" + (" (DRY RUN)" if dry_run else ""))
    print("=" * 70)
    print(f"Cutoff Date: {cutoff_date}")
    print(f"Eligible Analyses: {len(eligible)}")
    print()

    if eligible:
        print("Missing Agent Summary:")
        # Count analyses by number of missing agents
        missing_counts = {}
        for analysis in eligible:
            count = analysis["missing_count"]
            missing_counts[count] = missing_counts.get(count, 0) + 1

        for count in sorted(missing_counts.keys(), reverse=True):
            print(f"  {missing_counts[count]:3d} analyses missing {count} Tier 1 agent(s)")

        print()
        print("Sample Analyses (first 10):")
        for i, analysis in enumerate(eligible[:10]):
            title = analysis["title"][:50]
            missing = ", ".join(analysis["missing_agents"])
            print(f"  {i + 1:2d}. {title}")
            print(f"      Missing: {missing}")
            print(f"      Created: {analysis['created_at'][:10]}")

        if len(eligible) > 10:
            print(f"  ... and {len(eligible) - 10} more")

    print("=" * 70)


def confirm_execution(count: int) -> bool:
    """Prompt user to confirm execution.

    Args:
        count: Number of analyses to rerun

    Returns:
        True if user confirms, False otherwise

    """
    print()
    print(f"This will rerun {count} analyses via the /analyze/{{id}}/rerun API endpoint.")
    print("Each rerun will:")
    print("  - Preserve original extraction (raw_content, embeddings)")
    print("  - Re-execute analysis workflow with updated agents")
    print("  - Archive current artifact and generate new one")
    print()

    response = input("Continue? [y/N]: ").strip().lower()
    return response in {"y", "yes"}


async def execute_reruns(
    eligible: list[dict[str, Any]],
    base_url: str,
    rate_limit_seconds: int,
) -> dict[str, Any]:
    """Execute reruns for all eligible analyses.

    Args:
        eligible: List of eligible analysis dicts
        base_url: Base URL for API
        rate_limit_seconds: Seconds to wait between reruns

    Returns:
        Dict with success_count, failed_count, errors list

    """
    success_count = 0
    failed_count = 0
    errors: list[dict[str, Any]] = []

    total = len(eligible)

    for i, analysis in enumerate(eligible):
        analysis_id = analysis["analysis_id"]
        title = analysis["title"][:50]

        print(f"\n[{i + 1}/{total}] Rerunning: {title}")
        print(f"  Analysis ID: {analysis_id}")
        print(f"  Missing agents: {', '.join(analysis['missing_agents'])}")

        start_time = time.time()
        result = await rerun_analysis_via_api(analysis_id, base_url)
        elapsed = time.time() - start_time

        if result["status"] == "success":
            success_count += 1
            print(f"  ✅ Queued successfully ({elapsed:.1f}s)")
        else:
            failed_count += 1
            error_msg = result["error"]
            print(f"  ❌ Failed: {error_msg}")
            errors.append(
                {
                    "analysis_id": analysis_id,
                    "title": title,
                    "error": error_msg,
                }
            )

        # Rate limiting (skip for last item)
        if i < total - 1:
            print(f"  Waiting {rate_limit_seconds}s (rate limit)...")
            await asyncio.sleep(rate_limit_seconds)

    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "errors": errors,
    }


def print_final_summary(results: dict[str, Any], total_elapsed: float) -> None:
    """Print final execution summary.

    Args:
        results: Dict with success_count, failed_count, errors
        total_elapsed: Total execution time in seconds

    """
    print("\n" + "=" * 70)
    print("BACKFILL COMPLETE")
    print("=" * 70)
    print(f"  Success: {results['success_count']}")
    print(f"  Failed:  {results['failed_count']}")
    print(f"  Time:    {total_elapsed:.1f}s")

    if results["errors"]:
        print()
        print("Failed Reruns:")
        for error in results["errors"]:
            print(f"  - {error['title'][:50]}")
            print(f"    ID: {error['analysis_id']}")
            print(f"    Error: {error['error'][:80]}")

    print("=" * 70)


async def main() -> int:
    """Main backfill execution function."""
    parser = argparse.ArgumentParser(description="Backfill Tier 1 agents on old completed analyses")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview eligible analyses without executing reruns",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of analyses to process (for testing)",
    )
    parser.add_argument(
        "--before",
        type=str,
        default=DEFAULT_CUTOFF_DATE,
        help=f"Only process analyses created before this date (default: {DEFAULT_CUTOFF_DATE})",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:8500",
        help="Base URL for API (default: http://localhost:8500)",
    )
    parser.add_argument(
        "--rate-limit-seconds",
        type=int,
        default=DEFAULT_RATE_LIMIT_SECONDS,
        help=f"Seconds to wait between reruns (default: {DEFAULT_RATE_LIMIT_SECONDS})",
    )

    args = parser.parse_args()

    # Validate cutoff date format
    try:
        datetime.fromisoformat(args.before)
    except ValueError:
        logger.exception(f"Invalid date format: {args.before}. Use ISO format (YYYY-MM-DD)")
        return 1

    # Find eligible analyses
    logger.info(f"Finding analyses created before {args.before}...")
    eligible = await find_eligible_analyses(
        cutoff_date=args.before,
        limit=args.limit,
    )

    # Print summary
    print_summary(eligible, args.dry_run, args.before)

    if not eligible:
        print("\n✅ No analyses need backfilling. All complete analyses have Tier 1 agents!")
        return 0

    if args.dry_run:
        print("\n✅ Dry run complete. Remove --dry-run to execute reruns.")
        return 0

    # Confirm execution
    if not confirm_execution(len(eligible)):
        print("\n❌ Cancelled by user.")
        return 1

    # Execute reruns
    print("\n" + "=" * 70)
    print("EXECUTING RERUNS")
    print("=" * 70)

    start_time = time.time()
    results = await execute_reruns(eligible, args.base_url, args.rate_limit_seconds)
    total_elapsed = time.time() - start_time

    # Print final summary
    print_final_summary(results, total_elapsed)

    # Exit with error code if any failed
    return 1 if results["failed_count"] > 0 else 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
