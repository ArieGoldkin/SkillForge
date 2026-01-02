---
name: caching-prompt
description: Claude native prompt caching with cache breakpoints
version: 1.0.0
tags: [llm, caching, claude, prompts]
size: atomic
domain: ai-llm
---

# Claude Prompt Caching

## Cache Breakpoint Strategy

```python
class PromptCacheManager:
    def build_cached_messages(
        self,
        system_prompt: str,
        few_shot_examples: str | None = None,
        schema_prompt: str | None = None,
        dynamic_content: str = ""
    ) -> list[dict]:
        """Build messages with cache breakpoints.

        Cache structure:
        1. System prompt (always cached)
        2. Few-shot examples (cached per content type)
        3. Schema documentation (always cached)
        ──────────── CACHE BREAKPOINT ────────────
        4. Dynamic content (NEVER cached)
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

        # Breakpoint 3: Schema documentation
        if schema_prompt:
            content_parts.append({
                "type": "text",
                "text": schema_prompt,
                "cache_control": {"type": "ephemeral"}
            })

        # Dynamic content (NOT cached)
        content_parts.append({
            "type": "text",
            "text": dynamic_content
        })

        return [{"role": "user", "content": content_parts}]
```

## Cost Calculation

```
Without Prompt Caching:
─────────────────────────
System prompt:    2,000 tokens @ $3/MTok = $0.006
Few-shot:         5,000 tokens @ $3/MTok = $0.015
Schema:           1,000 tokens @ $3/MTok = $0.003
User content:    10,000 tokens @ $3/MTok = $0.030
────────────────────────────────────────
Total:           18,000 tokens           = $0.054

With Prompt Caching (90% hit rate):
───────────────────────────────────
Cached prefix:    8,000 tokens @ $0.30/MTok = $0.0024
User content:    10,000 tokens @ $3/MTok    = $0.0300
────────────────────────────────────────
Total:           18,000 tokens              = $0.0324

Savings: 40% per request
```

## Usage Example

```python
from anthropic import Anthropic

client = Anthropic()

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": SYSTEM_PROMPT,  # 2000 tokens
                "cache_control": {"type": "ephemeral"}
            },
            {
                "type": "text",
                "text": FEW_SHOT_EXAMPLES,  # 5000 tokens
                "cache_control": {"type": "ephemeral"}
            },
            {
                "type": "text",
                "text": user_query  # NOT cached
            }
        ]
    }]
)

# Check cache usage
print(f"Cache read: {response.usage.cache_read_input_tokens}")
print(f"Cache creation: {response.usage.cache_creation_input_tokens}")
```

## Best Practices

1. **Order matters**: Put static content first (system, examples, schema)
2. **Minimum size**: Cache requires ~1024 tokens to be effective
3. **TTL**: 5 minutes, auto-refresh on use
4. **Rate limits**: Cache reads don't count (March 2025)

## Combined Strategy

```python
async def llm_with_double_caching(query: str) -> str:
    # L1/L2: Semantic cache first
    cached = await semantic_cache.get(query, agent_type)
    if cached:
        return cached  # 100% savings

    # L3: Prompt caching for cache miss
    response = await client.messages.create(
        messages=prompt_cache_manager.build_cached_messages(
            system_prompt=AGENT_PROMPT,
            few_shot_examples=EXAMPLES,
            dynamic_content=query
        )
    )

    # Store in semantic cache for next time
    await semantic_cache.set(query, response.content, agent_type)

    return response.content
```
