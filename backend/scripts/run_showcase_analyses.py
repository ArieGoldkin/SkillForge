#!/usr/bin/env python
"""Run showcase analyses through the full SkillForge pipeline.

This script selects high-quality URLs from the golden dataset and runs them
through the complete analysis workflow for demonstration purposes.

Usage:
    cd backend
    poetry run python scripts/run_showcase_analyses.py --count 5
    poetry run python scripts/run_showcase_analyses.py --count 10 --clear-first
    poetry run python scripts/run_showcase_analyses.py --list  # List available URLs
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

# Showcase URLs - curated selection for best demo impact
# These are chosen for:
# - Diverse content types (articles, tutorials, research)
# - Good extraction quality
# - Interesting technical topics
SHOWCASE_URLS = [
    # AI/ML Topics
    "https://www.anthropic.com/engineering/building-effective-agents",
    "https://python.langchain.com/docs/how_to/lcel_cheatsheet/",
    "https://arxiv.org/abs/2308.11432",  # LLM Agent Architectures
    # System Design
    "https://tanstack.com/query/latest/docs/framework/react/overview",
    "https://python.org/3/tutorial/classes.html",
    # Security
    "https://owasp.org/API-Security/editions/2023/en/0x11-t10/",
    # Database/Performance
    "https://www.pgbouncer.org/",
    "https://www.credativ.de/en/blog/postgresql-en/postgresql-18-asynchronous-disk-i-o-deep-dive-into-implementation/",
    # Best Practices
    "https://docs.langchain.com/oss/python/integrations/splitters/index",
    "https://k8spatterns.io/",
]

# Backend API configuration
API_BASE_URL = "http://localhost:8500/api/v1"


async def clear_existing_analyses(urls: list[str]) -> int:
    """Delete existing analyses for the given URLs.

    Returns count of deleted analyses.
    """
    # We'll use direct database access for cleanup
    import os
    import subprocess

    # Build SQL to delete analyses with matching URLs
    url_list = ", ".join(f"'{url}'" for url in urls)

    # First get count
    count_sql = f"SELECT COUNT(*) FROM analyses WHERE url IN ({url_list});"
    delete_sql = f"""
        DELETE FROM analysis_progress WHERE analysis_id IN
            (SELECT id FROM analyses WHERE url IN ({url_list}));
        DELETE FROM agent_findings WHERE analysis_id IN
            (SELECT id FROM analyses WHERE url IN ({url_list}));
        DELETE FROM artifacts WHERE analysis_id IN
            (SELECT id FROM analyses WHERE url IN ({url_list}));
        DELETE FROM analyses WHERE url IN ({url_list});
    """

    try:
        # Get count first
        result = subprocess.run(
            [
                "docker",
                "exec",
                "skillforge-postgres-dev",
                "psql",
                "-U",
                "dev",
                "-d",
                "skillforge",
                "-t",
                "-c",
                count_sql,
            ],
            capture_output=True,
            text=True,
        )
        count = int(result.stdout.strip()) if result.returncode == 0 else 0

        if count > 0:
            # Delete
            subprocess.run(
                [
                    "docker",
                    "exec",
                    "skillforge-postgres-dev",
                    "psql",
                    "-U",
                    "dev",
                    "-d",
                    "skillforge",
                    "-c",
                    delete_sql,
                ],
                capture_output=True,
                text=True,
            )
            print(f"✓ Cleared {count} existing analyses")
        return count
    except Exception as e:
        print(f"⚠️  Could not clear analyses: {e}")
        return 0


async def trigger_analysis(client: httpx.AsyncClient, url: str) -> dict:
    """Trigger analysis for a single URL via the API.

    Returns response data or error dict.
    """
    try:
        response = await client.post(f"{API_BASE_URL}/analyze", json={"url": url}, timeout=30.0)

        if response.status_code in (200, 201):
            data = response.json()
            return {
                "success": True,
                "url": url,
                "analysis_id": data.get("analysis_id"),
                "existing": data.get("existing", False),
                "sse_endpoint": data.get("sse_endpoint"),
            }
        else:
            return {
                "success": False,
                "url": url,
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
            }
    except Exception as e:
        return {
            "success": False,
            "url": url,
            "error": str(e),
        }


async def wait_for_analysis(
    client: httpx.AsyncClient, analysis_id: str, timeout: int = 300
) -> dict:
    """Wait for an analysis to complete by polling the status endpoint.

    Args:
        client: HTTP client
        analysis_id: UUID of the analysis
        timeout: Max seconds to wait

    Returns:
        Final status dict
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = await client.get(f"{API_BASE_URL}/analyze/{analysis_id}")
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "unknown")

                if status in ("complete", "completed"):
                    return {"status": "complete", "artifact_id": data.get("artifact_id")}
                elif status == "failed":
                    return {"status": "failed", "error": data.get("error")}
                # Still running, wait and poll again
            await asyncio.sleep(5)
        except Exception as e:
            print(f"  ⚠️  Poll error: {e}")
            await asyncio.sleep(5)

    return {"status": "timeout", "error": f"Analysis did not complete within {timeout}s"}


