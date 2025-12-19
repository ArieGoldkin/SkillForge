/**
 * Web Vitals Performance Monitoring Service
 *
 * Tracks Core Web Vitals metrics with attribution data for production analytics.
 * Complements React Scan's development-time monitoring with production RUM data.
 *
 * Core Web Vitals Tracked:
 * - LCP (Largest Contentful Paint) - Loading performance
 * - CLS (Cumulative Layout Shift) - Visual stability
 * - INP (Interaction to Next Paint) - Responsiveness
 * - FCP (First Contentful Paint) - Initial render
 * - TTFB (Time to First Byte) - Server response
 */

import { onCLS, onINP, onLCP, onFCP, onTTFB, type Metric } from 'web-vitals'

// Google Analytics measurement ID (configure per environment)
const GA_MEASUREMENT_ID = import.meta.env.VITE_GA_MEASUREMENT_ID || 'G-XXXXXXXXXX'

// Queue for batching metrics to reduce network requests
const metricsQueue: Metric[] = []
const MAX_QUEUE_SIZE = 10
const FLUSH_INTERVAL = 30000 // 30 seconds

/**
 * Send metric to Google Analytics 4
 */
function sendToGoogleAnalytics(metric: Metric): void {
  if (!GA_MEASUREMENT_ID || GA_MEASUREMENT_ID === 'G-XXXXXXXXXX') {
    console.warn('Web Vitals: GA_MEASUREMENT_ID not configured, skipping analytics')
    return
  }

  // Send to Google Analytics
  if (typeof gtag !== 'undefined') {
    gtag('event', metric.name, {
      value: metric.delta,
      metric_id: metric.id,
      metric_value: metric.value,
      metric_delta: metric.delta,
      metric_rating: metric.rating,
      // Attribution data for debugging
      ...(metric.name === 'CLS' &&
        (metric as unknown as { attribution?: unknown }).attribution && {
          debug_target: (metric as unknown as { attribution: { largestShiftTarget?: string } })
            .attribution.largestShiftTarget,
          debug_time: (metric as unknown as { attribution: { largestShiftTime?: number } })
            .attribution.largestShiftTime,
          debug_value: (metric as unknown as { attribution: { largestShiftValue?: number } })
            .attribution.largestShiftValue,
        }),
      ...(metric.name === 'LCP' &&
        (metric as unknown as { attribution?: unknown }).attribution && {
          element_tag: (
            metric as unknown as {
              attribution: { element?: { tagName?: string } }
            }
          ).attribution.element?.tagName,
          element_url: (metric as unknown as { attribution: { url?: string } }).attribution.url,
          time_to_first_byte: (metric as unknown as { attribution: { timeToFirstByte?: number } })
            .attribution.timeToFirstByte,
        }),
      ...(metric.name === 'INP' &&
        (metric as unknown as { attribution?: unknown }).attribution && {
          interaction_target: (
            metric as unknown as {
              attribution: { interactionTarget?: string }
            }
          ).attribution.interactionTarget,
          interaction_type: (
            metric as unknown as {
              attribution: { interactionType?: string }
            }
          ).attribution.interactionType,
          input_delay: (metric as unknown as { attribution: { inputDelay?: number } }).attribution
            .inputDelay,
        }),
    })
  }
}

/**
 * Send metric to custom analytics endpoint
 */
function sendToCustomAnalytics(metric: Metric): void {
  const customEndpoint = import.meta.env.VITE_ANALYTICS_ENDPOINT

  if (!customEndpoint) {
    return // Custom analytics not configured
  }

  fetch(customEndpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      timestamp: Date.now(),
      metric: metric.name,
      value: metric.value,
      delta: metric.delta,
      rating: metric.rating,
      id: metric.id,
      attribution: (metric as unknown as { attribution?: unknown }).attribution,
      userAgent: navigator.userAgent,
      url: window.location.href,
    }),
    // Use sendBeacon for reliability (continues after page unload)
    keepalive: true,
  }).catch((error) => {
    console.warn('Failed to send web vitals to custom analytics:', error)
  })
}

/**
 * Add metric to queue for batch processing
 */
function queueMetric(metric: Metric): void {
  metricsQueue.push(metric)

  // Flush queue if it gets too large
  if (metricsQueue.length >= MAX_QUEUE_SIZE) {
    flushMetricsQueue()
  }
}

/**
 * Flush all queued metrics to analytics
 */
function flushMetricsQueue(): void {
  if (metricsQueue.length === 0) return

  console.log(`📊 Sending ${metricsQueue.length} Web Vitals metrics to analytics`)

  metricsQueue.forEach((metric) => {
    sendToGoogleAnalytics(metric)
    sendToCustomAnalytics(metric)
  })

  metricsQueue.length = 0 // Clear queue
}

/**
 * Initialize Web Vitals tracking
 * Should be called once when the app starts
 */
export function initWebVitals(): void {
  // Only track in production or when explicitly enabled
  if (import.meta.env.DEV && !import.meta.env.VITE_ENABLE_WEB_VITALS_DEV) {
    console.log(
      'ℹ️ Web Vitals: Skipping in development (set VITE_ENABLE_WEB_VITALS_DEV=true to enable)'
    )
    return
  }

  console.log('📊 Initializing Web Vitals tracking...')

  // Track all Core Web Vitals metrics
  onCLS((metric) => {
    console.log(`📏 CLS: ${metric.value.toFixed(3)} (${metric.rating})`, metric.attribution)
    queueMetric(metric)
  })

  onINP((metric) => {
    console.log(`⚡ INP: ${metric.value}ms (${metric.rating})`, metric.attribution)
    queueMetric(metric)
  })

  onLCP((metric) => {
    console.log(`🎨 LCP: ${metric.value}ms (${metric.rating})`, metric.attribution)
    queueMetric(metric)
  })

  onFCP((metric) => {
    console.log(`🖌️ FCP: ${metric.value}ms (${metric.rating})`, metric.attribution)
    queueMetric(metric)
  })

  onTTFB((metric) => {
    console.log(`🌐 TTFB: ${metric.value}ms (${metric.rating})`)
    queueMetric(metric)
  })

  // Set up periodic flushing
  setInterval(flushMetricsQueue, FLUSH_INTERVAL)

  // Flush on page visibility change (user switching tabs/minimizing)
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
      flushMetricsQueue()
    }
  })

  // Flush on page unload
  window.addEventListener('pagehide', flushMetricsQueue)
  window.addEventListener('beforeunload', flushMetricsQueue)

  console.log('✅ Web Vitals tracking initialized')
}

/**
 * Manually report a custom performance metric
 */
export function reportCustomMetric(
  name: string,
  value: number,
  context?: Record<string, unknown>
): void {
  const _customMetric: Partial<Metric> = {
    name,
    value,
    delta: value, // For custom metrics, delta equals value
    id: `custom-${name}-${Date.now()}`,
    rating: 'good', // Custom metrics don't have ratings
  }

  console.log(`📊 Custom metric: ${name} = ${value}`, context)

  if (typeof gtag !== 'undefined') {
    gtag('event', name, {
      value,
      ...context,
    })
  }
}

/**
 * Track component performance (complements React Scan)
 */
export function trackComponentPerformance(componentName: string, renderTime: number): void {
  reportCustomMetric(`component_render_${componentName}`, renderTime, {
    component: componentName,
    type: 'render_performance',
  })
}

/**
 * Track user interaction performance
 */
export function trackInteraction(name: string, duration: number): void {
  reportCustomMetric(`interaction_${name}`, duration, {
    interaction: name,
    type: 'user_interaction',
  })
}
