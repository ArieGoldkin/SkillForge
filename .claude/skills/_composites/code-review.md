---
name: code-review
description: Comprehensive code review process with conventional comments
version: 1.0.0
tags: [code-review, process, quality]
size: composite
atomics:
  - process/conventional-comments
  - process/review-checklist
---

# Code Review Workflow

## Load Order

```yaml
1. process/conventional-comments  # Comment format and labels
2. process/review-checklist       # Review checklists by area
```

## Review Process

```
┌─────────────────────────────────────────────────────────────┐
│                    CODE REVIEW FLOW                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. OVERVIEW                                                │
│     └── Understand PR purpose and scope                     │
│                                                             │
│  2. CHECKLIST REVIEW                                        │
│     ├── Logic correctness                                   │
│     ├── Security vulnerabilities                            │
│     ├── Performance implications                            │
│     ├── Error handling                                      │
│     └── Test coverage                                       │
│                                                             │
│  3. COMMENT WITH LABELS                                     │
│     ├── [blocking] Must fix before merge                    │
│     ├── [nitpick] Style suggestions                         │
│     ├── [question] Clarifications needed                    │
│     └── [praise] Highlight good patterns                    │
│                                                             │
│  4. VERDICT                                                 │
│     └── Approve / Request Changes / Comment                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Comment Examples

```python
# [blocking] Security: SQL injection vulnerability
# Use parameterized queries instead of string formatting

# [nitpick] Consider extracting to named constant

# [question] Why is this timeout set to 30s?

# [praise] Great use of early returns for readability
```

## Review Priorities

| Priority | Focus | Time |
|----------|-------|------|
| 1 | Security vulnerabilities | Always |
| 2 | Logic correctness | Always |
| 3 | Performance issues | High-traffic paths |
| 4 | Test coverage | New features |
| 5 | Code style | If time permits |
