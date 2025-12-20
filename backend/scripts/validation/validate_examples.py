#!/usr/bin/env python
"""CLI for human validation workflow.

This script provides a command-line interface for:
- Submitting annotations for example-chunk pairs
- Checking pending examples for annotation
- Computing consensus results
- Generating agreement reports
- Exporting validated datasets

Usage:
    # Submit an annotation
    python scripts/validate_examples.py submit \
        --annotator reviewer1 \
        --example example-001 \
        --chunk chunk-042 \
        --score 3 \
        --confidence 0.9

    # List pending examples
    python scripts/validate_examples.py pending --annotator reviewer1 --limit 10

    # Get consensus results
    python scripts/validate_examples.py consensus

    # Generate agreement report
    python scripts/validate_examples.py agreement

    # Export validated dataset
    python scripts/validate_examples.py export --output validated_dataset.json

    # Review coverage metric
    python scripts/validate_examples.py coverage --dataset queries_expanded.json
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.evaluation.validation.manager import ValidationManager
from app.evaluation.validation.models import Annotation, RelevanceScore

# Persistent storage path
ANNOTATIONS_PATH = Path(__file__).parent.parent / "data" / "validation_annotations.json"


def load_manager() -> ValidationManager:
    """Load validation manager with persisted annotations."""
    manager = ValidationManager()

    if ANNOTATIONS_PATH.exists():
        with ANNOTATIONS_PATH.open() as f:
            data = json.load(f)

        for ann_data in data.get("annotations", []):
            ann = Annotation(
                id=ann_data["id"],
                annotator_id=ann_data["annotator_id"],
                example_id=ann_data["example_id"],
                chunk_id=ann_data["chunk_id"],
                score=RelevanceScore(ann_data["score"]),
                confidence=ann_data["confidence"],
                notes=ann_data.get("notes"),
                timestamp=datetime.fromisoformat(ann_data["timestamp"]),
            )
            manager.annotations.append(ann)

    return manager


def save_manager(manager: ValidationManager) -> None:
    """Persist validation manager annotations."""
    ANNOTATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "version": "1.0",
        "updated_at": datetime.now(UTC).isoformat(),
        "annotations": [
            {
                "id": ann.id,
                "annotator_id": ann.annotator_id,
                "example_id": ann.example_id,
                "chunk_id": ann.chunk_id,
                "score": int(ann.score),
                "confidence": ann.confidence,
                "notes": ann.notes,
                "timestamp": ann.timestamp.isoformat(),
            }
            for ann in manager.annotations
        ],
    }

    with ANNOTATIONS_PATH.open("w") as f:
        json.dump(data, f, indent=2)


def cmd_submit(args: argparse.Namespace) -> int:
    """Submit an annotation."""
    manager = load_manager()

    annotation = Annotation(
        id=str(uuid.uuid4()),
        annotator_id=args.annotator,
        example_id=args.example,
        chunk_id=args.chunk,
        score=RelevanceScore(args.score),
        confidence=args.confidence,
        notes=args.notes,
        timestamp=datetime.now(UTC),
    )

    status = manager.submit_annotation(annotation)
    save_manager(manager)

    print(f"✅ Annotation submitted: {annotation.id}")
    print(f"   Status: {status}")
    print(f"   Score: {RelevanceScore(args.score).name} ({args.score})")
    return 0


def cmd_pending(args: argparse.Namespace) -> int:
    """List pending examples."""
    manager = load_manager()
    pending = manager.get_pending_examples(annotator_id=args.annotator, limit=args.limit)

    if not pending:
        print("✅ No pending examples!")
        return 0

    print(f"📋 Pending examples ({len(pending)}):")
    for item in pending:
        print(f"   - {item['example_id']} / {item['chunk_id']}")

    return 0


def cmd_consensus(args: argparse.Namespace) -> int:
    """Show consensus results."""
    manager = load_manager()
    results = manager.get_consensus_results()

    if not results:
        print("⚠️  No consensus results yet (need more annotations)")
        return 0

    print(f"📊 Consensus Results ({len(results)} pairs):")
    for result in results:
        emoji = {"include": "✅", "exclude": "❌", "review": "🔍"}.get(result.final_decision, "?")
        print(
            f"   {emoji} {result.example_id}/{result.chunk_id}: "
            f"{result.final_decision} (mean={result.mean_score:.2f}, var={result.variance:.2f})"
        )

    return 0


def cmd_agreement(args: argparse.Namespace) -> int:
    """Generate agreement report."""
    manager = load_manager()

    try:
        report = manager.get_agreement_report()
    except ValueError as e:
        print(f"⚠️  Cannot generate report: {e}")
        return 1

    print("📈 Agreement Report:")
    print(f"   Interpretation: {report.interpretation}")
    if report.cohens_kappa is not None:
        print(f"   Cohen's Kappa: {report.cohens_kappa:.3f}")
    if report.fleiss_kappa is not None:
        print(f"   Fleiss' Kappa: {report.fleiss_kappa:.3f}")
    print(f"   Percent Agreement: {report.percent_agreement:.1%}")

    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Export validated dataset."""
    manager = load_manager()
    output_path = Path(args.output)

    count = manager.export_validated_dataset(output_path, include_drafts=args.include_drafts)

    print(f"✅ Exported {count} examples to {output_path}")
    return 0


