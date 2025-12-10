#!/usr/bin/env python3
"""Generate edge case examples for evaluation dataset.

Usage:
    # Generate all 40 edge cases (8 categories x 5 each)
    python scripts/generate_edge_cases.py --output app/evaluation/datasets/edge_cases_v2.json

    # Generate specific category
    python scripts/generate_edge_cases.py --category misspellings --count 10

    # Validate generated dataset against v2.0 schema
    python scripts/generate_edge_cases.py --validate --output datasets/edge_cases_v2.json

    # List available categories
    python scripts/generate_edge_cases.py --list-categories
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.evaluation.ingestion.edge_case_generator import (
    ALL_CATEGORIES,
    EdgeCaseGenerator,
)
from app.evaluation.schemas.validation import validate_dataset


def list_categories() -> int:
    """List available edge case categories."""
    print("Available edge case categories:")
    print("-" * 40)
    for category in ALL_CATEGORIES:
        print(f"  - {category}")
    print(f"\nTotal: {len(ALL_CATEGORIES)} categories")
    return 0


def print_category_distribution(examples: list[dict[str, Any]]) -> None:
    """Print category distribution of generated examples."""
    category_counts: dict[str, int] = {}
    for ex in examples:
        cat = ex["metadata"]["edge_case_category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    print("\nCategory distribution:")
    for cat, count in sorted(category_counts.items()):
        print(f"  {cat}: {count}")


def validate_and_report(output_path: str) -> int:
    """Validate dataset and report results."""
    print("\nValidating against v2.0 schema...")
    result = validate_dataset(output_path)

    if result.is_valid:
        print("Schema validation PASSED")
        return 0

    print("Schema validation FAILED:")
    for error in result.errors[:5]:  # Show first 5 errors
        print(f"  - {error}")
    if len(result.errors) > 5:
        print(f"  ... and {len(result.errors) - 5} more errors")
    return 1


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        description="Generate edge case examples for evaluation dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Generate all 40 edge cases:
    python scripts/generate_edge_cases.py --output datasets/edge_cases_v2.json

  Generate 10 misspelling examples:
    python scripts/generate_edge_cases.py --category misspellings --count 10

  Validate existing dataset:
    python scripts/generate_edge_cases.py --validate --output datasets/edge_cases_v2.json
        """,
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="app/evaluation/datasets/edge_cases_v2.json",
        help="Output path for dataset JSON (default: app/evaluation/datasets/edge_cases_v2.json)",
    )

    parser.add_argument(
        "--category",
        "-c",
        type=str,
        choices=list(ALL_CATEGORIES),
        help="Specific category to generate (default: all categories)",
    )

    parser.add_argument(
        "--count",
        "-n",
        type=int,
        default=5,
        help="Number of examples per category (default: 5)",
    )

    parser.add_argument(
        "--validate",
        "-v",
        action="store_true",
        help="Validate output against v2.0 schema after generation",
    )

    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List available edge case categories and exit",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate examples but don't save to file",
    )

    return parser


def main() -> int:
    """Run edge case generation CLI.

    Returns:
        Exit code (0 for success, 1 for failure).

    """
    parser = create_parser()
    args = parser.parse_args()

    # Handle --list-categories
    if args.list_categories:
        return list_categories()

    # Initialize generator
    generator = EdgeCaseGenerator()

    # Generate examples
    if args.category:
        print(f"Generating {args.count} examples for category: {args.category}")
        examples = generator.generate_category(args.category, args.count)
    else:
        print(f"Generating {args.count} examples per category ({len(ALL_CATEGORIES)} categories)")
        examples = generator.generate_all(examples_per_category=args.count)

    print(f"Generated {len(examples)} edge case examples")
    print_category_distribution(examples)

    # Save or dry-run
    if args.dry_run:
        print("\n[Dry run] Not saving to file")
    else:
        output_path = Path(args.output)
        generator.save_dataset(examples, output_path)
        print(f"\nSaved to: {output_path}")

    # Validate if requested
    if args.validate and not args.dry_run:
        return validate_and_report(args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
