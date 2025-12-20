/** Performance Analysis Utilities for Issue #395 - Analyzes re-render patterns to identify optimizations. */
export interface ComponentRenderStats {
  componentName: string
  renderCount: number
  lastRenderTime: number
  propsChanged: boolean
  stateChanged: boolean
}
export interface PerformanceAnalysisResult {
  totalRenders: number
  componentStats: ComponentRenderStats[]
  renderFrequency: number
  memoryUsage: number
  executionTime: number
}
const renderStats = new Map<string, ComponentRenderStats>()
if (import.meta.env.DEV) {
  const React = await import('react')

  // Wrap createElement to track render stats in development
  // Type-safe monkey-patching of React.createElement
  type ReactCreateElement = (
    type: React.ElementType,
    props?: React.Attributes | null,
    ...children: React.ReactNode[]
  ) => React.ReactElement | null

  const originalCreateElement = React.createElement as ReactCreateElement
  ;(React as { createElement: ReactCreateElement }).createElement = function (
    type: React.ElementType,
    props?: React.Attributes | null,
    ...children: React.ReactNode[]
  ) {
    if (
      typeof type === 'function' &&
      'displayName' in (type as Record<string, unknown>) &&
      typeof (type as Record<string, unknown>).displayName === 'string'
    ) {
      const componentName = (type as { displayName: string }).displayName
      const existing = renderStats.get(componentName)
      if (existing) {
        existing.renderCount++
        existing.lastRenderTime = Date.now()
      } else {
        renderStats.set(componentName, {
          componentName,
          renderCount: 1,
          lastRenderTime: Date.now(),
          propsChanged: false,
          stateChanged: false,
        })
      }
    }
    return originalCreateElement.call(this, type, props, ...children)
  }
}
/** Analyze component re-render patterns */
export function analyzeComponentRenders(componentNames: string[]): PerformanceAnalysisResult {
  const componentStats: ComponentRenderStats[] = []
  let totalRenders = 0
  componentNames.forEach((name) => {
    const stats = renderStats.get(name)
    if (stats) {
      componentStats.push(stats)
      totalRenders += stats.renderCount
    }
  })
  const memoryUsage =
    'memory' in performance &&
    typeof performance.memory === 'object' &&
    performance.memory !== null &&
    'usedJSHeapSize' in performance.memory
      ? (performance.memory as { usedJSHeapSize: number }).usedJSHeapSize
      : 0
  return {
    totalRenders,
    componentStats,
    renderFrequency:
      totalRenders /
      ((Date.now() - Math.min(...componentStats.map((s) => s.lastRenderTime))) / 1000),
    memoryUsage,
    executionTime: performance.now(),
  }
}
/** Identify components that re-render too frequently */
export function identifyReRenderHotspots(threshold: number = 10): string[] {
  const hotspots: string[] = []
  renderStats.forEach((stats, componentName) => {
    if (stats.renderCount > threshold) {
      hotspots.push(`${componentName}: ${stats.renderCount} renders`)
    }
  })
  return hotspots
}
/** Performance baseline for analysis components */
export const ANALYSIS_COMPONENT_BASELINE = {
  components: [
    'AnalyzeResult',
    'ProgressColumn',
    'ActivityColumn',
    'StageItem',
    'AnalysisHeader',
    'AnalysisProgressCard',
    'LoadingStateDisplay',
    'TimeoutWarningBanner',
    'AnalysisCompleteCard',
    'CompletedAnalysisView',
    'ErrorAlert',
    'AnalysisErrorFallback',
  ],
  expectedMaxRenders: 100,
  expectedMaxExecutionTime: 500,
}
/** Validate performance against baseline */
export function validatePerformanceBaseline() {
  const analysis = analyzeComponentRenders(ANALYSIS_COMPONENT_BASELINE.components)
  const issues: string[] = []
  const recommendations: string[] = []
  const { totalRenders, executionTime, renderFrequency } = analysis
  const { expectedMaxRenders, expectedMaxExecutionTime } = ANALYSIS_COMPONENT_BASELINE
  if (totalRenders > expectedMaxRenders) {
    issues.push(`Total renders (${totalRenders}) exceeds baseline (${expectedMaxRenders})`)
    recommendations.push('Apply React.memo to high-render components')
  }
  if (executionTime > expectedMaxExecutionTime) {
    issues.push(
      `Execution time (${executionTime}ms) exceeds baseline (${expectedMaxExecutionTime}ms)`
    )
    recommendations.push('Add useMemo for expensive computations')
  }
  if (renderFrequency > 5) {
    issues.push(`Render frequency (${renderFrequency.toFixed(1)}/s) is too high`)
    recommendations.push('Optimize Zustand subscriptions')
  }
  const hotspots = identifyReRenderHotspots(20)
  if (hotspots.length > 0) {
    issues.push(`Found ${hotspots.length} component re-render hotspots`)
    recommendations.push(`Apply React.memo to: ${hotspots.slice(0, 3).join(', ')}`)
  }
  return { passed: issues.length === 0, issues, recommendations }
}
/** Performance improvement tracking */
export interface PerformanceImprovement {
  component: string
  beforeRenders: number
  afterRenders: number
  improvement: number
  optimization: string
}
export const performanceImprovements: PerformanceImprovement[] = []
/** Track performance improvement */
export function trackPerformanceImprovement(
  component: string,
  beforeRenders: number,
  afterRenders: number,
  optimization: string
) {
  const improvement = ((beforeRenders - afterRenders) / beforeRenders) * 100
  performanceImprovements.push({
    component,
    beforeRenders,
    afterRenders,
    improvement,
    optimization,
  })
  console.log(
    `🚀 ${component}: ${beforeRenders}→${afterRenders} renders (${improvement.toFixed(1)}% improvement) - ${optimization}`
  )
}
/** Generate performance report */
export function generatePerformanceReport(): string {
  const analysis = analyzeComponentRenders(ANALYSIS_COMPONENT_BASELINE.components)
  const validation = validatePerformanceBaseline()
  const parts = [
    '# Performance Analysis Report - Issue #395\n',
    '\n## Current Metrics\n',
    `- Total renders: ${analysis.totalRenders}\n`,
    `- Render frequency: ${analysis.renderFrequency.toFixed(1)}/s\n`,
    `- Memory usage: ${(analysis.memoryUsage / 1024 / 1024).toFixed(1)}MB\n`,
    `- Execution time: ${analysis.executionTime.toFixed(1)}ms\n\n`,
    `## Baseline Validation\n- Status: ${validation.passed ? '✅ PASSED' : '❌ FAILED'}\n\n`,
  ]
  if (validation.issues.length > 0) {
    parts.push('### Issues Found\n', ...validation.issues.map((i) => `- ${i}\n`), '\n')
  }
  if (validation.recommendations.length > 0) {
    parts.push('### Recommendations\n', ...validation.recommendations.map((r) => `- ${r}\n`), '\n')
  }
  if (performanceImprovements.length > 0) {
    const avg =
      performanceImprovements.reduce((sum, imp) => sum + imp.improvement, 0) /
      performanceImprovements.length
    parts.push(
      '## Performance Improvements\n',
      '| Component | Before | After | Improvement | Optimization |\n',
      '|-----------|--------|-------|-------------|--------------|\n',
      ...performanceImprovements.map(
        (i) =>
          `| ${i.component} | ${i.beforeRenders} | ${i.afterRenders} | ${i.improvement.toFixed(1)}% | ${i.optimization} |\n`
      ),
      `\n**Average Improvement: ${avg.toFixed(1)}%**\n\n`
    )
  }
  parts.push(
    '## Component Render Stats\n',
    ...analysis.componentStats.map((s) => `- ${s.componentName}: ${s.renderCount} renders\n`)
  )
  return parts.join('')
}
