---
name: system-design-questions
description: Five-dimension system design interrogation framework
version: 1.0.0
tags: [system-design, planning, architecture, questions]
size: atomic
domain: process
---

# System Design Questions

## The Five Dimensions

### 1. Scale

- How many users/tenants will use this?
- What's the expected data volume (now and 1 year)?
- Read-heavy or write-heavy?
- What happens at 10x? 100x?

### 2. Data

- Where does this data naturally belong?
- What's the primary access pattern?
- Master data or transactional?
- Does it need search? How?

### 3. Security

- Who can access this data/feature?
- How is tenant isolation enforced?
- What attack vectors does this introduce?
- Is there PII involved?

### 4. UX Impact

- What's the expected latency?
- What feedback does user get during operation?
- What happens on failure? Can they retry?
- Is optimistic UI possible?

### 5. Coherence

- Which layers does this touch?
- What contracts/interfaces change?
- Are types consistent frontend ↔ backend?
- Does this break existing clients?

## Quick Assessment Template

```markdown
## Feature: [Name]

### Scale
- Users:
- Data volume:
- Access pattern:

### Data
- Storage location:
- Schema changes:
- Search requirements:

### Security
- Authorization:
- Tenant isolation:
- Attack surface:

### UX
- Target latency:
- Error handling:
- Optimistic updates:

### Coherence
- Affected layers:
- Type changes:
- Breaking changes:

### Decision
[Final approach with rationale]
```

## Anti-Patterns

```
❌ "I'll add an index later if it's slow"
   → Ask: What's the query pattern NOW?

❌ "We can add tenant filtering later"
   → Ask: How is isolation enforced from DAY ONE?

❌ "The frontend can handle any shape"
   → Ask: What's the TypeScript type?

❌ "Users won't do that"
   → Ask: What's the attack vector?
```
