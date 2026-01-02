---
name: llm-safety
description: Secure LLM integration patterns
version: 1.0.0
type: composite
includes:
  - ai-llm/llm-context-separation
  - ai-llm/llm-pre-filter
  - ai-llm/llm-post-attribution
  - ai-llm/llm-output-guardrails
trigger: "**/llm/**/*.py"
---

# LLM Safety Patterns

Complete guide for secure LLM integration - prevent hallucination, injection, and data leakage.

## When to Use

- Building any LLM-powered feature
- Implementing RAG pipelines
- Multi-tenant LLM applications
- Auditing existing LLM code

## Core Principle

> **Identifiers flow AROUND the LLM, not THROUGH it.**
> **The LLM sees only content. Attribution happens deterministically.**

## Architecture Overview

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
│   └─────────┘     │  (content     │            └─────────┘    │
│        │          │   only!)      │                   │        │
│        │          └───────────────┘                   │        │
│        │                 │                            │        │
│        │                 ▼                            │        │
│        │          ┌─────────────┐                     │        │
│        └─────────▶│  GUARDRAILS │◀────────────────────┘        │
│                   │  (validate) │                              │
│                   └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

## Included Skills

1. **llm-context-separation** - IDs flow around, never through LLM
2. **llm-pre-filter** - Tenant filtering, content extraction
3. **llm-post-attribution** - Deterministic ID attachment
4. **llm-output-guardrails** - Schema validation, UUID detection

## Quick Start

```python
@dataclass
class RequestContext:
    user_id: UUID
    tenant_id: UUID
    analysis_id: UUID

async def analyze_safely(query: str, ctx: RequestContext) -> Analysis:
    # Phase 1: Pre-LLM (filter by tenant, extract content)
    query, context_texts, source_refs = await prepare_for_llm(query, ctx)

    # Phase 2: Build safe prompt (audit for IDs)
    prompt = build_prompt(query, context_texts)
    violations = audit_prompt(prompt)
    if violations:
        raise SecurityError(f"IDs in prompt: {violations}")

    # Phase 3: LLM call (content only)
    llm_output = await call_llm(prompt)

    # Phase 4: Validate output
    validation = await validate_output(llm_output, context_texts)
    if not validation.valid:
        raise ValidationError(validation.reason)

    # Phase 5: Post-LLM attribution (deterministic)
    return await save_with_attribution(llm_output, ctx, source_refs)
```

## Checklist Before Any LLM Call

- [ ] RequestContext available with user_id, tenant_id
- [ ] Data filtered by tenant_id and user_id
- [ ] Content extracted without IDs
- [ ] Source references saved for attribution
- [ ] Prompt passes audit (no forbidden patterns)
- [ ] Output validated before use
- [ ] Attribution uses context, not LLM output

## See Also

- [llm-context-separation](../_atomic/ai-llm/llm-context-separation.md)
- [llm-pre-filter](../_atomic/ai-llm/llm-pre-filter.md)
- [llm-post-attribution](../_atomic/ai-llm/llm-post-attribution.md)
- [llm-output-guardrails](../_atomic/ai-llm/llm-output-guardrails.md)
