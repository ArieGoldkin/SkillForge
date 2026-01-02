---
name: llm-post-attribution
description: Post-LLM attribution and context attachment
version: 1.0.0
tags: [llm, safety, attribution, context, deterministic]
size: atomic
domain: ai-llm
---

# Post-LLM Attribution

## Purpose

After LLM returns, attach:
1. System context (user_id, tenant_id, etc.)
2. Source references (document_ids, chunk_ids)
3. Metadata (timestamps, model info)

**Attribution is DETERMINISTIC, not LLM-generated.**

## Implementation

```python
async def save_with_attribution(
    llm_output: dict,
    ctx: RequestContext,
    source_refs: SourceRefs,
) -> Analysis:
    """
    Attach context and references to LLM output.
    Attribution is deterministic, not LLM-generated.
    """
    return await Analysis.create(
        # Generated
        id=uuid4(),

        # From RequestContext (system-provided)
        user_id=ctx.user_id,
        tenant_id=ctx.tenant_id,
        analysis_id=ctx.analysis_id,
        trace_id=ctx.trace_id,

        # From Pre-LLM refs (deterministic)
        source_document_ids=source_refs.document_ids,
        source_chunk_ids=source_refs.chunk_ids,

        # From LLM (content only)
        content=llm_output["analysis"],
        key_concepts=llm_output["key_concepts"],
        difficulty=llm_output["difficulty"],

        # Metadata
        created_at=datetime.utcnow(),
        model_used=MODEL_NAME,
    )
```

## Full Flow Example

```python
async def analyze_content(
    query: str,
    ctx: RequestContext
) -> Analysis:
    """Complete flow: pre-filter → LLM → post-attribute."""

    # Phase 1: Pre-LLM (filter & extract)
    query, context_texts, source_refs = await prepare_for_llm(
        query=query,
        ctx=ctx
    )

    # Phase 2: LLM call (content only)
    prompt = build_prompt(query, context_texts)
    llm_output = await call_llm(prompt)

    # Phase 3: Post-LLM (attribute)
    return await save_with_attribution(
        llm_output=llm_output,
        ctx=ctx,
        source_refs=source_refs
    )
```

## What Goes Where

| Data | Source | When Set |
|------|--------|----------|
| `user_id` | RequestContext | Post-LLM |
| `tenant_id` | RequestContext | Post-LLM |
| `analysis_id` | RequestContext | Post-LLM |
| `source_document_ids` | SourceRefs | Post-LLM |
| `content` | LLM output | Post-LLM |
| `key_concepts` | LLM output | Post-LLM |
| `created_at` | System | Post-LLM |

## Citation Pattern

```python
# LLM returns: {"analysis": "React uses virtual DOM...", ...}
# We add citations deterministically:

citations = []
for i, chunk_id in enumerate(source_refs.chunk_ids):
    citations.append({
        "index": i + 1,
        "chunk_id": chunk_id,
        "document_id": source_refs.document_ids[i // chunks_per_doc]
    })

result = {
    **llm_output,
    "citations": citations,  # Added deterministically
    "user_id": ctx.user_id,
    "tenant_id": ctx.tenant_id
}
```

## Best Practices

- **Never trust LLM for IDs** - it may hallucinate
- **Use RequestContext** for system identifiers
- **Use SourceRefs** for document references
- **Attribution is deterministic** - same refs → same attribution
