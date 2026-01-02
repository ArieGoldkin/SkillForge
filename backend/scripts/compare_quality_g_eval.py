#!/usr/bin/env python3
"""Quality Comparison with G-Eval LLM-as-Judge Scoring.

This script compares Control vs Few-Shot vs CoT variants using
G-Eval LLM-as-Judge scoring for quality differentiation.

Run:
    poetry run python scripts/compare_quality_g_eval.py

Expected: 15-25% quality improvement from prompting techniques
when measured with G-Eval vs 0% with heuristic scoring.
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

from app.domains.analysis.workflows.agents.schemas.code_reviewer import CodeReview  # noqa: E402
from app.domains.analysis.workflows.agents.schemas.implementation_planner import (  # noqa: E402
    ImplementationPlan,
)
from app.domains.analysis.workflows.agents.schemas.learning_path import LearningPath  # noqa: E402
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

from app.core.logging import get_logger  # noqa: E402
from app.db.models.agent_example import AgentExample  # noqa: E402
from app.db.session import get_session_factory  # noqa: E402
from app.domains.analysis.workflows.agents.base import create_structured_agent  # noqa: E402
from app.shared.services.g_eval import GEvalCostTracker, g_eval_score  # noqa: E402
from app.shared.services.prompts.chain_of_thought import get_cot_prompt  # noqa: E402

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
}

# System prompts
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
class VariantResult:
    """Result from running a single variant."""

    variant: str
    output: dict[str, Any] | None
    g_eval_overall: float
    g_eval_completeness: float
    g_eval_accuracy: float
    g_eval_coherence: float
    g_eval_depth: float
    confidence: float
    reasoning: dict[str, str] = field(default_factory=dict)
    error: str | None = None


@dataclass
class ComparisonResult:
    """Complete comparison across all variants."""

    example_id: str
    agent_type: str
    input_summary: str
    control: VariantResult
    few_shot: VariantResult
    cot: VariantResult
    few_shot_improvement: float
    cot_improvement: float


async def run_variant(
    example: AgentExample,
    variant: str,
    few_shot_examples: list[dict] | None = None,
) -> dict[str, Any]:
    """Run a single variant and return the output."""
    schema_class = AGENT_SCHEMAS.get(example.agent_type)
    input_content = example.input_content_preview or example.input_summary
    base_prompt = AGENT_PROMPTS.get(example.agent_type, "You are an expert analyst.")

    if variant == "control":
        # Baseline - no enhancements
        agent = create_structured_agent(
            system_prompt=base_prompt,
            response_schema=schema_class,
        )
    elif variant == "few_shot":
        # Few-shot with golden examples
        # Research: Quality > quantity, 3-5 examples optimal (Cleanlab.ai, DSPy)
        system_prompt = base_prompt
        if few_shot_examples:
            # Format examples with sufficient context and quality indicators
            formatted_examples = []
            for i, ex in enumerate(few_shot_examples[:4]):  # Use up to 4 examples
                input_preview = ex.get("input_summary", "")[:500]
                output_json = json.dumps(ex.get("output_example", {}), indent=2)
                # Truncate at valid JSON boundary to avoid malformed examples
                if len(output_json) > 1500:
                    truncated = output_json[:1500]
                    last_newline = truncated.rfind("\n")
                    if last_newline > 100:
                        output_json = truncated[:last_newline] + "\n  // ... (truncated)"
                # Include quality context to help model understand what makes it good
                quality_note = ex.get("quality_note", "High-quality curated example")
                formatted_examples.append(
                    f"--- EXAMPLE {i + 1} ({quality_note}) ---\n"
                    f"Input Context: {input_preview}\n\n"
                    f"Expected Output Structure:\n{output_json}"
                )
            examples_text = "\n\n".join(formatted_examples)
            system_prompt += (
                f"\n\n## Reference Examples\n"
                f"Study these high-quality examples to understand the expected output structure and level of detail:\n\n"
                f"{examples_text}\n\n"
                f"Follow a similar structure and depth of analysis in your response."
            )
        agent = create_structured_agent(
            system_prompt=system_prompt,
            response_schema=schema_class,
        )
    elif variant == "cot":
        # Chain-of-Thought enhanced
        cot_prompt = get_cot_prompt(example.agent_type)
        agent = create_structured_agent(
            system_prompt=cot_prompt,
            response_schema=schema_class,
        )
    else:
        msg = f"Unknown variant: {variant}"
        raise ValueError(msg)

    result = await agent.ainvoke({"messages": [HumanMessage(content=input_content)]})

    # Extract structured output
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, dict):
        return result
    return {"raw_output": str(result)}


async def score_variant(
    input_content: str,
    output: dict[str, Any],
    agent_type: str,
    variant: str,
) -> VariantResult:
    """Score a variant's output using G-Eval."""
    try:
        g_eval_result = await g_eval_score(
            input_content=input_content,
            output=output,
            agent_type=agent_type,
        )

        return VariantResult(
            variant=variant,
            output=output,
            g_eval_overall=g_eval_result.overall,
            g_eval_completeness=g_eval_result.completeness,
            g_eval_accuracy=g_eval_result.accuracy,
            g_eval_coherence=g_eval_result.coherence,
            g_eval_depth=g_eval_result.depth,
            confidence=g_eval_result.confidence,
            reasoning=g_eval_result.reasoning,
        )
    except Exception as e:
        logger.exception("variant_scoring_error", variant=variant, error=str(e))
        return VariantResult(
            variant=variant,
            output=output,
            g_eval_overall=0.0,
            g_eval_completeness=0.0,
            g_eval_accuracy=0.0,
            g_eval_coherence=0.0,
            g_eval_depth=0.0,
            confidence=0.0,
            error=str(e),
        )


