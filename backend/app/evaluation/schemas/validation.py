"""Schema validation utilities for evaluation datasets v2.0.

This module provides functions to validate evaluation datasets against
the v2.0 JSON Schema and perform additional business logic validation.

Usage:
    ```python
    from app.evaluation.schemas.validation import validate_dataset

    # Validate a dataset file
    result = validate_dataset("datasets/v2/agent/agent_analysis_golden_v2.json")
    if result.is_valid:
        print("Dataset is valid!")
    else:
        print(f"Validation errors: {result.errors}")
    ```

"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Valid difficulty levels (aligned with sprint spec)
VALID_DIFFICULTY_LEVELS = frozenset(["trivial", "easy", "medium", "hard", "adversarial"])

# Minimum queries per difficulty level for comprehensive coverage
MIN_QUERIES_PER_DIFFICULTY = 3

# Try to import jsonschema, but don't fail if not available
try:
    from jsonschema import Draft7Validator

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    Draft7Validator = None  # type: ignore[misc, assignment]
    logger.warning("jsonschema not available - install with: pip install jsonschema")


@dataclass
class ValidationResult:
    """Result of dataset validation.

    Attributes:
        is_valid: True if dataset passes all validation checks
        errors: List of validation error messages
        warnings: List of non-critical warnings
        dataset_name: Name of validated dataset
        example_count: Number of examples in dataset
        validated_examples: Number of examples with status='validated'
        draft_examples: Number of examples with status='draft'

    """

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    dataset_name: str = ""
    example_count: int = 0
    validated_examples: int = 0
    draft_examples: int = 0


def validate_dataset(
    dataset_path: str | Path, schema_path: str | Path | None = None
) -> ValidationResult:
    """Validate evaluation dataset against v2.0 schema.

    Performs both JSON Schema validation and business logic validation:
    - Schema compliance
    - Provenance completeness
    - Scoring rubric weights sum to 1.0
    - Required fields present
    - Validation status consistency

    Args:
        dataset_path: Path to dataset JSON file
        schema_path: Path to schema JSON file (defaults to dataset_v2_schema.json)

    Returns:
        ValidationResult with validation status and error/warning messages

    Example:
        ```python
        result = validate_dataset("datasets/v2/agent/agent_analysis_golden_v2.json")
        if not result.is_valid:
            for error in result.errors:
                print(f"Error: {error}")
        ```

    """
    dataset_path = Path(dataset_path)
    result = ValidationResult(is_valid=True, dataset_name=dataset_path.stem)

    # Check file exists
    if not dataset_path.exists():
        result.is_valid = False
        result.errors.append(f"Dataset file not found: {dataset_path}")
        return result

    # Load dataset
    try:
        with open(dataset_path) as f:
            dataset = json.load(f)
    except json.JSONDecodeError as e:
        result.is_valid = False
        result.errors.append(f"Invalid JSON: {e}")
        return result

    # JSON Schema validation
    if JSONSCHEMA_AVAILABLE:
        schema_errors = _validate_against_schema(dataset, schema_path)
        if schema_errors:
            result.is_valid = False
            result.errors.extend(schema_errors)
    else:
        result.warnings.append("jsonschema library not available - skipping schema validation")

    # Business logic validation
    logic_errors, logic_warnings = _validate_business_logic(dataset)
    if logic_errors:
        result.is_valid = False
        result.errors.extend(logic_errors)
    result.warnings.extend(logic_warnings)

    # Gather statistics
    if "examples" in dataset:
        result.example_count = len(dataset["examples"])
        result.validated_examples = sum(
            1 for ex in dataset["examples"] if ex.get("validation", {}).get("status") == "validated"
        )
        result.draft_examples = sum(
            1 for ex in dataset["examples"] if ex.get("validation", {}).get("status") == "draft"
        )

    # Log result
    if result.is_valid:
        logger.info(
            "dataset_validation_success",
            dataset=dataset_path.name,
            example_count=result.example_count,
            validated=result.validated_examples,
            drafts=result.draft_examples,
        )
    else:
        logger.error(
            "dataset_validation_failed",
            dataset=dataset_path.name,
            errors=result.errors,
            warnings=result.warnings,
        )

    return result


def _validate_against_schema(dataset: dict[str, Any], schema_path: str | Path | None) -> list[str]:
    """Validate dataset against JSON Schema.

    Args:
        dataset: Loaded dataset dictionary
        schema_path: Path to schema file (or None for default)

    Returns:
        List of validation error messages (empty if valid)

    """
    if not JSONSCHEMA_AVAILABLE:
        return []

    errors = []

    # Determine schema path
    if schema_path is None:
        # Default to schema in same directory
        schema_path = Path(__file__).parent / "dataset_v2_schema.json"
    else:
        schema_path = Path(schema_path)

    if not schema_path.exists():
        return [f"Schema file not found: {schema_path}"]

    # Load schema
    try:
        with open(schema_path) as f:
            schema = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid schema JSON: {e}"]

    # Validate
    validator = Draft7Validator(schema)
    for error in validator.iter_errors(dataset):
        # Format error message with path
        path = ".".join(str(p) for p in error.path) if error.path else "root"
        errors.append(f"{path}: {error.message}")

    return errors


def _validate_business_logic(dataset: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Validate business logic rules beyond JSON Schema.

    Args:
        dataset: Loaded dataset dictionary

    Returns:
        Tuple of (errors, warnings)

    """
    errors = []
    warnings = []

    # Check version
    version = dataset.get("version", "")
    if not version.startswith("2."):
        errors.append(f"Invalid version: {version} (must be 2.x.x)")

    # Check metadata
    metadata = dataset.get("metadata", {})
    if not metadata.get("task_type"):
        errors.append("Missing metadata.task_type")

    # Validate examples
    examples = dataset.get("examples", [])
    if not examples:
        warnings.append("Dataset has no examples")

    for i, example in enumerate(examples):
        example_id = example.get("id", f"example-{i}")

        # Check provenance
        provenance = example.get("provenance", {})
        if not provenance:
            errors.append(f"{example_id}: Missing provenance")
        elif not provenance.get("source"):
            errors.append(f"{example_id}: Missing provenance.source")
        elif not provenance.get("created_at"):
            errors.append(f"{example_id}: Missing provenance.created_at")

        # Check scoring rubric weights
        rubric = example.get("evaluation_criteria", {}).get("scoring_rubric", {})
        if rubric:
            weights = []
            for criterion in ["correctness", "completeness", "quality", "latency", "cost"]:
                if criterion in rubric:
                    weight = rubric[criterion].get("weight")
                    if weight is not None:
                        weights.append(weight)

            if weights:
                total_weight = sum(weights)
                if abs(total_weight - 1.0) > 0.01:  # Allow small floating point errors
                    errors.append(
                        f"{example_id}: Scoring rubric weights sum to {total_weight:.2f}, must sum to 1.0"
                    )

        # Check validation status
        validation = example.get("validation", {})
        status = validation.get("status", "draft")
        validated_by = validation.get("validated_by", [])

        if status == "validated" and not validated_by:
            errors.append(f"{example_id}: Status is 'validated' but no validators listed")
        elif status == "validated" and len(validated_by) < 2:
            warnings.append(f"{example_id}: Only {len(validated_by)} validator(s), recommend ≥2")

        # Check for required approvals
        if validated_by:
            approvals = sum(1 for v in validated_by if v.get("approved"))
            if status == "validated" and approvals < 2:
                errors.append(
                    f"{example_id}: Status 'validated' requires ≥2 approvals, found {approvals}"
                )

        # Warn about draft examples
        if status == "draft":
            warnings.append(f"{example_id}: Example is in draft status")

    return errors, warnings


