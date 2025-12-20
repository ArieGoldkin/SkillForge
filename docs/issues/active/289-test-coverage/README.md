# Issue #289: Backend Test Coverage 76% → 80%

**Status:** Planning
**Assignee:** TBD (Backend)
**Sprint:** Backlog - Technical Debt
**Priority:** Medium
**GitHub Issue:** [#289](https://github.com/ArieGoldkin/SkillForge/issues/289)
**Feature Branch:** `issue/289-test-coverage`

---

## Issue Overview

**Title:** test: Increase backend test coverage from 76% to 80%

**Description:**
Backend CI is failing due to test coverage being below the required 80% threshold. All 1553 tests pass - this is purely a coverage gap issue requiring additional unit tests.

**Labels:** `testing`, `backend`, `technical-debt`

---

## Quick Stats

| Metric | Value |
|--------|-------|
| Current Coverage | 76% (80% locally with all tests) |
| Target Coverage | 80%+ |
| Lines to Cover | ~1,815 |
| Files Below 80% | 7 files |
| Critical (0%) | 2 files |
| Estimated Effort | 3-4 days |

---

## Coverage Gap Summary

### Critical (0% Coverage)

| File | Lines | Impact |
|------|-------|--------|
| `app/api/dependencies.py` | 11 | Every endpoint depends on this |
| `app/workflows/nodes/agent_tools.py` | 27 | Supervisor routing core |

### Below Threshold (65-76%)

| File | Coverage | Missing Lines |
|------|----------|---------------|
| `workflows/nodes/parallel_agents.py` | 65.4% | 9 |
| `workflows/agents/base.py` | 67.7% | 20 |
| `workflows/agents/response_processing.py` | 68.4% | 6 |
| `core/agent_config.py` | 71.4% | 6 |
| `main.py` | 75.8% | 15 |

---

## Implementation Phases

```
Phase 1: Critical Gaps (P0)              [Day 1]     ~400 lines
Phase 2: High-Impact Targets             [Day 2-3]   ~900 lines
Phase 3: Quick Wins                      [Day 3]     ~300 lines
Phase 4: Polish (if needed)              [Day 4]     ~200 lines
```

See [PLAN.md](./PLAN.md) for detailed implementation plan.

---

## Verification

```bash
cd backend
poetry run pytest --cov=app --cov-report=term-missing --cov-fail-under=80
```

---

## Related Issues

- **#125:** E2E Tests with Playwright (CLOSED - PR #288)
- **#278:** Seed E2E Test Data (CLOSED - PR #288)
- **#279:** SSE Tests Timeout (CLOSED - PR #288)
- **#280:** Library Search Race Conditions (CLOSED - PR #288)

---

**Plan Created:** December 12, 2025
**Last Updated:** December 12, 2025
**Author:** Claude Code
