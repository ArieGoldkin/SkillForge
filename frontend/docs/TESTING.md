# Modern Testing Infrastructure (2025 Standards)

This document outlines the modern testing infrastructure implemented for the SkillForge frontend, following 2025 industry best practices for scalable, maintainable, and intelligent test automation.

## 🏗️ Architecture Overview

### Core Principles

- **🏷️ Test Categorization**: Comprehensive tagging system for selective execution
- **🌍 Environment Awareness**: Tests adapt to available infrastructure and execution context
- **⚡ Intelligent Execution**: Fast feedback loops with comprehensive coverage when needed
- **📊 Data-Driven**: Performance monitoring and regression detection
- **🔧 Developer Experience**: Intuitive commands and clear feedback

### Test Categories

| Category | Tag | Description | Environment |
|----------|-----|-------------|-------------|
| **Unit** | `@unit` | Pure functions, components, hooks | Always |
| **Integration** | `@integration` | API calls, database operations | With infrastructure |
| **E2E** | `@e2e` | Complete user workflows | `E2E_READY=true` only |
| **Performance** | `@slow` | Load testing, benchmarks | Explicit opt-in |
| **Critical** | `@critical` | Mission-critical functionality | Always in CI |

### Component Types

| Type | Tag | Examples |
|------|-----|----------|
| **Component** | `@component` | React component rendering |
| **Hook** | `@hook` | Custom React hooks |
| **Store** | `@store` | Zustand state management |
| **Util** | `@util` | Pure utility functions |

## 🚀 Quick Start

### Development Testing
```bash
# Fast unit tests (recommended for development)
npm run test:unit

# All tests with UI
npm run test:ui

# Debug specific test
npm run test:debug -- --grep "ProgressTracker"
```

### CI Testing
```bash
# CI validation (unit + integration)
npm run test:ci

# Full suite (nightly/release)
npm run test:coverage
```

### E2E Testing
```bash
# E2E tests (requires infrastructure)
E2E_READY=true npm run test:e2e
```

## 📋 Test Execution Patterns

### Environment-Based Execution

The test suite automatically adapts based on environment variables:

```bash
# Development (fast feedback)
npm run test:unit  # ~30s - unit tests only

# CI (comprehensive validation)
npm run test:ci    # ~2min - unit + integration + coverage

# Staging (full validation)
E2E_READY=true npm run test:coverage  # ~5min - all tests
```

### Selective Test Execution

```bash
# Test specific components
npm run test -- --grep "@component"

# Test critical functionality only
npm run test:critical

# Performance tests
npm run test:performance

# Flaky test retry
npm run test:flaky
```

## 🏷️ Test Tagging System

### Writing Tagged Tests

```typescript
describe('ProgressTracker Component @unit @component', () => {
  it('renders progress correctly', () => {
    // Test implementation
  })
})

describe('API Service @integration', () => {
  it('fetches data from backend', async () => {
    // Requires running backend
  })
})

describe('User Registration Flow @e2e', () => {
  it('completes full registration', async () => {
    // Requires full infrastructure
  })
})
```

### Tag Reference

| Tag | Purpose | Execution |
|-----|---------|-----------|
| `@unit` | Pure logic tests | Always |
| `@integration` | External dependencies | With infrastructure |
| `@e2e` | User workflows | `E2E_READY=true` only |
| `@component` | React components | Always |
| `@hook` | Custom hooks | Always |
| `@store` | State management | Always |
| `@slow` | Performance tests | Opt-in |
| `@critical` | Mission-critical | Always |
| `@flaky` | Unreliable tests | With retry |
| `@dev` | Development-only | Skip in CI |

## 🛠️ Test Utilities

### Environment Detection

```typescript
import { TestEnvironment } from '@/test-utils/environment'

// Check current environment
if (TestEnvironment.isE2EReady) {
  // E2E-specific setup
}

if (TestEnvironment.hasDatabase) {
  // Database-dependent tests
}
```

### Smart Test Execution

```typescript
import { conditionalTest } from '@/test-utils/environment'

conditionalTest.e2e('runs only with E2E infrastructure', () => {
  // Only executes when E2E_READY=true
})

conditionalTest.withDatabase('requires database connection', () => {
  // Only executes with database available
})
```

### Test Data Factory

```typescript
import { testDataFactory } from '@/test-utils/test-helpers'

const user = testDataFactory.createUser({ role: 'admin' })
const analysis = testDataFactory.createAnalysis({
  status: 'completed',
  wordCount: 1500
})
```

### Enhanced Rendering

```typescript
import { renderWithProviders } from '@/test-utils/test-helpers'

// Includes React Query, Router, and all providers
const { screen } = renderWithProviders(<MyComponent />)
```

## 📊 Coverage & Quality Gates

### Coverage Thresholds

```json
{
  "global": {
    "branches": 80,
    "functions": 80,
    "lines": 80,
    "statements": 80
  },
  "./src/features/": {
    "branches": 85,
    "functions": 85
  }
}
```

### Quality Gates

