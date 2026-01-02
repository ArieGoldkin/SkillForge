# Skill Orchestration System

## Architecture

```
.claude/skills/
├── _atomic/                     ← Focused, single-purpose skills (~100-200 lines)
│   ├── testing/                 ← 8 testing skills
│   ├── security/                ← 5 security skills
│   └── ai-llm/                  ← 4 caching skills
├── _composites/                 ← Combined workflows
│   ├── test-backend.md
│   ├── test-frontend.md
│   ├── test-full.md
│   ├── security-audit.md
│   └── llm-caching.md
├── _orchestration/              ← This directory
│   ├── manifest.json
│   └── README.md
└── [domain-skills]/             ← Not yet decomposed (future work)
```

## Atomic Skills

Single-purpose, ~100-200 lines each:

### Testing (8 skills)
| Skill | Purpose |
|-------|---------|
| `unit-testing-fundamentals` | AAA pattern, isolation, test design |
| `unit-testing-python` | pytest, fixtures, parametrize |
| `unit-testing-typescript` | Vitest, Testing Library |
| `api-mocking-msw` | Mock Service Worker (frontend) |
| `api-mocking-vcr` | VCR.py HTTP recording (Python) |
| `integration-testing` | API, database testing |
| `e2e-testing` | Playwright browser automation |
| `ai-llm-testing` | LLM mocking, timeout patterns |

### Security (5 skills)
| Skill | Purpose |
|-------|---------|
| `owasp-top10` | Top 10 vulnerabilities & mitigations |
| `auth-patterns` | JWT, sessions, RBAC |
| `input-sanitization` | XSS, injection prevention |
| `secrets-management` | Env vars, secret detection |
| `security-scanning` | npm audit, semgrep, etc. |

### AI/LLM (4 skills)
| Skill | Purpose |
|-------|---------|
| `caching-hierarchy` | L1/L2/L3/L4 cache architecture |
| `caching-semantic` | Redis vector cache |
| `caching-prompt` | Claude native prompt caching |
| `caching-observability` | Langfuse cost tracking |

## Composites

Bundles of atomic skills for common workflows:

| Composite | Includes | Trigger |
|-----------|----------|---------|
| `test-backend` | 5 testing skills | `backend/**/*.py` |
| `test-frontend` | 4 testing skills | `frontend/**/*.{ts,tsx}` |
| `test-full` | backend + frontend | `**/*.{py,ts,tsx}` |
| `security-audit` | 5 security skills | manual |
| `llm-caching` | 4 caching skills | `**/workflows/**/*.py` |

## Orchestration Patterns

### Auto-Routing
```json
{
  "routing": {
    "backend/**/*.py": "test-backend",
    "frontend/**/*.tsx": "test-frontend"
  }
}
```

### Pipelines
```json
{
  "pipelines": {
    "verify": {
      "steps": [
        { "mode": "parallel", "skills": ["lint", "test-full", "security-audit"] }
      ]
    }
  }
}
```

## Benefits

| Before | After |
|--------|-------|
| Load 1,200 lines for any test task | Load 100-200 lines for specific need |
| One-size-fits-all | Context-aware routing |
| Monolithic skills | Composable atomics |
| Hard to update | Change one, others unaffected |

## Future Work

Skills not yet decomposed (in root directory):
- `ai-native-development`
- `api-design-framework`
- `database-schema-designer`
- `devops-deployment`
- `langgraph-workflows`
- `observability-monitoring`
- `performance-optimization`
- `pgvector-search`

These can be decomposed following the same pattern when needed.
