/**
 * Web Vitals Performance Reporting Utility
 *
 * Simplified interface for capturing Core Web Vitals metrics.
 * Provides development logging and production analytics callback support.
 *
 * Core Web Vitals:
 * - CLS (Cumulative Layout Shift) - Visual stability
 * - FCP (First Contentful Paint) - Initial render
 * - INP (Interaction to Next Paint) - Responsiveness (replaces FID)
 * - LCP (Largest Contentful Paint) - Loading performance
 * - TTFB (Time to First Byte) - Server response
 *
 * Usage:
 * ```typescript
 * // Development only (auto-logs to console)
 * reportWebVitals()
 *
 * // With custom analytics handler
 * reportWebVitals((metric) => {
 *   // Send to your analytics service
 *   analytics.track(metric.name, metric.value)
 * })
 * ```
 */

import { onCLS, onFCP, onINP, onLCP, onTTFB, type Metric } from 'web-vitals'

import { logger } from './logger'

/**
 * Simplified metric handler type
 */
export type MetricHandler = (metric: { name: string; value: number; id: string }) => void

/**
 * Get human-readable rating description
 */
function getRatingDescription(name: string, value: number): string {
  // Web Vitals thresholds (good/needs-improvement/poor)
  const thresholds: Record<string, { good: number; poor: number }> = {
    CLS: { good: 0.1, poor: 0.25 },
    FCP: { good: 1800, poor: 3000 },
    INP: { good: 200, poor: 500 },
    LCP: { good: 2500, poor: 4000 },
    TTFB: { good: 800, poor: 1800 },
  }

  const threshold = thresholds[name]
  if (!threshold) return ''

  if (value <= threshold.good) return '✅ good'
  if (value <= threshold.poor) return '⚠️ needs improvement'
  return '❌ poor'
}

/**
 * Format metric value with appropriate units
 */
function formatMetricValue(name: string, value: number): string {
  if (name === 'CLS') {
    // CLS is unitless
    return value.toFixed(3)
  }
  // All other metrics are in milliseconds
  return `${Math.round(value)}ms`
}

/**
 * Default development logger
 */
function defaultHandler(metric: Metric): void {
  if (import.meta.env.DEV) {
    const formattedValue = formatMetricValue(metric.name, metric.value)
    const rating = getRatingDescription(metric.name, metric.value)

    logger.info(`[Web Vitals] ${metric.name}: ${formattedValue} ${rating}`, {
      id: metric.id,
      delta: metric.delta,
      rating: metric.rating,
      navigationType: metric.navigationType,
    })
  }
}

/**
 * Report Web Vitals metrics
 *
 * @param onReport - Optional custom handler for metric reporting
 *
 * @example
 * ```typescript
 * // Development mode (auto-logs)
 * reportWebVitals()
 *
 * // Production with Google Analytics
 * reportWebVitals((metric) => {
 *   gtag('event', metric.name, {
 *     value: Math.round(metric.value),
 *     metric_id: metric.id,
 *   })
 * })
 *
 * // Custom analytics service
 * reportWebVitals((metric) => {
 *   fetch('/api/analytics/web-vitals', {
 *     method: 'POST',
 *     body: JSON.stringify(metric),
 *   })
 * })
 * ```
 */
export function reportWebVitals(onReport?: MetricHandler): void {
  const handler = onReport
    ? (metric: Metric) => {
        // Call default logger in development
        defaultHandler(metric)
        // Call custom handler
        onReport({ name: metric.name, value: metric.value, id: metric.id })
      }
    : defaultHandler

  // Register all Core Web Vitals observers
  onCLS(handler)
  onFCP(handler)
  onINP(handler)
  onLCP(handler)
  onTTFB(handler)
}
