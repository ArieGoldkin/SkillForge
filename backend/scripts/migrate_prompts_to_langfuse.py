"""Migrate hardcoded prompts to Langfuse Prompt Management.

Issue #379: Upload all hardcoded prompts to Langfuse with "production" label.

Usage:
    # Dry run (preview what will be uploaded)
    poetry run python scripts/migrate_prompts_to_langfuse.py

    # Execute upload
    poetry run python scripts/migrate_prompts_to_langfuse.py --execute

Requirements:
    - LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in environment
    - Langfuse instance accessible at LANGFUSE_HOST
"""

import argparse
import sys
from typing import Any

from app.core.langfuse_config import get_langfuse_client
from app.core.logging import get_logger
from app.shared.services.prompts.prompt_manager import HARDCODED_PROMPTS

logger = get_logger(__name__)


def create_or_update_prompt(
    client: Any,
    name: str,
    prompt: str,
    label: str = "production",
    dry_run: bool = True,
) -> dict[str, Any]:
    """Create or update a prompt in Langfuse.

    Args:
        client: Langfuse client instance
        name: Prompt name (e.g., "analysis-supervisor-routing")
        prompt: Prompt content
        label: Label to apply (default: "production")
        dry_run: If True, only preview (don't actually create)

    Returns:
        Dictionary with result information

    """
    if dry_run:
        logger.info(
            "prompt_migration_dry_run",
            name=name,
            label=label,
            length=len(prompt),
        )
        return {
            "name": name,
            "label": label,
            "status": "dry_run",
            "length": len(prompt),
        }

    try:
        # Create prompt in Langfuse
        # Note: Langfuse client method signature may vary - check docs
        result = client.create_prompt(
            name=name,
            prompt=prompt,
            labels=[label],
            type="text",
        )

        logger.info(
            "prompt_migration_success",
            name=name,
            label=label,
            version=getattr(result, "version", "unknown"),
        )

        return {
            "name": name,
            "label": label,
            "status": "created",
            "version": getattr(result, "version", "unknown"),
        }

    except Exception as e:
        logger.error(
            "prompt_migration_failed",
            name=name,
            label=label,
            error=str(e),
            exc_info=True,
        )

        return {
            "name": name,
            "label": label,
            "status": "failed",
            "error": str(e),
        }


def migrate_all_prompts(dry_run: bool = True, label: str = "production") -> dict[str, Any]:
    """Migrate all hardcoded prompts to Langfuse.

    Args:
        dry_run: If True, only preview (don't actually create)
        label: Label to apply to all prompts

    Returns:
        Dictionary with migration results

    """
    # Get Langfuse client
    client = get_langfuse_client()

    if not client:
        logger.error(
            "langfuse_client_unavailable",
            message=(
                "Langfuse client not configured. Set LANGFUSE_PUBLIC_KEY "
                "and LANGFUSE_SECRET_KEY environment variables."
            ),
        )
        return {
            "status": "error",
            "message": "Langfuse client not configured",
        }

    results = []

    logger.info(
        "prompt_migration_started",
        total_prompts=len(HARDCODED_PROMPTS),
        label=label,
        dry_run=dry_run,
    )

    for name, prompt in HARDCODED_PROMPTS.items():
        result = create_or_update_prompt(
            client=client,
            name=name,
            prompt=prompt,
            label=label,
            dry_run=dry_run,
        )
        results.append(result)

    # Flush Langfuse client to ensure all prompts are sent
    if not dry_run:
        try:
            client.flush()
            logger.info("langfuse_client_flushed")
        except Exception as e:
            logger.warning(
                "langfuse_flush_failed",
                error=str(e),
                exc_info=True,
            )

    # Summarize results
    summary = {
        "total": len(results),
        "created": sum(1 for r in results if r["status"] == "created"),
        "dry_run": sum(1 for r in results if r["status"] == "dry_run"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "results": results,
    }

    logger.info(
        "prompt_migration_completed",
        **{k: v for k, v in summary.items() if k != "results"},
    )

    return summary


def main() -> int:
    """Main entry point for migration script.

    Returns:
        Exit code (0 for success, 1 for error)

    """
    parser = argparse.ArgumentParser(
        description="Migrate hardcoded prompts to Langfuse Prompt Management",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute the migration (default: dry run)",
    )
    parser.add_argument(
        "--label",
        type=str,
        default="production",
        help="Label to apply to prompts (default: production)",
    )

    args = parser.parse_args()

    dry_run = not args.execute

    if dry_run:
        print("\n" + "=" * 70)
        print("DRY RUN MODE - No prompts will be created")
        print("=" * 70 + "\n")
    else:
        print("\n" + "=" * 70)
        print("EXECUTING MIGRATION - Prompts will be created in Langfuse")
        print("=" * 70 + "\n")

    # Run migration
    summary = migrate_all_prompts(dry_run=dry_run, label=args.label)

    # Print summary
    print("\n" + "=" * 70)
    print("MIGRATION SUMMARY")
    print("=" * 70)
    print(f"Total prompts: {summary['total']}")

    if dry_run:
        print(f"Dry run previews: {summary['dry_run']}")
    else:
        print(f"Created: {summary['created']}")
        print(f"Failed: {summary['failed']}")

    # Print individual results
    if summary.get("results"):
        print("\nDetails:")
        for result in summary["results"]:
            status_icon = "✓" if result["status"] in ["created", "dry_run"] else "✗"
            print(f"  {status_icon} {result['name']} - {result['status']}")
            if result.get("error"):
                print(f"      Error: {result['error']}")

    print("=" * 70 + "\n")

    # Return appropriate exit code
    if summary.get("failed", 0) > 0:
        return 1

    if dry_run:
        print("Run with --execute to actually create prompts in Langfuse\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
