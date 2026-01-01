/**
 * Error code collection utilities
 *
 * Extracts error codes from failed stages, SSE events, and REST API responses for UI display.
 */

import { isErrorEvent, isProgressEvent } from '@/schemas/sse'
import type { SSEEvent } from '@/schemas/sse'

import type { StageStatusEntry } from './stageConfig'

/**
 * Collect error codes from failed stages
 */
export function collectErrorCodesFromStages(
  stageStatuses: Map<string, StageStatusEntry>
): Set<string> {
  const errorCodes = new Set<string>()
  for (const stageData of stageStatuses.values()) {
    if (stageData.status === 'failed' && stageData.details?.error_code) {
      const errorCode = stageData.details.error_code as string
      if (errorCode) {
        errorCodes.add(errorCode)
      }
    }
  }
  return errorCodes
}

/**
 * Collect error codes from events
 */
export function collectErrorCodesFromEvents(events: SSEEvent[]): Set<string> {
  const errorCodes = new Set<string>()
  for (const event of events) {
    if (isErrorEvent(event) && event.details?.error_code) {
      const errorCode = event.details.error_code as string
      if (errorCode) {
        errorCodes.add(errorCode)
      }
    }
    // Check failed progress events for error codes
    if (isProgressEvent(event) && event.status === 'failed') {
      const errorCode =
        (event.error_code as string | undefined) ||
        (event.details?.error_code as string | undefined)
      if (errorCode) {
        errorCodes.add(errorCode)
      }
    }
  }
  return errorCodes
}

/**
 * Collect error codes from REST API response
 *
 * Extracts error_code from analysis status response when viewing completed analyses.
 * This complements SSE-based collection for analyses viewed after completion.
 */
export function collectErrorCodesFromREST(errorCode: string | null | undefined): Set<string> {
  const errorCodes = new Set<string>()
  if (errorCode) {
    errorCodes.add(errorCode)
  }
  return errorCodes
}
