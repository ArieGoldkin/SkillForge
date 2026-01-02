---
name: llm-resilience
description: LLM-specific resilience - fallback chains and token budgets
version: 1.0.0
tags: [llm, resilience, fallback, cost-control]
size: atomic
domain: devops
---

# LLM Resilience

## Fallback Chain

```
Request ──▶ [Primary Model] ──success──▶ Response
                │
              fail
                ▼
          [Fallback Model] ──success──▶ Response
                │
              fail
                ▼
          [Cached Response] ──hit──▶ Response
                │
              miss
                ▼
          [Default Response] ──▶ Graceful Degradation
```

## Implementation

```python
async def call_with_fallback(prompt: str) -> str:
    models = [
        "claude-sonnet-4-20250514",
        "gpt-4o-mini",
    ]

    for model in models:
        try:
            return await call_llm(model, prompt)
        except (RateLimitError, ModelOverloadedError):
            continue

    # Try cache
    cached = await semantic_cache.get(prompt)
    if cached:
        return cached

    # Graceful degradation
    return "Analysis temporarily unavailable"
```

## Token Budget Guard

```python
class TokenBudgetGuard:
    def __init__(self, max_tokens: int, model: str):
        self.max_tokens = max_tokens
        self.encoder = tiktoken.encoding_for_model(model)

    def prepare_prompt(self, content: str) -> str:
        tokens = self.encoder.encode(content)

        if len(tokens) <= self.max_tokens:
            return content

        # Strategy 1: Truncate
        truncated = self.encoder.decode(tokens[:self.max_tokens])

        # Strategy 2: Summarize (for important content)
        # summarized = await summarize(content)

        return truncated
```

## Cost Control

```python
async def call_with_budget(prompt: str, max_cost: float = 0.10):
    # Estimate cost
    input_tokens = count_tokens(prompt)
    estimated_cost = (input_tokens / 1_000_000) * 3.00  # $3/MTok

    if estimated_cost > max_cost:
        # Use cheaper model
        return await call_llm("gpt-4o-mini", prompt)

    return await call_llm("claude-sonnet-4-20250514", prompt)
```

## Best Practices

- ✅ Always have fallback models
- ✅ Implement semantic caching
- ✅ Guard against token budget overruns
- ✅ Track costs per request
- ✅ Have graceful degradation message
