---
name: playwright-agents
description: Playwright autonomous test agents - Planner, Generator, Healer
version: 1.0.0
tags: [playwright, testing, e2e, automation]
size: atomic
domain: frontend
---

# Playwright Test Agents

## The Three Agents

```
1. PLANNER   ──▶ Explores app ──▶ Creates specs/checkout.md
                 (uses seed.spec.ts)
                      │
                      ▼
2. GENERATOR ──▶ Reads spec ──▶ Tests live app ──▶ tests/checkout.spec.ts
                 (verifies selectors)
                      │
                      ▼
3. HEALER    ──▶ Runs tests ──▶ Fixes failures ──▶ Updates selectors
```

## Quick Setup

```bash
# Install Playwright
npm install --save-dev @playwright/test

# Add MCP server
claude mcp add playwright npx '@playwright/mcp@latest'

# Initialize agents
npx playwright init-agents --loop=claude
```

## Directory Structure

```
project/
├── specs/              ← Planner outputs (Markdown plans)
├── tests/              ← Generator outputs (Playwright tests)
│   └── seed.spec.ts    ← Required: Planner learns from this
└── playwright.config.ts
```

## seed.spec.ts (Required)

```typescript
// tests/seed.spec.ts
import { test, expect } from '@playwright/test'

test('basic navigation', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveTitle(/My App/)
})

test('user can login', async ({ page }) => {
  await page.goto('/login')
  await page.fill('[name="email"]', 'test@example.com')
  await page.fill('[name="password"]', 'password')
  await page.click('button[type="submit"]')
  await expect(page).toHaveURL('/dashboard')
})
```

## Key Concepts

- **Planner** learns from seed.spec.ts (env setup, auth, elements)
- **Generator** validates live (actually tests app, not just translates)
- **Healer** auto-fixes (finds new selectors when UI changes)

## Best Practices

- ✅ Keep seed.spec.ts up to date
- ✅ Use data-testid for stable selectors
- ✅ Run Healer after UI changes
- ✅ Review generated tests before committing
