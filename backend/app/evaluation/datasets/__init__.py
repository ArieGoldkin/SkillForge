"""Golden datasets for LLM evaluation.

This module provides curated evaluation datasets organized by category:
- golden/       Production-validated golden datasets
- adversarial/  Attack and stress test datasets
- edge_cases/   Edge case and boundary datasets
- archive/      Deprecated versions (not loaded)

Dataset naming convention (no more _v1/_v2 suffixes):
- golden/supervisor.json      Supervisor routing golden set
- golden/agent_analysis.json  Agent analysis golden set
- golden/synthesis.json       Synthesis golden set
- adversarial/adversarial.json
- edge_cases/edge_cases.json

Datasets are designed for use with Langfuse experiments.
"""

import json
from pathlib import Path
from typing import Any

DATASETS_DIR = Path(__file__).parent

# Dataset category folders
GOLDEN_DIR = DATASETS_DIR / "golden"
ADVERSARIAL_DIR = DATASETS_DIR / "adversarial"
EDGE_CASES_DIR = DATASETS_DIR / "edge_cases"
ARCHIVE_DIR = DATASETS_DIR / "archive"


def _resolve_dataset_path(name: str) -> Path:
    """Resolve dataset name to file path.

    Expects folder-based paths like "golden/supervisor" or "adversarial/adversarial".
    """
    # Folder-based format (e.g., "golden/supervisor")
    if "/" in name:
        return DATASETS_DIR / f"{name}.json"

    # If no folder prefix, raise a clear error
    msg = f"Dataset name must include category folder (e.g., 'golden/{name}'). Got: '{name}'"
    raise ValueError(msg)


def load_dataset(name: str, include_metadata: bool = False) -> list[dict[str, Any]]:
    """Load a golden dataset by name.

    Supports both v1.0 (flat list) and v2.0 (wrapped with metadata) formats.
    For v2.0 datasets, extracts the 'examples' array by default.

    Args:
        name: Dataset name (e.g., "golden/supervisor", "adversarial/adversarial")
        include_metadata: If True and v2.0 format, return full dataset with metadata.

    Returns:
        List of examples with inputs, outputs, and metadata.
        If include_metadata=True for v2 datasets, returns the full dataset dict.

    """
    dataset_path = _resolve_dataset_path(name)
    if not dataset_path.exists():
        msg = f"Dataset not found: {name} (tried {dataset_path})"
        raise FileNotFoundError(msg)

    with dataset_path.open() as f:
        data = json.load(f)

    # Check if v2.0 format (has version and examples keys)
    if isinstance(data, dict) and "version" in data and "examples" in data:
        if include_metadata:
            return data  # type: ignore[return-value]
        examples: list[dict[str, Any]] = data["examples"]
        return examples

    # v1.0 format - flat list of examples
    examples_v1: list[dict[str, Any]] = data
    return examples_v1


def load_dataset_with_metadata(name: str) -> dict[str, Any]:
    """Load a v2.0 dataset with full metadata.

    Args:
        name: Dataset name (e.g., "golden/agent_analysis", "adversarial/adversarial")

    Returns:
        Full dataset dictionary with version, metadata, and examples.

    Raises:
        ValueError: If dataset is not v2.0 format.

    """
    dataset_path = _resolve_dataset_path(name)
    if not dataset_path.exists():
        msg = f"Dataset not found: {name}"
        raise FileNotFoundError(msg)

    with dataset_path.open() as f:
        data = json.load(f)

    if not isinstance(data, dict) or "version" not in data:
        msg = f"Dataset '{name}' is not v2.0 format"
        raise ValueError(msg)

    return data


def get_dataset_info(name: str) -> dict[str, Any]:
    """Get metadata information about a dataset.

    Args:
        name: Dataset name

    Returns:
        Dictionary with dataset info (version, example_count, metadata for v2).

    """
    dataset_path = _resolve_dataset_path(name)
    if not dataset_path.exists():
        msg = f"Dataset not found: {name}"
        raise FileNotFoundError(msg)

    with dataset_path.open() as f:
        data = json.load(f)

    if isinstance(data, dict) and "version" in data:
        # v2.0 format
        return {
            "name": name,
            "version": data.get("version", "unknown"),
            "example_count": len(data.get("examples", [])),
            "metadata": data.get("metadata", {}),
        }

    # v1.0 format
    return {
        "name": name,
        "version": "1.0.0",
        "example_count": len(data) if isinstance(data, list) else 0,
        "metadata": {},
    }


def list_datasets() -> list[str]:
    """List all available golden datasets (excludes archive)."""
    datasets = []

    # List from category folders
    for category_dir in [GOLDEN_DIR, ADVERSARIAL_DIR, EDGE_CASES_DIR]:
        if category_dir.exists():
            for p in category_dir.glob("*.json"):
                rel_path = p.relative_to(DATASETS_DIR)
                datasets.append(str(rel_path.with_suffix("")))

    return sorted(datasets)


def list_golden_datasets() -> list[str]:
    """List only production golden datasets."""
    if not GOLDEN_DIR.exists():
        return []
    return sorted([p.stem for p in GOLDEN_DIR.glob("*.json")])
