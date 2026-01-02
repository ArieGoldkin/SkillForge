---
name: conventional-comments
description: Standardized code review comment format with labels
version: 1.0.0
tags: [code-review, comments, feedback, collaboration]
size: atomic
domain: process
---

# Conventional Comments

## Format

```
<label> [decorations]: <subject>

[discussion]
```

## Labels

| Label | Meaning | Blocks Merge? |
|-------|---------|---------------|
| **praise** | Highlight positive | No |
| **nitpick** | Minor, optional | No |
| **suggestion** | Propose improvement | No |
| **issue** | Problem to address | Usually |
| **question** | Request clarification | No |
| **thought** | Idea to consider | No |
| **security** | Security concern | **Yes** |
| **bug** | Potential bug | **Yes** |

## Decorations

| Decoration | Meaning |
|------------|---------|
| **[blocking]** | Must address before merge |
| **[non-blocking]** | Optional, can defer |
| **[if-minor]** | Only if quick fix |

## Examples

```typescript
praise: Excellent use of TypeScript generics!
This makes the function much more reusable.

---

nitpick [non-blocking]: Consider const instead of let
This variable is never reassigned.

---

issue: Missing error handling for API call
If the API returns 500, this will crash.
Add try/catch:
```typescript
try {
  const data = await fetchUser(userId);
} catch (error) {
  throw new UserNotFoundError(userId);
}
```

---

security [blocking]: Endpoint missing auth
Add middleware:
```typescript
router.get('/admin/users', requireAdmin, getUsers);
```
```

## Best Practices

- ✅ Be specific with line references
- ✅ Explain *why* not just *what*
- ✅ Provide concrete alternatives
- ✅ Use blocking only for critical issues
