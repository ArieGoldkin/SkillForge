#!/usr/bin/env python3
"""Recalculate quality scores for agent examples using G-Eval.

This script uses G-Eval to score all agent examples in the database,
replacing the default 1.0 scores with real quality assessments.

Research basis:
- Cleanlab.ai: Data quality curation improves few-shot accuracy by 12%+
- DSPy: Bootstrap optimization selects best examples based on metrics
- PromptingGuide.ai: Quality > quantity for few-shot examples

Usage:
    # Dry run (no DB updates)
    poetry run python scripts/recalculate_example_quality.py --dry-run

    # Score specific agent type
    poetry run python scripts/recalculate_example_quality.py --agent-type tech_comparator

    # Full recalculation with DB updates
    poetry run python scripts/recalculate_example_quality.py --update-db

    # Score only examples with default 1.0 score
    poetry run python scripts/recalculate_example_quality.py --only-defaults --update-db
"""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update

from app.core.logging import get_logger
from app.db.session import get_session_factory
from app.models.agent_example import AgentExample
from app.shared.services.g_eval import g_eval_score
from app.shared.services.g_eval.cost_tracker import GEvalCostTracker

logger = get_logger(__name__)


@dataclass
class ScoringResult:
    """Result of scoring a single example."""

    example_id: str
    agent_type: str
    old_score: float
    new_score: float
    criteria_scores: dict[str, float]
    reasoning: str
    error: str | None = None


@dataclass
class ScoringReport:
    """Summary report of scoring run."""

    total_examples: int
    scored_successfully: int
    errors: int
    avg_old_score: float
    avg_new_score: float
    score_distribution: dict[str, int]  # e.g., {"0.9-1.0": 5, "0.8-0.9": 3, ...}
    low_quality_examples: list[ScoringResult]  # Examples with score < 0.70
    results: list[ScoringResult]


async def score_example(example: AgentExample) -> ScoringResult:
    """Score a single agent example using G-Eval."""
    try:
        # Create synthetic input content from the example's input_summary
        input_content = example.input_content_preview or example.input_summary or ""

        if not input_content:
            return ScoringResult(
                example_id=str(example.id),
                agent_type=example.agent_type,
                old_score=example.quality_score,
                new_score=0.0,
                criteria_scores={},
                reasoning="No input content available",
                error="Missing input content",
            )

        if not example.output_example:
            return ScoringResult(
                example_id=str(example.id),
                agent_type=example.agent_type,
                old_score=example.quality_score,
                new_score=0.0,
                criteria_scores={},
                reasoning="No output example available",
                error="Missing output example",
            )

        # Run G-Eval scoring
        result = await g_eval_score(
            input_content=input_content,
            output=example.output_example,
            agent_type=example.agent_type,
        )

        # Extract criteria scores as simple floats
        criteria_scores_dict = {
            k: v.normalized if hasattr(v, "normalized") else float(v)
            for k, v in result.criteria_scores.items()
        }

        # Extract reasoning from criteria scores
        reasoning_parts = []
        for k, v in result.criteria_scores.items():
            if hasattr(v, "reasoning") and v.reasoning:
                reasoning_parts.append(f"{k}: {v.reasoning[:50]}")
        reasoning_text = "; ".join(reasoning_parts) if reasoning_parts else "No reasoning"

        return ScoringResult(
            example_id=str(example.id),
            agent_type=example.agent_type,
            old_score=example.quality_score,
            new_score=result.overall,  # Use 'overall' not 'weighted_score'
            criteria_scores=criteria_scores_dict,
            reasoning=reasoning_text,
        )

    except Exception as exc:
        logger.exception(f"Error scoring example {example.id}")
        return ScoringResult(
            example_id=str(example.id),
            agent_type=example.agent_type,
            old_score=example.quality_score,
            new_score=example.quality_score,  # Keep old score on error
            criteria_scores={},
            reasoning="",
            error=str(exc),
        )


def get_score_bucket(score: float) -> str:
    """Get the score distribution bucket."""
    if score >= 0.9:
        return "0.9-1.0 (excellent)"
    elif score >= 0.8:
        return "0.8-0.9 (good)"
    elif score >= 0.7:
        return "0.7-0.8 (acceptable)"
    elif score >= 0.5:
        return "0.5-0.7 (poor)"
    else:
        return "0.0-0.5 (unusable)"


def generate_report(results: list[ScoringResult]) -> ScoringReport:
    """Generate a summary report from scoring results."""
    successful = [r for r in results if r.error is None]
    errors = [r for r in results if r.error is not None]

    # Calculate averages
    avg_old = sum(r.old_score for r in results) / len(results) if results else 0.0
    avg_new = (
        sum(r.new_score for r in successful) / len(successful) if successful else 0.0
    )

    # Score distribution
    distribution: dict[str, int] = {}
    for r in successful:
        bucket = get_score_bucket(r.new_score)
        distribution[bucket] = distribution.get(bucket, 0) + 1

    # Low quality examples (< 0.70)
    low_quality = [r for r in successful if r.new_score < 0.70]

    return ScoringReport(
        total_examples=len(results),
        scored_successfully=len(successful),
        errors=len(errors),
        avg_old_score=avg_old,
        avg_new_score=avg_new,
        score_distribution=distribution,
        low_quality_examples=low_quality,
        results=results,
    )


