---
name: webapp-testing
description: Playwright autonomous test agents for E2E testing
version: 1.0.0
tags: [playwright, testing, e2e, automation]
size: composite
atomics:
  - frontend/playwright-agents
---

# Webapp Testing Composite

Autonomous E2E testing with Playwright agents.

## When to Use

- Setting up E2E test automation
- Auto-generating tests from app exploration
- Self-healing tests after UI changes

## Atomic Skills

### 1. Playwright Agents (`playwright-agents`)
Planner, Generator, and Healer agents for autonomous testing.

## Quick Reference

```
┌─────────────────────────────────────────────────────────────┐
│  PLAYWRIGHT AGENT WORKFLOW                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Create seed.spec.ts (auth, basic nav)                   │
│  2. PLANNER explores app ──► specs/*.md                     │
│  3. GENERATOR creates tests ──► tests/*.spec.ts             │
│  4. HEALER fixes broken tests after UI changes              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Setup

```bash
npm install --save-dev @playwright/test
claude mcp add playwright npx '@playwright/mcp@latest'
npx playwright init-agents --loop=claude
```

## Related Atomics

Consider combining with:
- `testing-strategy-builder` composite for test planning
- `golden-dataset` composite for validation data