def validate_directory(
    directory: str | Path, recursive: bool = True
) -> dict[str, ValidationResult]:
    """Validate all datasets in a directory.

    Args:
        directory: Path to directory containing datasets
        recursive: If True, search subdirectories

    Returns:
        Dictionary mapping dataset filename -> ValidationResult

    Example:
        ```python
        results = validate_directory("datasets/v2/")
        for filename, result in results.items():
            if not result.is_valid:
                print(f"{filename}: FAILED")
        ```

    """
    directory = Path(directory)
    results = {}

    # Find all JSON files
    pattern = "**/*.json" if recursive else "*.json"
    for json_file in directory.glob(pattern):
        result = validate_dataset(json_file)
        results[json_file.name] = result

    return results


def generate_validation_report(results: dict[str, ValidationResult]) -> str:
    """Generate human-readable validation report.

    Args:
        results: Dictionary of validation results from validate_directory()

    Returns:
        Formatted markdown report

    Example:
        ```python
        results = validate_directory("datasets/v2/")
        report = generate_validation_report(results)
        print(report)
        ```

    """
    lines = [
        "# Evaluation Dataset Validation Report",
        "",
        f"**Generated**: {datetime.utcnow().isoformat()}Z",
        f"**Datasets Checked**: {len(results)}",
        "",
    ]

    # Summary
    valid_count = sum(1 for r in results.values() if r.is_valid)
    invalid_count = len(results) - valid_count
    total_examples = sum(r.example_count for r in results.values())
    total_validated = sum(r.validated_examples for r in results.values())
    total_drafts = sum(r.draft_examples for r in results.values())

    lines.extend(
        [
            "## Summary",
            "",
            f"- ✅ Valid: {valid_count}",
            f"- ❌ Invalid: {invalid_count}",
            f"- 📊 Total Examples: {total_examples}",
            f"- ✓ Validated Examples: {total_validated}",
            f"- 📝 Draft Examples: {total_drafts}",
            "",
        ]
    )

    # Details
    lines.extend(["## Dataset Details", ""])

    for filename, result in sorted(results.items()):
        status = "✅ VALID" if result.is_valid else "❌ INVALID"
        lines.append(f"### {filename} - {status}")
        lines.append("")
        lines.append(f"- Examples: {result.example_count}")
        lines.append(f"- Validated: {result.validated_examples}")
        lines.append(f"- Drafts: {result.draft_examples}")

        if result.errors:
            lines.append("")
            lines.append("**Errors:**")
            for error in result.errors:
                lines.append(f"- ❌ {error}")

        if result.warnings:
            lines.append("")
            lines.append("**Warnings:**")
            for warning in result.warnings:
                lines.append(f"- ⚠️ {warning}")

        lines.append("")

    return "\n".join(lines)


