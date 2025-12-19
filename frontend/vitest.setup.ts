import '@testing-library/jest-dom/vitest'
import { expect } from 'vitest'
import type { ProfiledComponent } from 'vitest-react-profiler'

// Custom matchers for render budget testing
declare module 'vitest' {
  interface Assertion<T = any> {
    toHaveRenderedOnlyOnMount(): void
    toMeetRenderBudget(budget: number): void
    toHavePerformanceRegression(maxRenders: number): void
  }
}

// Add custom matchers
expect.extend({
  toHaveRenderedOnlyOnMount(component: ProfiledComponent<any>) {
    const renderCount = component.getRenderCount()
    const pass = renderCount === 1 && component.hasMounted()

    return {
      pass,
      message: () =>
        pass
          ? `Expected component to render more than once`
          : `Expected component to render only on mount, but it rendered ${renderCount} times`,
    }
  },

  toMeetRenderBudget(component: ProfiledComponent<any>, budget: number) {
    const actual = component.getRenderCount()
    const pass = actual <= budget

    return {
      pass,
      message: () =>
        pass
          ? `Expected component to exceed render budget of ${budget}, but it rendered ${actual} times`
          : `Expected component to meet render budget of ${budget}, but it rendered ${actual} times`,
    }
  },

  toHavePerformanceRegression(component: ProfiledComponent<any>, maxRenders: number) {
    const actual = component.getRenderCount()
    const pass = actual <= maxRenders

    return {
      pass,
      message: () =>
        pass
          ? `Performance regression detected: component rendered ${actual} times (max allowed: ${maxRenders})`
          : `Component performance is within budget: ${actual} renders (max: ${maxRenders})`,
    }
  },
})

// Performance monitoring setup for CI/CD
if (process.env.CI) {
  // In CI, collect performance data after each test
  afterEach(() => {
    // This would collect performance metrics for CI reporting
    // Implementation would depend on your CI setup
    console.log('Performance test completed')
  })
}
