#!/usr/bin/env python3
"""Merge multiple document sources into expanded fixtures.

This script combines documents from multiple JSON files into a single
expanded fixtures file for the evaluation pipeline.

Usage:
    python scripts/merge_expanded_fixtures.py [--output PATH]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def load_documents(file_path: Path) -> list[dict]:
    """Load documents from a JSON file.

    Handles both array format and object format with 'documents' key.
    """
    if not file_path.exists():
        print(f"Warning: {file_path} not found, skipping")
        return []

    with file_path.open() as f:
        data = json.load(f)

    # Handle both formats
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "documents" in data:
        return data["documents"]
    else:
        print(f"Warning: Unexpected format in {file_path}")
        return []


def validate_document(doc: dict) -> list[str]:
    """Validate a document has required fields.

    Returns list of validation errors (empty if valid).
    """
    errors = []
    required = ["id", "title", "content_type", "bucket", "language", "sections"]

    for field in required:
        if field not in doc:
            errors.append(f"Missing required field: {field}")

    if "sections" in doc:
        for i, section in enumerate(doc["sections"]):
            if "id" not in section:
                errors.append(f"Section {i} missing 'id'")
            if "title" not in section:
                errors.append(f"Section {i} missing 'title'")
            if "content" not in section:
                errors.append(f"Section {i} missing 'content'")

    return errors


def merge_documents(
    source_files: list[Path],
    existing_file: Path | None = None,
) -> dict:
    """Merge documents from multiple sources.

    Args:
        source_files: List of JSON files containing documents
        existing_file: Optional existing fixtures file to include

    Returns:
        Complete fixtures dictionary

    """
    all_documents = []
    seen_ids = set()

    # Load existing documents first if provided
    if existing_file and existing_file.exists():
        existing_docs = load_documents(existing_file)
        for doc in existing_docs:
            if doc["id"] not in seen_ids:
                all_documents.append(doc)
                seen_ids.add(doc["id"])
        print(f"Loaded {len(existing_docs)} existing documents")

    # Load documents from each source
    for source_file in source_files:
        docs = load_documents(source_file)
        added = 0
        for doc in docs:
            # Validate
            errors = validate_document(doc)
            if errors:
                print(f"Warning: Skipping invalid doc '{doc.get('id', 'unknown')}': {errors}")
                continue

            # Skip duplicates
            if doc["id"] in seen_ids:
                print(f"Warning: Duplicate id '{doc['id']}', skipping")
                continue

            all_documents.append(doc)
            seen_ids.add(doc["id"])
            added += 1

        print(f"Added {added} documents from {source_file.name}")

    # Count sections
    total_sections = sum(len(doc.get("sections", [])) for doc in all_documents)

    return {
        "version": "2.0",
        "generated": datetime.now().strftime("%Y-%m-%d"),
        "source": "Sprint 12 - Golden Dataset Expansion (Merged)",
        "documents": all_documents,
        "metadata": {
            "total_documents": len(all_documents),
            "total_sections": total_sections,
        },
    }


def main() -> None:
    """CLI entry point for merging fixture documents."""
    parser = argparse.ArgumentParser(description="Merge expanded fixture documents")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tests/smoke/retrieval/fixtures/documents_expanded.json"),
        help="Output file path",
    )
    parser.add_argument(
        "--sources",
        type=Path,
        nargs="+",
        help="Additional source files to merge",
    )
    args = parser.parse_args()

    # Define source files
    fixtures_dir = Path(__file__).parent.parent / "tests/smoke/retrieval/fixtures"

    source_files = [
        fixtures_dir / "bytebytego_docs.json",
        fixtures_dir / "aiml_docs.json",
        fixtures_dir / "sysdesign_docs.json",
        fixtures_dir / "tech_fundamentals_docs.json",
    ]

    if args.sources:
        source_files.extend(args.sources)

    # Merge documents
    existing = fixtures_dir / "documents_expanded.json"
    merged = merge_documents(source_files, existing)

    # Write output
    output_path = Path(__file__).parent.parent / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w") as f:
        json.dump(merged, f, indent=2)

    print(f"\n✅ Merged {merged['metadata']['total_documents']} documents")
    print(f"   Total sections: {merged['metadata']['total_sections']}")
    print(f"   Output: {output_path}")


if __name__ == "__main__":
    main()
