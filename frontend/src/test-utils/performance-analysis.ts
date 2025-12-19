/**
 * Performance Analysis Utilities for Issue #395
 *
 * Analyzes and measures re-render patterns in analysis components
 * to identify optimization opportunities and track improvements.
 */

import type { ComponentType } from 'react'

// Component render tracking for analysis
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
  renderFrequency: number // renders per second
  memoryUsage: number
  executionTime: number
}

// Global render tracking (development only)
const renderStats = new Map<string, ComponentRenderStats>()

if (import.meta.env.DEV) {
  // Monkey patch React to track renders (development only)
  const React = await import('react')
  const originalCreateElement = React.createElement

  React.createElement = function (type: any, props: any, ...children: any[]) {
    if (typeof type === 'function' && type.displayName) {
      const componentName = type.displayName
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

/**
 * Analyze component re-render patterns
 */
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

  return {
    totalRenders,
    componentStats,
    renderFrequency:
      totalRenders /
      ((Date.now() - Math.min(...componentStats.map((s) => s.lastRenderTime))) / 1000),
    memoryUsage: (performance as any).memory?.usedJSHeapSize || 0,
    executionTime: performance.now(),
  }
}

/**
 * Identify components that re-render too frequently
 */
export function identifyReRenderHotspots(threshold: number = 10): string[] {
  const hotspots: string[] = []

  renderStats.forEach((stats, componentName) => {
    if (stats.renderCount > threshold) {
      hotspots.push(`${componentName}: ${stats.renderCount} renders`)
    }
  })

  return hotspots
}

/**
 * Performance baseline for analysis components
 */
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
  expectedMaxRenders: 100, // Target for 50 SSE events
  expectedMaxExecutionTime: 500, // ms
}

/**
 * Validate performance against baseline
 */
export function validatePerformanceBaseline(): {
  passed: boolean
  issues: string[]
  recommendations: string[]
} {
  const analysis = analyzeComponentRenders(ANALYSIS_COMPONENT_BASELINE.components)
  const issues: string[] = []
  const recommendations: string[] = []

  // Check total renders
  if (analysis.totalRenders > ANALYSIS_COMPONENT_BASELINE.expectedMaxRenders) {
    issues.push(
      `Total renders (${analysis.totalRenders}) exceeds baseline (${ANALYSIS_COMPONENT_BASELINE.expectedMaxRenders})`
    )
    recommendations.push('Apply React.memo to high-render components')
  }

  // Check execution time
  if (analysis.executionTime > ANALYSIS_COMPONENT_BASELINE.expectedMaxExecutionTime) {
    issues.push(
      `Execution time (${analysis.executionTime}ms) exceeds baseline (${ANALYSIS_COMPONENT_BASELINE.expectedMaxExecutionTime}ms)`
    )
    recommendations.push('Add useMemo for expensive computations')
  }

  // Check render frequency
  if (analysis.renderFrequency > 5) {
    // More than 5 renders per second sustained
    issues.push(`Render frequency (${analysis.renderFrequency.toFixed(1)}/s) is too high`)
    recommendations.push('Optimize Zustand subscriptions')
  }

  // Check individual component hotspots
  const hotspots = identifyReRenderHotspots(20) // Components with >20 renders
  if (hotspots.length > 0) {
    issues.push(`Found ${hotspots.length} component re-render hotspots`)
    recommendations.push('Apply React.memo to: ' + hotspots.slice(0, 3).join(', '))
  }

  return {
    passed: issues.length === 0,
    issues,
    recommendations,
  }
}

/**
 * Performance improvement tracking
 */
export interface PerformanceImprovement {
  component: string
  beforeRenders: number
  afterRenders: number
  improvement: number // percentage
  optimization: string
}

export const performanceImprovements: PerformanceImprovement[] = []

/**
 * Track performance improvement
 */
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

  console.log(`🚀 Performance Improvement: ${component}`)
  console.log(`   Before: ${beforeRenders} renders`)
  console.log(`   After: ${afterRenders} renders`)
  console.log(`   Improvement: ${improvement.toFixed(1)}%`)
  console.log(`   Optimization: ${optimization}`)
}

/**
 * Generate performance report
 */
export function generatePerformanceReport(): string {
  const analysis = analyzeComponentRenders(ANALYSIS_COMPONENT_BASELINE.components)
  const validation = validatePerformanceBaseline()

  let report = '# Performance Analysis Report - Issue #395\n\n'

  report += `## Current Metrics\n`
  report += `- Total renders: ${analysis.totalRenders}\n`
  report += `- Render frequency: ${analysis.renderFrequency.toFixed(1)}/s\n`
  report += `- Memory usage: ${(analysis.memoryUsage / 1024 / 1024).toFixed(1)}MB\n`
  report += `- Execution time: ${analysis.executionTime.toFixed(1)}ms\n\n`

  report += `## Baseline Validation\n`
  report += `- Status: ${validation.passed ? '✅ PASSED' : '❌ FAILED'}\n\n`

  if (validation.issues.length > 0) {
    report += `### Issues Found\n`
    validation.issues.forEach((issue) => {
      report += `- ${issue}\n`
    })
    report += '\n'
  }

  if (validation.recommendations.length > 0) {
    report += `### Recommendations\n`
    validation.recommendations.forEach((rec) => {
      report += `- ${rec}\n`
    })
    report += '\n'
  }

  if (performanceImprovements.length > 0) {
    report += `## Performance Improvements\n`
    report += `| Component | Before | After | Improvement | Optimization |\n`
    report += `|-----------|--------|-------|-------------|--------------|\n`

    performanceImprovements.forEach((imp) => {
      report += `| ${imp.component} | ${imp.beforeRenders} | ${imp.afterRenders} | ${imp.improvement.toFixed(1)}% | ${imp.optimization} |\n`
    })

    const avgImprovement =
      performanceImprovements.reduce((sum, imp) => sum + imp.improvement, 0) /
      performanceImprovements.length
    report += `\n**Average Improvement: ${avgImprovement.toFixed(1)}%**\n\n`
  }

  report += `## Component Render Stats\n`
  analysis.componentStats.forEach((stat) => {
    report += `- ${stat.componentName}: ${stat.renderCount} renders\n`
  })

  return report
}
