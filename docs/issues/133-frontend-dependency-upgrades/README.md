# Issue #133: Frontend Dependency Upgrades

**GitHub Issue:** https://github.com/ArieGoldkin/SkillForge/issues/133
**Status:** In Progress
**Created:** 2025-11-29

## Overview

Systematic upgrade of 8 frontend dependencies from Dependabot PRs.

## Documents

| File | Description |
|------|-------------|
| [ANALYSIS.md](./ANALYSIS.md) | Detailed impact analysis of each dependency |
| [UPGRADE_PLAN.md](./UPGRADE_PLAN.md) | Step-by-step execution plan |

## Related PRs

| PR | Package | Version Change |
|----|---------|----------------|
| #102 | lucide-react | 0.554.0 → 0.555.0 |
| #97 | @types/react | 19.2.6 → 19.2.7 |
| #106 | @tanstack/react-query | 5.90.10 → 5.90.11 |
| #100 | @tanstack/react-router | 1.139.3 → 1.139.10 |
| #104 | @biomejs/biome | 2.3.7 → 2.3.8 |
| #101 | typescript-eslint | 8.47.0 → 8.48.0 |
| #98 | dev-dependencies group | 2 updates |
| #54 | actions/upload-artifact | v4 → v5 |

## Progress

- [ ] Batch 1: Runtime dependencies merged
- [ ] Batch 2: Dev tooling merged
- [ ] Batch 3: CI/CD merged
- [ ] All tests passing
- [ ] Issue closed
