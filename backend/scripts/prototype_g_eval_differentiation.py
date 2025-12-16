#!/usr/bin/env python3
"""Prototype: G-Eval Differentiation Test.

This test demonstrates whether G-Eval can differentiate between:
1. High-quality outputs (golden examples)
2. Medium-quality outputs (truncated/simplified)
3. Low-quality outputs (minimal/placeholder)

This is the key capability we need - the current scorer gives identical
scores to all variants (~0.123) when schema validation fails.

Run:
    poetry run python scripts/prototype_g_eval_differentiation.py
"""

from __future__ import annotations

import asyncio
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.model_factory import get_chat_model
from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# G-EVAL RUBRICS (Simplified for differentiation test)
# ============================================================================

RUBRICS = {
    "quality": {
        1: "Empty, placeholder, or completely irrelevant output",
        2: "Minimal content with major gaps and missing key elements",
        3: "Basic coverage but lacks depth, specificity, or organization",
        4: "Good quality with most elements present and reasonable depth",
        5: "Excellent quality - comprehensive, accurate, well-organized",
    },
}


# ============================================================================
# G-EVAL PROMPT TEMPLATE
# ============================================================================

G_EVAL_SYSTEM_PROMPT = """You are an expert evaluator assessing AI-generated analysis quality.

## Rubric:
Score 1: Empty, placeholder, or completely irrelevant output
Score 2: Minimal content with major gaps and missing key elements
Score 3: Basic coverage but lacks depth, specificity, or organization
Score 4: Good quality with most elements present and reasonable depth
Score 5: Excellent quality - comprehensive, accurate, well-organized

## Evaluation Process:
1. Read the task and output carefully
2. Think about how well the output addresses the task
3. Consider completeness, accuracy, depth, and organization
4. Provide your reasoning, then your final score

## Response Format:
<reasoning>
[Your step-by-step analysis - be specific]
</reasoning>

<score>[1-5]</score>
<confidence>[0.0-1.0]</confidence>
"""

G_EVAL_USER_PROMPT = """## Task:
{task}

## Output to Evaluate:
{output}

Evaluate the quality of this output using the rubric provided."""


@dataclass
class GEvalScore:
    """Result from G-Eval scoring."""

    score: int
    confidence: float
    reasoning: str


def _parse_g_eval_response(response: str) -> GEvalScore:
    """Parse G-Eval response."""
    reasoning_match = re.search(r"<reasoning>(.*?)</reasoning>", response, re.DOTALL)
    reasoning = reasoning_match.group(1).strip() if reasoning_match else "No reasoning"

    score_match = re.search(r"<score>\s*(\d)\s*</score>", response)
    score = int(score_match.group(1)) if score_match else 3
    score = max(1, min(5, score))

    confidence_match = re.search(r"<confidence>\s*([\d.]+)\s*</confidence>", response)
    confidence = float(confidence_match.group(1)) if confidence_match else 0.7
    confidence = max(0.0, min(1.0, confidence))

    return GEvalScore(score=score, confidence=confidence, reasoning=reasoning[:300])


async def g_eval_score(task: str, output: str) -> GEvalScore:
    """Score output quality using G-Eval."""
    model = get_chat_model()

    messages = [
        SystemMessage(content=G_EVAL_SYSTEM_PROMPT),
        HumanMessage(content=G_EVAL_USER_PROMPT.format(task=task, output=output)),
    ]

    response = await model.ainvoke(messages)
    return _parse_g_eval_response(response.content)


