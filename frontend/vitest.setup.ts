import '@testing-library/jest-dom/vitest'
import { expect } from 'vitest'
import type { ProfiledComponent } from 'vitest-react-profiler'

// Polyfill ResizeObserver for jsdom (used by @tanstack/react-virtual)
global.ResizeObserver = class ResizeObserver {
  private callback: ResizeObserverCallback
  private targets: Element[] = []

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback
  }

  observe(target: Element): void {
    this.targets.push(target)
    // Simulate initial resize with realistic dimensions for virtualization
    const entry = {
      target,
      contentRect: { width: 1024, height: 800, top: 0, left: 0, bottom: 800, right: 1024, x: 0, y: 0, toJSON: () => ({}) },
      borderBoxSize: [{ blockSize: 800, inlineSize: 1024 }],
      contentBoxSize: [{ blockSize: 800, inlineSize: 1024 }],
      devicePixelContentBoxSize: [{ blockSize: 800, inlineSize: 1024 }],
    } as unknown as ResizeObserverEntry
    // Delay callback to allow React to mount
    setTimeout(() => this.callback([entry], this), 0)
  }

  unobserve(): void {}
  disconnect(): void {}
}

// Mock element dimensions for virtualization (jsdom returns 0 by default)
Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
  configurable: true,
  get() {
    return 1024
  },
})

Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
  configurable: true,
  get() {
    return 800
  },
})

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
