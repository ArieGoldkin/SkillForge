#!/usr/bin/env python3
"""Regenerate high-quality agent examples from golden dataset artifacts.

This script addresses the root cause of the -4.5% few-shot regression:
AgentExample outputs were storing metadata (e.g., {"complexity": "intermediate"})
instead of actual analysis outputs that match G-Eval rubric expectations.

Solution: Run actual agents on golden artifact content and store their real outputs.

Research basis:
- Cleanlab.ai: Data-centric AI improves few-shot accuracy by 12%+
- DSPy: Bootstrap optimization selects best examples based on metrics
- Self-consistency: 15-25% accuracy improvement through majority voting

Usage:
    # Dry run - see what would be generated
    poetry run python scripts/regenerate_examples_from_artifacts.py --dry-run

    # Generate for specific agent type
    poetry run python scripts/regenerate_examples_from_artifacts.py --agent-type tech_comparator

    # Full regeneration with quality filtering
    poetry run python scripts/regenerate_examples_from_artifacts.py --update-db --min-quality 0.70

    # Use self-consistency for higher quality (3x cost)
    poetry run python scripts/regenerate_examples_from_artifacts.py --self-consistency --update-db
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.domains.analysis.workflows.agents.research_analyst import RESEARCH_ANALYST_PROMPT
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from sqlalchemy import delete

from app.core.logging import get_logger
from app.db.models.agent_example import AgentExample
from app.db.session import get_session_factory
from app.domains.analysis.schemas.agents.code_quality_critic import CodeQualityReview
from app.domains.analysis.schemas.agents.implementation_planner import ImplementationPlan
from app.domains.analysis.schemas.agents.learning_path import LearningPath
from app.domains.analysis.schemas.agents.performance_analyst import PerformanceAnalysis
from app.domains.analysis.schemas.agents.research_analyst import ResearchAnalysis
from app.domains.analysis.schemas.agents.security_auditor import SecurityAudit

# Import agent schemas and prompts
from app.domains.analysis.schemas.agents.tech_comparator import TechComparison
from app.domains.analysis.workflows.agents.base import create_structured_agent
from app.domains.analysis.workflows.agents.code_quality_critic import (
    CODE_QUALITY_CRITIC_PROMPT,
)
from app.domains.analysis.workflows.agents.implementation_planner import (
    IMPLEMENTATION_PLANNER_PROMPT,
)
from app.domains.analysis.workflows.agents.learning_path import LEARNING_PATH_PROMPT
from app.domains.analysis.workflows.agents.performance_analyst import PERFORMANCE_ANALYST_PROMPT
from app.domains.analysis.workflows.agents.security_auditor import SECURITY_AUDITOR_PROMPT

# Import prompts
from app.domains.analysis.workflows.agents.tech_comparator import TECH_COMPARATOR_PROMPT
from app.shared.services.g_eval import g_eval_score
from app.shared.services.g_eval.cost_tracker import GEvalCostTracker

logger = get_logger(__name__)

# ============================================================================
# Agent Configuration
# ============================================================================


@dataclass
class AgentConfig:
    """Configuration for an agent type."""

    prompt: str
    schema: type[BaseModel]
    content_types: list[str]  # Which content types this agent handles


@dataclass
class ContentSignals:
    """Content signals that indicate suitability for an agent.

    Issue #299-304: Content filtering to improve HQ rates.
    Research: tech_comparator needs comparison content (2% of dataset → 80% HQ when filtered)
              research_analyst needs research content (3% of dataset → 60% HQ when filtered)
    """

    # Keywords to search for in title (case-insensitive)
    title_keywords: list[str] = field(default_factory=list)
    # Keywords to search for in content (case-insensitive)
    content_keywords: list[str] = field(default_factory=list)
    # Minimum number of keyword matches required
    min_matches: int = 1
    # If True, agent works well on ANY content (no filtering needed)
    universal: bool = False


# Content signals for agents that need specific content types
# Issue #299-304: Tightened criteria after initial testing showed 45% pass rate was too lenient
AGENT_CONTENT_SIGNALS: dict[str, ContentSignals] = {
    "tech_comparator": ContentSignals(
        # Title keywords are strong indicators - any match is sufficient
        title_keywords=["vs", "versus", "comparison", "compare"],
        # Content keywords require multiple matches (weak signals individually)
        content_keywords=[
            "compared to",
            "versus",
            "pros and cons",
            "trade-off",
            "better than",
            "worse than",
            "advantages over",
            "disadvantages of",
        ],
        min_matches=2,  # Increased from 1 - need stronger evidence of comparison
        universal=False,
    ),
    "research_analyst": ContentSignals(
        title_keywords=["survey", "study", "research", "evaluation", "benchmark"],
        content_keywords=[
            "methodology",
            "findings",
            "results show",
            "study found",
            "sample size",
            "participants",
            "experiment",
            "hypothesis",
            "statistical significance",
        ],
        min_matches=2,  # Needs stronger signals
        universal=False,
    ),
    # These agents work well on most content
    "security_auditor": ContentSignals(universal=True),
    "implementation_planner": ContentSignals(universal=True),
    "performance_analyst": ContentSignals(universal=True),
    "code_reviewer": ContentSignals(universal=True),
    "learning_path": ContentSignals(universal=True),
}


def check_content_signals(
    artifact: GoldenArtifact,
    agent_type: str,
) -> tuple[bool, int, str]:
    """Check if content has signals suitable for the agent.

    Issue #299-304: Title keywords are strong indicators (count as 2 matches).
    Content keywords are weaker and need multiple matches.

    Args:
        artifact: Golden artifact to check
        agent_type: Agent type to check compatibility

    Returns:
        Tuple of (is_suitable, match_count, reason)

    """
    signals = AGENT_CONTENT_SIGNALS.get(agent_type)

    # No signals defined = universal
    if not signals or signals.universal:
        return True, 0, "Agent works on all content"

    title_lower = artifact.title.lower()
    content_lower = artifact.markdown_content.lower()

    matches = 0
    matched_keywords: list[str] = []

    # Check title keywords - these are STRONG indicators (count as 2 matches)
    for kw in signals.title_keywords:
        if kw.lower() in title_lower:
            matches += 2  # Title match is worth 2 points
            matched_keywords.append(f"TITLE:{kw}")

    # Check content keywords - weaker signals
    for kw in signals.content_keywords:
        if kw.lower() in content_lower:
            matches += 1
            matched_keywords.append(f"content:{kw}")

    is_suitable = matches >= signals.min_matches
    reason = (
        f"Found {matches} signals: {', '.join(matched_keywords[:5])}"
        if matched_keywords
        else f"No signals found (need {signals.min_matches})"
    )

    return is_suitable, matches, reason


AGENT_CONFIGS: dict[str, AgentConfig] = {
    "tech_comparator": AgentConfig(
        prompt=TECH_COMPARATOR_PROMPT,
        schema=TechComparison,
        content_types=["article", "tutorial", "research_paper"],
    ),
    "security_auditor": AgentConfig(
        prompt=SECURITY_AUDITOR_PROMPT,
        schema=SecurityAudit,
        content_types=["article", "tutorial", "repo"],
    ),
    "implementation_planner": AgentConfig(
        prompt=IMPLEMENTATION_PLANNER_PROMPT,
        schema=ImplementationPlan,
        content_types=["tutorial", "article"],
    ),
    "performance_analyst": AgentConfig(
        prompt=PERFORMANCE_ANALYST_PROMPT,
        schema=PerformanceAnalysis,
        content_types=["article", "tutorial", "repo"],
    ),
    # Note: DB stores as "code_reviewer", G-Eval rubric uses "code_reviewer"
    # Schema/prompt file is named code_quality_critic but agent_type is code_reviewer
    "code_reviewer": AgentConfig(
        prompt=CODE_QUALITY_CRITIC_PROMPT,
        schema=CodeQualityReview,
        content_types=["article", "tutorial", "repo"],
    ),
    "research_analyst": AgentConfig(
        prompt=RESEARCH_ANALYST_PROMPT,
        schema=ResearchAnalysis,
        content_types=["article", "research_paper", "tutorial"],
    ),
    "learning_path": AgentConfig(
        prompt=LEARNING_PATH_PROMPT,
        schema=LearningPath,
        content_types=["article", "tutorial", "course"],
    ),
}

# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class GoldenArtifact:
    """Represents a golden dataset artifact."""

    id: str
    analysis_id: str
    markdown_content: str
    title: str
    content_type: str
    topics: list[str]
    complexity: str
    source_url: str


@dataclass
class GeneratedExample:
    """Result of generating an example from an artifact."""

    artifact_id: str
    agent_type: str
    input_summary: str
    input_content_preview: str
    output_example: dict[str, Any]
    quality_score: float
    criteria_scores: dict[str, float]
    reasoning: str
    error: str | None = None


@dataclass
class RegenerationReport:
    """Summary report of the regeneration run."""

    total_artifacts: int
    processed: int
    successful: int
    errors: int
    filtered_out: int  # Issue #299-304: Content not suitable
    avg_quality_score: float
    score_distribution: dict[str, int]
    examples_by_agent: dict[str, int]
    high_quality_count: int  # Score >= 0.70
    results: list[GeneratedExample] = field(default_factory=list)


# ============================================================================
# Golden Dataset Loading
# ============================================================================


def load_golden_artifacts(
    backup_path: Path,
    content_types: list[str] | None = None,
    limit: int | None = None,
) -> list[GoldenArtifact]:
    """Load artifacts from golden dataset backup.

    Args:
        backup_path: Path to golden_dataset_backup.json
        content_types: Filter to specific content types (optional)
        limit: Maximum artifacts to load (optional)

    Returns:
        List of GoldenArtifact objects

    """
    with backup_path.open() as f:
        data = json.load(f)

    # Build analysis ID to metadata mapping
    analysis_map: dict[str, dict[str, Any]] = {}
    for analysis in data["data"]["analyses"]:
        analysis_map[analysis["id"]] = {
            "title": analysis.get("title", ""),
            "content_type": analysis.get("content_type", "article"),
            "url": analysis.get("url", ""),
        }

    artifacts: list[GoldenArtifact] = []

    for artifact in data["data"]["artifacts"]:
        analysis_id = artifact["analysis_id"]
        analysis_info = analysis_map.get(analysis_id, {})

        metadata = artifact.get("artifact_metadata", {})
        content_type = analysis_info.get("content_type", metadata.get("content_type", "article"))

        # Filter by content type if specified
        if content_types and content_type not in content_types:
            continue

        artifacts.append(
            GoldenArtifact(
                id=artifact["id"],
                analysis_id=analysis_id,
                markdown_content=artifact.get("markdown_content", ""),
                title=analysis_info.get("title", metadata.get("document_id", "")),
                content_type=content_type,
                topics=metadata.get("topics", []),
                complexity=metadata.get("complexity", "intermediate"),
                source_url=metadata.get("source_url", analysis_info.get("url", "")),
            )
        )

    # Shuffle for diversity
    random.shuffle(artifacts)

    if limit:
        artifacts = artifacts[:limit]

    logger.info(
        "loaded_golden_artifacts",
        total=len(artifacts),
        content_types=content_types,
        limit=limit,
    )

    return artifacts


# ============================================================================
# Agent Execution
# ============================================================================


def _extract_output_dict(result: Any) -> dict[str, Any] | None:
    """Extract output dict from agent result."""
    if hasattr(result, "model_dump"):
        output: dict[str, Any] = result.model_dump()
        return output
    if isinstance(result, dict):
        if "structured_response" in result:
            resp = result["structured_response"]
            if hasattr(resp, "model_dump"):
                output = resp.model_dump()
                return output
            return dict(resp) if isinstance(resp, dict) else None
        return dict(result)
    return None


async def run_agent_on_artifact(
    artifact: GoldenArtifact,
    agent_type: str,
    use_self_consistency: bool = False,
    n_samples: int = 3,
) -> dict[str, Any] | None:
    """Run an agent on artifact content to generate structured output.

    Args:
        artifact: Golden artifact with markdown content
        agent_type: Type of agent to run
        use_self_consistency: Whether to use multiple samples
        n_samples: Number of samples for self-consistency

    Returns:
        Structured output dict or None on error

    """
    config = AGENT_CONFIGS.get(agent_type)
    if not config:
        logger.warning("unknown_agent_type", agent_type=agent_type)
        return None

    try:
        # Create agent with structured output
        agent = create_structured_agent(
            system_prompt=config.prompt,
            response_schema=config.schema,
        )

        # Build input message with artifact content
        input_content = f"""Analyze the following technical content and provide your structured analysis:

