#!/usr/bin/env python3
"""Prototype: G-Eval LLM-as-Judge Quality Scorer.

This prototype demonstrates the difference between:
1. Current approach: Schema validation + heuristics (produces 0.123 scores)
2. G-Eval approach: LLM-judged rubrics with chain-of-thought reasoning

Run:
    poetry run python scripts/prototype_g_eval_scorer.py

Expected result: G-Eval should produce meaningful quality differentiation
where current scorer produces identical low scores due to validation errors.
"""

from __future__ import annotations

import asyncio
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import select

from app.core.model_factory import get_chat_model
from app.core.logging import get_logger
from app.db.session import get_session_factory
from app.models.agent_example import AgentExample
from app.shared.services.quality_scorer import score_output_quality

logger = get_logger(__name__)


# ============================================================================
# G-EVAL RUBRICS (Research-based scoring criteria)
# ============================================================================

RUBRICS = {
    "completeness": {
        1: "Output is empty, placeholder, or completely off-topic",
        2: "Missing most required elements (>50% absent or superficial)",
        3: "Has basic structure but missing key details or sections",
        4: "All major elements present but some lack depth or specificity",
        5: "Comprehensive output with all elements thoroughly addressed",
    },
    "accuracy": {
        1: "Contains major factual errors or contradictions",
        2: "Some inaccuracies or unsupported claims present",
        3: "Generally accurate but lacks verification or specificity",
        4: "Accurate with good supporting evidence",
        5: "Highly accurate, well-sourced, factually rigorous",
    },
    "coherence": {
        1: "Disorganized, contradictory, or incomprehensible",
        2: "Poor organization with unclear logical flow",
        3: "Adequate structure but some disconnected elements",
        4: "Well-organized with clear logical progression",
        5: "Excellent structure, seamless flow, highly readable",
    },
    "depth": {
        1: "Superficial treatment with no meaningful analysis",
        2: "Basic coverage without insight or analysis",
        3: "Moderate depth with some analytical elements",
        4: "Good depth with meaningful insights and analysis",
        5: "Exceptional depth, nuanced analysis, expert-level insight",
    },
}


# ============================================================================
# G-EVAL PROMPT TEMPLATE (Chain-of-Thought scoring)
# ============================================================================

G_EVAL_SYSTEM_PROMPT = """You are an expert evaluator assessing AI-generated analysis quality.

Your task is to evaluate the {criterion} of the output on a 1-5 scale.

## Rubric for {criterion}:
{rubric_text}

## Evaluation Process:
1. Read the input content and generated output carefully
2. Think step-by-step about how well the output addresses the criterion
3. Consider specific examples from the output that support your assessment
4. Provide your reasoning, then your final score

## Response Format:
<reasoning>
[Your step-by-step analysis here - be specific about what you observe]
</reasoning>

<score>[1-5]</score>
<confidence>[0.0-1.0]</confidence>
"""

G_EVAL_USER_PROMPT = """## Input Content (what was analyzed):
{input_content}

## Generated Output (what to evaluate):
{output}

Evaluate the {criterion} of this output using the rubric provided."""


@dataclass
class GEvalScore:
    """Result from G-Eval scoring."""

    criterion: str
    score: int
    confidence: float
    reasoning: str


@dataclass
class CompositeGEvalScore:
    """Composite score from all G-Eval criteria."""

    completeness: GEvalScore
    accuracy: GEvalScore
    coherence: GEvalScore
    depth: GEvalScore
    overall_score: float

    def __str__(self) -> str:
        return (
            f"G-Eval Scores:\n"
            f"  Completeness: {self.completeness.score}/5 (conf: {self.completeness.confidence:.2f})\n"
            f"  Accuracy:     {self.accuracy.score}/5 (conf: {self.accuracy.confidence:.2f})\n"
            f"  Coherence:    {self.coherence.score}/5 (conf: {self.coherence.confidence:.2f})\n"
            f"  Depth:        {self.depth.score}/5 (conf: {self.depth.confidence:.2f})\n"
            f"  Overall:      {self.overall_score:.3f}"
        )


