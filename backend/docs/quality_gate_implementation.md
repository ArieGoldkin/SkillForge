# Quality Gate Implementation (Issue #301)

## Overview

This document describes the quality validation gate added to SkillForge's analysis workflow. The quality gate validates synthesized insights using LLM-as-judge evaluators and triggers retries if quality falls below threshold.

## Architecture

### Components

1. **Quality Gate Node** (`app/workflows/nodes/quality_gate_node.py`)
   - Validates aggregated insights using LLM-as-judge evaluators
   - Evaluates three quality aspects: relevance, depth, coherence
   - Calculates average quality score (0.0-1.0)
   - Determines if gate passes based on 0.7 threshold
   - Emits SSE events for observability

2. **State Extensions** (`app/workflows/state.py`)
   - `quality_scores`: Dict with individual aspect scores
   - `quality_gate_avg_score`: Average score across all aspects
   - `quality_gate_passed`: Boolean gate result
   - `quality_gate_retry_count`: Number of retry attempts
   - `quality_gate_error`: Error message if evaluation fails

3. **Workflow Integration** (`app/workflows/graph_builder.py`)
   - Quality gate runs after aggregation/synthesis
   - Conditional routing based on gate result:
     - Pass → Continue to artifact generation
     - Fail + retries available → Increment retry counter → Re-run aggregation
     - Fail + max retries reached → Continue anyway (fail open)
   - Increment retry node tracks retry attempts

### Workflow Flow

```
┌─────────────┐
│  Aggregate  │
│  Findings   │
└──────┬──────┘
       │
       v
┌─────────────┐
│  Quality    │
│  Gate       │
└──────┬──────┘
       │
       ├─────────────────┐
       │                 │
   Pass/MaxRetry      Fail
       │                 │
       v                 v
┌─────────────┐   ┌─────────────┐
│  Generate   │   │  Increment  │
│  Artifact   │   │  Retry      │
└─────────────┘   └──────┬──────┘
                         │
                         └──> Back to Aggregate
```

## Quality Evaluation

### Aspects Evaluated

1. **Relevance** (0-10 scale, normalized to 0.0-1.0)
   - How relevant are the insights to the input content?
   - Evaluator: `create_quality_evaluator("relevance")`

2. **Depth** (0-10 scale, normalized to 0.0-1.0)
   - How thorough and detailed is the analysis?
   - Evaluator: `create_quality_evaluator("depth")`

3. **Coherence** (0-10 scale, normalized to 0.0-1.0)
   - How well-structured and clear are the insights?
   - Evaluator: `create_quality_evaluator("coherence")`

### Scoring Logic

- Each aspect is scored independently by LLM judge (gpt-4o-mini)
- Scores are normalized to 0.0-1.0 range
- Average score = (relevance + depth + coherence) / 3
- Gate passes if avg_score >= 0.7 threshold

### Retry Logic

- **Max retries**: 2 (total 3 attempts: initial + 2 retries)
- **Retry condition**: avg_score < 0.7 AND retry_count < MAX_RETRY_ATTEMPTS
- **Fail open**: If max retries reached, continue to artifact generation anyway
- **Retry increment**: Dedicated node increments `quality_gate_retry_count`

## Error Handling

### Fail Open Strategy

The quality gate uses a "fail open" strategy to ensure the workflow doesn't break:

1. **Evaluation errors**: If LLM evaluation fails, gate passes with error logged
2. **Max retries reached**: After 2 retries, continue regardless of score
3. **Missing insights**: If no insights to validate, gate passes

### Logging and Tracing

- All events logged with structured logging
- LangSmith trace integration for debugging
- SSE events emitted for real-time observability
- Quality scores persisted to state for analysis

## Configuration

### Tunable Parameters

Located in `app/workflows/nodes/quality_gate_node.py`:

```python
QUALITY_THRESHOLD = 0.7  # Minimum score (0-1) to pass gate
MAX_RETRY_ATTEMPTS = 2   # Maximum retry attempts
QUALITY_ASPECTS = ["relevance", "depth", "coherence"]
```

### LLM Judge Model

- Default: `gpt-4o-mini` (cost-effective)
- Can be changed via `judge_model` parameter in evaluator creation
- Evaluators reuse existing LLM infrastructure from `app/core/model_factory`

## Testing

### Unit Tests

Located in `tests/unit/workflows/test_quality_gate_node.py`:

- Test formatting of insights for evaluation
- Test retry logic for all conditions
- Test gate behavior on errors
- Test gate skipping when no insights

Run tests:
```bash
poetry run pytest tests/unit/workflows/test_quality_gate_node.py -v
```

### Integration Testing

To test the full workflow with quality gate:

```bash
# Start backend
poetry run uvicorn app.main:app --reload

# Submit analysis via API
curl -X POST http://localhost:8000/api/v1/analyses \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article", "skill_level": "intermediate"}'

# Monitor SSE stream for quality_gate events
curl http://localhost:8000/api/v1/analyses/{id}/stream
```

## Observability

### SSE Events

Quality gate emits structured SSE events:

```json
{
  "event": "quality_gate",
  "data": {
    "analysis_id": "...",
    "stage": "quality_validation",
    "status": "passed" | "failed",
    "avg_score": 0.75,
    "threshold": 0.7,
    "retry_count": 0,
    "scores": {
      "relevance": {"score": 0.8, "comment": "8/10"},
      "depth": {"score": 0.7, "comment": "7/10"},
      "coherence": {"score": 0.75, "comment": "7.5/10"}
    }
  }
}
```

### Structured Logs

Quality gate logs all events with structured fields:

```python
logger.info(
    "quality_gate_evaluated",
    analysis_id=analysis_id,
    retry_count=retry_count,
    avg_quality_score=avg_score,
    threshold=QUALITY_THRESHOLD,
    gate_passed=gate_passed,
    individual_scores={...},
    duration_seconds=duration,
    trace_id=trace_id,
)
```

### LangSmith Traces

Quality gate integrates with LangSmith:

- Node execution automatically traced by LangGraph
- Runtime metadata includes retry count and quality scores
- LLM judge calls traced for cost and latency analysis

## Future Enhancements

### Potential Improvements

1. **Adaptive thresholds**: Adjust threshold based on content type or complexity
2. **Aspect weights**: Weight aspects differently (e.g., relevance > coherence)
3. **Incremental retry**: Only re-run agents that contributed to low scores
4. **Quality prediction**: Use historical data to predict quality before synthesis
5. **Multi-model judging**: Use multiple judge models for consensus

### Metrics to Track

- Gate pass rate by content type
- Average quality scores over time
- Retry frequency and effectiveness
- Impact of retries on latency
- Correlation between quality scores and user satisfaction

## References

- Issue #301: Add Quality Validation Gate
- `app/evaluation/evaluators/quality.py`: LLM-as-judge evaluators
- `app/workflows/graph_builder.py`: Workflow integration
- `app/workflows/state.py`: State schema
- LangSmith documentation: https://docs.smith.langchain.com/

## Changelog

### v1.0.0 (2025-12-14)
- Initial implementation with 3 quality aspects
- 0.7 threshold, 2 max retries
- Fail-open error handling
- SSE events and structured logging
- Unit test coverage
