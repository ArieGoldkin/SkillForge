#!/usr/bin/env python3
"""Upload golden datasets to Langfuse (standalone version).

This standalone version bypasses app configuration for simple execution.

Usage:
    export LANGFUSE_ENABLED=true
    export LANGFUSE_PUBLIC_KEY=pk-lf-...
    export LANGFUSE_SECRET_KEY=sk-lf-...
    export LANGFUSE_HOST=http://localhost:3000

    poetry run python scripts/upload_datasets_to_langfuse_standalone.py
    poetry run python scripts/upload_datasets_to_langfuse_standalone.py --dry-run
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add app to path for dataset loading only
sys.path.insert(0, str(Path(__file__).parent.parent))

from langfuse import Langfuse

# Dataset mapping
DATASET_MAPPING = {
    "supervisor": {
        "file_path": "app/evaluation/datasets/golden/supervisor.json",
        "langfuse_name": "supervisor_routing_golden_v1_prod",
        "description": "Golden dataset for supervisor routing decisions (v1, production)",
    },
    "agent_analysis": {
        "file_path": "app/evaluation/datasets/golden/agent_analysis.json",
        "langfuse_name": "agent_analysis_golden_v1_prod",
        "description": "Golden dataset for agent analysis evaluation (v1, production)",
    },
    "synthesis": {
        "file_path": "app/evaluation/datasets/golden/synthesis.json",
        "langfuse_name": "synthesis_golden_v1_prod",
        "description": "Golden dataset for synthesis quality evaluation (v1, production)",
    },
}


def load_dataset_from_file(file_path: str) -> list[dict[str, Any]]:
    """Load dataset from JSON file."""
    full_path = Path(__file__).parent.parent / file_path
    with open(full_path) as f:
        return json.load(f)


def format_supervisor_item(example: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Format supervisor dataset item."""
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


def format_agent_analysis_item(example: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Format agent_analysis dataset item."""
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


def format_synthesis_item(example: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Format synthesis dataset item."""
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


FORMATTERS = {
    "supervisor": format_supervisor_item,
    "agent_analysis": format_agent_analysis_item,
    "synthesis": format_synthesis_item,
}


def compute_item_hash(input_data: dict[str, Any], expected_output: dict[str, Any]) -> str:
    """Compute deterministic hash for deduplication."""
    input_str = json.dumps(input_data, sort_keys=True)
    output_str = json.dumps(expected_output, sort_keys=True)
    combined = f"{input_str}||{output_str}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def upload_dataset(
    client: Langfuse,
    dataset_name: str,
    config: dict[str, Any],
    dry_run: bool = False,
    replace: bool = False,
) -> dict[str, Any]:
    """Upload a single dataset with deduplication."""
    print(f"\n=== Uploading {dataset_name} ===")

    # Load dataset
    examples = load_dataset_from_file(config["file_path"])
    print(f"Loaded {len(examples)} examples from {config['file_path']}")

    if dry_run:
        print(f"[DRY RUN] Would upload to '{config['langfuse_name']}'")
        if examples:
            formatter = FORMATTERS[dataset_name]
            input_data, expected_output, metadata = formatter(examples[0])
            print(f"  Example input keys: {list(input_data.keys())}")
            print(f"  Example output keys: {list(expected_output.keys())}")
        return {"total": len(examples), "uploaded": 0, "skipped": 0, "failed": 0}

    # Check for existing dataset and compute hashes
    existing_hashes = set()
    try:
        existing_dataset = client.get_dataset(config["langfuse_name"])
        if not replace:
            print(f"Dataset exists, computing hashes for deduplication...")
            for item in existing_dataset.items:
                item_hash = compute_item_hash(item.input, item.expected_output or {})
                existing_hashes.add(item_hash)
            print(f"Found {len(existing_hashes)} existing items")
    except Exception:
        print(f"Dataset '{config['langfuse_name']}' does not exist, will create")
        # Create dataset
        client.create_dataset(
            name=config["langfuse_name"],
            description=config["description"],
            metadata={
                "uploaded_at": datetime.now(UTC).isoformat(),
                "source": "golden_dataset_backup",
                "script_version": "2.0.0",
            },
        )

    # Upload items with deduplication
    formatter = FORMATTERS[dataset_name]
    uploaded = 0
    skipped = 0
    failed = 0

    for example in examples:
        try:
            input_data, expected_output, metadata = formatter(example)
            item_hash = compute_item_hash(input_data, expected_output)

            if item_hash in existing_hashes:
                skipped += 1
                continue

            client.create_dataset_item(
                dataset_name=config["langfuse_name"],
                input=input_data,
                expected_output=expected_output,
                metadata=metadata,
            )

            existing_hashes.add(item_hash)
            uploaded += 1

        except Exception as e:
            failed += 1
            print(f"  ERROR uploading item {example.get('id')}: {e}")

    client.flush()

    print(f"✓ Complete: {uploaded} uploaded, {skipped} skipped, {failed} failed")
    return {
        "dataset_name": dataset_name,
        "langfuse_name": config["langfuse_name"],
        "total": len(examples),
        "uploaded": uploaded,
        "skipped": skipped,
        "failed": failed,
    }


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Upload golden datasets to Langfuse")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be uploaded")
    parser.add_argument("--replace", action="store_true", help="Skip deduplication")
    parser.add_argument("--dataset", choices=list(DATASET_MAPPING.keys()), help="Upload specific dataset")
    args = parser.parse_args()

    # Check environment
    if not args.dry_run:
        if os.getenv("LANGFUSE_ENABLED", "false").lower() != "true":
            print("ERROR: LANGFUSE_ENABLED must be set to 'true'")
            return 1

        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

        if not public_key or not secret_key:
            print("ERROR: LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY must be set")
            return 1

        print(f"Connecting to Langfuse at {host}")
        client = Langfuse(public_key=public_key, secret_key=secret_key, host=host)
    else:
        client = None  # type: ignore

    # Upload datasets
    datasets_to_upload = [args.dataset] if args.dataset else list(DATASET_MAPPING.keys())
    results = []

    for dataset_name in datasets_to_upload:
        config = DATASET_MAPPING[dataset_name]
        result = upload_dataset(client, dataset_name, config, dry_run=args.dry_run, replace=args.replace)
        results.append(result)

    # Summary
    print("\n=== Summary ===")
    total_uploaded = sum(r["uploaded"] for r in results)
    total_skipped = sum(r["skipped"] for r in results)
    total_failed = sum(r["failed"] for r in results)
    total_items = sum(r["total"] for r in results)

    print(f"Total: {total_items} items")
    print(f"Uploaded: {total_uploaded}")
    print(f"Skipped: {total_skipped}")
    print(f"Failed: {total_failed}")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