def cmd_coverage(args: argparse.Namespace) -> int:
    """Calculate review coverage metric."""
    manager = load_manager()
    dataset_path = Path(args.dataset)

    if not dataset_path.exists():
        print(f"❌ Dataset not found: {dataset_path}")
        return 1

    with dataset_path.open() as f:
        dataset = json.load(f)

    total_examples = len(dataset.get("queries", []))
    results = manager.get_consensus_results()
    validated_count = sum(1 for r in results if r.final_decision in ["include", "exclude"])

    coverage = validated_count / total_examples if total_examples > 0 else 0

    print("📊 Review Coverage Metric:")
    print(f"   Total examples: {total_examples}")
    print(f"   Validated: {validated_count}")
    print(f"   Coverage: {coverage:.1%}")

    if coverage >= 0.1:  # 10% target for critical examples
        print("   ✅ Meets minimum coverage target (10%)")
    else:
        print("   ⚠️  Below minimum coverage target (10%)")

    return 0


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Human validation workflow CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Submit command
    submit_parser = subparsers.add_parser("submit", help="Submit an annotation")
    submit_parser.add_argument("--annotator", required=True, help="Annotator ID")
    submit_parser.add_argument("--example", required=True, help="Example ID")
    submit_parser.add_argument("--chunk", required=True, help="Chunk ID")
    submit_parser.add_argument(
        "--score",
        type=int,
        required=True,
        choices=[0, 1, 2, 3],
        help="Relevance score (0=irrelevant, 1=tangential, 2=partial, 3=highly_relevant)",
    )
    submit_parser.add_argument("--confidence", type=float, default=0.8, help="Confidence (0-1)")
    submit_parser.add_argument("--notes", help="Optional notes")

    # Pending command
    pending_parser = subparsers.add_parser("pending", help="List pending examples")
    pending_parser.add_argument("--annotator", help="Filter by annotator")
    pending_parser.add_argument("--limit", type=int, default=10, help="Max results")

    # Consensus command
    subparsers.add_parser("consensus", help="Show consensus results")

    # Agreement command
    subparsers.add_parser("agreement", help="Generate agreement report")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export validated dataset")
    export_parser.add_argument("--output", default="validated_dataset.json", help="Output path")
    export_parser.add_argument(
        "--include-drafts", action="store_true", help="Include pending items"
    )

    # Coverage command
    coverage_parser = subparsers.add_parser("coverage", help="Calculate coverage metric")
    coverage_parser.add_argument(
        "--dataset",
        default="tests/smoke/retrieval/fixtures/queries_expanded.json",
        help="Dataset to measure coverage against",
    )

    args = parser.parse_args()

    commands = {
        "submit": cmd_submit,
        "pending": cmd_pending,
        "consensus": cmd_consensus,
        "agreement": cmd_agreement,
        "export": cmd_export,
        "coverage": cmd_coverage,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
