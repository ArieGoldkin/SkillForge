---
name: e2e-testing
description: End-to-end testing with Playwright
version: 1.0.0
tags: [testing, e2e, playwright, browser]
size: atomic
domain: testing
---

# E2E Testing with Playwright

## Setup

```bash
npm install -D @playwright/test
npx playwright install
```

```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
})
```

## Basic Test Structure

```typescript
import { test, expect } from '@playwright/test'

test.describe('User Authentication', () => {
  test('user can log in', async ({ page }) => {
    await page.goto('/login')

    await page.fill('[name="email"]', 'user@example.com')
    await page.fill('[name="password"]', 'password123')
    await page.click('button[type="submit"]')

    await expect(page).toHaveURL('/dashboard')
    await expect(page.getByText('Welcome back')).toBeVisible()
  })

  test('shows error for invalid credentials', async ({ page }) => {
    await page.goto('/login')

    await page.fill('[name="email"]', 'wrong@example.com')
    await page.fill('[name="password"]', 'wrongpassword')
    await page.click('button[type="submit"]')

    await expect(page.getByText('Invalid credentials')).toBeVisible()
    await expect(page).toHaveURL('/login')
  })
})
```

## Page Object Model

```typescript
// e2e/pages/login.page.ts
import { Page, Locator } from '@playwright/test'

export class LoginPage {
  readonly page: Page
  readonly emailInput: Locator
  readonly passwordInput: Locator
  readonly submitButton: Locator
  readonly errorMessage: Locator

  constructor(page: Page) {
    this.page = page
    this.emailInput = page.locator('[name="email"]')
    this.passwordInput = page.locator('[name="password"]')
    this.submitButton = page.locator('button[type="submit"]')
    this.errorMessage = page.locator('[data-testid="error-message"]')
  }

  async goto() {
    await this.page.goto('/login')
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email)
    await this.passwordInput.fill(password)
    await this.submitButton.click()
  }
}

// e2e/auth.spec.ts
import { test, expect } from '@playwright/test'
import { LoginPage } from './pages/login.page'

test('user can log in', async ({ page }) => {
  const loginPage = new LoginPage(page)
  await loginPage.goto()
  await loginPage.login('user@example.com', 'password123')

  await expect(page).toHaveURL('/dashboard')
})
```

## Fixtures

```typescript
// e2e/fixtures.ts
import { test as base } from '@playwright/test'
import { LoginPage } from './pages/login.page'

type Fixtures = {
  loginPage: LoginPage
  authenticatedPage: Page
}

export const test = base.extend<Fixtures>({
  loginPage: async ({ page }, use) => {
    const loginPage = new LoginPage(page)
    await use(loginPage)
  },

  authenticatedPage: async ({ page }, use) => {
    // Login before test
    await page.goto('/login')
    await page.fill('[name="email"]', 'test@example.com')
    await page.fill('[name="password"]', 'password')
    await page.click('button[type="submit"]')
    await page.waitForURL('/dashboard')
    await use(page)
  },
})

// Usage
test('dashboard shows user data', async ({ authenticatedPage }) => {
  await expect(authenticatedPage.getByText('Welcome')).toBeVisible()
})
```

## API Mocking in E2E

```typescript
test('shows data from API', async ({ page }) => {
  // Mock API response
  await page.route('/api/users', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([{ id: 1, name: 'Mocked User' }]),
    })
  })

  await page.goto('/users')
  await expect(page.getByText('Mocked User')).toBeVisible()
})
```

## Running Tests

```bash
npx playwright test                    # All tests
npx playwright test auth.spec.ts       # Specific file
npx playwright test --headed           # See browser
npx playwright test --ui               # Visual mode
npx playwright show-report             # View report
```

## Best Practices

- **Test critical paths only** - 5-10 key user journeys
- **Use data-testid** - Stable selectors over CSS classes
- **Avoid sleep()** - Use waitFor, expect with timeout
- **Isolate tests** - Each test should be independent
- **Use Page Objects** - Encapsulate page interactions
