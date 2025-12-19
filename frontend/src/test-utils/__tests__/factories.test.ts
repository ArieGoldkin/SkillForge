/**
 * Tests for Test Factory Utilities
 *
 * Verifies that factory functions create properly typed mock objects
 * with correct default values and override behavior.
 */

import { describe, expect, it, vi } from 'vitest'

import {
  createMockInfiniteQueryResult,
  createTestSSEProgressEvent,
  createMockAnchorElement,
} from '../factories'

describe('Test Factories', () => {
  describe('createMockInfiniteQueryResult', () => {
    it('creates default infinite query result with success state', () => {
      const result = createMockInfiniteQueryResult()

      expect(result.isSuccess).toBe(true)
      expect(result.isLoading).toBe(false)
      expect(result.isError).toBe(false)
      expect(result.error).toBeNull()
      expect(result.data).toEqual({ pages: [], pageParams: [] })
    })

    it('allows overriding specific properties', () => {
      const mockData = { pages: [{ id: 1, name: 'Test' }], pageParams: [undefined] }
      const result = createMockInfiniteQueryResult({
        data: mockData,
        isLoading: true,
        isSuccess: false,
      })

      expect(result.data).toEqual(mockData)
      expect(result.isLoading).toBe(true)
      expect(result.isSuccess).toBe(false)
    })

    it('creates mock functions for methods', () => {
      const result = createMockInfiniteQueryResult()

      expect(result.refetch).toBeDefined()
      expect(result.fetchNextPage).toBeDefined()
      expect(result.fetchPreviousPage).toBeDefined()
      expect(vi.isMockFunction(result.refetch)).toBe(true)
    })

    it('supports infinite query pagination properties', () => {
      const result = createMockInfiniteQueryResult({
        hasNextPage: true,
        isFetchingNextPage: true,
      })

      expect(result.hasNextPage).toBe(true)
      expect(result.hasPreviousPage).toBe(false)
      expect(result.isFetchingNextPage).toBe(true)
    })

    it('is fully typed without any type assertions', () => {
      const result = createMockInfiniteQueryResult<{ id: number; name: string }>()

      // TypeScript should understand these properties exist
      expect(result.status).toBe('success')
      expect(result.fetchStatus).toBe('idle')
      expect(typeof result.dataUpdatedAt).toBe('number')
    })
  })

  describe('createTestSSEProgressEvent', () => {
    it('creates default SSE progress event', () => {
      const event = createTestSSEProgressEvent({})

      expect(event.type).toBe('progress')
      expect(event.stage).toBe('extraction')
      expect(event.status).toBe('running')
      expect(event.analysis_id).toBe('00000000-0000-0000-0000-000000000000')
      expect(event.timestamp).toBeDefined()
    })

    it('allows overriding core fields', () => {
      const event = createTestSSEProgressEvent({
        analysis_id: '123e4567-e89b-12d3-a456-426614174000',
        stage: 'synthesis',
        status: 'complete',
      })

      expect(event.analysis_id).toBe('123e4567-e89b-12d3-a456-426614174000')
      expect(event.stage).toBe('synthesis')
      expect(event.status).toBe('complete')
    })

    it('supports optional SSE fields', () => {
      const event = createTestSSEProgressEvent({
        expected_total_stages: 10,
        findings_summary: 'Found 5 key insights',
        confidence_score: 0.85,
      })

      expect(event.expected_total_stages).toBe(10)
      expect(event.findings_summary).toBe('Found 5 key insights')
      expect(event.confidence_score).toBe(0.85)
    })

    it('allows adding extra backend fields not in schema', () => {
      const event = createTestSSEProgressEvent(
        {
          analysis_id: '123e4567-e89b-12d3-a456-426614174000',
          stage: 'extraction',
        },
        {
          internal_step_id: 42,
          debug_info: 'Processing chunk 5/10',
        }
      )

      expect(event.type).toBe('progress')
      expect(event.stage).toBe('extraction')
      // @ts-expect-error - extras are not in strict schema but allowed at runtime
      expect(event.internal_step_id).toBe(42)
      // @ts-expect-error - extras are not in strict schema but allowed at runtime
      expect(event.debug_info).toBe('Processing chunk 5/10')
    })

    it('generates valid ISO timestamp by default', () => {
      const event = createTestSSEProgressEvent({})

      expect(event.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)
    })
  })

  describe('createMockAnchorElement', () => {
    it('creates default anchor element', () => {
      const anchor = createMockAnchorElement()

      expect(anchor.tagName).toBe('A')
      expect(anchor.nodeName).toBe('A')
      expect(anchor.nodeType).toBe(1)
      expect(anchor.href).toBe('')
      expect(anchor.download).toBe('')
    })

    it('allows overriding anchor properties', () => {
      const anchor = createMockAnchorElement({
        href: 'https://example.com/file.pdf',
        download: 'document.pdf',
        target: '_blank',
      })

      expect(anchor.href).toBe('https://example.com/file.pdf')
      expect(anchor.download).toBe('document.pdf')
      expect(anchor.target).toBe('_blank')
    })

    it('creates mock functions for methods', () => {
      const anchor = createMockAnchorElement()

      // Verify methods exist and are functions
      expect(typeof anchor.click).toBe('function')
      expect(typeof anchor.setAttribute).toBe('function')
      expect(typeof anchor.getAttribute).toBe('function')
      expect(vi.isMockFunction(anchor.click)).toBe(true)
    })

    it('supports custom click handler', () => {
      const mockClick = vi.fn()
      const anchor = createMockAnchorElement({ click: mockClick })

      anchor.click()
      expect(mockClick).toHaveBeenCalled()
    })

    it('includes classList utilities', () => {
      const anchor = createMockAnchorElement()

      expect(anchor.classList).toBeTruthy()
      expect(typeof anchor.classList.add).toBe('function')
      expect(vi.isMockFunction(anchor.classList.add)).toBe(true)
    })

    it('can be used in document.createElement mock', () => {
      const mockAnchor = createMockAnchorElement()
      const createElementSpy = vi
        .spyOn(document, 'createElement')
        .mockReturnValue(mockAnchor as unknown as HTMLElement)

      const anchor = document.createElement('a') as unknown as HTMLAnchorElement
      expect(anchor.tagName).toBe('A')
      expect(typeof anchor.click).toBe('function')

      createElementSpy.mockRestore()
    })
  })
})
