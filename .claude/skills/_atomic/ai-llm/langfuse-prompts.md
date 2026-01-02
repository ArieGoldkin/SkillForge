---
name: langfuse-prompts
description: Prompt versioning and management with Langfuse
version: 1.0.0
tags: [langfuse, prompts, versioning, management]
size: atomic
domain: ai-llm
---

# Langfuse Prompt Management

## Fetch Prompt

```python
from langfuse import Langfuse

langfuse = Langfuse()

# Get latest production version
prompt = langfuse.get_prompt("security_auditor", label="production")

# Use in LLM call
response = await llm.generate(
    messages=[
        {"role": "system", "content": prompt.compile()},
        {"role": "user", "content": user_input}
    ]
)
```

## Prompt Versioning

```
security_auditor
├── v1 (Jan 15) - production
│   └── "You are a security auditor..."
├── v2 (Jan 20) - staging
│   └── "You are an expert security auditor..."
└── v3 (Jan 25) - draft
    └── "As a cybersecurity expert..."
```

## Link Prompt to Generation

**CRITICAL:** To track prompt usage in Langfuse UI:

```python
from langfuse import get_client

langfuse = get_client()
prompt = langfuse.get_prompt("security_auditor", label="production")

# Method 1: update_current_generation
langfuse.update_current_generation(prompt=prompt)

# Method 2: Pass when starting generation
with langfuse.start_as_current_generation(
    name="security-analysis",
    model="claude-sonnet-4-20250514",
    prompt=prompt  # Links automatically!
) as generation:
    response = await llm.generate(...)
    generation.update(output=response)
```

## Template Variables

```python
# Define prompt with variables in Langfuse UI:
# "You are a {role}. Analyze for {criteria}."

prompt = langfuse.get_prompt("analyzer")
compiled = prompt.compile(
    role="security auditor",
    criteria="XSS vulnerabilities"
)
# → "You are a security auditor. Analyze for XSS vulnerabilities."
```

## Caching Pattern

```python
class PromptManager:
    """L1 cache + Langfuse fetch."""

    def __init__(self):
        self._cache: dict[str, tuple[str, Any]] = {}

    async def get_prompt_with_client(
        self, name: str, label: str = "production"
    ) -> tuple[str, Any]:
        cache_key = f"{name}:{label}"

        if cache_key in self._cache:
            content, _ = self._cache[cache_key]
            return content, None  # No client for cache hits

        prompt = langfuse.get_prompt(name, label=label)
        content = prompt.compile()
        self._cache[cache_key] = (content, prompt)

        return content, prompt  # Return client for linking
```

## A/B Testing

```python
import random

prompt_v1 = langfuse.get_prompt("analyzer", version=1)
prompt_v2 = langfuse.get_prompt("analyzer", version=2)

for test_input in dataset:
    prompt = random.choice([prompt_v1, prompt_v2])
    response = await llm.generate(prompt.compile())

    langfuse.trace(
        name="ab_test",
        metadata={"prompt_version": prompt.version}
    )

# Compare in UI: filter by prompt_version, compare scores
```

## Best Practices

- **Use labels** (production, staging, draft) not version numbers
- **Link prompts to generations** for usage tracking
- **Cache prompts** to reduce API calls
- **A/B test** prompt changes before deploying