- **Linting**: ESLint + Biome (zero warnings)
- **TypeScript**: Strict type checking
- **Coverage**: Minimum thresholds enforced
- **Performance**: Regression detection for slow tests

## 🔧 Configuration Files

### Vitest Configuration (`vitest.config.ts`)

```typescript
export default defineConfig({
  test: {
    // Environment-aware filtering
    testNamePattern: process.env.E2E_READY === 'true'
      ? undefined
      : /^(?!.*@e2e).*$/,

    // Comprehensive tagging
    tags: { /* ... */ },

    // Coverage with component-specific thresholds
    coverage: { /* ... */ },

    // Smart timeouts and retries
    testTimeout: process.env.CI ? 10000 : 5000,
    retry: process.env.CI ? 2 : 0,
  }
})
```

### Package.json Scripts

```json
{
  "scripts": {
    "test:unit": "vitest run --grep \"@unit\"",
    "test:integration": "vitest run --grep \"@integration\"",
    "test:e2e": "E2E_READY=true vitest run --grep \"@e2e\"",
    "test:ci": "vitest run --grep \"@ci\" --coverage",
    "test:performance": "RUN_PERFORMANCE_TESTS=true vitest run --grep \"@slow\""
  }
}
```

## 🚨 CI/CD Integration

### GitHub Actions Example

```yaml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        test-type: [unit, integration]
    steps:
      - uses: actions/checkout@v4
      - name: Run ${{ matrix.test-type }} tests
        run: npm run test:${{ matrix.test-type }}

  e2e:
    if: github.event_name == 'push' && contains(github.event.head_commit.message, '[e2e]')
    runs-on: ubuntu-latest
    steps:
      - name: Run E2E tests
        run: E2E_READY=true npm run test:e2e
```

## 📈 Performance Monitoring

### Regression Detection

```typescript
import { PerformanceMonitor } from '@/test-utils/environment'

it('performs within budget @slow', async () => {
  const start = performance.now()
  // Test code
  const duration = performance.now() - start

  PerformanceMonitor.checkRegression('test-name', duration, baseline)
})
```

### Test Performance Dashboard

- Slow test detection (>5s in development, >10s in CI)
- Performance regression alerts
- Historical performance trends
- Test execution time distribution

## 🐛 Debugging & Troubleshooting

### Common Issues

```bash
# Debug specific test
npm run test:debug -- --grep "component name"

# Run with verbose output
npm run test -- --reporter=verbose

# Debug E2E setup
E2E_READY=true npm run test:e2e -- --reporter=verbose
```

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `E2E_READY` | Enable E2E tests | `false` |
| `RUN_PERFORMANCE_TESTS` | Enable performance tests | `false` |
| `CI` | CI environment detection | Auto-detected |

## 🎯 Best Practices

### Test Organization

```
src/
├── components/
│   └── Button/
│       ├── Button.tsx
│       └── __tests__/
│           ├── Button.test.tsx          # @unit @component
│           ├── Button.integration.test.tsx # @integration
│           └── Button.e2e.test.tsx      # @e2e
└── features/
    └── analysis/
        ├── __tests__/
        │   ├── AnalysisFlow.test.tsx   # @e2e
        │   └── hooks/
        │       └── useAnalysis.test.tsx # @unit @hook
```

### Test Naming Conventions

```typescript
// Good: Descriptive and tagged
describe('ProgressTracker displays stages correctly @unit @component', () => {
  it('shows loading state during extraction', () => {})
  it('transitions to completed state', () => {})
})

// Avoid: Untagged or unclear
describe('ProgressTracker', () => {
  it('works', () => {})
})
```

### Performance Considerations

- Keep unit tests under 100ms each
- Mark slow tests with `@slow` tag
- Use `beforeAll` for expensive setup
- Mock external dependencies liberally

## 📚 API Reference

### TestEnvironment

```typescript
interface TestEnvironment {
  isCI: boolean
  isE2EReady: boolean
  isDevelopment: boolean
  hasDatabase: boolean
  hasRedis: boolean
  hasExternalAPIs: boolean
  slowTestThreshold: number
  testTimeout: number
}
```

### Conditional Test Helpers

```typescript
const conditionalTest = {
  e2e: (name: string, fn: () => void) => it.skipIf(!TestEnvironment.isE2EReady, name, fn)
  withDatabase: (name: string, fn: () => void) => it.skipIf(!TestEnvironment.hasDatabase, name, fn)
  // ... more helpers
}
```

## 🔮 Future Enhancements

- **AI-Powered Test Generation**: Automatically generate tests from code changes
- **Visual Regression**: Screenshot comparison for UI changes
- **Load Testing**: Distributed performance testing
- **Test Analytics**: Detailed insights and recommendations
- **Parallel Execution**: Shard tests across multiple machines

---

## 📞 Support

For questions about the testing infrastructure:

1. Check this document first
2. Review existing test examples
3. Ask in the development channel

**Remember**: Tests are documentation. Write them to be read by future developers! 📖
