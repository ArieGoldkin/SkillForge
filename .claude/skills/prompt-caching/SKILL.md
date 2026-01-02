---
name: prompt-caching
description: Provider-native prompt caching for Claude and OpenAI. Use when optimizing LLM costs with cache breakpoints, caching system prompts, or reducing token costs for repeated prefixes.
---

# Prompt Caching

Cache LLM prompt prefixes for 90% token savings.

## When to Use

- Same system prompts across requests
- Few-shot examples in prompts
- Schema documentation in prompts
- High-volume API calls

## Claude Prompt Caching

```python
def build_cached_messages(
    system_prompt: str,
    few_shot_examples: str | None,
    user_content: str
) -> list[dict]:
    """Build messages with cache breakpoints.

    Cache structure:
    1. System prompt (cached)
    2. Few-shot examples (cached)
    ─────── CACHE BREAKPOINT ───────
    3. User content (NOT cached)
    """
    content_parts = []

    # Breakpoint 1: System prompt
    content_parts.append({
        "type": "text",
        "text": system_prompt,
        "cache_control": {"type": "ephemeral"}
    })

    # Breakpoint 2: Few-shot examples
    if few_shot_examples:
        content_parts.append({
            "type": "text",
            "text": few_shot_examples,
            "cache_control": {"type": "ephemeral"}
        })

    # Dynamic content (NOT cached)
    content_parts.append({
        "type": "text",
        "text": user_content
    })

    return [{"role": "user", "content": content_parts}]
```

## Cost Calculation

```
Without Prompt Caching:
System prompt:     2,000 tokens @ $3/MTok  = $0.006
Few-shot examples: 5,000 tokens @ $3/MTok  = $0.015
User content:     10,000 tokens @ $3/MTok  = $0.030
───────────────────────────────────────────────────
Total:            17,000 tokens            = $0.051

With Prompt Caching (90% hit rate):
Cached prefix:     7,000 tokens @ $0.30/MTok = $0.0021
User content:     10,000 tokens @ $3/MTok    = $0.0300
───────────────────────────────────────────────────
Total:            17,000 tokens              = $0.0321

Savings: 37% per request
```

## OpenAI Automatic Caching

```python
# OpenAI caches prefixes automatically
# No cache_control markers needed

response = await openai.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": system_prompt},  # Cached
        {"role": "user", "content": user_content}      # Not cached
    ]
)

# Check cache usage in response
cache_tokens = response.usage.prompt_tokens_cached
```

## Cache TTL

| Provider | TTL | Notes |
|----------|-----|-------|
| Claude | 5 min | Auto-refreshes on use |
| OpenAI | Session | Persists during session |

## Best Practices

```python
# ✅ Good: Long, stable prefix first
messages = [
    {"role": "system", "content": LONG_SYSTEM_PROMPT},
    {"role": "user", "content": FEW_SHOT_EXAMPLES},
    {"role": "user", "content": user_input}  # Variable
]

# ❌ Bad: Variable content early
messages = [
    {"role": "user", "content": user_input},  # Breaks cache
    {"role": "system", "content": LONG_SYSTEM_PROMPT}
]
```

## Key Decisions

| Decision | Recommendation |
|----------|----------------|
| Min prefix size | 1,024 tokens (Claude) |
| Breakpoint count | 2-4 per request |
| Content order | Stable prefix first |
| TTL handling | Keep-alive with periodic calls |

## Common Mistakes

- Variable content before cached prefix
- Too many breakpoints (overhead)
- Prefix too short (min 1024 tokens)
- Not checking cache_read_input_tokens

## Related Skills

- `semantic-caching` - Redis similarity caching
- `cache-cost-tracking` - Cost monitoring
- `llm-streaming` - Streaming with caching
