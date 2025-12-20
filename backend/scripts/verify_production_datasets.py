#!/usr/bin/env python3
"""Verify production datasets in Langfuse.

This script verifies that production datasets have the correct number of items
and that they are properly structured for evaluation.

Usage:
    poetry run python scripts/verify_production_datasets.py

Environment variables required:
    LANGFUSE_ENABLED=true
    LANGFUSE_PUBLIC_KEY=<your-key>
    LANGFUSE_SECRET_KEY=<your-key>
    LANGFUSE_HOST=<your-host>  # Optional, defaults to http://localhost:3000
"""

import sys
from pathlib import Path

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.langfuse_service import get_langfuse_service
from app.core.logging import get_logger

logger = get_logger(__name__)

# Expected item counts for production datasets
EXPECTED_COUNTS = {
    "supervisor_routing_golden_v1_prod": 20,
    "agent_analysis_golden_v1_prod": 9,
    "synthesis_golden_v1_prod": 5,
}


def verify_datasets() -> bool:
    """Verify production dataset item counts.

    Returns:
        True if all datasets have expected counts, False otherwise.

    """
    service = get_langfuse_service()
    if not service or not service.sdk_client:
        logger.error(
            "langfuse_client_unavailable",
            message="Failed to get Langfuse client. Check LANGFUSE_ENABLED and credentials.",
        )
        return False

    client = service.sdk_client

    logger.info(
        "verification_start",
        datasets=list(EXPECTED_COUNTS.keys()),
        message="Starting production dataset verification",
    )

    all_pass = True
    total_expected = sum(EXPECTED_COUNTS.values())
    total_actual = 0

    for dataset_name, expected_count in EXPECTED_COUNTS.items():
        try:
            dataset = client.get_dataset(dataset_name)
            actual_count = len(dataset.items)
            total_actual += actual_count

            if actual_count == expected_count:
                logger.info(
                    "dataset_verified",
                    dataset_name=dataset_name,
                    count=actual_count,
                    status="PASS",
                    message=f"✓ {dataset_name}: {actual_count} items",
                )
            else:
                logger.error(
                    "dataset_count_mismatch",
                    dataset_name=dataset_name,
                    expected=expected_count,
                    actual=actual_count,
                    status="FAIL",
                    message=f"✗ {dataset_name}: expected {expected_count}, got {actual_count}",
                )
                all_pass = False

        except Exception as e:
            logger.error(
                "dataset_verification_failed",
                dataset_name=dataset_name,
                error=str(e),
                status="ERROR",
                message=f"✗ {dataset_name}: {e!s}",
                exc_info=True,
            )
            all_pass = False

    # Summary
    if all_pass:
        logger.info(
            "verification_complete",
            status="SUCCESS",
            total_datasets=len(EXPECTED_COUNTS),
            total_items=total_actual,
            message=f"✅ ALL DATASETS VERIFIED ({total_actual}/{total_expected} items)",
        )
    else:
        logger.error(
            "verification_failed",
            status="FAILURE",
            total_datasets=len(EXPECTED_COUNTS),
            expected_items=total_expected,
            actual_items=total_actual,
            message=f"❌ SOME DATASETS FAILED ({total_actual}/{total_expected} items)",
        )

    return all_pass


def main() -> int:
    """Main entry point for the script.

    Returns:
        Exit code (0 for success, 1 for failure).

    """
    success = verify_datasets()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