async def compare_example(
    example: AgentExample,
    few_shot_examples: list[dict] | None,
) -> ComparisonResult:
    """Run full comparison for a single example."""
    input_content = example.input_content_preview or example.input_summary

    # OPTIMIZATION: Run all variants in parallel for 3x speedup
    # This is safe because:
    # 1. Each variant uses independent LLM calls
    # 2. Model factory handles rate limiting internally
    # 3. Variants don't share state
    print("      Running variants in parallel (3x speedup)...")
    control_output, few_shot_output, cot_output = await asyncio.gather(
        run_variant(example, "control"),
        run_variant(example, "few_shot", few_shot_examples),
        run_variant(example, "cot"),
    )

    # Score all variants with G-Eval in parallel
    print("      Scoring with G-Eval...")
    control_score, few_shot_score, cot_score = await asyncio.gather(
        score_variant(input_content, control_output, example.agent_type, "control"),
        score_variant(input_content, few_shot_output, example.agent_type, "few_shot"),
        score_variant(input_content, cot_output, example.agent_type, "cot"),
    )

    # Calculate improvements
    few_shot_improvement = (
        (few_shot_score.g_eval_overall - control_score.g_eval_overall)
        / control_score.g_eval_overall
        * 100
        if control_score.g_eval_overall > 0
        else 0
    )
    cot_improvement = (
        (cot_score.g_eval_overall - control_score.g_eval_overall)
        / control_score.g_eval_overall
        * 100
        if control_score.g_eval_overall > 0
        else 0
    )

    return ComparisonResult(
        example_id=str(example.id),
        agent_type=example.agent_type,
        input_summary=example.input_summary[:50],
        control=control_score,
        few_shot=few_shot_score,
        cot=cot_score,
        few_shot_improvement=few_shot_improvement,
        cot_improvement=cot_improvement,
    )


def select_diverse_examples(
    examples: list[AgentExample],
    num_examples: int = 2,
    min_quality: float = 0.85,
) -> list[dict]:
    """Select diverse, high-quality few-shot examples.

    Strategy:
    1. Filter by quality threshold (>= 0.85)
    2. Select diverse examples using Jaccard similarity on output keys
    3. Avoid redundant examples with similar structures

    Args:
        examples: Pool of candidate examples
        num_examples: Number to select (default: 2)
        min_quality: Minimum quality score (default: 0.85)

    Returns:
        List of diverse few-shot examples

    """
    # Filter by quality and sort by quality score (highest first)
    high_quality = sorted(
        [ex for ex in examples if ex.quality_score >= min_quality],
        key=lambda x: x.quality_score,
        reverse=True,
    )

    if len(high_quality) < num_examples:
        # Not enough high-quality examples, fall back to best available
        print(f"      Warning: Only {len(high_quality)} examples with quality >= {min_quality}")
        sorted_examples = sorted(examples, key=lambda x: x.quality_score, reverse=True)
        return [
            {"input_summary": ex.input_summary, "output_example": ex.output_example}
            for ex in sorted_examples[:num_examples]
        ]

    # Select diverse examples using Jaccard similarity on output keys
    # Start with BEST quality example (list is pre-sorted by quality)
    selected: list[AgentExample] = [high_quality[0]]

    for candidate in high_quality[1:]:
        if len(selected) >= num_examples:
            break

        # Check diversity: compare output structure using Jaccard similarity
        candidate_keys = set(candidate.output_example.keys()) if candidate.output_example else set()
        is_diverse = True

        for selected_ex in selected:
            selected_keys = (
                set(selected_ex.output_example.keys()) if selected_ex.output_example else set()
            )

            # Jaccard similarity: intersection / union
            if candidate_keys and selected_keys:
                intersection = len(candidate_keys & selected_keys)
                union = len(candidate_keys | selected_keys)
                similarity = intersection / union if union > 0 else 0.0

                # If too similar (>80% overlap), skip this candidate
                if similarity > 0.8:
                    is_diverse = False
                    break

        if is_diverse:
            selected.append(candidate)

    print(f"      Selected {len(selected)} diverse examples (quality >= {min_quality})")
    return [
        {"input_summary": ex.input_summary, "output_example": ex.output_example} for ex in selected
    ]