def print_report(report: ScoringReport) -> None:
    """Print a formatted report to console."""
    print("\n" + "=" * 70)
    print("              AGENT EXAMPLE QUALITY SCORING REPORT")
    print("=" * 70)

    print("\n📊 Summary:")
    print(f"   Total examples:     {report.total_examples}")
    print(f"   Scored successfully: {report.scored_successfully}")
    print(f"   Errors:             {report.errors}")
    print(f"   Avg OLD score:      {report.avg_old_score:.3f}")
    print(f"   Avg NEW score:      {report.avg_new_score:.3f}")
    score_change = report.avg_new_score - report.avg_old_score
    print(f"   Score change:       {score_change:+.3f}")

    print("\n📈 Score Distribution (NEW scores):")
    for bucket, count in sorted(report.score_distribution.items(), reverse=True):
        bar = "█" * count
        print(f"   {bucket:20} | {count:3} | {bar}")

    if report.low_quality_examples:
        print(f"\n⚠️  Low Quality Examples (< 0.70): {len(report.low_quality_examples)}")
        print("-" * 70)
        for r in report.low_quality_examples[:10]:  # Show top 10
            print(f"   ID: {r.example_id[:8]}... | Type: {r.agent_type:20} | Score: {r.new_score:.2f}")
        if len(report.low_quality_examples) > 10:
            print(f"   ... and {len(report.low_quality_examples) - 10} more")

    print("\n" + "=" * 70)


def save_report_json(report: ScoringReport, path: Path) -> None:
    """Save report as JSON for later analysis."""
    data = {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "total_examples": report.total_examples,
            "scored_successfully": report.scored_successfully,
            "errors": report.errors,
            "avg_old_score": report.avg_old_score,
            "avg_new_score": report.avg_new_score,
            "score_distribution": report.score_distribution,
        },
        "low_quality_examples": [
            {
                "id": r.example_id,
                "agent_type": r.agent_type,
                "old_score": r.old_score,
                "new_score": r.new_score,
                "criteria_scores": r.criteria_scores,
            }
            for r in report.low_quality_examples
        ],
        "all_results": [
            {
                "id": r.example_id,
                "agent_type": r.agent_type,
                "old_score": r.old_score,
                "new_score": r.new_score,
                "criteria_scores": r.criteria_scores,
                "error": r.error,
            }
            for r in report.results
        ],
    }

    path.parent.mkdir(exist_ok=True)
    with path.open("w") as f:
        json.dump(data, f, indent=2)

    print(f"\n📄 Report saved to: {path}")


async def update_database_scores(
    results: list[ScoringResult], dry_run: bool = True
) -> int:
    """Update quality scores in the database."""
    if dry_run:
        print("\n🔍 DRY RUN - No database updates performed")
        return 0

    session_factory = get_session_factory()
    updated = 0

    async with session_factory() as session:
        for result in results:
            if result.error is None:
                stmt = (
                    update(AgentExample)
                    .where(AgentExample.id == result.example_id)
                    .values(quality_score=result.new_score)
                )
                await session.execute(stmt)
                updated += 1

        await session.commit()

    print(f"\n✅ Updated {updated} examples in database")
    return updated


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Recalculate quality scores for agent examples using G-Eval"
    )
    parser.add_argument(
        "--agent-type",
        type=str,
        help="Only score examples of this agent type",
    )
    parser.add_argument(
        "--only-defaults",
        action="store_true",
        help="Only score examples with default 1.0 quality score",
    )
    parser.add_argument(
        "--update-db",
        action="store_true",
        help="Update database with new scores (default: dry run)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without updating database (default behavior)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of examples to score (for testing)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/quality_scoring_report.json",
        help="Output path for JSON report",
    )

    args = parser.parse_args()

    # Determine if we should update DB
    update_db = args.update_db and not args.dry_run

    print("\n🔄 Agent Example Quality Score Recalculation")
    print("=" * 50)
    print(f"   Agent type filter: {args.agent_type or 'ALL'}")
    print(f"   Only defaults:     {args.only_defaults}")
    print(f"   Update database:   {update_db}")
    print(f"   Limit:             {args.limit or 'None'}")
    print("=" * 50)

    # Reset cost tracker
    tracker = GEvalCostTracker.get_instance()
    tracker.reset()

    # Load examples from database
    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(AgentExample)

        if args.agent_type:
            stmt = stmt.where(AgentExample.agent_type == args.agent_type)

        if args.only_defaults:
            # Score >= 0.99 catches the 1.0 defaults
            stmt = stmt.where(AgentExample.quality_score >= 0.99)

        if args.limit:
            stmt = stmt.limit(args.limit)

        result = await session.execute(stmt)
        examples = list(result.scalars().all())

    print(f"\n📦 Loaded {len(examples)} examples to score")

    if not examples:
        print("No examples found matching criteria. Exiting.")
        return

    # Score all examples
    results: list[ScoringResult] = []
    for i, example in enumerate(examples, 1):
        print(f"\r   Scoring {i}/{len(examples)}: {example.agent_type[:20]:20}...", end="", flush=True)
        result = await score_example(example)
        results.append(result)

    print()  # New line after progress

    # Generate and print report
    report = generate_report(results)
    print_report(report)

    # Print cost summary
    cost_summary = tracker.get_session_summary()
    print("\n💰 Cost Summary:")
    print(f"   Total evaluations: {cost_summary.total_evaluations}")
    print(f"   Input tokens:      {cost_summary.total_input_tokens:,}")
    print(f"   Output tokens:     {cost_summary.total_output_tokens:,}")
    print(f"   Cached tokens:     {cost_summary.total_cached_tokens:,}")
    print(f"   Estimated cost:    ${cost_summary.total_cost:.4f}")

    # Save JSON report
    save_report_json(report, Path(args.output))

    # Update database if requested
    if update_db:
        await update_database_scores(results, dry_run=False)
    else:
        print("\n💡 To update the database, run with --update-db flag")


if __name__ == "__main__":
    asyncio.run(main())
