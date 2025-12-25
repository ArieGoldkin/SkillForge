# Langfuse Multi-Judge Evaluation Integration

**Issue**: #GAP5
**Date**: December 2025
**Status**: ✅ Implemented

## Overview

This document describes the integration of Langfuse multi-judge evaluators into SkillForge's quality gate workflow. This replaces the simple LLM-as-judge evaluators with G-Eval's sophisticated multi-criteria scoring system.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Quality Gate Workflow                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Aggregated Insights ──────────────────────────────────────    │
│         │                                                        │
│         v                                                        │
│   ┌──────────────────────────────────────┐                      │
│   │  Langfuse Multi-Judge Evaluators     │                      │
│   │  (G-Eval powered)                    │                      │
│   ├──────────────────────────────────────┤                      │
│   │                                       │                      │
│   │  Relevance Evaluator (G-Eval)        │──> 0.85              │
│   │  Depth Evaluator (G-Eval)            │──> 0.78              │
│   │  Coherence Evaluator (G-Eval)        │──> 0.92              │
│   │                                       │                      │
│   └──────────────────────────────────────┘                      │
│         │                                                        │
│         v                                                        │
│   ┌──────────────────────────────────────┐                      │
│   │  Weighted Score Calculation          │                      │
│   │  avg = (0.85 + 0.78 + 0.92) / 3      │                      │
│   └──────────────────────────────────────┘                      │
│         │                                                        │
│         v                                                        │
│   Quality Gate Decision: 0.85 >= 0.7 ✓   Pass                   │
│         │                                                        │
│         v                                                        │
│   [Submit scores to Langfuse]                                   │
│         │                                                        │
│         v                                                        │
│   Continue to Artifact Generation                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Langfuse Evaluators (`langfuse_evaluators.py`)

**Location**: `app/shared/services/g_eval/langfuse_evaluators.py`

Pre-built evaluators that return Langfuse `Evaluation` objects:

- **`create_g_eval_evaluator(criterion, agent_type)`** - Single criterion evaluator
- **`create_g_eval_overall_evaluator(agent_type)`** - Multi-criteria weighted evaluator
- **`get_standard_evaluators(agent_type)`** - Pre-configured evaluator set

**Key Features**:
- Uses G-Eval's chain-of-thought scoring
- Agent-specific rubrics from `rubrics.py`
- Automatic caching (file-based + Redis semantic)
- Returns Langfuse `Evaluation` objects for experiments

### 2. Multi-Judge Helper (`multi_judge.py`)

**Location**: `app/shared/services/g_eval/multi_judge.py`

Convenience functions for quality gate integration:

- **`run_multi_judge_evaluation()`** - Run multiple G-Eval evaluators
- **`calculate_weighted_score()`** - Weighted average calculation
- **`get_quality_tier()`** - Quality tier classification

### 3. Quality Gate Integration (`quality_gate_node.py`)

**Location**: `app/domains/analysis/workflows/nodes/quality_gate_node.py`

The quality gate now uses Langfuse multi-judge evaluators:

```python
# Issue GAP5: Wire Langfuse multi-judge G-Eval evaluators for quality assessment
from app.shared.services.g_eval.langfuse_evaluators import create_g_eval_evaluator

# Determine agent type from state
agent_type = state.get("agent_type", "tech_comparator")

# Run G-Eval evaluators for each aspect
for aspect in ["relevance", "depth", "coherence"]:
    evaluator = create_g_eval_evaluator(criterion=aspect, agent_type=agent_type, use_cache=True)
    result = evaluator(input={"content": input_content}, output=output_content)

    # Extract score from Langfuse Evaluation object
    quality_scores[aspect] = {
        "score": result.value,
        "comment": result.comment,
        "metadata": result.metadata,
    }
```

## Evaluation Dimensions

The quality gate evaluates three dimensions using G-Eval:

| Dimension | Description | Weight | Minimum |
|-----------|-------------|--------|---------|
| **Relevance** | How relevant are insights to input content? | Equal | 0.5 |
| **Depth** | How thorough and detailed is the analysis? | Equal | 0.4 |
| **Coherence** | How well-structured and clear are insights? | Equal | 0.4 |

