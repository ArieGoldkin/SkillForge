---
name: test-full
description: Full-stack testing composite - backend + frontend + E2E
version: 1.0.0
type: composite
includes:
  - test-backend
  - test-frontend
trigger: "**/*.{py,ts,tsx}"
tags: [testing, fullstack, composite]
---

# Full-Stack Testing Composite

Complete testing strategy for full-stack applications.

## Included Composites

```
test-full
├── test-backend
│   ├── unit-testing-fundamentals
│   ├── unit-testing-python
│   ├── api-mocking-vcr
│   ├── integration-testing
│   └── ai-llm-testing
└── test-frontend
    ├── unit-testing-fundamentals
    ├── unit-testing-typescript
    ├── api-mocking-msw
    └── e2e-testing
```

## Testing Layers

```
┌─────────────────────────────────────────────────────────┐
│                    E2E Tests                             │
│           (Playwright - critical user journeys)          │
├─────────────────────────────────────────────────────────┤
│     Frontend Integration    │    Backend Integration     │
│        (MSW mocking)        │      (VCR recording)       │
├─────────────────────────────────────────────────────────┤
│      Frontend Unit          │       Backend Unit         │
│    (Vitest + Testing Lib)   │    (pytest + fixtures)     │
├─────────────────────────────────────────────────────────┤
│                   Static Analysis                        │
│      (TypeScript + ESLint + Ruff + mypy)                │
└─────────────────────────────────────────────────────────┘
```

## Commands

```bash
# Backend
cd backend
pytest tests/unit/ -v                        # Unit tests
pytest tests/integration/ -v                 # Integration
pytest --cov=app --cov-fail-under=80        # Coverage

# Frontend
cd frontend
npm run test                                 # Unit tests
npm run test:coverage                        # Coverage

# E2E (from root)
npm run test:e2e                             # All E2E
npm run test:e2e -- --headed                 # Watch mode
```

## CI Pipeline

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Backend Tests
        run: |
          cd backend
          poetry install
          poetry run pytest --cov=app --cov-fail-under=80

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Frontend Tests
        run: |
          cd frontend
          npm ci
          npm run test:coverage

  e2e:
    runs-on: ubuntu-latest
    needs: [backend, frontend]
    steps:
      - uses: actions/checkout@v4
      - name: E2E Tests
        run: |
          docker-compose up -d
          npx playwright test
```

## Coverage Targets

| Layer | Target | Scope |
|-------|--------|-------|
| Backend Unit | 90% | Business logic |
| Backend Integration | 80% | API endpoints |
| Frontend Unit | 80% | Components, hooks |
| Frontend Integration | 70% | Data flows |
| E2E | 5-10 flows | Critical paths |

## Quality Gates

- [ ] All tests pass
- [ ] Coverage >= 80%
- [ ] No lint errors
- [ ] Type checks pass
- [ ] E2E critical paths pass