def validate_difficulty_distribution(
    examples: list[dict[str, Any]], min_per_level: int = MIN_QUERIES_PER_DIFFICULTY
) -> tuple[list[str], list[str], dict[str, int]]:
    """Validate difficulty field presence and distribution across examples.

    Args:
        examples: List of example dictionaries with metadata.difficulty
        min_per_level: Minimum required examples per difficulty level

    Returns:
        Tuple of (errors, warnings, distribution_counts)

    Example:
        ```python
        errors, warnings, counts = validate_difficulty_distribution(dataset["examples"])
        if errors:
            print(f"Difficulty validation failed: {errors}")
        print(f"Distribution: {counts}")
        ```

    """
    errors: list[str] = []
    warnings: list[str] = []
    distribution: dict[str, int] = dict.fromkeys(VALID_DIFFICULTY_LEVELS, 0)

    # Check each example for difficulty field
    for i, example in enumerate(examples):
        example_id = example.get("id", f"example-{i}")
        metadata = example.get("metadata", {})
        difficulty = metadata.get("difficulty")

        if difficulty is None:
            errors.append(f"{example_id}: Missing metadata.difficulty field")
        elif difficulty not in VALID_DIFFICULTY_LEVELS:
            errors.append(
                f"{example_id}: Invalid difficulty '{difficulty}', "
                f"must be one of: {sorted(VALID_DIFFICULTY_LEVELS)}"
            )
        else:
            distribution[difficulty] += 1

    # Check distribution coverage
    for level, count in distribution.items():
        if count == 0:
            warnings.append(f"No examples with difficulty='{level}'")
        elif count < min_per_level:
            warnings.append(
                f"Only {count} examples with difficulty='{level}', recommend ≥{min_per_level}"
            )

    return errors, warnings, distribution


