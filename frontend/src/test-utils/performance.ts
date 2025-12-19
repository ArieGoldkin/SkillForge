/**
 * Performance Testing Utilities
 *
 * Provides utilities for performance monitoring and render budget testing
 * using Vitest React Profiler and custom performance metrics.
 */

import type { ComponentType } from 'react'

import type { ProfiledComponent } from 'vitest-react-profiler'
import { withProfiler } from 'vitest-react-profiler'

import {
  trackComponentPerformance,
  trackInteraction,
} from '@services/performance/webVitals.service'

/**
 * Wrap a component with performance profiling
 */
export function withPerformanceProfiler<T extends ComponentType<Record<string, unknown>>>(
  Component: T,
  displayName?: string
): ProfiledComponent<T> {
  return withProfiler(Component, displayName || Component.displayName || Component.name)
}

/**
 * Render budget limits for different component types
 */
export const RENDER_BUDGETS = {
  // Simple display components
  simple: 3,
  // Form components with state
  form: 10,
  // List components
  list: 50,
  // Complex analysis components
  analysis: 100,
  // Loading states (should be minimal)
  loading: 5,
} as const

/**
 * Performance test utilities
 */
export const performanceUtils = {
  /**
   * Assert component meets render budget
   */
  assertRenderBudget(
    component: ProfiledComponent<ComponentType<Record<string, unknown>>>,
    budget: number,
    componentName?: string
  ) {
    const renderCount = component.getRenderCount()
    const componentLabel = componentName || component.displayName || 'Component'

    if (renderCount > budget) {
      throw new Error(
        `${componentLabel} exceeded render budget: ${renderCount} renders (budget: ${budget})`
      )
    }

    console.log(`✅ ${componentLabel} performance: ${renderCount}/${budget} renders`)
  },

  /**
   * Check for performance regression
   */
  checkPerformanceRegression(
    component: ProfiledComponent<ComponentType<Record<string, unknown>>>,
    baseline: number,
    componentName?: string
  ) {
    const current = component.getRenderCount()
    const regression = ((current - baseline) / baseline) * 100

    if (regression > 50) {
      console.warn(
        `⚠️ Performance regression detected: ${componentName || 'Component'} +${regression.toFixed(1)}% renders`
      )
    }

    return { current, baseline, regression }
  },

  /**
   * Measure component render time
   */
  async measureRenderTime<T>(
    renderFn: () => T,
    componentName?: string
  ): Promise<{ result: T; duration: number }> {
    const start = performance.now()
    const result = renderFn()
    const duration = performance.now() - start

    // Track in analytics
    trackComponentPerformance(componentName || 'unknown', duration)

    console.log(`⏱️ ${componentName || 'Component'} render time: ${duration.toFixed(2)}ms`)

    return { result, duration }
  },

  /**
   * Track user interaction performance
   */
  trackUserInteraction(interactionName: string, duration: number) {
    trackInteraction(interactionName, duration)
    console.log(`👆 User interaction: ${interactionName} (${duration.toFixed(2)}ms)`)
  },
}

/**
 * Performance test hooks for common patterns
 */
export const performanceHooks = {
  /**
   * Hook for testing component re-render performance
   */
  useRenderPerformanceTest(componentName: string) {
    return {
      assertBudget: (
        component: ProfiledComponent<ComponentType<Record<string, unknown>>>,
        budget: number
      ) => {
        performanceUtils.assertRenderBudget(component, budget, componentName)
      },

      checkRegression: (
        component: ProfiledComponent<ComponentType<Record<string, unknown>>>,
        baseline: number
      ) => {
        return performanceUtils.checkPerformanceRegression(component, baseline, componentName)
      },

      logPerformance: (component: ProfiledComponent<ComponentType<Record<string, unknown>>>) => {
        const renders = component.getRenderCount()
        const history = component.getRenderHistory()
        console.log(`📊 ${componentName} performance:`, { renders, history })
      },
    }
  },

  /**
   * Hook for testing user interaction performance
   */
  useInteractionPerformanceTest() {
    return {
      measureInteraction: (name: string, action: () => void | Promise<void>) => {
        const start = performance.now()
        const result = action()
        const duration = performance.now() - start

        if (result instanceof Promise) {
          return result.then(() => {
            performanceUtils.trackUserInteraction(name, duration)
            return duration
          })
        } else {
          performanceUtils.trackUserInteraction(name, duration)
          return duration
        }
      },
    }
  },
}

/**
 * CI/CD performance reporting utilities
 */
export const ciUtils = {
  /**
   * Generate performance report for CI
   */
  generatePerformanceReport(
    results: Array<{
      component: string
      renders: number
      budget: number
      passed: boolean
    }>
  ) {
    const report = {
      timestamp: new Date().toISOString(),
      totalTests: results.length,
      passed: results.filter((r) => r.passed).length,
      failed: results.filter((r) => !r.passed).length,
      results,
      summary: {
        averageRenders: results.reduce((sum, r) => sum + r.renders, 0) / results.length,
        budgetUtilization:
          results.reduce((sum, r) => sum + r.renders / r.budget, 0) / results.length,
      },
    }

    // In CI, this could be written to a file or sent to analytics
    if (process.env.CI) {
      console.log('📊 Performance Report:', JSON.stringify(report, null, 2))
    }

    return report
  },

  /**
   * Check if performance test should fail CI
   */
  shouldFailCI(results: Array<{ passed: boolean }>): boolean {
    const failureRate = results.filter((r) => !r.passed).length / results.length
    return failureRate > 0.1 // Fail if more than 10% of tests fail
  },
}

/**
 * Component performance presets for common patterns
 */
export const performancePresets = {
  /**
   * Loading component performance test
   */
  loadingComponent: {
    budget: RENDER_BUDGETS.loading,
    description: 'Loading components should render minimally',
  },

  /**
   * Form component performance test
   */
  formComponent: {
    budget: RENDER_BUDGETS.form,
    description: 'Form components can have more renders due to state changes',
  },

  /**
   * List component performance test
   */
  listComponent: {
    budget: RENDER_BUDGETS.list,
    description: 'List components may render more due to data changes',
  },

  /**
   * Analysis component performance test
   */
  analysisComponent: {
    budget: RENDER_BUDGETS.analysis,
    description: 'Analysis components are complex and may have more renders',
  },
}
