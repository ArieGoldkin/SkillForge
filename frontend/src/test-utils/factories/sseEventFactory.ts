/**
 * SSE Event Factory for Testing
 *
 * Provides type-safe builders for creating SSE progress events in tests,
 * with support for both strict schema fields and flexible backend extras.
 *
 * @module test-utils/factories/sseEventFactory
 */

import type { SSEProgressEvent } from '@app-types/sse'

/**
 * Create a type-safe SSE progress event with optional extra fields
 *
 * This factory supports the common testing pattern where backend may send
 * additional fields not strictly defined in the TypeScript schema.
 * The returned type includes both the strict SSEProgressEvent fields
 * and any additional properties from the extras parameter.
 *
 * @example
 * ```typescript
 * // Standard progress event
 * const event = createTestSSEProgressEvent({
 *   analysis_id: '123e4567-e89b-12d3-a456-426614174000',
 *   stage: 'extraction',
 *   status: 'running'
 * })
 *
 * // With backend-specific extras not in schema
 * const eventWithExtras = createTestSSEProgressEvent(
 *   {
 *     analysis_id: '123e4567-e89b-12d3-a456-426614174000',
 *     stage: 'extraction',
 *     status: 'running'
 *   },
 *   {
 *     internal_step_id: 42,
 *     debug_info: 'Processing chunk 5/10'
 *   }
 * )
 * ```
 *
 * @param base - Core SSE progress event fields (partial for convenience)
 * @param extras - Additional fields that backend may send but aren't in strict schema
 * @returns SSEProgressEvent with both schema fields and extras
 */
export function createTestSSEProgressEvent(
  base: Partial<SSEProgressEvent>,
  extras?: Record<string, unknown>
): SSEProgressEvent & Record<string, unknown> {
  // Generate default UUID if not provided
  const defaultAnalysisId = '00000000-0000-0000-0000-000000000000'

  // Filter out undefined values from base to avoid overriding defaults
  const filteredBase = Object.entries(base).reduce(
    (acc, [key, value]) => {
      if (value !== undefined) {
        acc[key as keyof SSEProgressEvent] = value
      }
      return acc
    },
    {} as Partial<SSEProgressEvent>
  )

  // Core required fields with defaults
  const coreEvent: SSEProgressEvent = {
    type: 'progress',
    analysis_id: defaultAnalysisId,
    stage: 'extraction',
    status: 'running',
    timestamp: new Date().toISOString(),
    ...filteredBase, // Override with any provided base fields
  }

  // Merge with extras if provided
  return extras ? { ...coreEvent, ...extras } : coreEvent
}
