#!/usr/bin/env python
"""Lightweight golden dataset validation for pre-commit hooks.

Issue #411: Dataset validation quality gates for Langfuse integration.

This script validates the golden_dataset_backup.json file without requiring
database access or the full app context. It's designed to run fast in
pre-commit hooks to catch data integrity issues before commits.

Validates:
1. JSON schema (required fields, types)
2. Count consistency (counts match actual data)
3. Referential integrity (no orphan artifacts/chunks)
4. URL validity (no placeholder skillforge.dev URLs)
5. Langfuse compatibility (fields needed for dataset sync)

Usage:
    python scripts/validate_golden_dataset_precommit.py
    python scripts/validate_golden_dataset_precommit.py --verbose
    python scripts/validate_golden_dataset_precommit.py --schema-only

Exit codes:
    0 - Validation passed
    1 - Validation failed
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Expected schema version
EXPECTED_VERSION = "2.0"

# Required fields for Langfuse dataset sync
# Note: These match the actual backup schema (v2.0), not the database schema
REQUIRED_ANALYSIS_FIELDS = {"id", "url", "title", "status", "content_type"}
REQUIRED_ARTIFACT_FIELDS = {"id", "analysis_id", "markdown_content"}
REQUIRED_CHUNK_FIELDS = {"id", "analysis_id", "snippet"}

# Placeholder URLs that should not be in golden dataset
PLACEHOLDER_PREFIXES = (
    "https://docs.skillforge.dev/",
    "https://learn.skillforge.dev/",
    "https://papers.skillforge.dev/",
    "https://content.skillforge.dev/",
)


def load_backup(backup_path: Path) -> dict[str, Any]:
    """Load and parse the backup JSON file."""
    if not backup_path.exists():
        print(f"ERROR: Backup file not found: {backup_path}")
        sys.exit(1)

    with backup_path.open() as f:
        return json.load(f)


def validate_schema(data: dict[str, Any], verbose: bool = False) -> list[str]:
    """Validate the basic schema structure."""
    errors = []

    # Check top-level fields
    required_top_level = {"version", "created_at", "counts", "data"}
    missing_top = required_top_level - set(data.keys())
    if missing_top:
        errors.append(f"Missing top-level fields: {missing_top}")

    # Check version
    version = data.get("version", "")
    if not version.startswith(EXPECTED_VERSION):
        errors.append(f"Unexpected version: {version} (expected {EXPECTED_VERSION}.x)")

    # Check data structure
    data_section = data.get("data", {})
    required_data = {"analyses", "artifacts", "chunks"}
    missing_data = required_data - set(data_section.keys())
    if missing_data:
        errors.append(f"Missing data sections: {missing_data}")

    if verbose and not errors:
        print("  Schema structure: OK")

    return errors


def validate_counts(data: dict[str, Any], verbose: bool = False) -> list[str]:
    """Validate that counts match actual data."""
    errors = []

    counts = data.get("counts", {})
    data_section = data.get("data", {})

    expected_counts = {
        "analyses": len(data_section.get("analyses", [])),
        "artifacts": len(data_section.get("artifacts", [])),
        "chunks": len(data_section.get("chunks", [])),
    }

    for key, expected in expected_counts.items():
        actual = counts.get(key, 0)
        if actual != expected:
            errors.append(f"Count mismatch for {key}: declared={actual}, actual={expected}")

    if verbose and not errors:
        print(
            f"  Counts: analyses={expected_counts['analyses']}, "
            f"artifacts={expected_counts['artifacts']}, "
            f"chunks={expected_counts['chunks']}"
        )

    return errors


def validate_required_fields(data: dict[str, Any], verbose: bool = False) -> list[str]:
    """Validate required fields for Langfuse compatibility."""
    errors = []
    data_section = data.get("data", {})

    # Check analyses
    for i, analysis in enumerate(data_section.get("analyses", [])):
        missing = REQUIRED_ANALYSIS_FIELDS - set(analysis.keys())
        if missing:
            errors.append(f"Analysis[{i}] missing fields: {missing}")

    # Check artifacts
    for i, artifact in enumerate(data_section.get("artifacts", [])):
        missing = REQUIRED_ARTIFACT_FIELDS - set(artifact.keys())
        if missing:
            errors.append(f"Artifact[{i}] missing fields: {missing}")

    # Check chunks
    for i, chunk in enumerate(data_section.get("chunks", [])):
        missing = REQUIRED_CHUNK_FIELDS - set(chunk.keys())
        if missing:
            errors.append(f"Chunk[{i}] missing fields: {missing}")

    if verbose and not errors:
        print("  Required fields: OK")

    return errors


def validate_referential_integrity(
    data: dict[str, Any], verbose: bool = False
) -> tuple[list[str], list[str]]:
    """Validate referential integrity between tables.

    Returns:
        Tuple of (errors, warnings) - errors block commit, warnings are logged

    """
    errors = []
    warnings = []
    data_section = data.get("data", {})

    analysis_ids = {a["id"] for a in data_section.get("analyses", [])}

    # Check for orphan artifacts (warning - may be pre-existing data issue)
    orphan_artifacts = [
        a["id"]
        for a in data_section.get("artifacts", [])
        if a.get("analysis_id") not in analysis_ids
    ]
    if orphan_artifacts:
        warnings.append(f"Orphan artifacts (no matching analysis): {len(orphan_artifacts)}")

    # Check for orphan chunks (warning - may be pre-existing data issue)
    orphan_chunks = [
        c["id"] for c in data_section.get("chunks", []) if c.get("analysis_id") not in analysis_ids
    ]
    if orphan_chunks:
        warnings.append(f"Orphan chunks (no matching analysis): {len(orphan_chunks)}")

    # Check all analyses have artifacts (warning - some may be in-progress)
    artifact_analysis_ids = {a.get("analysis_id") for a in data_section.get("artifacts", [])}
    missing_artifacts = [
        a["id"] for a in data_section.get("analyses", []) if a["id"] not in artifact_analysis_ids
    ]
    if missing_artifacts:
        warnings.append(f"Analyses without artifacts: {len(missing_artifacts)}")

    if verbose:
        if not errors and not warnings:
            print("  Referential integrity: OK")
        elif warnings:
            print(f"  Referential integrity: {len(warnings)} warning(s)")

    return errors, warnings


def validate_urls(data: dict[str, Any], verbose: bool = False) -> list[str]:
    """Validate that no placeholder URLs exist."""
    errors = []
    data_section = data.get("data", {})

    placeholder_analyses = []
    for analysis in data_section.get("analyses", []):
        url = analysis.get("url", "")
        if isinstance(url, str) and url.startswith(PLACEHOLDER_PREFIXES):
            placeholder_analyses.append(url)

    if placeholder_analyses:
        errors.append(
            f"Placeholder URLs found: {len(placeholder_analyses)} "
            f"(example: {placeholder_analyses[0][:60]}...)"
        )

    if verbose and not errors:
        print("  URL validation: OK")

    return errors


def validate_langfuse_compatibility(data: dict[str, Any], verbose: bool = False) -> list[str]:
    """Validate fields needed for Langfuse dataset sync."""
    errors = []
    data_section = data.get("data", {})

    # Check analyses have valid status
    invalid_status = [
        a["id"] for a in data_section.get("analyses", []) if a.get("status") != "complete"
    ]
    if invalid_status:
        errors.append(f"Non-completed analyses in golden dataset: {len(invalid_status)}")

    # Check analyses have content_type
    missing_content_type = [
        a["id"] for a in data_section.get("analyses", []) if not a.get("content_type")
    ]
    if missing_content_type:
        errors.append(f"Analyses missing content_type: {len(missing_content_type)}")

    if verbose and not errors:
        print("  Langfuse compatibility: OK")

    return errors


def main():
    """Main validation entry point."""
    parser = argparse.ArgumentParser(
        description="Validate golden dataset backup for pre-commit",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed validation output",
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="Only validate schema structure (faster)",
    )

    args = parser.parse_args()

    # Find backup file
    backup_path = Path(__file__).parent.parent / "data" / "golden_dataset_backup.json"

    if args.verbose:
        print(f"\nValidating: {backup_path}")
        print("-" * 50)

    # Load data
    data = load_backup(backup_path)

    # Run validations
    all_errors: list[str] = []
    all_warnings: list[str] = []

    all_errors.extend(validate_schema(data, args.verbose))

    if not args.schema_only:
        all_errors.extend(validate_counts(data, args.verbose))
        all_errors.extend(validate_required_fields(data, args.verbose))

        # Referential integrity returns (errors, warnings)
        ref_errors, ref_warnings = validate_referential_integrity(data, args.verbose)
        all_errors.extend(ref_errors)
        all_warnings.extend(ref_warnings)

        all_errors.extend(validate_urls(data, args.verbose))
        all_errors.extend(validate_langfuse_compatibility(data, args.verbose))

    # Report results
    if args.verbose:
        print("-" * 50)

    # Show warnings (non-blocking)
    if all_warnings:
        print("\nGolden Dataset Warnings (non-blocking):")
        for warning in all_warnings:
            print(f"  ! {warning}")

    if all_errors:
        print("\nGolden Dataset Validation FAILED:")
        for error in all_errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        if args.verbose or all_warnings:
            print("\nGolden Dataset Validation PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
