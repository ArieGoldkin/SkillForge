"""Upload golden datasets to Langfuse.

This script uploads our golden evaluation datasets to Langfuse for:
- Dataset versioning and management
- Experiment tracking
- Collaborative evaluation
- UI-based dataset exploration

Usage:
    # Upload all golden datasets
    poetry run python scripts/upload_datasets_to_langfuse.py

    # Upload specific dataset
    poetry run python scripts/upload_datasets_to_langfuse.py --dataset supervisor

    # Replace existing datasets
    poetry run python scripts/upload_datasets_to_langfuse.py --replace

    # Dry run (show what would be uploaded)
    poetry run python scripts/upload_datasets_to_langfuse.py --dry-run

Supported datasets:
    - supervisor: Supervisor routing decisions
    - agent_analysis: Agent analysis quality
    - synthesis: Synthesis quality
    - adversarial: Adversarial/safety testing examples
    - edge_cases: Edge case and boundary testing examples

Environment variables required:
    LANGFUSE_ENABLED=true
    LANGFUSE_PUBLIC_KEY=<your-key>
    LANGFUSE_SECRET_KEY=<your-key>
    LANGFUSE_HOST=<your-host>  # Optional, defaults to http://localhost:3000
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.langfuse_service import get_langfuse_service
from app.core.logging import get_logger
from app.evaluation.datasets import load_dataset, load_dataset_with_metadata

logger = get_logger(__name__)

# Dataset mapping: file name -> Langfuse dataset name
DATASET_MAPPING = {
    "supervisor": {
        "file_path": "golden/supervisor",
        "langfuse_name": "supervisor_routing_golden_v1_prod",
        "description": "Golden dataset for supervisor routing decisions (v1, production). Contains examples of content that should route to specific agent combinations.",
    },
    "agent_analysis": {
        "file_path": "golden/agent_analysis",
        "langfuse_name": "agent_analysis_golden_v1_prod",
        "description": "Golden dataset for agent analysis evaluation (v1, production). Contains examples of high-quality agent analysis outputs.",
    },
    "synthesis": {
        "file_path": "golden/synthesis",
        "langfuse_name": "synthesis_golden_v1_prod",
        "description": "Golden dataset for synthesis quality evaluation (v1, production). Contains examples of high-quality synthesis outputs.",
    },
    "adversarial": {
        "file_path": "adversarial/adversarial",
        "langfuse_name": "adversarial_safety_v1_prod",
        "description": "Adversarial dataset for safety and robustness testing (v1, production). Contains prompt injection, jailbreak, and security anti-pattern examples.",
    },
    "edge_cases": {
        "file_path": "edge_cases/edge_cases",
        "langfuse_name": "edge_cases_boundary_v1_prod",
        "description": "Edge cases dataset for boundary testing (v1, production). Contains very short, very long, multilingual, and ambiguous input examples.",
    },
}


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


def format_supervisor_item(
    example: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Format supervisor dataset item for Langfuse.

    Args:
        example: Example from supervisor.json

    Returns:
        Tuple of (input, expected_output, metadata)

    """
    input_data = {
        "content": example["inputs"]["content"],
        "content_type": example["inputs"]["content_type"],
        "url": example["inputs"].get("url"),
        "extraction_metadata": example["inputs"].get("extraction_metadata", {}),
    }

    expected_output = {
        "expected_agents": example["outputs"]["expected_agents"],
        "optional_agents": example["outputs"].get("optional_agents", []),
        "reasoning": example["outputs"].get("reasoning", ""),
    }

    metadata = {
        "id": example.get("id"),
        "complexity": example.get("metadata", {}).get("complexity"),
        "primary_agent": example.get("metadata", {}).get("primary_agent"),
        "source": example.get("metadata", {}).get("source"),
    }

    return input_data, expected_output, metadata


