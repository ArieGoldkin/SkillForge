---
name: langfuse-cost
description: Token usage and cost tracking with Langfuse
version: 1.0.0
tags: [langfuse, cost, tokens, pricing, budget]
size: atomic
domain: ai-llm
---

# Langfuse Cost Tracking

## Log Token Usage

```python
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context

@observe(name="llm_call")
async def call_llm(prompt: str, model: str) -> str:
    response = await anthropic.messages.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024
    )

    # Log usage for cost calculation
    langfuse_context.update_current_observation(
        model=model,
        usage={
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "unit": "TOKENS"
        }
    )

    return response.content[0].text
```

## Manual Generation Logging

```python
langfuse = Langfuse()

trace = langfuse.trace(name="analysis", user_id="user_123")

generation = trace.generation(
    name="security_audit",
    model="claude-sonnet-4-20250514",
    model_parameters={"temperature": 1.0, "max_tokens": 4096},
    input=[{"role": "user", "content": "Analyze..."}],
    output="Analysis: Found 3 issues...",
    usage={
        "input": 1500,
        "output": 1000,
        "unit": "TOKENS"
    }
)
# Langfuse auto-calculates: $0.0045 + $0.015 = $0.0195
```

## Custom Model Pricing

```python
# Define pricing for custom/fine-tuned models
langfuse.create_model(
    model_name="claude-sonnet-4-20250514",
    match_pattern="claude-sonnet-4.*",
    unit="TOKENS",
    input_price=0.000003,   # $3/MTok
    output_price=0.000015,  # $15/MTok
)
```

## Query Costs After Analysis

```python
# Get total cost for a trace
trace = langfuse.get_trace(trace_id)
total_cost = sum(
    gen.calculated_total_cost or 0
    for gen in trace.observations
    if gen.type == "GENERATION"
)

# Store in database
await analysis_repo.update(
    analysis_id,
    total_cost_usd=total_cost
)
```

## Dashboard SQL Queries

```sql
-- Top 10 most expensive traces (last 7 days)
SELECT name, user_id, calculated_total_cost
FROM traces
WHERE timestamp > NOW() - INTERVAL '7 days'
ORDER BY calculated_total_cost DESC
LIMIT 10;

-- Average cost by agent type
SELECT
    metadata->>'agent_type' as agent,
    AVG(calculated_total_cost) as avg_cost,
    SUM(calculated_total_cost) as total_cost
FROM traces
GROUP BY agent
ORDER BY total_cost DESC;
```

## Best Practices

- **Always log usage** with input/output tokens
- **Set model name** for automatic pricing lookup
- **Track per-user costs** with user_id
- **Monitor daily** to catch cost spikes early
- **Set budget alerts** in Langfuse dashboard
