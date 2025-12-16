#!/usr/bin/env python3
"""Quality comparison testing for Few-Shot Prompting (Phase 1, Week 3).

Runs golden dataset examples through control (baseline) and treatment (few-shot)
variants to measure quality improvement. Generates comprehensive report with
statistical analysis and sample comparisons.

Target: Validate 15-25% quality improvement from few-shot prompting

Strategy:
1. Load golden dataset examples (97 total)
2. Sample 10-15 diverse examples per agent type
3. Run control variant (no few-shot examples)
4. Run treatment variant (with few-shot examples)
5. Compare quality scores across multiple dimensions
6. Generate statistical report with recommendations

Usage:
    # Full comparison test
    poetry run python scripts/compare_few_shot_quality.py

    # Test specific agent type
    poetry run python scripts/compare_few_shot_quality.py --agent-type tech_comparator

    # Limit sample size for quick test
    poetry run python scripts/compare_few_shot_quality.py --sample-size 5

    # Dry run (no actual LLM calls)
    poetry run python scripts/compare_few_shot_quality.py --dry-run

Requirements:
    - Golden dataset seeded (97 examples)
    - Agent examples seeded (113 examples)
    - OPENAI_API_KEY environment variable set
    - Database accessible

Output:
    - Console progress output
    - docs/phase1-quality-comparison-report.md
    - data/phase1-quality-comparison-results.json

"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from sqlalchemy import select
from tqdm.asyncio import tqdm  # type: ignore[import-untyped]

sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

from app.core.logging import get_logger  # noqa: E402
from app.db.session import get_session_factory  # noqa: E402
from app.domains.analysis.workflows.agents.base import create_structured_agent  # noqa: E402
from app.domains.analysis.workflows.agents.schemas.code_reviewer import (  # noqa: E402
    CodeReview,
)
from app.domains.analysis.workflows.agents.schemas.implementation_planner import (  # noqa: E402
    ImplementationPlan,
)
from app.domains.analysis.workflows.agents.schemas.learning_path import (  # noqa: E402
    LearningPath,
)
from app.domains.analysis.workflows.agents.schemas.performance_analyst import (  # noqa: E402
    PerformanceAnalysis,
)
from app.domains.analysis.workflows.agents.schemas.research_analyst import (  # noqa: E402
    ResearchAnalysis,
)
from app.domains.analysis.workflows.agents.schemas.security_auditor import (  # noqa: E402
    SecurityAudit,
)
from app.domains.analysis.workflows.agents.schemas.tech_comparator import (  # noqa: E402
    TechComparison,
)
from app.models.agent_example import AgentExample  # noqa: E402
from app.shared.services.agents.few_shot_factory import create_few_shot_agent  # noqa: E402
from app.shared.services.embeddings.service import EmbeddingService  # noqa: E402
from app.shared.services.prompts.chain_of_thought import get_cot_prompt  # noqa: E402
from app.shared.services.quality_scorer import QualityScore, score_output_quality  # noqa: E402

logger = get_logger(__name__)

# Schema mapping for agent types
AGENT_SCHEMAS: dict[str, type | None] = {
    "tech_comparator": TechComparison,
    "security_auditor": SecurityAudit,
    "implementation_planner": ImplementationPlan,
    "research_analyst": ResearchAnalysis,
    "code_reviewer": CodeReview,
    "learning_path": LearningPath,
    "performance_analyst": PerformanceAnalysis,
    "dependency_mapper": None,  # Not yet implemented
    "trend_validator": None,
}

# System prompts (simplified for testing)
AGENT_PROMPTS = {
    "tech_comparator": "You are an expert technology comparator. Analyze technologies and provide comprehensive comparisons.",
    "security_auditor": "You are a security expert. Identify vulnerabilities and recommend mitigations.",
    "implementation_planner": "You are an implementation guide expert. Create detailed step-by-step plans.",
    "performance_analyst": "You are a performance optimization expert. Analyze performance characteristics.",
    "code_reviewer": "You are a code quality expert. Review code and suggest improvements.",
    "learning_path": "You are a learning path designer. Create structured learning paths.",
    "research_analyst": "You are a research analyst. Analyze research papers and technical documents.",
}


@dataclass
class ComparisonResult:
    """Result of comparing control vs treatment vs CoT for a single example."""

    example_id: str
    agent_type: str
    input_summary: str
    control_score: QualityScore
    treatment_score: QualityScore
    cot_score: QualityScore  # Chain-of-Thought variant
    improvement_pct: float  # Few-shot vs control
    cot_improvement_pct: float  # CoT vs control
    control_time_ms: float
    treatment_time_ms: float
    cot_time_ms: float
    control_output: dict[str, Any] | None = None
    treatment_output: dict[str, Any] | None = None
    cot_output: dict[str, Any] | None = None


@dataclass
class AgentTypeResults:
    """Aggregated results for a single agent type."""

    agent_type: str
    sample_count: int
    control_avg_score: float
    treatment_avg_score: float
    cot_avg_score: float  # CoT average
    improvement_pct: float  # Few-shot improvement
    cot_improvement_pct: float  # CoT improvement
    improvement_std: float
    cot_improvement_std: float
    best_improvement: ComparisonResult | None
    worst_improvement: ComparisonResult | None
    best_cot_improvement: ComparisonResult | None
    control_avg_tokens: float
    treatment_avg_tokens: float
    cot_avg_tokens: float
    token_increase_pct: float


async def load_agent_examples(
    agent_type: str | None,
    sample_size: int,
) -> list[AgentExample]:
    """Load agent examples from database.

    Args:
        agent_type: Specific agent type to load (None for all)
        sample_size: Maximum examples per agent type

    Returns:
        List of agent examples

    """
    factory = get_session_factory()
    async with factory() as session:
        query = select(AgentExample)

        if agent_type:
            query = query.where(AgentExample.agent_type == agent_type)

        # Order by quality score descending to get best examples
        query = query.order_by(AgentExample.quality_score.desc())

        result = await session.execute(query)
        examples = list(result.scalars().all())

        # Sample per agent type
        if not agent_type:
            sampled = []
            by_type = defaultdict(list)
            for ex in examples:
                by_type[ex.agent_type].append(ex)

            for _, type_examples in by_type.items():
                sampled.extend(type_examples[:sample_size])

            return sampled

        return examples[:sample_size]


async def run_control_variant(
    example: AgentExample,
    dry_run: bool = False,
) -> tuple[dict[str, Any] | None, float]:
    """Run control variant (baseline, no few-shot).

    Args:
        example: Agent example to test
        dry_run: If True, return mock output without LLM call

    Returns:
        Tuple of (output_dict, time_ms)

    """
    start_time = time.perf_counter()

    if dry_run:
        # Mock output for testing
        mock_output = {
            "primary_tech": "MockTech",
            "alternatives": ["Alt1", "Alt2"],
            "recommendation": "This is a mock recommendation for testing.",
            "confidence_score": 0.75,
        }
        elapsed_ms = 100  # Mock timing
        return mock_output, elapsed_ms

    # Use baseline agent (no few-shot examples)
    try:
        # Get schema for this agent type
        schema_class = AGENT_SCHEMAS.get(example.agent_type)
        if schema_class is None:
            logger.warning(
                "agent_type_no_schema",
                agent_type=example.agent_type,
                example_id=str(example.id),
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return None, elapsed_ms

        # Create baseline agent directly (bypassing few-shot factory)
        agent = create_structured_agent(
            system_prompt=AGENT_PROMPTS.get(example.agent_type, "You are an AI assistant."),
            response_schema=schema_class,
        )

        # Invoke agent with proper message format (required by Gemini)
        input_content = example.input_content_preview or example.input_summary
        result = await agent.ainvoke({"messages": [HumanMessage(content=input_content)]})

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Extract output dict (handle both dict and Pydantic model)
        if hasattr(result, "dict"):
            output_dict = result.dict()
        elif hasattr(result, "model_dump"):
            output_dict = result.model_dump()
        else:
            output_dict = result

        logger.info(
            "control_variant_completed",
            agent_type=example.agent_type,
            example_id=str(example.id),
            elapsed_ms=elapsed_ms,
        )

        return output_dict, elapsed_ms

    except Exception as e:
        logger.error(
            "control_variant_failed",
            agent_type=example.agent_type,
            example_id=str(example.id),
            error=str(e),
            exc_info=True,
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return None, elapsed_ms


async def run_treatment_variant(
    example: AgentExample,
    dry_run: bool = False,
) -> tuple[dict[str, Any] | None, float]:
    """Run treatment variant (with few-shot examples).

    Args:
        example: Agent example to test
        dry_run: If True, return mock output without LLM call

    Returns:
        Tuple of (output_dict, time_ms)

    """
    start_time = time.perf_counter()

    if dry_run:
        # Mock output with slightly better quality
        mock_output = {
            "primary_tech": "MockTech",
            "alternatives": ["Alt1", "Alt2", "Alt3"],
            "comparison": {
                "MockTech": {
                    "pros": ["Pro 1", "Pro 2", "Pro 3"],
                    "cons": ["Con 1", "Con 2"],
                    "use_cases": ["Case 1", "Case 2"],
                }
            },
            "recommendation": "This is a more detailed mock recommendation with better structure and explanation.",
            "confidence_score": 0.85,
        }
        elapsed_ms = 150  # Slightly longer due to few-shot overhead
        return mock_output, elapsed_ms

    # Use few-shot factory with treatment variant (with few-shot examples)
    try:
        async with get_session_factory()() as session:
            # Get schema for this agent type
            schema_class = AGENT_SCHEMAS.get(example.agent_type)
            if schema_class is None:
                logger.warning(
                    "agent_type_no_schema",
                    agent_type=example.agent_type,
                    example_id=str(example.id),
                )
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                return None, elapsed_ms

            # Base agent factory for few-shot wrapper
            def base_agent_factory(**kwargs):
                prompt = kwargs.get(
                    "system_prompt",
                    AGENT_PROMPTS.get(example.agent_type, "You are an AI assistant."),
                )
                return create_structured_agent(
                    system_prompt=prompt,
                    response_schema=schema_class,
                )

            # Create embedding service
            embedding_service = EmbeddingService()

            # Create agent with few-shot examples using treatment variant
            agent = await create_few_shot_agent(
                agent_type=example.agent_type,
                content=example.input_content_preview or example.input_summary,
                base_agent_factory=base_agent_factory,
                session=session,
                embedding_service=embedding_service,
                variant="treatment",  # Force treatment variant
                max_examples=3,
                min_quality_score=0.8,
                system_prompt=AGENT_PROMPTS.get(example.agent_type, "You are an AI assistant."),
            )

            # Invoke agent with proper message format (required by Gemini)
            input_content = example.input_content_preview or example.input_summary
            result = await agent.ainvoke({"messages": [HumanMessage(content=input_content)]})

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # Extract output dict (handle both dict and Pydantic model)
            if hasattr(result, "dict"):
                output_dict = result.dict()
            elif hasattr(result, "model_dump"):
                output_dict = result.model_dump()
            else:
                output_dict = result

            logger.info(
                "treatment_variant_completed",
                agent_type=example.agent_type,
                example_id=str(example.id),
                elapsed_ms=elapsed_ms,
            )

            return output_dict, elapsed_ms

    except Exception as e:
        logger.error(
            "treatment_variant_failed",
            agent_type=example.agent_type,
            example_id=str(example.id),
            error=str(e),
            exc_info=True,
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return None, elapsed_ms


async def run_cot_variant(
    example: AgentExample,
    dry_run: bool = False,
) -> tuple[dict[str, Any] | None, float]:
    """Run Chain-of-Thought variant (structured reasoning prompts).

    Uses explicit reasoning steps before generating structured output,
    based on research showing CoT can outperform few-shot for complex tasks.

    Args:
        example: Agent example to test
        dry_run: If True, return mock output without LLM call

    Returns:
        Tuple of (output_dict, time_ms)

    """
    start_time = time.perf_counter()

    try:
        schema_class = AGENT_SCHEMAS.get(example.agent_type)
        if schema_class is None:
            logger.warning(
                "cot_variant_no_schema",
                agent_type=example.agent_type,
                example_id=str(example.id),
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return None, elapsed_ms

        # Get Chain-of-Thought prompt (includes reasoning steps)
        cot_prompt = get_cot_prompt(example.agent_type)

        # Create agent with CoT prompt
        agent = create_structured_agent(
            system_prompt=cot_prompt,
            response_schema=schema_class,
        )

        # Invoke agent with proper message format (required by Gemini)
        input_content = example.input_content_preview or example.input_summary
        result = await agent.ainvoke({"messages": [HumanMessage(content=input_content)]})

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Extract output dict (handle both dict and Pydantic model)
        if hasattr(result, "dict"):
            output_dict = result.dict()
        elif hasattr(result, "model_dump"):
            output_dict = result.model_dump()
        else:
            output_dict = result

        logger.info(
            "cot_variant_completed",
            agent_type=example.agent_type,
            example_id=str(example.id),
            elapsed_ms=elapsed_ms,
        )

        return output_dict, elapsed_ms

    except Exception as e:
        logger.error(
            "cot_variant_failed",
            agent_type=example.agent_type,
            example_id=str(example.id),
            error=str(e),
            exc_info=True,
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return None, elapsed_ms


async def compare_example(
    example: AgentExample,
    dry_run: bool = False,
) -> ComparisonResult:
    """Compare control vs treatment vs CoT for a single example.

    Args:
        example: Agent example to test
        dry_run: If True, use mock outputs

    Returns:
        ComparisonResult with quality scores and timing for all three variants

    """
    logger.info(
        "comparing_example",
        agent_type=example.agent_type,
        example_id=str(example.id),
    )

    # Run all three variants
    control_output, control_time = await run_control_variant(example, dry_run)
    treatment_output, treatment_time = await run_treatment_variant(example, dry_run)
    cot_output, cot_time = await run_cot_variant(example, dry_run)

    # Score all outputs
    schema_class = AGENT_SCHEMAS.get(example.agent_type)
    golden_example_dict = {
        "output_example": example.output_example,
        "quality_score": example.quality_score,
    }

    control_score = score_output_quality(
        output=control_output or {},
        golden_example=golden_example_dict,
        agent_type=example.agent_type,
        schema_class=schema_class,
    )

    treatment_score = score_output_quality(
        output=treatment_output or {},
        golden_example=golden_example_dict,
        agent_type=example.agent_type,
        schema_class=schema_class,
    )

    cot_score = score_output_quality(
        output=cot_output or {},
        golden_example=golden_example_dict,
        agent_type=example.agent_type,
        schema_class=schema_class,
    )

    # Calculate improvements vs control
    if control_score.overall_score > 0:
        improvement_pct = (
            (treatment_score.overall_score - control_score.overall_score)
            / control_score.overall_score
        ) * 100
        cot_improvement_pct = (
            (cot_score.overall_score - control_score.overall_score) / control_score.overall_score
        ) * 100
    else:
        improvement_pct = 0.0
        cot_improvement_pct = 0.0

    return ComparisonResult(
        example_id=str(example.id),
        agent_type=example.agent_type,
        input_summary=example.input_summary[:100],
        control_score=control_score,
        treatment_score=treatment_score,
        cot_score=cot_score,
        improvement_pct=improvement_pct,
        cot_improvement_pct=cot_improvement_pct,
        control_time_ms=control_time,
        treatment_time_ms=treatment_time,
        cot_time_ms=cot_time,
        control_output=control_output,
        treatment_output=treatment_output,
        cot_output=cot_output,
    )


def aggregate_results(results: list[ComparisonResult]) -> dict[str, AgentTypeResults]:
    """Aggregate results by agent type.

    Args:
        results: List of comparison results

    Returns:
        Dictionary mapping agent_type to aggregated results

    """
    by_type: dict[str, list[ComparisonResult]] = defaultdict(list)
    for result in results:
        by_type[result.agent_type].append(result)

    aggregated = {}
    for agent_type, type_results in by_type.items():
        control_scores = [r.control_score.overall_score for r in type_results]
        treatment_scores = [r.treatment_score.overall_score for r in type_results]
        cot_scores = [r.cot_score.overall_score for r in type_results]
        improvements = [r.improvement_pct for r in type_results]
        cot_improvements = [r.cot_improvement_pct for r in type_results]

        control_tokens = [r.control_score.token_count for r in type_results]
        treatment_tokens = [r.treatment_score.token_count for r in type_results]
        cot_tokens = [r.cot_score.token_count for r in type_results]

        control_avg = sum(control_scores) / len(control_scores) if control_scores else 0
        treatment_avg = sum(treatment_scores) / len(treatment_scores) if treatment_scores else 0
        cot_avg = sum(cot_scores) / len(cot_scores) if cot_scores else 0
        improvement_avg = sum(improvements) / len(improvements) if improvements else 0
        cot_improvement_avg = (
            sum(cot_improvements) / len(cot_improvements) if cot_improvements else 0
        )

        # Standard deviation for few-shot
        if len(improvements) > 1:
            mean = improvement_avg
            variance = sum((x - mean) ** 2 for x in improvements) / len(improvements)
            improvement_std = variance**0.5
        else:
            improvement_std = 0.0

        # Standard deviation for CoT
        if len(cot_improvements) > 1:
            cot_mean = cot_improvement_avg
            cot_variance = sum((x - cot_mean) ** 2 for x in cot_improvements) / len(
                cot_improvements
            )
            cot_improvement_std = cot_variance**0.5
        else:
            cot_improvement_std = 0.0

        # Token usage
        control_avg_tokens = sum(control_tokens) / len(control_tokens) if control_tokens else 0
        treatment_avg_tokens = (
            sum(treatment_tokens) / len(treatment_tokens) if treatment_tokens else 0
        )
        cot_avg_tokens = sum(cot_tokens) / len(cot_tokens) if cot_tokens else 0
        token_increase_pct = (
            ((treatment_avg_tokens - control_avg_tokens) / control_avg_tokens) * 100
            if control_avg_tokens > 0
            else 0
        )

        # Best and worst improvements
        best = max(type_results, key=lambda r: r.improvement_pct)
        worst = min(type_results, key=lambda r: r.improvement_pct)
        best_cot = max(type_results, key=lambda r: r.cot_improvement_pct)

        aggregated[agent_type] = AgentTypeResults(
            agent_type=agent_type,
            sample_count=len(type_results),
            control_avg_score=control_avg,
            treatment_avg_score=treatment_avg,
            cot_avg_score=cot_avg,
            improvement_pct=improvement_avg,
            cot_improvement_pct=cot_improvement_avg,
            improvement_std=improvement_std,
            cot_improvement_std=cot_improvement_std,
            best_improvement=best,
            worst_improvement=worst,
            best_cot_improvement=best_cot,
            control_avg_tokens=control_avg_tokens,
            treatment_avg_tokens=treatment_avg_tokens,
            cot_avg_tokens=cot_avg_tokens,
            token_increase_pct=token_increase_pct,
        )

    return aggregated


def generate_markdown_report(
    results: list[ComparisonResult],
    aggregated: dict[str, AgentTypeResults],
    output_path: Path,
) -> None:
    """Generate markdown report.

    Args:
        results: All comparison results
        aggregated: Aggregated results by agent type
        output_path: Path to write report

    """
    # Calculate overall statistics
    all_improvements = [r.improvement_pct for r in results]
    all_cot_improvements = [r.cot_improvement_pct for r in results]
    overall_avg = sum(all_improvements) / len(all_improvements) if all_improvements else 0
    overall_cot_avg = (
        sum(all_cot_improvements) / len(all_cot_improvements) if all_cot_improvements else 0
    )
    overall_median = sorted(all_improvements)[len(all_improvements) // 2] if all_improvements else 0

    # Statistical significance (basic check)
    target_min = 15.0
    target_max = 25.0
    target_met = target_min <= overall_avg <= target_max
    cot_target_met = target_min <= overall_cot_avg <= target_max

    # Determine winner
    winner = "CoT" if overall_cot_avg > overall_avg else "Few-Shot"
    best_improvement = max(overall_avg, overall_cot_avg)

    lines = [
        "# Phase 1 Quality Comparison Report (Few-Shot vs Chain-of-Thought)",
        "",
        f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "## Executive Summary",
        "",
        f"- **Few-Shot Improvement**: {overall_avg:+.1f}% {'✅' if target_met else '❌'}",
        f"- **Chain-of-Thought Improvement**: {overall_cot_avg:+.1f}% {'✅' if cot_target_met else '❌'}",
        f"- **Winner**: **{winner}** ({best_improvement:+.1f}%)",
        f"- **Target Achievement**: {'✅ YES' if target_met or cot_target_met else '❌ NO'} (target: 15-25%)",
        f"- **Samples Tested**: {len(results)} examples across {len(aggregated)} agent types",
        "",
        "## Results by Agent Type",
        "",
    ]

    # Add table header with CoT column
    lines.extend(
        [
            "| Agent Type | Samples | Control | Few-Shot | CoT | Few-Shot Δ | CoT Δ |",
            "|------------|---------|---------|----------|-----|------------|-------|",
        ]
    )

    for agent_type in sorted(aggregated.keys()):
        agg = aggregated[agent_type]
        lines.append(
            f"| {agent_type} | {agg.sample_count} | {agg.control_avg_score:.3f} | "
            f"{agg.treatment_avg_score:.3f} | {agg.cot_avg_score:.3f} | "
            f"{agg.improvement_pct:+.1f}% | {agg.cot_improvement_pct:+.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Statistical Analysis",
            "",
            f"- **Few-Shot mean improvement**: {overall_avg:+.1f}%",
            f"- **CoT mean improvement**: {overall_cot_avg:+.1f}%",
            f"- **Median improvement (Few-Shot)**: {overall_median:+.1f}%",
            f"- **Sample size**: {len(results)} examples",
            "",
        ]
    )

    # Detailed agent analysis
    lines.extend(
        [
            "## Detailed Agent Analysis",
            "",
        ]
    )

    for agent_type in sorted(aggregated.keys()):
        agg = aggregated[agent_type]
        local_winner = "CoT" if agg.cot_improvement_pct > agg.improvement_pct else "Few-Shot"
        lines.extend(
            [
                f"### {agent_type}",
                "",
                f"- **Samples**: {agg.sample_count}",
                f"- **Control avg score**: {agg.control_avg_score:.3f}",
                f"- **Few-Shot avg score**: {agg.treatment_avg_score:.3f} ({agg.improvement_pct:+.1f}%)",
                f"- **CoT avg score**: {agg.cot_avg_score:.3f} ({agg.cot_improvement_pct:+.1f}%)",
                f"- **Winner**: **{local_winner}**",
                "",
                f"**Best Few-Shot**: {agg.best_improvement.improvement_pct:+.1f}% "
                f"(Example: {agg.best_improvement.input_summary[:50]}...)",
                "",
                f"**Best CoT**: {agg.best_cot_improvement.cot_improvement_pct:+.1f}% "
                f"(Example: {agg.best_cot_improvement.input_summary[:50]}...)",
                "",
            ]
        )

    # Recommendations
    lines.extend(
        [
            "## Recommendations",
            "",
        ]
    )

    if target_met:
        lines.extend(
            [
                "✅ **Deploy to Production**: Quality improvement meets target (15-25%)",
                "",
                "- Recommended rollout: 20% traffic initially",
                "- Monitor quality metrics closely",
                "- Expand to 50% if no regressions detected",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "❌ **DO NOT Deploy**: Quality improvement below target",
                "",
                "- Current improvement too low for production deployment",
                "- Investigate low-performing agent types",
                "- Consider increasing few-shot example quality",
                "- Re-test after improvements",
                "",
            ]
        )

    # Cost analysis
    avg_token_increase = sum(agg.token_increase_pct for agg in aggregated.values()) / len(
        aggregated
    )

    lines.extend(
        [
            "## Cost Analysis",
            "",
            f"- **Average token increase**: {avg_token_increase:+.1f}%",
            f"- **Quality per token**: {overall_avg / (avg_token_increase + 100):.3f}",
            "",
            "*Token increase is acceptable if quality improvement justifies cost.*",
            "",
        ]
    )

    # Write report
    output_path.write_text("\n".join(lines))
    logger.info("report_generated", path=str(output_path))


async def main() -> int:
    """Main entry point for comparison testing.

    Returns:
        Exit code (0 for success, 1 for error)

    """
    parser = argparse.ArgumentParser(description="Compare few-shot quality (control vs treatment)")
    parser.add_argument(
        "--agent-type",
        type=str,
        help="Test specific agent type only",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=15,
        help="Maximum examples per agent type (default: 15)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use mock outputs (no LLM calls)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs"),
        help="Output directory for report (default: docs/)",
    )

    args = parser.parse_args()

    logger.info(
        "comparison_test_started",
        agent_type=args.agent_type,
        sample_size=args.sample_size,
        dry_run=args.dry_run,
    )

    try:
        # Load examples
        examples = await load_agent_examples(args.agent_type, args.sample_size)
        logger.info("examples_loaded", count=len(examples))

        if not examples:
            logger.error("no_examples_found")
            print("❌ No examples found. Run seed_few_shot_examples.py first.")
            return 1

        # Run comparisons
        results = []
        with tqdm(total=len(examples), desc="Comparing variants") as pbar:
            for example in examples:
                result = await compare_example(example, args.dry_run)
                results.append(result)
                pbar.update(1)
                pbar.set_postfix({"improvement": f"{result.improvement_pct:+.1f}%"})

        # Aggregate results
        aggregated = aggregate_results(results)

        # Generate report
        report_path = args.output_dir / "phase1-quality-comparison-report.md"
        generate_markdown_report(results, aggregated, report_path)

        # Save raw results JSON
        results_path = Path("data") / "phase1-quality-comparison-results.json"
        results_path.parent.mkdir(exist_ok=True)

        results_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "config": {
                "agent_type": args.agent_type,
                "sample_size": args.sample_size,
                "dry_run": args.dry_run,
            },
            "results": [
                {
                    "example_id": r.example_id,
                    "agent_type": r.agent_type,
                    "improvement_pct": r.improvement_pct,
                    "control_score": r.control_score.overall_score,
                    "treatment_score": r.treatment_score.overall_score,
                }
                for r in results
            ],
        }

        results_path.write_text(json.dumps(results_data, indent=2))

        # Print summary
        overall_avg = sum(r.improvement_pct for r in results) / len(results)
        print("\n✅ Comparison complete!")
        print(f"   Overall improvement: {overall_avg:+.1f}%")
        print(f"   Report: {report_path}")
        print(f"   Results: {results_path}")

        return 0

    except Exception as e:
        logger.error("comparison_test_failed", error=str(e), exc_info=True)
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
