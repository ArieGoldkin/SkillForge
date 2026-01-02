---
name: cost-optimization
description: Reduce LLM API costs through caching, model selection, and batching
version: 1.0.0
tags: [ai, llm, cost, optimization, caching, batching, tokens]
size: atomic
domain: ai-llm
---

# LLM Cost Optimization

## Cost Comparison (Dec 2025)

| Provider | Model | Input | Output | Best For |
|----------|-------|-------|--------|----------|
| Anthropic | Claude 4.5 Opus | $15/MTok | $75/MTok | Complex reasoning |
| Anthropic | Claude 4 Sonnet | $3/MTok | $15/MTok | Balanced tasks |
| Anthropic | Claude 4 Haiku | $0.25/MTok | $1.25/MTok | High-volume |
| OpenAI | GPT-4 Turbo | $10/MTok | $30/MTok | Code, analysis |
| OpenAI | GPT-3.5 Turbo | $0.50/MTok | $1.50/MTok | Simple tasks |
| Local | Ollama | $0 | $0 | Dev, CI (93% savings) |

## Model Selection Strategy

```python
def select_model(task_complexity: str, cost_priority: bool = True) -> str:
    """Select optimal model based on task complexity and cost."""

    if task_complexity == "simple":
        # Haiku for classification, extraction, simple chat
        return "claude-3-haiku-20240307" if cost_priority else "claude-sonnet-4-20250514"

    elif task_complexity == "moderate":
        # Sonnet for most tasks
        return "claude-sonnet-4-20250514"

    elif task_complexity == "complex":
        # Opus for multi-step reasoning, code generation
        return "claude-opus-4-5-20250514"

    return "claude-sonnet-4-20250514"  # Default
```

## Token Counting

```python
import tiktoken

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count tokens for cost estimation."""
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))

def estimate_cost(input_text: str, output_tokens: int, model: str) -> float:
    """Estimate API cost in dollars."""
    PRICING = {
        "claude-opus-4-5-20250514": (0.015, 0.075),   # (input, output) per 1K tokens
        "claude-sonnet-4-20250514": (0.003, 0.015),
        "gpt-4-turbo-preview": (0.01, 0.03),
    }

    input_tokens = count_tokens(input_text)
    rates = PRICING.get(model, (0.003, 0.015))

    return (input_tokens * rates[0] + output_tokens * rates[1]) / 1000
```

## Caching Strategies

### Prompt Caching (Claude Native)

```python
# 90% cost savings on repeated context
response = anthropic.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    system=[{
        "type": "text",
        "text": LONG_SYSTEM_PROMPT,  # 1000+ tokens
        "cache_control": {"type": "ephemeral"}  # Cache for 5 min
    }],
    messages=[{"role": "user", "content": query}]
)
```

### Semantic Caching (Redis)

```python
async def get_with_semantic_cache(query: str, threshold: float = 0.92) -> str:
    """Return cached response if semantically similar query exists."""
    query_embedding = await embed_text(query)

    # Search for similar cached queries
    cached = await redis_vector.search(query_embedding, threshold=threshold)
    if cached:
        return cached.response  # 70-85% cost savings

    # Cache miss - call LLM
    response = await llm.complete(query)
    await redis_vector.store(query_embedding, response)
    return response
```

## Batching Requests

```python
async def batch_process(items: list[str], batch_size: int = 10) -> list[str]:
    """Process items in batches to reduce API calls."""
    results = []

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]

        # Single prompt for batch
        batch_prompt = "\n".join(f"{j+1}. {item}" for j, item in enumerate(batch))

        response = await llm.complete(f"Process these items:\n{batch_prompt}")

        # Parse batch response
        results.extend(parse_batch_response(response))

    return results
```

## max_tokens Optimization

```python
# Set max_tokens based on expected output
TASK_TOKEN_LIMITS = {
    "classification": 50,      # "positive", "negative", etc.
    "extraction": 200,         # Short structured data
    "summary": 500,            # Paragraph summary
    "analysis": 1000,          # Detailed analysis
    "generation": 2000,        # Content creation
}

response = await llm.complete(
    prompt,
    max_tokens=TASK_TOKEN_LIMITS.get(task_type, 1000)
)
```

## SkillForge Cost Results

```
Baseline (no optimization):    $35,000/year
With prompt caching (90%):     -$31,500
With semantic cache (75%):     -$2,625
Final cost:                    $875/year (97.5% reduction)
```

## Best Practices

- **Use Haiku**: For classification, extraction, simple tasks
- **Prompt cache**: Enable for repeated system prompts
- **Semantic cache**: Cache similar queries with vector search
- **Batch requests**: Combine multiple items in one call
- **Local models**: Use Ollama for dev/CI (93% savings)
- **Set max_tokens**: Don't use default 4096 for short outputs
