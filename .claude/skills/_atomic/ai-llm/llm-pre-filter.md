---
name: llm-pre-filter
description: Pre-LLM filtering and content extraction
version: 1.0.0
tags: [llm, safety, filtering, rag, retrieval]
size: atomic
domain: ai-llm
---

# Pre-LLM Filtering

## Purpose

Before calling the LLM:
1. Filter data by tenant/user permissions
2. Extract content (remove IDs)
3. Save references for post-LLM attribution

## Implementation

```python
@dataclass
class SourceRefs:
    """References saved for post-LLM attribution."""
    document_ids: list[UUID]
    chunk_ids: list[UUID]

async def prepare_for_llm(
    query: str,
    ctx: RequestContext,
) -> tuple[str, list[str], SourceRefs]:
    """
    Filter data and extract content for LLM.

    Returns: (query, context_texts, source_references)
    """
    # 1. Retrieve with tenant filter (CRITICAL)
    documents = await semantic_search(
        query_embedding=embed(query),
        tenant_id=ctx.tenant_id,  # Filter by tenant
        user_id=ctx.user_id,      # Filter by user
    )

    # 2. Save references for attribution
    source_refs = SourceRefs(
        document_ids=[d.id for d in documents],
        chunk_ids=[c.id for d in documents for c in d.chunks],
    )

    # 3. Extract content only (NO IDs)
    content_texts = [d.content for d in documents]

    return query, content_texts, source_refs
```

## Build Safe Prompt

```python
def build_prompt(content: str, context_texts: list[str]) -> str:
    """Build prompt with ONLY content, no identifiers."""

    prompt = f"""
    Analyze the following content.

    CONTENT:
    {content}

    RELEVANT CONTEXT:
    {chr(10).join(f"- {text}" for text in context_texts)}

    Provide analysis covering:
    1. Key concepts
    2. Prerequisites
    3. Learning objectives
    """

    # AUDIT: Verify no IDs leaked
    violations = audit_prompt(prompt)
    if violations:
        raise SecurityError(f"IDs leaked to prompt: {violations}")

    return prompt
```

## Tenant Filtering SQL

```sql
-- ALWAYS filter by tenant_id
SELECT content, embedding
FROM chunks c
JOIN documents d ON c.document_id = d.id
WHERE d.tenant_id = $1  -- REQUIRED
  AND (d.user_id = $2 OR d.is_public = true)
ORDER BY c.embedding <=> $3
LIMIT 10;
```

## Pre-LLM Checklist

- [ ] Query filtered by `tenant_id`
- [ ] Query filtered by `user_id` or `is_public`
- [ ] Content extracted without IDs
- [ ] Source references saved for attribution
- [ ] Prompt passes audit (no forbidden patterns)

## Best Practices

- **Always filter by tenant** before any data access
- **Extract content only** - IDs stay in SourceRefs
- **Audit prompt** before sending
- **Save refs** for post-LLM attribution
