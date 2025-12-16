#!/usr/bin/env python3
"""CLI entrypoint for running evaluation pipeline.

This script is designed for CI/CD integration and provides:
- Command-line interface for running evaluations
- Output to JSON/Markdown formats
- Proper exit codes for CI (0=pass, 1=fail)
- Regression detection against baseline

Usage:
    # Run all difficulties, output to JSON
    python scripts/run_evaluation.py --output results/current.json

    # Run specific difficulties
    python scripts/run_evaluation.py --datasets easy medium --output results.json

    # Generate markdown report
    python scripts/run_evaluation.py --format markdown --output report.md

    # Compare against baseline (for PR checks)
    python scripts/run_evaluation.py --output current.json --baseline baseline.json

    # Fail on warnings (strict mode)
    python scripts/run_evaluation.py --fail-on-warn --output results.json

Environment Variables:
    OPENAI_API_KEY: Required for embedding generation
    DATABASE_URL: PostgreSQL connection string (default: from .env)
    EVALUATION_BASELINE: Default baseline file path

Exit Codes:
    0: All evaluations passed
    1: Evaluations failed or regressions detected
    2: Configuration/setup error
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

# Add backend to path for running from scripts directory
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config import get_settings
from app.core.logging import get_logger
from app.evaluation.metrics import check_regression
from app.evaluation.pipeline import Difficulty, EvaluationRunner, ThresholdStatus

if TYPE_CHECKING:
    from app.evaluation.pipeline import PipelineResult

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run evaluation pipeline with threshold checking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=[d.value for d in Difficulty],
        help="Specific difficulties to evaluate (default: all)",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation_results.json"),
        help="Output file path (default: evaluation_results.json)",
    )

    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format (default: json)",
    )

    parser.add_argument(
        "--baseline",
        type=Path,
        help="Baseline results for regression detection",
    )

    parser.add_argument(
        "--fail-on-warn",
        action="store_true",
        help="Exit with error on warnings (strict mode)",
    )

    parser.add_argument(
        "--regression-threshold",
        type=float,
        default=0.05,
        help="Regression detection threshold (default: 0.05 = 5%%)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--expanded",
        action="store_true",
        help="Use expanded fixtures (queries_expanded.json)",
    )

    return parser.parse_args()


async def run_evaluation(
    difficulties: list[Difficulty] | None = None,
    expanded: bool = False,
) -> PipelineResult:
    """Run evaluation pipeline.

    Args:
        difficulties: List of difficulties to evaluate (None = all)
        expanded: Use expanded fixtures (queries_expanded.json)

    Returns:
        PipelineResult with evaluation results

    """
    import json

    from sqlalchemy.ext.asyncio import create_async_engine

    from app.db.session import AsyncSessionLocal, get_async_database_url
    from app.services.embeddings import EmbeddingService
    from app.services.embeddings.deterministic import DeterministicEmbeddingService

    settings = get_settings()
    force_deterministic = (os.environ.get("SKILLFORGE_DETERMINISTIC_EMBEDDINGS") or "").lower() in {
        "1",
        "true",
        "yes",
    }

    # Determine fixtures directory and queries file
    fixtures_dir = Path(__file__).parent.parent / "tests/smoke/retrieval/fixtures"
    queries_file = "queries_expanded.json" if expanded else "queries.json"
    queries_path = fixtures_dir / queries_file

    if not queries_path.exists():
        logger.error(f"Queries file not found: {queries_path}")
        print(f"Error: Queries file not found: {queries_path}", file=sys.stderr)
        sys.exit(2)

    # Load queries
    with queries_path.open() as f:
        data = json.load(f)

    queries = data.get("queries", data) if isinstance(data, dict) else data
    logger.info(f"Loaded {len(queries)} queries from {queries_file}")

    # Create database session with async URL
    async_url = get_async_database_url()
    engine = create_async_engine(async_url, echo=False)

    try:
        async with AsyncSessionLocal() as session:
            # Create services (default to deterministic when API key is absent)
            if force_deterministic or not settings.OPENAI_API_KEY:
                embedding_service = DeterministicEmbeddingService()
            else:
                embedding_service = EmbeddingService()

            # Run evaluation
            runner = EvaluationRunner(
                session=session,
                embedding_service=embedding_service,
            )

            # Load queries into runner
            runner._queries = queries

            logger.info("Starting evaluation pipeline", difficulties=difficulties)
            result = await runner.run_all(difficulties=difficulties)

            return result

    finally:
        await engine.dispose()


def write_output(result: PipelineResult, output_path: Path, format: str) -> None:
    """Write evaluation results to file.

    Args:
        result: Pipeline result to write
        output_path: Path to output file
        format: Output format (json or markdown)

    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    content = result.to_json() if format == "json" else result.to_markdown()

    with output_path.open("w") as f:
        f.write(content)

    logger.info(f"Results written to {output_path}")


def check_status(
    result: PipelineResult,
    fail_on_warn: bool = False,
) -> bool:
    """Check if evaluation passed based on status.

    Args:
        result: Pipeline result to check
        fail_on_warn: If True, warnings are treated as failures

    Returns:
        True if passed, False if failed

    """
    if result.overall_status == ThresholdStatus.FAIL:
        logger.error("Evaluation FAILED", status=result.overall_status.value)
        return False

    if result.overall_status == ThresholdStatus.WARN:
        if fail_on_warn:
            logger.error(
                "Evaluation FAILED (warnings in strict mode)", status=result.overall_status.value
            )
            return False
        logger.warning("Evaluation passed with WARNINGS", status=result.overall_status.value)
        return True

    logger.info("Evaluation PASSED", status=result.overall_status.value)
    return True


async def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0=success, 1=failure, 2=error)

    """
    args = parse_args()

    # Configure logging
    if args.verbose:
        import logging

        logging.getLogger("app").setLevel(logging.DEBUG)

    # Parse difficulties
    difficulties = None
    if args.datasets:
        try:
            difficulties = [Difficulty(d) for d in args.datasets]
        except ValueError:
            logger.exception("Invalid difficulty")
            return 2

    # Run evaluation
    try:
        result = await run_evaluation(difficulties, expanded=args.expanded)
    except Exception as e:
        logger.error("Evaluation failed", error=str(e), exc_info=True)
        print(f"Error: {e}", file=sys.stderr)
        return 2

    # Write output
    try:
        write_output(result, args.output, args.format)
    except Exception as e:
        logger.exception("Failed to write output", error=str(e))
        print(f"Error writing output: {e}", file=sys.stderr)
        return 2

    # Check for regressions if baseline provided
    if args.baseline:
        try:
            regression_report = check_regression(
                current_path=args.output,
                baseline_path=args.baseline,
                threshold=args.regression_threshold,
            )

            # Write regression report
            regression_path = args.output.parent / f"{args.output.stem}_regression.md"
            with regression_path.open("w") as f:
                f.write(regression_report.to_markdown())

            logger.info(f"Regression report written to {regression_path}")

            if regression_report.has_regressions:
                logger.error("Regressions detected")
                print("\n" + regression_report.to_markdown())
                return 1

        except Exception as e:
            logger.exception("Regression check failed", error=str(e))
            print(f"Warning: Regression check failed: {e}", file=sys.stderr)
            # Continue - don't fail on regression check errors

    # Check status
    if not check_status(result, fail_on_warn=args.fail_on_warn):
        print("\n" + result.to_markdown())
        return 1

    # Success
    print(f"\n✅ Evaluation passed: {result.total_passed}/{result.total_examples} examples")
    print(f"📊 Results: {args.output}")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