async def run_showcase_analyses(urls: list[str], wait: bool = True) -> list[dict]:
    """Run analyses for multiple URLs.

    Args:
        urls: List of URLs to analyze
        wait: If True, wait for each analysis to complete

    Returns:
        List of result dicts
    """
    results = []

    async with httpx.AsyncClient() as client:
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Analyzing: {url[:60]}...")

            result = await trigger_analysis(client, url)

            if result["success"]:
                analysis_id = result["analysis_id"]
                if result.get("existing"):
                    print(f"  → Already exists: {analysis_id}")
                else:
                    print(f"  → Started: {analysis_id}")

                if wait and not result.get("existing"):
                    print("  → Waiting for completion...")
                    status = await wait_for_analysis(client, analysis_id)
                    result["final_status"] = status

                    if status["status"] == "complete":
                        print(f"  ✓ Complete! Artifact: {status.get('artifact_id', 'N/A')}")
                    else:
                        print(f"  ✗ {status['status']}: {status.get('error', 'Unknown error')}")
            else:
                print(f"  ✗ Failed: {result['error']}")

            results.append(result)

    return results


def list_golden_urls():
    """List all URLs from the golden dataset."""
    golden_file = Path(__file__).parent.parent / "data" / "golden_dataset_backup.json"

    if not golden_file.exists():
        print("Golden dataset not found!")
        return

    with open(golden_file) as f:
        data = json.load(f)

    analyses = data.get("data", {}).get("analyses", [])
    print(f"\n📚 Golden Dataset URLs ({len(analyses)} total):\n")

    for i, analysis in enumerate(analyses, 1):
        url = analysis.get("url", "N/A")
        title = analysis.get("title", "Untitled")[:50]
        print(f"{i:3}. {title}")
        print(f"     {url}\n")


async def main():
    parser = argparse.ArgumentParser(description="Run showcase analyses through the pipeline")
    parser.add_argument(
        "--count", type=int, default=5, help="Number of analyses to run (default: 5)"
    )
    parser.add_argument("--clear-first", action="store_true", help="Clear existing analyses first")
    parser.add_argument("--no-wait", action="store_true", help="Don't wait for completion")
    parser.add_argument("--list", action="store_true", help="List all golden dataset URLs")
    parser.add_argument("--all", action="store_true", help="Run all showcase URLs")

    args = parser.parse_args()

    if args.list:
        list_golden_urls()
        return

    # Select URLs
    urls = SHOWCASE_URLS if args.all else SHOWCASE_URLS[: args.count]

    print("=" * 60)
    print("🚀 SkillForge Showcase Analysis Runner")
    print("=" * 60)
    print(f"\n📌 Running {len(urls)} analyses through the full pipeline\n")

    # Clear first if requested
    if args.clear_first:
        await clear_existing_analyses(urls)

    # Run analyses
    results = await run_showcase_analyses(urls, wait=not args.no_wait)

    # Summary
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)

    successful = sum(1 for r in results if r.get("success"))
    completed = sum(1 for r in results if r.get("final_status", {}).get("status") == "complete")
    existing = sum(1 for r in results if r.get("existing"))

    print(f"  Total:     {len(results)}")
    print(f"  Started:   {successful}")
    print(f"  Completed: {completed}")
    print(f"  Existing:  {existing}")

    if not args.no_wait:
        print("\n✅ Showcase data ready for demonstration!")
        print(f"   View at: http://localhost:5173/library")


if __name__ == "__main__":
    asyncio.run(main())