def validate_query_fixtures(
    fixture_path: str | Path, min_per_level: int = MIN_QUERIES_PER_DIFFICULTY
) -> ValidationResult:
    """Validate retrieval test fixture queries for difficulty coverage.

    Specifically designed for queries.json format in retrieval fixtures.

    Args:
        fixture_path: Path to queries.json fixture file
        min_per_level: Minimum required queries per difficulty level

    Returns:
        ValidationResult with validation status and distribution info

    Example:
        ```python
        result = validate_query_fixtures("tests/smoke/retrieval/fixtures/queries.json")
        if result.is_valid:
            print("Query fixtures are valid!")
        ```

    """
    fixture_path = Path(fixture_path)
    result = ValidationResult(is_valid=True, dataset_name=fixture_path.stem)

    if not fixture_path.exists():
        result.is_valid = False
        result.errors.append(f"Fixture file not found: {fixture_path}")
        return result

    try:
        with open(fixture_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        result.is_valid = False
        result.errors.append(f"Invalid JSON: {e}")
        return result

    queries = data.get("queries", [])
    result.example_count = len(queries)

    if not queries:
        result.warnings.append("Fixture has no queries")
        return result

    # Validate difficulty for queries (using same logic but different field structure)
    distribution: dict[str, int] = dict.fromkeys(VALID_DIFFICULTY_LEVELS, 0)

    for query in queries:
        query_id = query.get("id", "unknown")
        difficulty = query.get("difficulty")

        if difficulty is None:
            result.errors.append(f"{query_id}: Missing difficulty field")
            result.is_valid = False
        elif difficulty not in VALID_DIFFICULTY_LEVELS:
            result.errors.append(
                f"{query_id}: Invalid difficulty '{difficulty}', "
                f"must be one of: {sorted(VALID_DIFFICULTY_LEVELS)}"
            )
            result.is_valid = False
        else:
            distribution[difficulty] += 1

    # Check distribution coverage
    for level, count in distribution.items():
        if count == 0:
            result.warnings.append(f"No queries with difficulty='{level}'")
        elif count < min_per_level:
            result.warnings.append(
                f"Only {count} queries with difficulty='{level}', recommend ≥{min_per_level}"
            )

    # Add distribution summary to warnings for visibility
    dist_summary = ", ".join(f"{k}: {v}" for k, v in sorted(distribution.items()))
    result.warnings.append(f"Distribution: {dist_summary}")

    return result


# CLI entry point
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate evaluation datasets against v2.0 schema")
    parser.add_argument("--dataset", type=str, help="Path to single dataset file")
    parser.add_argument("--directory", type=str, help="Path to directory of datasets")
    parser.add_argument("--schema", type=str, help="Path to schema file (optional)")
    parser.add_argument("--output", type=str, help="Write report to file")
    parser.add_argument("--recursive", action="store_true", help="Search subdirectories")

    args = parser.parse_args()

    if args.dataset:
        # Validate single dataset
        result = validate_dataset(args.dataset, schema_path=args.schema)
        report = generate_validation_report({Path(args.dataset).name: result})
    elif args.directory:
        # Validate directory
        results = validate_directory(args.directory, recursive=args.recursive)
        report = generate_validation_report(results)
    else:
        parser.error("Must specify --dataset or --directory")
        sys.exit(1)

    # Output report
    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        print(report)

    # Exit with error code if any validation failed
    if args.directory:
        if any(not r.is_valid for r in results.values()):
            sys.exit(1)
    elif not result.is_valid:
        sys.exit(1)
