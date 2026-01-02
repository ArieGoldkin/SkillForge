---
name: llm-context-separation
description: IDs flow AROUND the LLM, not THROUGH it
version: 1.0.0
tags: [llm, safety, security, context, ids]
size: atomic
domain: ai-llm
---

# LLM Context Separation

## The Core Principle

> **Identifiers flow AROUND the LLM, not THROUGH it.**
> **The LLM sees only content. Attribution happens deterministically.**

## Why This Matters

When identifiers appear in prompts, bad things happen:

1. **Hallucination:** LLM invents IDs that don't exist
2. **Confusion:** LLM mixes up which ID belongs where
3. **Injection:** Attacker manipulates IDs via prompt injection
4. **Leakage:** IDs appear in logs, caches, traces
5. **Cross-tenant:** LLM could reference other users' data

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   SYSTEM CONTEXT (flows around LLM)                             │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ user_id │ tenant_id │ analysis_id │ trace_id            │   │
│   └─────────────────────────────────────────────────────────┘   │
│        │                                               │        │
│        ▼                                               ▼        │
│   ┌─────────┐                                   ┌─────────┐    │
│   │ PRE-LLM │     ┌───────────────┐            │POST-LLM │    │
│   │ FILTER  │────▶│     LLM       │───────────▶│ATTRIBUTE│    │
│   │         │     │               │            │         │    │
│   │ Returns │     │ Sees ONLY:    │            │ Adds:   │    │
│   │ CONTENT │     │ - content     │            │ - IDs   │    │
│   │ (no IDs)│     │ - context     │            │ - refs  │    │
│   └─────────┘     │ (NO IDs!)     │            └─────────┘    │
│                   └───────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

## Forbidden Parameters

| Parameter | Why Forbidden |
|-----------|---------------|
| `user_id` | Can be hallucinated, enables cross-user access |
| `tenant_id` | Critical for multi-tenant isolation |
| `analysis_id` | Job tracking, not for LLM |
| `document_id` | Source tracking, not for LLM |
| `chunk_id` | RAG reference, not for LLM |
| `session_id` | Auth context, not for LLM |
| Any UUID | Pattern: `[0-9a-f]{8}-...` |

## Detection Pattern

```python
import re

FORBIDDEN_PATTERNS = [
    r'user[_-]?id',
    r'tenant[_-]?id',
    r'analysis[_-]?id',
    r'document[_-]?id',
    r'chunk[_-]?id',
    r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
]

def audit_prompt(prompt: str) -> list[str]:
    """Check for forbidden patterns in prompt."""
    violations = []
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, prompt, re.IGNORECASE):
            violations.append(pattern)
    return violations
```

## Request Context Pattern

```python
@dataclass
class RequestContext:
    """System context that flows AROUND the LLM."""
    user_id: UUID
    tenant_id: UUID
    analysis_id: UUID
    trace_id: str
    permissions: set[str]

# Pass through call stack, never into prompts
async def process(ctx: RequestContext, content: str):
    # ctx flows around
    result = await call_llm(content)  # Only content goes in
    return save_with_context(result, ctx)  # ctx added after
```

## Best Practices

- **Never include UUIDs in prompts**
- **Use RequestContext** for system identifiers
- **Audit prompts** before sending to LLM
- **Attribution happens AFTER** LLM returns