async def run_g_eval_comparison(sample_size: int = 2) -> None:  # noqa: PLR0912
    """Run G-Eval quality comparison."""
    # Reset cost tracker for this session
    tracker = GEvalCostTracker.get_instance()
    tracker.reset()

    print("\n" + "=" * 70)
    print("G-EVAL QUALITY COMPARISON")
    print("=" * 70)
    print(f"Date: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Sample size per agent type: {sample_size}")
    print("=" * 70 + "\n")

    # Load examples
    factory = get_session_factory()
    async with factory() as session:
        query = (
            select(AgentExample).where(AgentExample.quality_score >= 0.8).limit(sample_size * 10)
        )
        result = await session.execute(query)
        all_examples = result.scalars().all()

    if not all_examples:
        print("No examples found in database")
        return

    # Group by agent type (only supported types)
    by_type: dict[str, list[AgentExample]] = {}
    for ex in all_examples:
        if ex.agent_type in AGENT_SCHEMAS and ex.agent_type not in by_type:
            by_type[ex.agent_type] = []
        if ex.agent_type in AGENT_SCHEMAS and len(by_type.get(ex.agent_type, [])) < sample_size:
            by_type[ex.agent_type].append(ex)

    results: list[ComparisonResult] = []

    for agent_type, examples in list(by_type.items())[:5]:  # Limit to 5 agent types
        print(f"\n📊 Agent Type: {agent_type}")
        print("-" * 50)

        # OPTIMIZATION: Smart few-shot selection with quality filter + diversity
        # Research shows 3-5 examples optimal (diminishing returns after)
        # Sources: PromptingGuide.ai, Cleanlab.ai, DSPy best practices
        # Strategy: Filter quality >= 0.85, ensure Jaccard diversity, rank by quality
        few_shot_examples = select_diverse_examples(
            examples,
            num_examples=4,  # Increased from 2 (research: 3-5 optimal)
            min_quality=0.85,
        )

        for i, example in enumerate(examples, 1):
            print(f"\n  Example {i}/{len(examples)}: {example.input_summary[:40]}...")

            try:
                # Run comparison
                comparison = await compare_example(example, few_shot_examples)
                results.append(comparison)

                # Print results
                print(f"\n    Control:   {comparison.control.g_eval_overall:.3f}")
                print(
                    f"    Few-Shot:  {comparison.few_shot.g_eval_overall:.3f} ({comparison.few_shot_improvement:+.1f}%)"
                )
                print(
                    f"    CoT:       {comparison.cot.g_eval_overall:.3f} ({comparison.cot_improvement:+.1f}%)"
                )

            except Exception as e:
                print(f"    Error: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if results:
        avg_control = sum(r.control.g_eval_overall for r in results) / len(results)
        avg_few_shot = sum(r.few_shot.g_eval_overall for r in results) / len(results)
        avg_cot = sum(r.cot.g_eval_overall for r in results) / len(results)
        avg_few_shot_improvement = sum(r.few_shot_improvement for r in results) / len(results)
        avg_cot_improvement = sum(r.cot_improvement for r in results) / len(results)

        print(f"\n  Samples tested:              {len(results)}")
        print("\n  Average Scores (G-Eval):")
        print(f"    Control:                   {avg_control:.3f}")
        print(f"    Few-Shot:                  {avg_few_shot:.3f}")
        print(f"    CoT:                       {avg_cot:.3f}")
        print("\n  Average Improvement:")
        print(f"    Few-Shot vs Control:       {avg_few_shot_improvement:+.1f}%")
        print(f"    CoT vs Control:            {avg_cot_improvement:+.1f}%")

        # Determine winner
        winner = "CoT" if avg_cot_improvement > avg_few_shot_improvement else "Few-Shot"
        best_improvement = max(avg_few_shot_improvement, avg_cot_improvement)

        print(f"\n  Winner: {winner} ({best_improvement:+.1f}%)")

        if best_improvement >= 15:
            print("\n  ✅ SUCCESS: Target 15-25% improvement achieved!")
        elif best_improvement >= 5:
            print("\n  ⚠️  PARTIAL: Improvement detected but below 15% target")
        else:
            print("\n  ❌ LOW: Minimal improvement detected")

        # Agent-type breakdown
        print("\n" + "-" * 50)
        print("By Agent Type:")
        print("-" * 50)

        agent_results: dict[str, list[ComparisonResult]] = {}
        for r in results:
            if r.agent_type not in agent_results:
                agent_results[r.agent_type] = []
            agent_results[r.agent_type].append(r)

        for agent_type, agent_results_list in agent_results.items():
            avg_fs = sum(r.few_shot_improvement for r in agent_results_list) / len(
                agent_results_list
            )
            avg_ct = sum(r.cot_improvement for r in agent_results_list) / len(agent_results_list)
            print(f"  {agent_type:25} Few-Shot: {avg_fs:+.1f}%  CoT: {avg_ct:+.1f}%")

        # Token and Cost Summary
        print("\n" + "-" * 50)
        print("Token Usage & Cost Summary:")
        print("-" * 50)

        summary = tracker.get_session_summary()
        print(f"  Total Evaluations:         {summary.total_evaluations}")
        print(f"  Total Tokens:              {summary.total_tokens:,}")
        print(f"    - Input Tokens:          {summary.total_input_tokens:,}")
        print(f"    - Output Tokens:         {summary.total_output_tokens:,}")
        print(f"    - Cached Tokens:         {summary.total_cached_tokens:,}")
        print(f"  Total Cost:                ${summary.total_cost:.4f}")
        print(f"  Avg Tokens/Eval:           {summary.avg_tokens_per_eval:,.0f}")
        print(f"  Avg Cost/Eval:             ${summary.avg_cost_per_eval:.4f}")

        # Breakdown by model (if multiple models used)
        if len(summary.by_model) > 0:
            print("\n  By Model:")
            for model, cost in summary.by_model.items():
                print(f"    {model:25} {cost.total_tokens:,} tokens  ${cost.total_cost:.4f}")

    print("\n" + "=" * 70)

    # Save report
    report_path = Path("docs/phase2-g-eval-comparison-report.md")
    report_path.parent.mkdir(exist_ok=True)

    with report_path.open("w") as f:
        f.write("# Phase 2 G-Eval Quality Comparison Report\n\n")
        f.write(f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
        f.write("## Executive Summary\n\n")
        if results:
            f.write(f"- **Few-Shot Improvement:** {avg_few_shot_improvement:+.1f}%\n")
            f.write(f"- **CoT Improvement:** {avg_cot_improvement:+.1f}%\n")
            f.write(f"- **Winner:** {winner}\n")
            f.write(
                f"- **Target Achievement:** {'✅ YES' if best_improvement >= 15 else '❌ NO'} (target: 15-25%)\n"
            )
            f.write(f"- **Samples Tested:** {len(results)}\n\n")

            f.write("## Results by Agent Type\n\n")
            f.write("| Agent Type | Control | Few-Shot | CoT | FS Δ | CoT Δ |\n")
            f.write("|------------|---------|----------|-----|------|-------|\n")
            for agent_type, agent_results_list in agent_results.items():
                ctrl = sum(r.control.g_eval_overall for r in agent_results_list) / len(
                    agent_results_list
                )
                fs = sum(r.few_shot.g_eval_overall for r in agent_results_list) / len(
                    agent_results_list
                )
                ct = sum(r.cot.g_eval_overall for r in agent_results_list) / len(agent_results_list)
                fs_d = sum(r.few_shot_improvement for r in agent_results_list) / len(
                    agent_results_list
                )
                ct_d = sum(r.cot_improvement for r in agent_results_list) / len(agent_results_list)
                f.write(
                    f"| {agent_type} | {ctrl:.3f} | {fs:.3f} | {ct:.3f} | {fs_d:+.1f}% | {ct_d:+.1f}% |\n"
                )

            f.write("\n## Key Insight\n\n")
            f.write("G-Eval LLM-as-Judge provides meaningful quality differentiation compared to\n")
            f.write(
                "the heuristic scorer which produced identical scores across variants in Phase 1.\n"
            )

    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    asyncio.run(run_g_eval_comparison(sample_size=2))  # Larger sample for validation
