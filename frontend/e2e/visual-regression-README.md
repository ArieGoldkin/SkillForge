# Percy Visual Regression Testing

This directory contains visual regression tests for the SkillForge frontend using Percy and Playwright.

## Overview

Percy captures visual snapshots of the application UI across different states, viewports, and themes. It automatically detects visual changes between builds, helping catch unintended UI regressions.

## Setup

### 1. Percy Account Setup

1. Create a Percy account at [percy.io](https://percy.io)
2. Create a new project for SkillForge frontend
3. Copy the `PERCY_TOKEN` from your project settings

### 2. Local Setup

```bash
# Install dependencies (already included in package.json)
npm install

# Set Percy token (for local testing)
export PERCY_TOKEN=your_percy_token_here
```

### 3. GitHub Actions Setup

Add the `PERCY_TOKEN` as a GitHub repository secret:

1. Go to repository Settings > Secrets and variables > Actions
2. Click "New repository secret"
3. Name: `PERCY_TOKEN`
4. Value: Your Percy project token
5. Click "Add secret"

## Running Tests

### Local Development

```bash
# Start the test environment (backend + frontend)
npm run test:env:up

# Run Percy visual regression tests
npm run e2e:percy

# Stop the test environment
npm run test:env:down
```

### CI/CD

Percy tests run automatically on **pull requests only** to avoid consuming snapshot quota on every push.

The workflow:
1. Runs after the build phase completes
2. Starts the test environment (docker-compose)
3. Captures visual snapshots
4. Uploads to Percy for comparison
5. Posts results as PR comment

## Test Coverage

### Pages Tested
- **Homepage** (light/dark mode, with/without input)
- **Library Page** (with cards, empty state)
- **Analysis Progress** (loading, complete, error states)
- **Artifact View** (markdown rendering, dark mode)

### Viewports
- Mobile: 375px (iPhone)
- Tablet: 768px (iPad) - in responsive tests
- Desktop: 1280px (MacBook Pro)

### Themes
- Light mode
- Dark mode

## Configuration

### `.percy.yml`

The Percy configuration file controls:
- **Viewport widths**: `[375, 1280]`
- **Min height**: `1024px` for full-page captures
- **Percy CSS**: Hides dynamic elements (timestamps, animations)
- **Network timeouts**: Ensures pages are fully loaded

### `visual-regression.spec.ts`

The test file structure:
```typescript
test.describe('Visual Regression Tests', () => {
  test.describe('Homepage', () => {
    test('should match homepage snapshot (light mode)', async ({ page }) => {
      // Test implementation
    });
  });

  // More test groups...
});
```

## Best Practices

### 1. Stable Selectors
Use data-testid attributes or semantic selectors (role, aria-label) instead of class names:

```typescript
// Good
await page.waitForSelector('[data-testid="analysis-card"]');
await page.getByRole('article');

// Avoid
await page.waitForSelector('.card-123');
```

### 2. Hide Dynamic Content
Use Percy CSS to hide timestamps, animations, and other dynamic elements:

```css
/* .percy.yml */
percy-css: |
  [data-testid="timestamp"] {
    visibility: hidden !important;
  }
```

### 3. Wait for Stability
Ensure pages are fully loaded before capturing:

```typescript
// Wait for specific element
await page.waitForSelector('[data-testid="content"]', { timeout: 10000 });

// Wait for network idle
await page.waitForLoadState('networkidle');
```

### 4. Skip Tests When Needed
Skip tests that require backend processing or specific data:

```typescript
test('should match loading state', async ({ page }) => {
  test.skip(!!process.env.CI, 'Requires backend LLM processing');
  // Test implementation
});
```

## Troubleshooting

### Issue: Flaky Snapshots

**Symptoms**: Percy shows differences on every build, even without code changes

**Solutions**:
1. Hide dynamic elements (timestamps, animations) in `.percy.yml`
2. Wait for network idle: `await page.waitForLoadState('networkidle')`
3. Add explicit waits for async content: `await page.waitForSelector(...)`
4. Disable animations: `percy-css: "* { animation: none !important; }"`

### Issue: Percy Token Not Found

**Symptoms**: `Error: Missing Percy token`

**Solutions**:
1. Local: `export PERCY_TOKEN=your_token_here`
2. CI: Verify GitHub secret `PERCY_TOKEN` is set
3. Check token is not expired in Percy dashboard

### Issue: Test Environment Not Starting

**Symptoms**: Tests fail with "Cannot connect to localhost:5174"

**Solutions**:
1. Ensure Docker is running: `docker ps`
2. Check ports are not in use: `lsof -i :5174` and `lsof -i :8501`
3. Manually start test environment: `npm run test:env:up`
4. Check logs: `npm run test:env:logs`

### Issue: Snapshots Not Uploading

**Symptoms**: Tests pass locally but no snapshots appear in Percy dashboard

**Solutions**:
1. Verify `PERCY_TOKEN` is correct
2. Check network connectivity to Percy API
3. Review Percy CLI output for error messages
4. Ensure `percy exec` wrapper is used: `percy exec -- playwright test`

## Percy Dashboard

View visual regression results at [percy.io/dashboard](https://percy.io):

- **Builds**: See all snapshot builds and their status
- **Visual Diffs**: Review side-by-side comparisons of changes
- **Baseline**: Approve snapshots to set as new baseline
- **Comments**: Collaborate with team on visual changes

## Resources

- [Percy Documentation](https://www.browserstack.com/docs/percy)
- [Percy + Playwright Integration](https://www.browserstack.com/docs/percy/integrate/playwright)
- [Percy CLI Configuration](https://www.browserstack.com/docs/percy/get-started/cli-configuration)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)

## Maintenance

### Adding New Tests

1. Create a new test in `visual-regression.spec.ts`
2. Use descriptive snapshot names: `percySnapshot(page, 'Page Name - State')`
3. Test multiple viewports if layout changes significantly
4. Test both light and dark mode for color-sensitive components

### Updating Baselines

When intentional visual changes are made:

1. Percy will show differences in the dashboard
2. Review the changes carefully
3. Click "Approve" to update the baseline
4. Future builds will compare against the new baseline

### Monitoring Quota

Percy has snapshot limits based on your plan:

1. Check usage in Percy dashboard
2. Optimize tests to reduce snapshot count
3. Run Percy only on PRs (not on every push)
4. Remove redundant or duplicate snapshots
