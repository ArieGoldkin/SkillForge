---
name: langfuse-evaluation
description: LLM output scoring and evaluation with Langfuse
version: 1.0.0
tags: [langfuse, evaluation, scores, quality, testing]
size: atomic
domain: ai-llm
---

# Langfuse Evaluation

## Score Traces

```python
from langfuse import Langfuse

langfuse = Langfuse()

trace = langfuse.trace(name="content_analysis", id="trace_123")

# After LLM response, score it
trace.score(
    name="relevance",
    value=0.85,  # 0-1 scale
    comment="Response addresses query but lacks depth"
)

trace.score(
    name="factuality",
    value=0.92,
    data_type="NUMERIC"
)

trace.score(
    name="approved",
    value=1,  # Boolean as 0/1
    data_type="BOOLEAN"
)
```

## Automated Scoring (G-Eval)

```python
from app.shared.services.g_eval import GEvalScorer

scorer = GEvalScorer()
scores = await scorer.score(
    query=user_query,
    response=llm_response,
    criteria=["relevance", "coherence", "depth"]
)

for criterion, score in scores.items():
    trace.score(name=criterion, value=score)
```

## Datasets for Regression Testing

```python
# Create dataset in Langfuse UI with test cases
dataset = langfuse.get_dataset("security_audit_test_set")

for item in dataset.items:
    # Run LLM
    response = await llm.generate(item.input)

    # Create observation linked to dataset item
    trace = langfuse.trace(
        name="evaluation_run",
        metadata={"dataset_item_id": item.id}
    )
    trace.generation(
        input=item.input,
        output=response,
        usage=response.usage
    )

    # Score against expected output
    score = evaluate(item.expected_output, response)
    langfuse.score(
        trace_id=trace.id,
        name="accuracy",
        value=score
    )
```

## Score Trends Query

```sql
SELECT
    DATE(timestamp) as date,
    AVG(value) FILTER (WHERE name = 'relevance') as avg_relevance,
    AVG(value) FILTER (WHERE name = 'depth') as avg_depth,
    AVG(value) FILTER (WHERE name = 'factuality') as avg_factuality
FROM scores
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp)
ORDER BY date;
```

## Quality Gate Pattern

```python
@observe(name="quality_gate")
async def quality_gate(llm_output: str, context: str) -> bool:
    """Score output and decide if it passes."""

    scores = await scorer.score(
        response=llm_output,
        context=context,
        criteria=["relevance", "grounding", "completeness"]
    )

    # Log all scores
    for name, value in scores.items():
        langfuse_context.update_current_observation(
            metadata={f"score_{name}": value}
        )

    # Quality threshold
    avg_score = sum(scores.values()) / len(scores)
    passed = avg_score >= 0.7

    langfuse_context.update_current_observation(
        output={"passed": passed, "avg_score": avg_score}
    )

    return passed
```

## Dashboard Views

- **Score distributions**: Histogram of scores by type
- **Quality trends**: Track improvement over time
- **Filter by threshold**: Find low-quality traces
- **Compare prompts**: Which version scores higher?

## Best Practices

- **Score all production traces** for quality monitoring
- **Use 0-1 scale** for consistency
- **Add comments** explaining low scores
- **Create datasets** for regression testing
- **Set quality thresholds** for automated gates
