---
name: defense-layers
description: 8-layer defense-in-depth security architecture
version: 1.0.0
tags: [security, defense-in-depth, layers, validation]
size: atomic
domain: tools
---

# Defense-in-Depth Layers

## 8-Layer Architecture

```
┌──────────────────────────────────────────────────────┐
│ Layer 0: EDGE        │ WAF, Rate Limiting, DDoS      │
├──────────────────────────────────────────────────────┤
│ Layer 1: GATEWAY     │ JWT Verify, Build Context     │
├──────────────────────────────────────────────────────┤
│ Layer 2: INPUT       │ Schema Validation, PII Check  │
├──────────────────────────────────────────────────────┤
│ Layer 3: AUTHZ       │ RBAC/ABAC, Tenant Check       │
├──────────────────────────────────────────────────────┤
│ Layer 4: DATA        │ Parameterized Queries         │
├──────────────────────────────────────────────────────┤
│ Layer 5: LLM         │ No IDs in Prompts             │
├──────────────────────────────────────────────────────┤
│ Layer 6: OUTPUT      │ Schema Validation, Guardrails │
├──────────────────────────────────────────────────────┤
│ Layer 7: STORAGE     │ Attribution, Audit Trail      │
├──────────────────────────────────────────────────────┤
│ Layer 8: OBSERVABILITY│ Sanitized Logging, Tracing  │
└──────────────────────────────────────────────────────┘
```

## Key Patterns

### Layer 1: Request Context

```python
@dataclass(frozen=True)
class RequestContext:
    user_id: UUID
    tenant_id: UUID
    permissions: frozenset[str]
    request_id: str
```

### Layer 3: Authorization

```python
async def authorize(ctx, action, resource):
    if action not in ctx.permissions:
        raise Forbidden("Missing permission")
    if resource.tenant_id != ctx.tenant_id:
        raise Forbidden("Cross-tenant denied")
```

### Layer 4: Tenant Scoping

```python
class TenantScopedRepository:
    def __init__(self, ctx):
        self._base_filter = {"tenant_id": ctx.tenant_id}

    async def find(self, query):
        safe_query = {**self._base_filter, **query}
        return await self.db.find(safe_query)
```

### Layer 5: LLM Safety

IDs flow AROUND the LLM, not THROUGH it.

## Checklist

- [ ] Layer 0: Rate limiting configured
- [ ] Layer 1: JWT validation active
- [ ] Layer 2: Pydantic validates all input
- [ ] Layer 3: Authorization check on every endpoint
- [ ] Layer 4: All queries include tenant_id
- [ ] Layer 5: No IDs in LLM prompts
- [ ] Layer 6: Output schema validation
- [ ] Layer 7: Attribution uses context
- [ ] Layer 8: Logging sanitized