def format_agent_analysis_item(
    example: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Format agent_analysis dataset item for Langfuse.

    Args:
        example: Example from agent_analysis.json

    Returns:
        Tuple of (input, expected_output, metadata)

    """
    input_data = {
        "content": example["inputs"]["content"],
        "content_type": example["inputs"]["content_type"],
        "agent_type": example["inputs"]["agent_type"],
        "metadata": example["inputs"].get("metadata", {}),
    }

    expected_output = example.get("expected_outputs", {})

    metadata = {
        "id": example.get("id"),
        "evaluation_criteria": example.get("evaluation_criteria", {}),
    }

    return input_data, expected_output, metadata


def format_synthesis_item(
    example: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Format synthesis dataset item for Langfuse.

    Args:
        example: Example from synthesis.json

    Returns:
        Tuple of (input, expected_output, metadata)

    """
    # Synthesis dataset has different structure - agent findings as input
    input_data = {
        "agent_findings": example["inputs"]["agent_findings"],
        "content_summary": example["inputs"].get("content_summary", ""),
        "coverage_score": example["inputs"].get("coverage_score", 0.0),
    }

    expected_output = example.get("outputs", {})

    metadata = {
        "id": example.get("id"),
        "evaluation_criteria": example.get("evaluation_criteria", {}),
        "metadata": example.get("metadata", {}),
    }

    return input_data, expected_output, metadata


def format_adversarial_item(
    example: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Format adversarial dataset item for Langfuse.

    Args:
        example: Example from adversarial.json (v2.0 format)

    Returns:
        Tuple of (input, expected_output, metadata)

    """
    input_data = {
        "content": example["inputs"]["content"],
        "content_type": example["inputs"].get("content_type", "article"),
        "attack_type": example.get("metadata", {}).get("tags", ["unknown"])[0],
    }

    expected_output = {
        "behavior": example["expected_outputs"]["primary"].get("behavior"),
        "expected_response": example["expected_outputs"]["primary"].get("expected_response"),
        "forbidden_outputs": example["expected_outputs"].get("forbidden_outputs", []),
    }

    metadata = {
        "id": example.get("id"),
        "difficulty": example.get("metadata", {}).get("difficulty"),
        "adversarial": example.get("metadata", {}).get("adversarial", True),
        "tags": example.get("metadata", {}).get("tags", []),
        "evaluation_criteria": example.get("evaluation_criteria", {}),
    }

    return input_data, expected_output, metadata


def format_edge_cases_item(
    example: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Format edge_cases dataset item for Langfuse.

    Args:
        example: Example from edge_cases.json (v2.0 format)

    Returns:
        Tuple of (input, expected_output, metadata)

    """
    input_data = {
        "content": example["inputs"]["content"],
        "content_type": example["inputs"].get("content_type", "query"),
        "edge_case_type": example.get("metadata", {}).get("tags", ["unknown"])[0],
    }

    expected_output = {
        "behavior": example["expected_outputs"]["primary"].get("behavior"),
        "expected_response": example["expected_outputs"]["primary"].get("expected_response"),
        "expected_error": example["expected_outputs"]["primary"].get("expected_error"),
        "forbidden_outputs": example["expected_outputs"].get("forbidden_outputs", []),
    }

    metadata = {
        "id": example.get("id"),
        "difficulty": example.get("metadata", {}).get("difficulty"),
        "edge_case": example.get("metadata", {}).get("edge_case", True),
        "tags": example.get("metadata", {}).get("tags", []),
        "evaluation_criteria": example.get("evaluation_criteria", {}),
    }

    return input_data, expected_output, metadata


# Formatter registry
FORMATTERS = {
    "supervisor": format_supervisor_item,
    "agent_analysis": format_agent_analysis_item,
    "synthesis": format_synthesis_item,
    "adversarial": format_adversarial_item,
    "edge_cases": format_edge_cases_item,
}


def _compute_item_hash(input_data: dict[str, Any], expected_output: dict[str, Any]) -> str:
    """Compute deterministic hash for dataset item deduplication.

    The hash is based on the (input, expected_output) pair to detect exact duplicates.
    This enables idempotent uploads - running the script multiple times will not
    create duplicate items in Langfuse.

    Args:
        input_data: The input dictionary for the dataset item
        expected_output: The expected output dictionary for the dataset item

    Returns:
        16-character hex hash string for fast comparison

    """
    input_str = json.dumps(input_data, sort_keys=True)
    output_str = json.dumps(expected_output, sort_keys=True)
    combined = f"{input_str}||{output_str}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def upload_dataset(  # noqa: PLR0912 - Script function with necessary complexity
    dataset_name: str,
    *,
    replace: bool = False,
    dry_run: bool = False,
) -> bool:
    """Upload a single dataset to Langfuse.

    Args:
        dataset_name: Name of the dataset to upload (e.g., "supervisor")
        replace: If True, delete and recreate the dataset if it exists
        dry_run: If True, only show what would be uploaded without uploading

    Returns:
        True if upload succeeded, False otherwise.

    """
    if dataset_name not in DATASET_MAPPING:
        logger.error(
            "unknown_dataset",
            message=f"Unknown dataset: {dataset_name}",
            available_datasets=list(DATASET_MAPPING.keys()),
        )
        return False

    config = DATASET_MAPPING[dataset_name]
    file_path = config["file_path"]
    langfuse_name = config["langfuse_name"]
    description = config["description"]

    logger.info(
        "upload_dataset_start",
        dataset_name=dataset_name,
        file_path=file_path,
        langfuse_name=langfuse_name,
    )

    # Load dataset
    try:
        examples = load_dataset(file_path)
        logger.info(
            "dataset_loaded",
            dataset_name=dataset_name,
            example_count=len(examples),
        )
    except FileNotFoundError:
        logger.exception(
            "dataset_file_not_found",
            dataset_name=dataset_name,
            file_path=file_path,
        )
        return False

    if dry_run:
        logger.info(
            "dry_run_mode",
            message=f"Would upload {len(examples)} items to dataset '{langfuse_name}'",
            dataset_name=dataset_name,
        )
        # Show first example
        if examples:
            formatter = FORMATTERS[dataset_name]
            input_data, expected_output, metadata = formatter(examples[0])
            logger.info(
                "dry_run_example",
                input_keys=list(input_data.keys()),
                expected_output_keys=list(expected_output.keys()),
                metadata_keys=list(metadata.keys()),
            )
        return True

    # Get Langfuse service
    service = get_langfuse_service()
    if not service or not service.sdk_client:
        logger.error(
            "langfuse_client_unavailable",
            message="Failed to get Langfuse client",
        )
        return False

    client = service.sdk_client

    # Check if dataset exists and fetch existing item hashes for deduplication
    dataset_exists = False
    existing_hashes = set()
    try:
        existing_dataset = client.get_dataset(langfuse_name)
        dataset_exists = True

        if not replace:
            # Fetch existing items and compute their hashes for deduplication
            logger.info(
                "dataset_exists",
                langfuse_name=langfuse_name,
                replace=replace,
                message="Fetching existing items for deduplication",
            )

            formatter = FORMATTERS[dataset_name]
            for item in existing_dataset.items:
                # Reformat the existing item to match our hash format
                # Note: We use item.input and item.expected_output directly
                item_hash = _compute_item_hash(item.input, item.expected_output or {})
                existing_hashes.add(item_hash)

            logger.info(
                "existing_hashes_computed",
                count=len(existing_hashes),
                dataset_name=dataset_name,
            )
        else:
            logger.warning(
                "replace_mode_enabled",
                message="Replace mode enabled but Langfuse SDK does not support dataset deletion. Items will be added to existing dataset.",
                langfuse_name=langfuse_name,
            )
    except Exception:
        logger.debug(
            "dataset_not_found_creating_new",
            langfuse_name=langfuse_name,
            message="Dataset does not exist, will create new",
        )

    # Create dataset if it doesn't exist
    if not dataset_exists:
        try:
            # Try to load metadata for v2 datasets
            try:
                dataset_with_metadata = load_dataset_with_metadata(file_path)
                dataset_metadata = dataset_with_metadata.get("metadata", {})
            except (ValueError, FileNotFoundError):
                dataset_metadata = {}

            dataset_metadata.update(
                {
                    "uploaded_at": datetime.now(UTC).isoformat(),
                    "source": "golden_dataset_backup",
                    "script_version": "1.0.0",
                }
            )

            client.create_dataset(
                name=langfuse_name,
                description=description,
                metadata=dataset_metadata,
            )
            logger.info(
                "dataset_created",
                langfuse_name=langfuse_name,
                metadata=dataset_metadata,
            )
        except Exception as e:
            logger.error(
                "dataset_creation_failed",
                langfuse_name=langfuse_name,
                error=str(e),
                exc_info=True,
            )
            return False

    # Upload dataset items with deduplication
    formatter = FORMATTERS[dataset_name]
    uploaded_count = 0
    skipped_count = 0
    failed_count = 0

    for idx, example in enumerate(examples, 1):
        try:
            input_data, expected_output, metadata = formatter(example)

            # Compute hash for this item
            item_hash = _compute_item_hash(input_data, expected_output)

            # Skip if already exists (deduplication)
            if item_hash in existing_hashes:
                skipped_count += 1
                logger.debug(
                    "skipping_duplicate",
                    dataset_name=dataset_name,
                    item_id=example.get("id"),
                    item_hash=item_hash,
                )
                continue

            # Upload new item
            client.create_dataset_item(
                dataset_name=langfuse_name,
                input=input_data,
                expected_output=expected_output,
                metadata=metadata,
            )

            # Track uploaded hash to prevent duplicates within this batch
            existing_hashes.add(item_hash)
            uploaded_count += 1

            if uploaded_count % 10 == 0:
                logger.info(
                    "upload_progress",
                    dataset_name=dataset_name,
                    uploaded=uploaded_count,
                    skipped=skipped_count,
                    total=len(examples),
                    progress_pct=round((uploaded_count / len(examples)) * 100, 1),
                )

        except Exception as e:
            failed_count += 1
            logger.error(
                "item_upload_failed",
                dataset_name=dataset_name,
                item_index=idx,
                item_id=example.get("id"),
                error=str(e),
                exc_info=True,
            )

    # Flush events
    try:
        client.flush()
    except Exception as e:
        logger.warning(
            "flush_failed",
            error=str(e),
        )

    logger.info(
        "upload_complete",
        dataset_name=dataset_name,
        langfuse_name=langfuse_name,
        uploaded=uploaded_count,
        skipped=skipped_count,
        failed=failed_count,
        total=len(examples),
        success_rate=round((uploaded_count / len(examples)) * 100, 1) if examples else 0,
    )

    return failed_count == 0


def main() -> int:
    """Main entry point for the script.

    Returns:
        Exit code (0 for success, 1 for failure).

    """
    parser = argparse.ArgumentParser(
        description="Upload golden datasets to Langfuse for experiment tracking and evaluation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Upload all datasets
    poetry run python scripts/upload_datasets_to_langfuse.py

    # Upload specific dataset
    poetry run python scripts/upload_datasets_to_langfuse.py --dataset supervisor

    # Replace existing datasets
    poetry run python scripts/upload_datasets_to_langfuse.py --replace

    # Dry run
    poetry run python scripts/upload_datasets_to_langfuse.py --dry-run

Available datasets:
    - supervisor: Supervisor routing decisions (20 items)
    - agent_analysis: Agent analysis quality (9 items)
    - synthesis: Synthesis quality (5 items)
    - adversarial: Adversarial/safety testing (31 items)
    - edge_cases: Edge case/boundary testing (40 items)
        """,
    )

    parser.add_argument(
        "--dataset",
        type=str,
        choices=list(DATASET_MAPPING.keys()),
        help="Upload specific dataset (default: upload all)",
    )

    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing datasets (note: Langfuse SDK does not support dataset deletion)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be uploaded without uploading",
    )

    args = parser.parse_args()

    # Check Langfuse configuration
    if not check_langfuse_enabled():
        return 1

    # Determine which datasets to upload
    datasets_to_upload = [args.dataset] if args.dataset else list(DATASET_MAPPING.keys())

    logger.info(
        "upload_start",
        datasets=datasets_to_upload,
        replace=args.replace,
        dry_run=args.dry_run,
    )

    # Upload datasets
    all_success = True
    for dataset_name in datasets_to_upload:
        success = upload_dataset(
            dataset_name,
            replace=args.replace,
            dry_run=args.dry_run,
        )
        if not success:
            all_success = False

    if all_success:
        logger.info(
            "upload_all_complete",
            message="All datasets uploaded successfully",
            datasets=datasets_to_upload,
        )
        return 0
    logger.error(
        "upload_some_failed",
        message="Some datasets failed to upload",
        datasets=datasets_to_upload,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
