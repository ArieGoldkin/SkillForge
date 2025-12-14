"""Golden datasets for LLM evaluation.

This module provides curated evaluation datasets for:
- Supervisor routing decisions
- Agent analysis quality
- Synthesis coherence
- Edge cases and adversarial examples (v2.0)

Datasets are designed for use with LangSmith experiments.

Supports both v1.0 (flat list) and v2.0 (wrapped with metadata) formats.
"""

import json
from pathlib import Path
from typing import Any

DATASETS_DIR = Path(__file__).parent


def load_dataset(name: str, include_metadata: bool = False) -> list[dict[str, Any]]:
    """Load a golden dataset by name.

    Supports both v1.0 (flat list) and v2.0 (wrapped with metadata) formats.
    For v2.0 datasets, extracts the 'examples' array by default.

    Args:
        name: Dataset name (e.g., 'supervisor_golden_v1', 'adversarial_v2')
        include_metadata: If True and v2.0 format, return full dataset with metadata.

    Returns:
        List of examples with inputs, outputs, and metadata.
        If include_metadata=True for v2 datasets, returns the full dataset dict.

    """
    dataset_path = DATASETS_DIR / f"{name}.json"
    if not dataset_path.exists():
        msg = f"Dataset not found: {name}"
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
        name: Dataset name (e.g., 'adversarial_v2', 'edge_cases_v2')

    Returns:
        Full dataset dictionary with version, metadata, and examples.

    Raises:
        ValueError: If dataset is not v2.0 format.

    """
    dataset_path = DATASETS_DIR / f"{name}.json"
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
    dataset_path = DATASETS_DIR / f"{name}.json"
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
    """List all available golden datasets."""
    return [p.stem for p in DATASETS_DIR.glob("*.json")]
