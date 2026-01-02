---
name: quality-gates
description: Quality gates with complexity scoring and LLM validation
version: 1.0.0
tags: [quality, validation, gates, llm-judge]
size: composite
atomics:
  - process/complexity-scoring
  - process/blocking-thresholds
  - process/llm-judge-validation
---

# Quality Gates System

## Load Order

```yaml
1. process/complexity-scoring     # Task complexity 1-5 scale
2. process/blocking-thresholds    # What blocks merge/deploy
3. process/llm-judge-validation   # LLM-as-judge patterns
```

## Gate Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    QUALITY GATE FLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Code Commit                                                │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────┐                                   │
│  │ GATE 1: Pre-commit  │ Format, lint, type check          │
│  └─────────────────────┘                                   │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────┐                                   │
│  │ GATE 2: CI Tests    │ Unit, integration tests           │
│  └─────────────────────┘                                   │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────┐                                   │
│  │ GATE 3: LLM Review  │ Optional AI validation            │
│  └─────────────────────┘                                   │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────┐                                   │
│  │ GATE 4: Human Review│ Code review approval              │
│  └─────────────────────┘                                   │
│       │                                                     │
│       ▼                                                     │
│  Merge to Main                                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Blocking Conditions

| Gate | Blocking If |
|------|-------------|
| Pre-commit | Lint errors, type errors |
| CI Tests | Test failures, <80% coverage |
| LLM Review | Security vulnerabilities flagged |
| Human Review | Blocking comments unresolved |

## Complexity-Based Requirements

| Complexity | Tests | Review | Documentation |
|------------|-------|--------|---------------|
| 1-2 | Unit | 1 reviewer | Inline comments |
| 3 | Unit + Integration | 1 reviewer | README update |
| 4-5 | Full suite | 2 reviewers | ADR + docs |
