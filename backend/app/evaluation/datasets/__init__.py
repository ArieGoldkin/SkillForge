"""Golden datasets for LLM evaluation.

This module provides curated evaluation datasets for:
- Supervisor routing decisions
- Agent analysis quality
- Synthesis coherence

Datasets are designed for use with LangSmith experiments.
"""

import json
from pathlib import Path
from typing import Any

DATASETS_DIR = Path(__file__).parent


def load_dataset(name: str) -> list[dict[str, Any]]:
    """Load a golden dataset by name.

    Args:
        name: Dataset name (e.g., 'supervisor_golden_v1')

    Returns:
        List of examples with inputs, outputs, and metadata

    """
    dataset_path = DATASETS_DIR / f"{name}.json"
    if not dataset_path.exists():
        msg = f"Dataset not found: {name}"
        raise FileNotFoundError(msg)

    with open(dataset_path) as f:
        return json.load(f)


def list_datasets() -> list[str]:
    """List all available golden datasets."""
    return [p.stem for p in DATASETS_DIR.glob("*.json")]