def _format_rubric(criterion: str) -> str:
    """Format rubric for prompt injection."""
    rubric = RUBRICS.get(criterion, {})
    lines = [f"Score {score}: {description}" for score, description in sorted(rubric.items())]
    return "\n".join(lines)


def _parse_g_eval_response(response: str, criterion: str) -> GEvalScore:
    """Parse G-Eval response to extract score, confidence, and reasoning."""
    # Extract reasoning
    reasoning_match = re.search(r"<reasoning>(.*?)</reasoning>", response, re.DOTALL)
    reasoning = reasoning_match.group(1).strip() if reasoning_match else "No reasoning provided"

    # Extract score
    score_match = re.search(r"<score>\s*(\d)\s*</score>", response)
    score = int(score_match.group(1)) if score_match else 3  # Default to middle
    score = max(1, min(5, score))  # Clamp to 1-5

    # Extract confidence
    confidence_match = re.search(r"<confidence>\s*([\d.]+)\s*</confidence>", response)
    confidence = float(confidence_match.group(1)) if confidence_match else 0.7
    confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1

    return GEvalScore(
        criterion=criterion,
        score=score,
        confidence=confidence,
        reasoning=reasoning[:500],  # Truncate for display
    )


async def g_eval_score_criterion(
    input_content: str,
    output: str,
    criterion: str,
) -> GEvalScore:
    """Score a single criterion using G-Eval LLM-as-Judge."""
    model = get_chat_model()

    rubric_text = _format_rubric(criterion)

    system_prompt = G_EVAL_SYSTEM_PROMPT.format(
        criterion=criterion,
        rubric_text=rubric_text,
    )

    user_prompt = G_EVAL_USER_PROMPT.format(
        input_content=input_content[:2000],  # Truncate for context
        output=output[:3000],
        criterion=criterion,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = await model.ainvoke(messages)
    return _parse_g_eval_response(response.content, criterion)


async def g_eval_score_output(
    input_content: str,
    output: dict[str, Any] | str,
) -> CompositeGEvalScore:
    """Score output across all G-Eval criteria."""
    # Convert dict to string for evaluation
    if isinstance(output, dict):
        import json
        output_str = json.dumps(output, indent=2, default=str)
    else:
        output_str = str(output)

    # Score all criteria in parallel
    criteria = ["completeness", "accuracy", "coherence", "depth"]
    tasks = [
        g_eval_score_criterion(input_content, output_str, criterion)
        for criterion in criteria
    ]

    results = await asyncio.gather(*tasks)
    scores = {r.criterion: r for r in results}

    # Calculate weighted overall score (normalized to 0-1)
    weights = {"completeness": 0.25, "accuracy": 0.30, "coherence": 0.25, "depth": 0.20}
    overall = sum(
        (scores[c].score / 5.0) * weights[c]
        for c in criteria
    )

    return CompositeGEvalScore(
        completeness=scores["completeness"],
        accuracy=scores["accuracy"],
        coherence=scores["coherence"],
        depth=scores["depth"],
        overall_score=overall,
    )


async def compare_scorers(
    input_content: str,
    output: dict[str, Any],
    agent_type: str,
    golden_output: str | None = None,
) -> dict[str, Any]:
    """Compare current scorer vs G-Eval scorer."""
    # Current scorer (schema-based)
    current_score = score_output_quality(
        output=output,
        golden_example={"output_example": golden_output} if golden_output else {},
        agent_type=agent_type,
        schema_class=None,  # Skip schema validation for fair comparison
    )

    # G-Eval scorer (LLM-judged)
    g_eval_score = await g_eval_score_output(input_content, output)

    return {
        "current_scorer": {
            "overall": current_score.overall_score,
            "completeness": current_score.completeness_score,
            "accuracy": current_score.accuracy_score,
            "detail": current_score.detail_score,
            "structure": current_score.structure_score,
        },
        "g_eval_scorer": {
            "overall": g_eval_score.overall_score,
            "completeness": g_eval_score.completeness.score / 5.0,
            "accuracy": g_eval_score.accuracy.score / 5.0,
            "coherence": g_eval_score.coherence.score / 5.0,
            "depth": g_eval_score.depth.score / 5.0,
        },
        "g_eval_details": g_eval_score,
        "improvement": g_eval_score.overall_score - current_score.overall_score,
    }


async def run_prototype_test(sample_size: int = 3) -> None:
    """Run prototype comparison on real examples."""
    print("\n" + "=" * 70)
    print("G-EVAL PROTOTYPE: Comparing Current vs LLM-as-Judge Scoring")
    print("=" * 70 + "\n")

    # Load some agent examples
    factory = get_session_factory()
    async with factory() as session:
        query = (
            select(AgentExample)
            .where(AgentExample.quality_score >= 0.8)
            .limit(sample_size * 3)
        )
        result = await session.execute(query)
        examples = result.scalars().all()

    if not examples:
        print("❌ No examples found in database")
        return

    # Sample diverse agent types
    by_type: dict[str, list[AgentExample]] = {}
    for ex in examples:
        if ex.agent_type not in by_type:
            by_type[ex.agent_type] = []
        if len(by_type[ex.agent_type]) < sample_size:
            by_type[ex.agent_type].append(ex)

    results = []

    for agent_type, type_examples in list(by_type.items())[:3]:  # Limit types
        print(f"\n📊 Testing agent type: {agent_type}")
        print("-" * 50)

        for i, example in enumerate(type_examples[:sample_size], 1):
            print(f"\n  Example {i}/{sample_size}: {example.input_summary[:50]}...")

            # Create a mock output (using the golden example as reference)
            # In real use, this would be the actual agent output
            import json
            output_data = example.output_example or {}
            if isinstance(output_data, dict):
                mock_output = output_data  # Use the actual golden output
            else:
                mock_output = {
                    "summary": str(output_data)[:500] if output_data else "No output",
                    "confidence_score": 0.85,
                    "key_points": ["Point 1", "Point 2", "Point 3"],
                }

            try:
                comparison = await compare_scorers(
                    input_content=example.input_content_preview or example.input_summary,
                    output=mock_output,
                    agent_type=agent_type,
                    golden_output=example.output_example,
                )

                print(f"\n  Current Scorer:  {comparison['current_scorer']['overall']:.3f}")
                print(f"  G-Eval Scorer:   {comparison['g_eval_scorer']['overall']:.3f}")
                print(f"  Improvement:     {comparison['improvement']:+.3f}")

                # Show G-Eval breakdown
                g = comparison['g_eval_scorer']
                print(f"\n  G-Eval Breakdown:")
                print(f"    Completeness: {g['completeness']:.2f}")
                print(f"    Accuracy:     {g['accuracy']:.2f}")
                print(f"    Coherence:    {g['coherence']:.2f}")
                print(f"    Depth:        {g['depth']:.2f}")

                results.append(comparison)

            except Exception as e:
                print(f"  ❌ Error: {e}")

    # Summary
    if results:
        avg_current = sum(r['current_scorer']['overall'] for r in results) / len(results)
        avg_g_eval = sum(r['g_eval_scorer']['overall'] for r in results) / len(results)
        avg_improvement = sum(r['improvement'] for r in results) / len(results)

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"\n  Samples tested:       {len(results)}")
        print(f"  Avg Current Score:    {avg_current:.3f}")
        print(f"  Avg G-Eval Score:     {avg_g_eval:.3f}")
        print(f"  Avg Improvement:      {avg_improvement:+.3f} ({avg_improvement/avg_current*100:+.1f}%)")

        if avg_improvement > 0:
            print("\n  ✅ G-Eval produces HIGHER quality scores (more discriminative)")
        else:
            print("\n  ⚠️  G-Eval produces similar or lower scores")

        print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(run_prototype_test(sample_size=2))
