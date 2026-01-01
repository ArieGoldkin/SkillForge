import { describe, expect, it } from 'vitest'

import {
  collectErrorCodesFromEvents,
  collectErrorCodesFromREST,
  collectErrorCodesFromStages,
} from '../errorCodeCollection'

import type { SSEEvent } from '@/schemas/sse'
import type { StageStatusEntry } from '../stageConfig'

describe('errorCodeCollection', () => {
  describe('collectErrorCodesFromREST', () => {
    it('collects error code from REST response', () => {
      const result = collectErrorCodesFromREST('EXTRACTION_FAILED')
      expect(Array.from(result)).toEqual(['EXTRACTION_FAILED'])
    })

    it('handles null error code', () => {
      const result = collectErrorCodesFromREST(null)
      expect(Array.from(result)).toEqual([])
    })

    it('handles undefined error code', () => {
      const result = collectErrorCodesFromREST(undefined)
      expect(Array.from(result)).toEqual([])
    })

    it('returns empty set for empty string', () => {
      const result = collectErrorCodesFromREST('')
      expect(Array.from(result)).toEqual([])
    })
  })

  describe('collectErrorCodesFromStages', () => {
    it('collects error codes from failed stages', () => {
      const stageStatuses = new Map<string, StageStatusEntry>([
        [
          'extraction',
          {
            status: 'failed',
            details: { error_code: 'EXTRACTION_FAILED' },
          } as StageStatusEntry,
        ],
        [
          'analysis',
          {
            status: 'complete',
            details: {},
          } as StageStatusEntry,
        ],
      ])

      const result = collectErrorCodesFromStages(stageStatuses)
      expect(Array.from(result)).toEqual(['EXTRACTION_FAILED'])
    })

    it('returns empty set when no failed stages', () => {
      const stageStatuses = new Map<string, StageStatusEntry>([
        [
          'extraction',
          {
            status: 'complete',
            details: {},
          } as StageStatusEntry,
        ],
      ])

      const result = collectErrorCodesFromStages(stageStatuses)
      expect(Array.from(result)).toEqual([])
    })
  })

  describe('collectErrorCodesFromEvents', () => {
    it('collects error codes from error events', () => {
      const events: SSEEvent[] = [
        {
          type: 'error',
          analysis_id: '123e4567-e89b-12d3-a456-426614174000',
          stage: 'extraction',
          status: 'failed',
          timestamp: '2025-01-01T00:00:00Z',
          details: { error_code: 'ANALYSIS_FAILED' },
        } as SSEEvent,
      ]

      const result = collectErrorCodesFromEvents(events)
      expect(Array.from(result)).toEqual(['ANALYSIS_FAILED'])
    })

    it('collects error codes from failed progress events', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: '123e4567-e89b-12d3-a456-426614174000',
          stage: 'extraction',
          status: 'failed',
          timestamp: '2025-01-01T00:00:00Z',
          error_code: 'EXTRACTION_FAILED',
        } as SSEEvent,
      ]

      const result = collectErrorCodesFromEvents(events)
      expect(Array.from(result)).toEqual(['EXTRACTION_FAILED'])
    })

    it('returns empty set when no error events', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: 'test-id',
          stage: 'extraction',
          status: 'complete',
          timestamp: '2025-01-01T00:00:00Z',
        } as SSEEvent,
      ]

      const result = collectErrorCodesFromEvents(events)
      expect(Array.from(result)).toEqual([])
    })
  })

  describe('integration: combining all sources', () => {
    it('deduplicates error codes from multiple sources', () => {
      const stageStatuses = new Map<string, StageStatusEntry>([
        [
          'extraction',
          {
            status: 'failed',
            details: { error_code: 'EXTRACTION_FAILED' },
          } as StageStatusEntry,
        ],
      ])

      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: 'test-id',
          stage: 'extraction',
          status: 'failed',
          timestamp: '2025-01-01T00:00:00Z',
          error_code: 'EXTRACTION_FAILED',
        } as SSEEvent,
      ]

      const restErrorCode = 'EXTRACTION_FAILED'

      const allCodes = new Set<string>()
      collectErrorCodesFromStages(stageStatuses).forEach((code) => allCodes.add(code))
      collectErrorCodesFromEvents(events).forEach((code) => allCodes.add(code))
      collectErrorCodesFromREST(restErrorCode).forEach((code) => allCodes.add(code))

      // Should deduplicate - only one instance of EXTRACTION_FAILED
      expect(Array.from(allCodes)).toEqual(['EXTRACTION_FAILED'])
    })

    it('combines different error codes from multiple sources', () => {
      const stageStatuses = new Map<string, StageStatusEntry>([
        [
          'extraction',
          {
            status: 'failed',
            details: { error_code: 'EXTRACTION_FAILED' },
          } as StageStatusEntry,
        ],
      ])

      const events: SSEEvent[] = [
        {
          type: 'error',
          analysis_id: '123e4567-e89b-12d3-a456-426614174000',
          stage: 'analysis',
          status: 'failed',
          timestamp: '2025-01-01T00:00:00Z',
          details: { error_code: 'ANALYSIS_FAILED' },
        } as SSEEvent,
      ]

      const restErrorCode = 'QUALITY_GATE_FAILED'

      const allCodes = new Set<string>()
      collectErrorCodesFromStages(stageStatuses).forEach((code) => allCodes.add(code))
      collectErrorCodesFromEvents(events).forEach((code) => allCodes.add(code))
      collectErrorCodesFromREST(restErrorCode).forEach((code) => allCodes.add(code))

      expect(Array.from(allCodes).sort()).toEqual([
        'ANALYSIS_FAILED',
        'EXTRACTION_FAILED',
        'QUALITY_GATE_FAILED',
      ])
    })
  })
})
