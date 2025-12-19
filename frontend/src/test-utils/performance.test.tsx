/**
 * Basic test to verify performance monitoring setup
 */

import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { withPerformanceProfiler, performanceUtils, RENDER_BUDGETS } from './performance'

// Simple test component
function TestComponent({ count }: { count: number }) {
  return <div>Count: {count}</div>
}

describe('Performance Monitoring Setup', () => {
  it('should profile component renders', () => {
    const TestComponentProfiled = withPerformanceProfiler(TestComponent, 'TestComponent')

    const { rerender } = render(<TestComponentProfiled count={0} />)

    // Check initial render
    expect(TestComponentProfiled).toHaveRenderedTimes(1)

    // Re-render with different props
    rerender(<TestComponentProfiled count={1} />)

    // Should have rendered twice
    expect(TestComponentProfiled).toHaveRenderedTimes(2)

    // Check render budget
    performanceUtils.assertRenderBudget(
      TestComponentProfiled,
      RENDER_BUDGETS.simple,
      'TestComponent'
    )
  })

  it('should work with custom matchers', () => {
    const TestComponentProfiled = withPerformanceProfiler(TestComponent, 'TestComponent')

    render(<TestComponentProfiled count={0} />)

    // Test custom matchers
    expect(TestComponentProfiled).toHaveRenderedOnlyOnMount()
    expect(TestComponentProfiled).toMeetRenderBudget(5)
  })
})