## Content Title: {artifact.title}

## Content Type: {artifact.content_type}

## Topics: {", ".join(artifact.topics)}

## Full Content:

{artifact.markdown_content[:8000]}  # Limit to avoid token overflow
"""

        if use_self_consistency:
            # Generate multiple candidates and pick best
            candidates = []
            for _ in range(n_samples):
                result = await agent.ainvoke({"messages": [HumanMessage(content=input_content)]})
                output = _extract_output_dict(result)
                if output:
                    candidates.append(output)
            return candidates[0] if candidates else None

        # Single invocation
        result = await agent.ainvoke({"messages": [HumanMessage(content=input_content)]})
        return _extract_output_dict(result)

    except Exception as exc:
        logger.exception(
            "agent_execution_failed",
            artifact_id=artifact.id,
            agent_type=agent_type,
            error=str(exc),
        )
        return None


# ============================================================================
# Quality Scoring
# ============================================================================


async def score_generated_example(
    artifact: GoldenArtifact,
    agent_type: str,
    output: dict[str, Any],
) -> tuple[float, dict[str, float], str]:
    """Score a generated example using G-Eval.

    Args:
        artifact: Source artifact
        agent_type: Type of agent that generated the output
        output: Generated structured output

    Returns:
        Tuple of (overall_score, criteria_scores, reasoning)

    """
    try:
        result = await g_eval_score(
            input_content=artifact.markdown_content[:2000],
            output=output,
            agent_type=agent_type,
        )

        criteria_scores = {
            k: v.normalized if hasattr(v, "normalized") else v.score / 5.0
            for k, v in result.criteria_scores.items()
        }

        # Build reasoning from criteria
        reasoning_parts = []
        for k, v in result.criteria_scores.items():
            if hasattr(v, "reasoning") and v.reasoning:
                reasoning_parts.append(f"{k}: {v.reasoning[:100]}")
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "No reasoning"

        return result.overall, criteria_scores, reasoning

    except Exception as exc:
        logger.exception("scoring_failed", artifact_id=artifact.id)
        return 0.0, {}, f"Scoring error: {exc}"


# ============================================================================
# Example Generation Pipeline
# ============================================================================


def select_agent_for_artifact(artifact: GoldenArtifact) -> str | None:
    """Select the most appropriate agent type for an artifact.

    Uses content type and topics to determine which agent should analyze it.
    """
    # Check topics for security-related content
    security_keywords = {"security", "vulnerability", "authentication", "encryption", "owasp"}
    if any(topic.lower() in security_keywords for topic in artifact.topics):
        return "security_auditor"

    # Check topics for comparison content
    comparison_keywords = {"comparison", "vs", "alternative", "benchmark", "evaluation"}
    title_lower = artifact.title.lower()
    if any(kw in title_lower for kw in comparison_keywords):
        return "tech_comparator"

    # Check for implementation/tutorial content
    if artifact.content_type == "tutorial":
        return "implementation_planner"

    # Default to tech_comparator for articles (most common)
    if artifact.content_type in ["article", "research_paper"]:
        return "tech_comparator"

    return None


async def generate_example_from_artifact(
    artifact: GoldenArtifact,
    agent_type: str | None = None,
    use_self_consistency: bool = False,
    skip_content_filtering: bool = False,
) -> GeneratedExample:
    """Generate a high-quality example from a golden artifact.

    Args:
        artifact: Golden artifact to process
        agent_type: Force specific agent type (optional)
        use_self_consistency: Use multiple samples for quality
        skip_content_filtering: Skip content signal checking (default: False)

    Returns:
        GeneratedExample with output and quality score

    """
    # Select agent type if not specified
    if not agent_type:
        agent_type = select_agent_for_artifact(artifact)

    if not agent_type:
        return GeneratedExample(
            artifact_id=artifact.id,
            agent_type="unknown",
            input_summary="",
            input_content_preview="",
            output_example={},
            quality_score=0.0,
            criteria_scores={},
            reasoning="",
            error="Could not determine agent type for artifact",
        )

    # Issue #299-304: Content signal filtering to improve HQ rates
    if not skip_content_filtering:
        is_suitable, match_count, reason = check_content_signals(artifact, agent_type)
        if not is_suitable:
            return GeneratedExample(
                artifact_id=artifact.id,
                agent_type=agent_type,
                input_summary=artifact.title,
                input_content_preview=artifact.markdown_content[:500],
                output_example={},
                quality_score=0.0,
                criteria_scores={},
                reasoning=reason,
                error=f"Content not suitable for {agent_type}: {reason}",
            )

    # Run agent on artifact
    output = await run_agent_on_artifact(
        artifact=artifact,
        agent_type=agent_type,
        use_self_consistency=use_self_consistency,
    )

    if not output:
        return GeneratedExample(
            artifact_id=artifact.id,
            agent_type=agent_type,
            input_summary=artifact.title,
            input_content_preview=artifact.markdown_content[:500],
            output_example={},
            quality_score=0.0,
            criteria_scores={},
            reasoning="",
            error="Agent execution failed",
        )

    # Score the generated output
    quality_score, criteria_scores, reasoning = await score_generated_example(
        artifact=artifact,
        agent_type=agent_type,
        output=output,
    )

    return GeneratedExample(
        artifact_id=artifact.id,
        agent_type=agent_type,
        input_summary=artifact.title,
        input_content_preview=artifact.markdown_content[:2000],
        output_example=output,
        quality_score=quality_score,
        criteria_scores=criteria_scores,
        reasoning=reasoning,
    )


# ============================================================================
# Database Operations
# ============================================================================


async def save_examples_to_database(
    examples: list[GeneratedExample],
    min_quality: float = 0.70,
    replace_existing: bool = False,
) -> int:
    """Save high-quality examples to the database.

    Args:
        examples: List of generated examples
        min_quality: Minimum quality score to save
        replace_existing: Whether to replace existing examples

    Returns:
        Number of examples saved

    """
    # Filter to high quality
    high_quality = [ex for ex in examples if ex.quality_score >= min_quality and not ex.error]

    if not high_quality:
        logger.warning("no_high_quality_examples", min_quality=min_quality)
        return 0

    session_factory = get_session_factory()
    saved = 0

    async with session_factory() as session:
        if replace_existing:
            # Delete existing examples for these agent types
            agent_types = {ex.agent_type for ex in high_quality}
            for agent_type in agent_types:
                stmt = delete(AgentExample).where(AgentExample.agent_type == agent_type)
                await session.execute(stmt)
            logger.info("deleted_existing_examples", agent_types=list(agent_types))

        # Insert new examples - DB generates UUIDs via server_default
        for ex in high_quality:
            example = AgentExample(
                agent_type=ex.agent_type,
                input_summary=ex.input_summary,
                input_content_preview=ex.input_content_preview,
                output_example=ex.output_example,
                quality_score=ex.quality_score,
                is_golden=True,
                content_type="article",  # Default
                difficulty_level="intermediate",
            )
            session.add(example)
            saved += 1

        await session.commit()

    logger.info("saved_examples", count=saved, min_quality=min_quality)
    return saved


# ============================================================================
# Reporting
# ============================================================================


def get_score_bucket(score: float) -> str:
    """Get the score distribution bucket."""
    if score >= 0.9:
        return "0.9-1.0 (excellent)"
    if score >= 0.8:
        return "0.8-0.9 (good)"
    if score >= 0.7:
        return "0.7-0.8 (acceptable)"
    if score >= 0.5:
        return "0.5-0.7 (poor)"
    return "0.0-0.5 (unusable)"


def generate_report(results: list[GeneratedExample]) -> RegenerationReport:
    """Generate a summary report from results."""
    successful = [r for r in results if not r.error]
    errors = [r for r in results if r.error]

    # Issue #299-304: Track content-filtered results separately
    filtered_out = len([r for r in errors if r.error and "Content not suitable" in r.error])
    actual_errors = len(errors) - filtered_out

    avg_quality = sum(r.quality_score for r in successful) / len(successful) if successful else 0.0

    # Score distribution
    distribution: dict[str, int] = {}
    for r in successful:
        bucket = get_score_bucket(r.quality_score)
        distribution[bucket] = distribution.get(bucket, 0) + 1

    # Examples by agent type
    by_agent: dict[str, int] = {}
    for r in successful:
        by_agent[r.agent_type] = by_agent.get(r.agent_type, 0) + 1

    high_quality = len([r for r in successful if r.quality_score >= 0.70])

    return RegenerationReport(
        total_artifacts=len(results),
        processed=len(results),
        successful=len(successful),
        errors=actual_errors,
        filtered_out=filtered_out,
        avg_quality_score=avg_quality,
        score_distribution=distribution,
        examples_by_agent=by_agent,
        high_quality_count=high_quality,
        results=results,
    )


def print_report(report: RegenerationReport) -> None:
    """Print formatted report to console."""
    print("\n" + "=" * 70)
    print("         AGENT EXAMPLE REGENERATION REPORT")
    print("=" * 70)

    print("\n📊 Summary:")
    print(f"   Total artifacts:      {report.total_artifacts}")
    print(f"   Processed:            {report.processed}")
    print(f"   Successful:           {report.successful}")
    print(f"   Filtered out:         {report.filtered_out} (content not suitable)")
    print(f"   Errors:               {report.errors}")
    print(f"   Avg quality score:    {report.avg_quality_score:.3f}")
    print(f"   High quality (≥0.70): {report.high_quality_count}")

    # Show HQ rate for processed vs successful
    if report.successful > 0:
        hq_rate = report.high_quality_count / report.successful * 100
        print(f"   HQ Rate:              {hq_rate:.1f}% of processed")

    print("\n📈 Score Distribution:")
    for bucket, count in sorted(report.score_distribution.items(), reverse=True):
        bar = "█" * count
        print(f"   {bucket:20} | {count:3} | {bar}")

    print("\n🤖 Examples by Agent Type:")
    for agent_type, count in sorted(report.examples_by_agent.items()):
        print(f"   {agent_type:25} | {count:3}")

    # Show top examples
    top_examples = sorted(
        [r for r in report.results if not r.error], key=lambda x: x.quality_score, reverse=True
    )[:5]

    if top_examples:
        print("\n⭐ Top 5 Examples:")
        print("-" * 70)
        for ex in top_examples:
            print(
                f"   {ex.agent_type:20} | Score: {ex.quality_score:.2f} | {ex.input_summary[:40]}..."
            )

    print("\n" + "=" * 70)


def save_report_json(report: RegenerationReport, path: Path) -> None:
    """Save report as JSON for later analysis."""
    hq_rate = report.high_quality_count / report.successful * 100 if report.successful > 0 else 0.0
    data = {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "total_artifacts": report.total_artifacts,
            "processed": report.processed,
            "successful": report.successful,
            "filtered_out": report.filtered_out,
            "errors": report.errors,
            "avg_quality_score": report.avg_quality_score,
            "high_quality_count": report.high_quality_count,
            "hq_rate_percent": hq_rate,
            "score_distribution": report.score_distribution,
            "examples_by_agent": report.examples_by_agent,
        },
        "results": [
            {
                "artifact_id": r.artifact_id,
                "agent_type": r.agent_type,
                "input_summary": r.input_summary,
                "quality_score": r.quality_score,
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


# ============================================================================
# Main Entry Point
# ============================================================================


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Regenerate agent examples from golden dataset artifacts"
    )
    parser.add_argument(
        "--agent-type",
        type=str,
        choices=list(AGENT_CONFIGS.keys()),
        help="Only generate for this agent type",
    )
    parser.add_argument(
        "--content-type",
        type=str,
        action="append",
        help="Filter to specific content types (can repeat)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum artifacts to process",
    )
    parser.add_argument(
        "--min-quality",
        type=float,
        default=0.70,
        help="Minimum quality score to save (default: 0.70)",
    )
    parser.add_argument(
        "--self-consistency",
        action="store_true",
        help="Use self-consistency (3 samples) for higher quality",
    )
    parser.add_argument(
        "--update-db",
        action="store_true",
        help="Save to database (default: dry run)",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Replace existing examples (use with --update-db)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/example_regeneration_report.json",
        help="Output path for JSON report",
    )
    parser.add_argument(
        "--backup-path",
        type=str,
        default="data/golden_dataset_backup.json",
        help="Path to golden dataset backup",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Number of parallel workers (default: 5)",
    )
    parser.add_argument(
        "--skip-content-filtering",
        action="store_true",
        help="Skip content signal filtering (run all agent-artifact combinations)",
    )

    args = parser.parse_args()

    print("\n🔄 Agent Example Regeneration from Golden Artifacts")
    print("=" * 60)
    print(f"   Agent type filter:   {args.agent_type or 'ALL'}")
    print(f"   Content types:       {args.content_type or 'ALL'}")
    print(f"   Limit:               {args.limit or 'None'}")
    print(f"   Min quality:         {args.min_quality}")
    print(f"   Self-consistency:    {args.self_consistency}")
    print(f"   Concurrency:         {args.concurrency} workers")
    print(f"   Content filtering:   {'DISABLED' if args.skip_content_filtering else 'ENABLED'}")
    print(f"   Update database:     {args.update_db}")
    print(f"   Replace existing:    {args.replace_existing}")
    print("=" * 60)

    # Reset cost tracker
    tracker = GEvalCostTracker.get_instance()
    tracker.reset()

    # Load golden artifacts
    backup_path = Path(args.backup_path)
    if not backup_path.exists():
        print(f"\n❌ Backup file not found: {backup_path}")
        return

    artifacts = load_golden_artifacts(
        backup_path=backup_path,
        content_types=args.content_type,
        limit=args.limit,
    )

    print(f"\n📦 Loaded {len(artifacts)} artifacts to process")

    if not artifacts:
        print("No artifacts found matching criteria. Exiting.")
        return

    # Process artifacts in PARALLEL using semaphore for concurrency control
    results: list[GeneratedExample] = []
    semaphore = asyncio.Semaphore(args.concurrency)
    completed = 0
    high_quality_found = 0

    async def process_with_semaphore(artifact: GoldenArtifact) -> GeneratedExample:
        """Process single artifact with semaphore-limited concurrency."""
        nonlocal completed, high_quality_found
        async with semaphore:
            example = await generate_example_from_artifact(
                artifact=artifact,
                agent_type=args.agent_type,
                use_self_consistency=args.self_consistency,
                skip_content_filtering=args.skip_content_filtering,
            )
            completed += 1
            if example.quality_score >= args.min_quality:
                high_quality_found += 1
            print(
                f"\r   ⚡ Processed {completed}/{len(artifacts)} | "
                f"HQ: {high_quality_found} | "
                f"Latest: {artifact.title[:30]:30} → {example.quality_score:.2f}",
                end="",
                flush=True,
            )
            return example

    # Run all tasks in parallel (semaphore limits actual concurrency)
    print(f"\n   🚀 Running {args.concurrency} parallel workers...")
    tasks = [process_with_semaphore(artifact) for artifact in artifacts]
    results = await asyncio.gather(*tasks)

    print()  # New line after progress

    # Generate report
    report = generate_report(results)
    print_report(report)

    # Print cost summary
    cost_summary = tracker.get_session_summary()
    print("\n💰 Cost Summary:")
    print(f"   Total evaluations: {cost_summary.total_evaluations}")
    print(f"   Input tokens:      {cost_summary.total_input_tokens:,}")
    print(f"   Output tokens:     {cost_summary.total_output_tokens:,}")
    print(f"   Estimated cost:    ${cost_summary.total_cost:.4f}")

    # Save JSON report
    save_report_json(report, Path(args.output))

    # Save to database if requested
    if args.update_db:
        saved = await save_examples_to_database(
            examples=results,
            min_quality=args.min_quality,
            replace_existing=args.replace_existing,
        )
        print(f"\n✅ Saved {saved} high-quality examples to database")
    else:
        high_quality = len(
            [r for r in results if r.quality_score >= args.min_quality and not r.error]
        )
        print(f"\n💡 {high_quality} examples would be saved. Run with --update-db to save.")


if __name__ == "__main__":
    asyncio.run(main())
