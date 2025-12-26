import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PREFETCH_TARGETS } from '../usePrefetch'

/**
 * @unit Test usePrefetch configuration and targets
 */

// Mock fetch globally
global.fetch = vi.fn()

describe('usePrefetch', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should expose PREFETCH_TARGETS', () => {
    expect(PREFETCH_TARGETS).toBeDefined()
    expect(PREFETCH_TARGETS).toHaveProperty('analysisDetail')
    expect(PREFETCH_TARGETS).toHaveProperty('artifactDetail')
    expect(PREFETCH_TARGETS).toHaveProperty('library')
  })

  describe('PREFETCH_TARGETS', () => {
    it('should generate correct analysis target', () => {
      const target = PREFETCH_TARGETS.analysisDetail('test-123')

      expect(target.route).toBe('/analyze/test-123')
      expect(target.queryKey).toEqual(['analysis', 'test-123'])
      expect(target.queryFn).toBeDefined()
    })

    it('should generate correct artifact target with analysisId', () => {
      const target = PREFETCH_TARGETS.artifactDetail('artifact-456', 'analysis-123')

      expect(target.route).toBe('/artifact/artifact-456?analysisId=analysis-123')
      expect(target.queryKey).toEqual(['artifact', 'artifact-456'])
      expect(target.queryFn).toBeDefined()
    })

    it('should generate artifact target without analysisId', () => {
      const target = PREFETCH_TARGETS.artifactDetail('artifact-456')

      expect(target.route).toBe('/artifact/artifact-456')
      expect(target.queryKey).toEqual(['artifact', 'artifact-456'])
    })

    it('should generate correct library target', () => {
      const target = PREFETCH_TARGETS.library()

      expect(target.route).toBe('/library')
      expect(target.queryKey).toBeUndefined()
      expect(target.queryFn).toBeUndefined()
    })

    it('should provide queryFn that fetches analysis data', async () => {
      const mockResponse = { id: 'test-123', status: 'complete' }
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const target = PREFETCH_TARGETS.analysisDetail('test-123')
      const result = await target.queryFn!()

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/api/v1/analyze/test-123'))
    })

    it('should provide queryFn that fetches artifact data', async () => {
      const mockResponse = { id: 'artifact-456', title: 'Test Artifact' }
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const target = PREFETCH_TARGETS.artifactDetail('artifact-456')
      const result = await target.queryFn!()

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/api/v1/artifacts/artifact-456'))
    })

    it('should throw error when fetch fails', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 404,
      } as Response)

      const target = PREFETCH_TARGETS.analysisDetail('test-123')

      await expect(target.queryFn!()).rejects.toThrow('Failed to prefetch analysis: 404')
    })
  })
})
