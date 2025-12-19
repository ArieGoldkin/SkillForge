/**
 * Performance Verification for Issue #395
 *
 * Simulates 50 SSE events and measures render performance
 * to verify the 16× re-render reduction target.
 */

import * as React from 'react'

import { useSSEStore } from '@stores/sseStore'
import { act, render } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AnalyzeResult from '../features/analysis/AnalyzeResult'

import { sseEventFactory, sseStoreStateFactory } from './factories/sseEventFactory'

// Mock child components to isolate AnalyzeResult performance
vi.mock('../features/analysis/components', () => ({
  ActivityColumn: () => <div>MockActivityColumn</div>,
  AnalysisCompleteCard: () => <div>MockAnalysisCompleteCard</div>,
  AnalysisErrorFallback: () => <div>MockAnalysisErrorFallback</div>,
  AnalysisHeader: () => <div>MockAnalysisHeader</div>,
  ErrorAlert: () => <div>MockErrorAlert</div>,
  LoadingStateDisplay: () => <div>MockLoadingStateDisplay</div>,
  ProgressColumn: () => <div>MockProgressColumn</div>,
  TimeoutWarningBanner: () => <div>MockTimeoutWarningBanner</div>,
}))

vi.mock('../features/analysis/components/states/CompletedAnalysisView', () => ({
  default: () => <div>MockCompletedAnalysisView</div>,
}))

vi.mock('../features/analysis/hooks/useAnalysisProgress', () => ({
  useAnalysisProgress: () => ({
    overallProgress: { stage: 'analyzing', progress: 50 },
    steps: [],
    agentActivity: [],
  }),
}))

vi.mock('../features/analysis/hooks/useAnalysisStatus', () => ({
  useAnalysisStatus: () => ({
    resolvedStatus: undefined,
    resolvedArtifactId: undefined,
    statusError: null,
    loading: false,
    shouldConnect: true,
  }),
}))

vi.mock('@tanstack/react-router', () => ({
  getRouteApi: () => () => ({ id: 'test-analysis-id' }),
}))

/**
 * Helper: Creates a render counter spy for performance testing
 */
function createRenderCounter(component: React.ComponentType): {
  spy: ReturnType<typeof vi.spyOn>
  getCount: () => number
} {
  let renderCount = 0
  const spy = vi.spyOn(React, 'createElement')

  spy.mockImplementation((type, props, ...children) => {
    if (type === component || (type as { name?: string })?.name === component.name) {
      renderCount++
    }
    // Call original createElement
    return React.createElement(type as string, props, ...children)
  })

  return {
    spy,
    getCount: () => renderCount,
  }
}

/**
 * Helper: Simulates SSE events and triggers re-renders
 */
async function simulateSSEEvents(
  count: number,
  rerender: (ui: React.ReactElement) => void
): Promise<void> {
  for (let i = 0; i < count; i++) {
    useSSEStore.setState({
      events: Array.from({ length: i + 1 }, (_, idx) =>
        sseEventFactory.build({
          stage: idx % 2 === 0 ? 'extraction' : 'tech_comparison',
          status: 'running',
          timestamp: new Date(Date.now() + idx * 100).toISOString(),
        })
      ),
      latestEvent: sseEventFactory.build({
        stage: i % 2 === 0 ? 'extraction' : 'tech_comparison',
        status: 'running',
      }),
    })

    rerender(<AnalyzeResult />)
  }
}

/**
 * Helper: Simulates batched SSE events for stress testing
 */
async function simulateBatchedEvents(
  batches: number,
  batchSize: number,
  rerender: (ui: React.ReactElement) => void
): Promise<void> {
  for (let batch = 0; batch < batches; batch++) {
    const events = Array.from({ length: batchSize }, (_, idx) =>
      sseEventFactory.build({
        stage: 'tech_comparison',
        status: 'running',
        timestamp: new Date(Date.now() + (batch * batchSize + idx) * 50).toISOString(),
      })
    )

    useSSEStore.setState({
      events: events,
      latestEvent: events[events.length - 1],
    })

    rerender(<AnalyzeResult />)
  }
}

/**
 * Performance verification test for Issue #395
 */
describe('Performance Verification - Issue #395', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset Zustand store state
    useSSEStore.setState(sseStoreStateFactory.build())
  })

  it('should achieve 16x re-render reduction target (<100 renders for 50 SSE events)', async () => {
    const renderCounter = createRenderCounter(AnalyzeResult)
    const { rerender } = render(<AnalyzeResult />)

    const initialRenderCount = renderCounter.getCount()
    expect(initialRenderCount).toBeGreaterThan(0)

    // Simulate 50 SSE events (the problematic scenario from the issue)
    await act(async () => {
      await simulateSSEEvents(50, rerender)
    })

    const finalRenderCount = renderCounter.getCount()
    const totalRenders = finalRenderCount - initialRenderCount

    console.log(`🎯 Performance Verification Results:`)
    console.log(`   Initial renders: ${initialRenderCount}`)
    console.log(`   Final renders: ${finalRenderCount}`)
    console.log(`   Total renders for 50 events: ${totalRenders}`)
    console.log(`   Target: <100 renders (16x improvement from 1,600+)`)

    // Verify the 16x improvement target
    expect(totalRenders).toBeLessThan(100)

    // Additional performance assertions
    expect(totalRenders).toBeLessThan(50) // Even more ambitious target
    expect(totalRenders / 50).toBeLessThan(2) // Less than 2 renders per event

    // Cleanup
    renderCounter.spy.mockRestore()
  })

  it('should maintain functionality while optimizing performance', () => {
    const { getByText } = render(<AnalyzeResult />)

    // Verify basic functionality still works
    expect(getByText('MockAnalysisHeader')).toBeInTheDocument()
    expect(getByText('MockProgressColumn')).toBeInTheDocument()
    expect(getByText('MockActivityColumn')).toBeInTheDocument()
  })

  it('should handle rapid state changes efficiently', async () => {
    const renderCounter = createRenderCounter(AnalyzeResult)
    const { rerender } = render(<AnalyzeResult />)
    const initialRenderCount = renderCounter.getCount()

    // Simulate rapid SSE events (stress test)
    await act(async () => {
      await simulateBatchedEvents(10, 5, rerender)
    })

    const totalRenders = renderCounter.getCount() - initialRenderCount

    console.log(`🚀 Rapid State Changes Test:`)
    console.log(`   Events processed: 50`)
    console.log(`   Total renders: ${totalRenders}`)
    console.log(`   Renders per event: ${(totalRenders / 50).toFixed(2)}`)

    // Should handle rapid changes without excessive renders
    expect(totalRenders).toBeLessThan(75) // Very conservative target

    renderCounter.spy.mockRestore()
  })
})