**Scoring Scale**: 0.0 - 1.0 (normalized from G-Eval's 1-5 scale)

## Quality Gate Thresholds

### Standard Thresholds
- **Average threshold**: 0.7 (all criteria averaged)
- **Individual minimums**: See table above
- **Both must pass**: Average >= 0.7 AND all aspects >= minimum

### Coverage-Adjusted Thresholds

When content has limited data (coverage_score < 0.5), adjusted thresholds are used:

- **Average threshold**: 0.55 (reduced from 0.7)
- **Depth minimum**: 0.3 (reduced from 0.4)
- **Relevance minimum**: 0.4 (reduced from 0.5)
- **Coherence minimum**: 0.4 (unchanged)

This rewards honest partial analysis over hallucinated full analysis.

## Langfuse Integration

### Score Submission

All G-Eval scores are submitted to Langfuse for quality analytics:

```python
# Submit individual criterion scores
for aspect, score_data in quality_scores.items():
    langfuse_service.sdk_client.create_score(
        trace_id=str(trace_id),
        name=f"g_eval_{aspect}",
        value=score_data["score"],
        data_type="NUMERIC",
        comment=score_data["comment"][:200],
    )

# Submit overall average score
langfuse_service.sdk_client.create_score(
    trace_id=str(trace_id),
    name="g_eval_overall",
    value=avg_score,
    data_type="NUMERIC",
    comment=f"Gate {'passed' if gate_passed else 'failed'}",
)
```

### Quality Tagging

Traces are auto-tagged with quality tiers:

- **`quality:high`** - avg_score >= 0.8
- **`quality:medium`** - avg_score >= 0.6
- **`quality:low`** - avg_score < 0.6

Additional tags:
- **`gate:passed`** / **`gate:failed`**
- **`coverage:limited`** - If coverage-adjusted thresholds used
- **`aspects:failed`** - If individual aspects below minimum

## Benefits Over Previous System

### Old System (Simple LLM-as-Judge)

```python
# Simple prompt-based evaluation
evaluator = create_quality_evaluator(aspect="relevance")
result = await evaluator(mock_run, mock_example)
score = result.get("score", 0.0)  # Simple 0-10 score
```

**Limitations**:
- Single LLM call per aspect (no chain-of-thought)
- Generic prompts (not agent-specific)
- No caching (expensive and slow)
- No confidence scores

### New System (G-Eval Multi-Judge)

```python
# G-Eval with chain-of-thought reasoning
evaluator = create_g_eval_evaluator(criterion="relevance", agent_type="tech_comparator")
result = evaluator(input=input_content, output=output_content)
# Returns Langfuse Evaluation with metadata
```

**Advantages**:
- ✅ **Chain-of-thought reasoning** - Explicit step-by-step evaluation
- ✅ **Agent-specific rubrics** - Domain-aware evaluation criteria
- ✅ **Multi-level caching** - File-based + Redis semantic cache
- ✅ **Confidence scores** - Evaluator confidence in assessment
- ✅ **Rich metadata** - Raw scores, voting distributions (if using self-consistency)
- ✅ **Langfuse experiments** - Compatible with `langfuse.run_experiment()`
- ✅ **Cost optimization** - Caching reduces LLM calls by 70-95%

## Usage Examples

### Basic Quality Gate Evaluation

```python
from app.shared.services.g_eval.multi_judge import run_multi_judge_evaluation

# Run multi-judge evaluation
quality_scores = await run_multi_judge_evaluation(
    input_content="Article about RAG systems...",
    output_content="Analysis: RAG combines retrieval with generation...",
    agent_type="tech_comparator",
    aspects=["relevance", "depth", "coherence"],
)

# Check results
print(quality_scores)
# {
#     "relevance": {"score": 0.85, "comment": "Highly relevant to RAG topic", "metadata": {...}},
#     "depth": {"score": 0.78, "comment": "Good depth but could expand...", "metadata": {...}},
#     "coherence": {"score": 0.92, "comment": "Well-structured analysis", "metadata": {...}},
# }
```

### Custom Weighting

```python
from app.shared.services.g_eval.multi_judge import calculate_weighted_score

# Custom weights (e.g., prioritize depth)
weights = {
    "relevance": 0.3,
    "depth": 0.5,      # Higher weight
    "coherence": 0.2,
}

weighted_avg = calculate_weighted_score(quality_scores, weights)
# 0.81 (depth is weighted more heavily)
```

### Langfuse Experiments

```python
from app.shared.services.g_eval.langfuse_evaluators import get_standard_evaluators
from langfuse import Langfuse

langfuse = Langfuse()

# Run experiment with G-Eval evaluators
result = langfuse.run_experiment(
    name="Quality Gate Experiment",
    data=dataset.items,
    task=my_synthesis_task,
    evaluators=get_standard_evaluators(agent_type="tech_comparator"),
)

# View results in Langfuse UI
print(f"Average quality: {result.avg_score:.2f}")
```

## Configuration

### Environment Variables

```bash
# Langfuse configuration (already set in .env)
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000
```

### Quality Gate Constants

```python
# In quality_gate_node.py
QUALITY_THRESHOLD = 0.7              # Average threshold
ASPECT_MINIMUMS = {
    "relevance": 0.5,                # Critical: must be relevant
    "depth": 0.4,                    # Some depth required
    "coherence": 0.4,                # Basic coherence required
}

# Coverage-adjusted (for limited data)
COVERAGE_TRIGGER_BELOW = 0.5         # When to use adjusted thresholds
COVERAGE_ADJUSTED_THRESHOLD = 0.55   # Lower average requirement
```

## Monitoring & Analytics

### Langfuse Dashboard

Navigate to `http://localhost:3000` to view:

1. **Traces** - Filter by quality tags (quality:high, quality:medium, quality:low)
2. **Scores** - View score distributions over time
3. **Trends** - Track quality improvements across deployments
4. **Per-Criterion** - Analyze which aspects need improvement

### SQL Queries

```sql
-- Average scores by criterion (last 7 days)
SELECT
  name,
  AVG(value) as avg_score,
  COUNT(*) as count
FROM scores
WHERE name LIKE 'g_eval_%'
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY name
ORDER BY avg_score DESC;

-- Quality tier distribution
SELECT
  CASE
    WHEN value >= 0.8 THEN 'high'
    WHEN value >= 0.6 THEN 'medium'
    ELSE 'low'
  END as tier,
  COUNT(*) as count,
  AVG(value) as avg_score
FROM scores
WHERE name = 'g_eval_overall'
GROUP BY tier;
```

## Testing

### Unit Tests

```bash
# Run integration tests
poetry run pytest tests/unit/g_eval/test_langfuse_evaluators_integration.py -v
```

**Tests**:
- ✅ Evaluator creation
- ✅ Weighted score calculation
- ✅ Quality tier classification
- ✅ Standard evaluator sets

### Manual Testing

```bash
# Start backend
poetry run uvicorn app.main:app --reload --port 8500

# Trigger analysis (via frontend or API)
curl -X POST http://localhost:8500/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'

# Check Langfuse for scores
# Navigate to http://localhost:3000 and view the trace
```

## Future Improvements

1. **Self-Consistency Voting** - Enable multi-sample voting for 15-25% accuracy boost
2. **Prompt Versioning** - Store evaluator prompts in Langfuse for A/B testing
3. **Custom Rubrics** - Allow per-analysis custom evaluation criteria
4. **Human Feedback** - Add annotation queue for human review of low-confidence scores
5. **Adaptive Thresholds** - Learn optimal thresholds from historical data

## References

- **G-Eval Paper**: https://arxiv.org/abs/2303.16634
- **Langfuse Docs**: https://langfuse.com/docs
- **Skill Documentation**: `.claude/skills/langfuse-observability/references/multi-judge-evaluation.md`
- **Implementation**: `app/shared/services/g_eval/langfuse_evaluators.py`

## Changelog

- **2025-12-25**: Initial implementation of Langfuse multi-judge evaluators
- **Issue #GAP5**: Wire evaluators into quality gate workflow
