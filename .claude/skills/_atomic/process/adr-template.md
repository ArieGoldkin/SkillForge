---
name: adr-template
description: Architecture Decision Record template (Nygard format)
version: 1.0.0
tags: [adr, architecture, decisions, documentation]
size: atomic
domain: process
---

# Architecture Decision Record

## ADR Template (Nygard Format)

```markdown
# ADR-XXXX: [Title]

## Status

[Proposed | Accepted | Deprecated | Superseded by ADR-YYYY]

## Context

What is the issue that we're seeing that is motivating this decision?
What are the constraints?
What forces are at play?

## Decision

What is the change that we're proposing and/or doing?
State the decision in full sentences, with active voice.

## Consequences

What becomes easier or harder after this change?
What are the trade-offs?

### Positive
- [Benefit 1]
- [Benefit 2]

### Negative
- [Drawback 1]
- [Drawback 2]

### Neutral
- [Neutral consequence]

## Alternatives Considered

### Option A: [Name]
- **Pros:** [List]
- **Cons:** [List]
- **Rejected because:** [Reason]

### Option B: [Name]
- **Pros:** [List]
- **Cons:** [List]
- **Rejected because:** [Reason]

---

**Date:** YYYY-MM-DD
**Author:** [Name]
**Reviewers:** [Names]
```

## When to Write an ADR

- Choosing between technologies (PostgreSQL vs MongoDB)
- Architectural patterns (monolith vs microservices)
- API design decisions (REST vs GraphQL)
- Security approaches (JWT vs sessions)
- Infrastructure choices (Kubernetes vs serverless)

## Naming Convention

```
docs/adr/
├── 0001-use-postgresql-for-storage.md
├── 0002-adopt-react-server-components.md
├── 0003-implement-hybrid-search.md
└── 0004-langfuse-for-observability.md
```

## Best Practices

- ✅ Write ADRs before implementation
- ✅ Keep them short (1-2 pages)
- ✅ Include alternatives considered
- ✅ Never delete, only deprecate
- ✅ Link related ADRs