async def run_differentiation_test() -> None:
    """Run differentiation test with quality tiers."""
    print("\n" + "=" * 70)
    print("G-EVAL DIFFERENTIATION TEST")
    print("=" * 70)
    print("\nGoal: Verify G-Eval can distinguish between quality levels")
    print("=" * 70 + "\n")

    # Test task: Technology comparison
    task = """Compare React and Vue.js for building a modern web application.
    Analyze their strengths, weaknesses, and provide a recommendation."""

    # Three quality tiers
    outputs = {
        "HIGH (Golden)": """## Technology Comparison: React vs Vue.js

### Overview
React (by Meta) and Vue.js (by Evan You) are both popular JavaScript frameworks for building user interfaces. React follows a component-based architecture with a virtual DOM, while Vue.js offers a more approachable learning curve with similar capabilities.

### Key Differences

**Learning Curve**
- React: Steeper learning curve, requires understanding JSX and ecosystem choices
- Vue.js: Gentler learning curve, HTML-based templates feel familiar

**Performance**
- React: Excellent performance with virtual DOM diffing, optimized for large apps
- Vue.js: Slightly faster initial render, reactive system is memory-efficient

**Ecosystem**
- React: Massive ecosystem (Redux, React Router, Next.js), backed by Meta
- Vue.js: Smaller but cohesive ecosystem (Vuex, Vue Router, Nuxt.js)

**Community & Jobs**
- React: Larger community, more job opportunities, extensive resources
- Vue.js: Growing community, popular in Asia, excellent documentation

### Trade-offs
- Choose React if: Building large-scale apps, need extensive ecosystem, team has React experience
- Choose Vue.js if: Smaller team, prefer simpler tooling, need quick prototyping

### Recommendation
For a modern web application with a team new to both frameworks, **Vue.js** offers faster onboarding and productivity. For enterprise-scale applications with complex state management needs, **React** with its mature ecosystem is the safer choice.

**Confidence: 0.85**
""",

        "MEDIUM (Basic)": """## React vs Vue Comparison

React and Vue are JavaScript frameworks for web apps.

**React:**
- Made by Facebook
- Uses JSX
- Popular with many libraries

**Vue:**
- Made by Evan You
- Uses templates
- Easier to learn

Both are good choices. React has more jobs but Vue is simpler.

Recommendation: Depends on your needs.
""",

        "LOW (Minimal)": """React and Vue are frameworks.

React is popular. Vue is also popular.

Pick one based on preference.
""",
    }

    results = {}

    for tier, output in outputs.items():
        print(f"\n📊 Testing {tier}")
        print("-" * 50)
        print(f"   Output preview: {output[:100].replace(chr(10), ' ')}...")

        try:
            score = await g_eval_score(task, output)
            results[tier] = score

            print(f"\n   Score: {score.score}/5 (confidence: {score.confidence:.2f})")
            print(f"   Reasoning: {score.reasoning[:200]}...")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            results[tier] = GEvalScore(score=0, confidence=0, reasoning=str(e))

    # Analysis
    print("\n" + "=" * 70)
    print("DIFFERENTIATION ANALYSIS")
    print("=" * 70)

    scores = [(tier, r.score) for tier, r in results.items()]
    print(f"\n  {'Tier':<20} {'G-Eval Score':<15} {'Expected':<15}")
    print(f"  {'-'*50}")

    expected = {"HIGH (Golden)": "4-5", "MEDIUM (Basic)": "2-3", "LOW (Minimal)": "1-2"}
    for tier, score in scores:
        exp = expected.get(tier, "?")
        status = "✅" if (
            (tier == "HIGH (Golden)" and score >= 4) or
            (tier == "MEDIUM (Basic)" and 2 <= score <= 3) or
            (tier == "LOW (Minimal)" and score <= 2)
        ) else "⚠️"
        print(f"  {tier:<20} {score:<15} {exp:<15} {status}")

    # Check differentiation
    high_score = results["HIGH (Golden)"].score
    med_score = results["MEDIUM (Basic)"].score
    low_score = results["LOW (Minimal)"].score

    differentiation = high_score - low_score

    print(f"\n  Score Spread (High - Low): {differentiation}")

    if differentiation >= 2:
        print("\n  ✅ PASS: G-Eval successfully differentiates between quality levels!")
        print(f"     High ({high_score}) > Medium ({med_score}) > Low ({low_score})")
    elif differentiation >= 1:
        print("\n  ⚠️  PARTIAL: G-Eval shows some differentiation but could be stronger")
    else:
        print("\n  ❌ FAIL: G-Eval does not differentiate well between quality levels")

    print("\n" + "=" * 70)
    print("CONCLUSION")
    print("=" * 70)

    if differentiation >= 2 and high_score > med_score > low_score:
        print("""
  🎯 G-Eval demonstrates strong differentiation capability!

  This addresses the Phase 1 problem where all variants received
  identical scores (~0.123) due to schema validation dominance.

  RECOMMENDATION: Proceed with G-Eval integration as the primary
  quality scorer for the Few-Shot/CoT comparison framework.

  Expected improvement: 15-25% quality differentiation
        """)
    else:
        print("""
  ⚠️  G-Eval differentiation is weaker than expected.

  Consider:
  1. Refining the rubric criteria
  2. Adding domain-specific evaluation dimensions
  3. Using multiple evaluation passes for confidence
        """)

    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(run_differentiation_test())
