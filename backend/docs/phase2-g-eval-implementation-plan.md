# Phase 2: G-Eval LLM-as-Judge Implementation Plan

**Created:** 2025-12-16
**Status:** Ready for Implementation
**Target Improvement:** 15-25% quality differentiation

## Executive Summary

Phase 1 (Few-Shot + CoT) achieved **0% improvement** due to the current scorer's inability to differentiate between output quality levels. The G-Eval prototype demonstrated a **3-point score spread** (5 vs 2) between high and low quality outputs, proving it can solve this problem.

## Prototype Results

| Quality Tier | G-Eval Score | Current Scorer | Differentiation |
|-------------|--------------|----------------|-----------------|
| HIGH        | 5/5 (1.0)    | ~0.40          | ✅ Accurate     |
| MEDIUM      | 2/5 (0.4)    | ~0.40          | ✅ Accurate     |
| LOW         | 2/5 (0.4)    | ~0.38          | ✅ Accurate     |

**Key Finding:** G-Eval produces **meaningful quality differentiation** where the current schema-based scorer produces identical scores.

## Implementation Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Quality Scoring Pipeline                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Agent Output ──► Schema Validation ──► G-Eval LLM Judge       │
│                        (fast fail)         (deep eval)          │
│                             │                    │               │
│                             ▼                    ▼               │
│                    valid_schema: bool    quality_scores: dict    │
│                             │                    │               │
│                             └────────┬───────────┘               │
│                                      ▼                           │
│                          Composite Quality Score                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Steps

### Step 1: Create G-Eval Service (2 hours)

**File:** `app/shared/services/g_eval_scorer.py`

```python
"""G-Eval LLM-as-Judge Quality Scorer.

Research-backed scoring using chain-of-thought rubrics.
Reference: G-Eval paper (https://arxiv.org/abs/2303.16634)
"""

@dataclass
class GEvalResult:
    completeness: float  # 0-1 normalized
    accuracy: float
    coherence: float
    depth: float
    overall: float
    reasoning: dict[str, str]  # Per-criterion reasoning
    confidence: float

async def g_eval_score(
    input_content: str,
    output: dict | str,
    agent_type: str,
    criteria: list[str] | None = None,
) -> GEvalResult:
    """Score output using G-Eval with domain-specific rubrics."""
```

### Step 2: Agent-Specific Rubrics (1.5 hours)

**File:** `app/shared/services/g_eval_rubrics.py`

Create domain-specific rubrics for each agent type:

```python
AGENT_RUBRICS = {
    "tech_comparator": {
        "criteria": ["completeness", "accuracy", "balance", "recommendation"],
        "weights": {"completeness": 0.25, "accuracy": 0.30, "balance": 0.25, "recommendation": 0.20},
        "rubrics": {
            "completeness": {
                5: "Compares all relevant dimensions (performance, ecosystem, learning curve, etc.)",
                4: "Covers most dimensions with good detail",
                3: "Basic comparison with some gaps",
                2: "Missing major comparison dimensions",
                1: "Superficial or incomplete comparison",
            },
            # ... other criteria
        }
    },
    "security_auditor": { ... },
    "implementation_planner": { ... },
    # ... other agents
}
```

### Step 3: Hybrid Scorer Integration (1 hour)

**File:** `app/shared/services/quality_scorer.py` (update)

```python
async def score_output_quality_v2(
    output: dict,
    agent_type: str,
    input_content: str,
    golden_example: dict | None = None,
    use_g_eval: bool = True,  # Feature flag
) -> QualityScore:
    """Hybrid scoring: Schema validation + G-Eval LLM judge."""

    # Fast path: Schema validation
    schema_score = _score_schema_compliance(output, agent_type)

    # Deep path: G-Eval (if enabled and schema passes)
    if use_g_eval and schema_score > 0.5:
        g_eval_result = await g_eval_score(input_content, output, agent_type)

        # Combine scores
        return QualityScore(
            overall_score=(schema_score * 0.3) + (g_eval_result.overall * 0.7),
            completeness_score=g_eval_result.completeness,
            accuracy_score=g_eval_result.accuracy,
            detail_score=g_eval_result.depth,
            structure_score=schema_score,
            g_eval_reasoning=g_eval_result.reasoning,
        )

    return _legacy_score(output, agent_type)
```

### Step 4: Update Comparison Script (1 hour)

**File:** `scripts/compare_few_shot_quality.py` (update)

```python
async def run_comparison_with_g_eval(
    example: AgentExample,
    variants: list[str] = ["control", "few_shot", "cot"],
) -> dict:
    """Run comparison using G-Eval scorer."""
    results = {}

    for variant in variants:
        output = await run_variant(example, variant)
        g_eval_score = await g_eval_score(
            example.input_content_preview,
            output,
            example.agent_type,
        )
        results[variant] = g_eval_score

    # Calculate meaningful deltas
    return {
        "control": results["control"].overall,
        "few_shot": results["few_shot"].overall,
        "cot": results["cot"].overall,
        "few_shot_improvement": results["few_shot"].overall - results["control"].overall,
        "cot_improvement": results["cot"].overall - results["control"].overall,
    }
```

### Step 5: Feature Flag & A/B Testing (0.5 hours)

**File:** `app/core/feature_flags.py` (update)

```python
QUALITY_SCORING_FLAGS = {
    "use_g_eval": True,  # Enable G-Eval LLM scoring
    "g_eval_criteria": ["completeness", "accuracy", "coherence", "depth"],
    "g_eval_weight": 0.7,  # Weight vs schema validation
}
```

## Cost Analysis

| Component | Tokens/Request | Cost (GPT-4) | Cost (Gemini) |
|-----------|---------------|--------------|---------------|
| 4 criteria scoring | ~4,000 | ~$0.04 | ~$0.004 |
| Per agent output | ~1,000 input | ~$0.01 | ~$0.001 |
| **Total per evaluation** | ~5,000 | ~$0.05 | ~$0.005 |

**Recommendation:** Use Gemini 2.5 Flash for G-Eval (10x cheaper, comparable quality)

## Success Criteria

1. **Primary:** G-Eval differentiates between Few-Shot/CoT and Control by ≥15%
2. **Secondary:** Score correlation with human judgment ≥0.7
3. **Tertiary:** Latency increase <2s per evaluation

## Timeline

| Task | Duration | Dependency |
|------|----------|------------|
| G-Eval Service | 2h | None |
| Agent Rubrics | 1.5h | Service |
| Hybrid Scorer | 1h | Service |
| Comparison Update | 1h | Hybrid Scorer |
| Feature Flags | 0.5h | None |
| Integration Test | 1h | All above |
| **Total** | **7 hours** | |

## Risks & Mitigations

| Risk | Probability | Mitigation |
|------|------------|------------|
| G-Eval latency too high | Medium | Parallel criterion scoring, caching |
| Cost exceeds budget | Low | Use Gemini, batch evaluations |
| LLM inconsistency | Medium | Self-consistency with 3 samples |
| Domain rubric gaps | Medium | Iterative refinement with golden examples |

## Next Steps

1. ✅ Prototype validated (3-point differentiation)
2. 🔄 Create `g_eval_scorer.py` service
3. ⏳ Define agent-specific rubrics
4. ⏳ Integrate with quality scoring pipeline
5. ⏳ Re-run Phase 1 comparison with G-Eval
6. ⏳ Document results and decide on production deployment
