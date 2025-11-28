/**
 * Tests for api.service - Backend API integration
 *
 * Tests the core API functionality:
 * - URL construction
 * - Error handling and message transformation
 * - Response data mapping
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { analyzeAPI, healthAPI } from '../api.service'

// Mock fetch globally
const mockFetch = vi.fn()

describe('api.service', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch)
    vi.stubEnv('VITE_API_URL', 'http://localhost:8500')
    mockFetch.mockReset()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  describe('analyzeAPI.getSSEEndpoint', () => {
    it('constructs correct SSE endpoint URL', () => {
      const analysisId = 'abc-123-def'
      const endpoint = analyzeAPI.getSSEEndpoint(analysisId)

      expect(endpoint).toBe('http://localhost:8500/api/v1/analyze/abc-123-def/stream')
    })

    it('handles different analysis IDs', () => {
      expect(analyzeAPI.getSSEEndpoint('test-id')).toContain('/test-id/stream')
      expect(analyzeAPI.getSSEEndpoint('uuid-format-id')).toContain('/uuid-format-id/stream')
    })
  })

  describe('analyzeAPI.createAnalysis', () => {
    it('sends POST request with correct payload', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          analysis_id: 'new-analysis-123',
          url: 'https://example.com/article',
          content_type: 'article',
          status: 'processing',
          sse_endpoint: '/api/v1/analyze/new-analysis-123/stream',
        }),
      })

      const request = {
        url: 'https://example.com/article',
        content_type: 'article' as const,
      }

      await analyzeAPI.createAnalysis(request)

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8500/api/v1/analyze',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(request),
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      )
    })

    it('transforms backend response to frontend format', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          analysis_id: 'response-123',
          url: 'https://example.com',
          content_type: 'article',
          status: 'processing',
          sse_endpoint: '/api/v1/analyze/response-123/stream',
        }),
      })

      const result = await analyzeAPI.createAnalysis({
        url: 'https://example.com',
        content_type: 'article',
      })

      expect(result).toEqual({
        analysis_id: 'response-123',
        sse_endpoint: '/api/v1/analyze/response-123/stream',
        status: 'processing',
      })
    })

    it('throws error with detail message on API failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({
          detail: 'Invalid URL format',
        }),
      })

      await expect(
        analyzeAPI.createAnalysis({
          url: 'invalid-url',
          content_type: 'article',
        })
      ).rejects.toThrow('Invalid URL format')
    })

    it('throws error with message field on API failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({
          message: 'Internal server error',
        }),
      })

      await expect(
        analyzeAPI.createAnalysis({
          url: 'https://example.com',
          content_type: 'article',
        })
      ).rejects.toThrow('Internal server error')
    })

    it('throws generic error when no error message available', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 503,
        json: async () => ({}),
      })

      await expect(
        analyzeAPI.createAnalysis({
          url: 'https://example.com',
          content_type: 'article',
        })
      ).rejects.toThrow('API error: 503')
    })

    it('handles JSON parse failure in error response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('Invalid JSON')
        },
      })

      await expect(
        analyzeAPI.createAnalysis({
          url: 'https://example.com',
          content_type: 'article',
        })
      ).rejects.toThrow('API error: 500')
    })
  })

  describe('analyzeAPI.getAnalysis', () => {
    it('returns analysis data on success', async () => {
      const mockAnalysis = {
        id: 'analysis-123',
        url: 'https://example.com',
        status: 'complete',
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAnalysis,
      })

      const result = await analyzeAPI.getAnalysis('analysis-123')

      expect(result).toEqual(mockAnalysis)
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8500/api/v1/analyze/analysis-123',
        expect.any(Object)
      )
    })

    it('returns null on 501 (not implemented)', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 501,
        json: async () => ({ detail: 'Not implemented' }),
      })

      // Suppress console.warn for this test
      vi.spyOn(console, 'warn').mockImplementation(() => {})

      const result = await analyzeAPI.getAnalysis('analysis-123')

      expect(result).toBe(null)
    })
  })

  describe('analyzeAPI.getArtifact', () => {
    it('returns artifact data on success', async () => {
      const mockArtifact = {
        id: 'artifact-123',
        content: '# Implementation Guide',
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockArtifact,
      })

      const result = await analyzeAPI.getArtifact('analysis-123')

      expect(result).toEqual(mockArtifact)
    })

    it('returns null on error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Not found' }),
      })

      vi.spyOn(console, 'warn').mockImplementation(() => {})

      const result = await analyzeAPI.getArtifact('analysis-123')

      expect(result).toBe(null)
    })
  })

  describe('analyzeAPI.listAnalyses', () => {
    it('returns array of analyses on success', async () => {
      const mockAnalyses = [
        { id: '1', url: 'https://a.com', status: 'complete' },
        { id: '2', url: 'https://b.com', status: 'processing' },
      ]

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAnalyses,
      })

      const result = await analyzeAPI.listAnalyses()

      expect(result).toEqual(mockAnalyses)
    })

    it('returns empty array on error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 501,
        json: async () => ({ detail: 'Not implemented' }),
      })

      vi.spyOn(console, 'warn').mockImplementation(() => {})

      const result = await analyzeAPI.listAnalyses()

      expect(result).toEqual([])
    })
  })

  describe('healthAPI.check', () => {
    it('returns health status on success', async () => {
      const mockHealth = {
        status: 'healthy',
        version: '1.0.0',
        environment: 'development',
        database: { status: 'connected' },
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockHealth,
      })

      const result = await healthAPI.check()

      expect(result).toEqual(mockHealth)
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8500/api/v1/health',
        expect.any(Object)
      )
    })
  })
})
