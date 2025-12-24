/**
 * Tests for api.service - Backend API integration
 *
 * Tests the core API functionality:
 * - URL construction
 * - Error handling and message transformation
 * - Response data mapping
 *
 * Note: Uses vi.hoisted + vi.mock to ensure env is set BEFORE module loads
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// Set up env BEFORE the module imports (hoisted to top of file)
const { mockFetch } = vi.hoisted(() => {
  // Stub the env variable before any module loads
  vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8500')
  return {
    mockFetch: vi.fn(),
  }
})

// eslint-disable-next-line import/first -- Module must import AFTER vi.hoisted stubs the env
import { analyzeAPI, healthAPI } from '../api.service'

describe('api.service', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch)
    mockFetch.mockReset()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
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

  describe('analyzeAPI.getAnalysisStatus', () => {
    it('returns analysis status data on success', async () => {
      const mockAnalysis = {
        analysis_id: 'analysis-123',
        url: 'https://example.com',
        content_type: 'article',
        status: 'complete',
        title: 'Example',
        artifact_id: 'artifact-1',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAnalysis,
      })

      const result = await analyzeAPI.getAnalysisStatus('analysis-123')

      expect(result).toEqual(mockAnalysis)
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8500/api/v1/analyze/analysis-123',
        expect.any(Object)
      )
    })

    it('throws on error response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Not found' }),
      })

      await expect(analyzeAPI.getAnalysisStatus('missing')).rejects.toThrow('Not found')
    })
  })

  describe('analyzeAPI.getArtifact', () => {
    it('returns artifact data on success', async () => {
      const mockArtifact = {
        artifact_id: 'artifact-123',
        analysis_id: 'analysis-123',
        markdown_content: '# Implementation Guide',
        created_at: '2025-01-01T00:00:00Z',
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

  describe('analyzeAPI.downloadArtifact', () => {
    it('returns markdown content on success', async () => {
      const markdownContent = '# Implementation Guide\n\nThis is the content.'

      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: async () => markdownContent,
      })

      const result = await analyzeAPI.downloadArtifact('artifact-123')

      expect(result).toBe(markdownContent)
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8500/api/v1/artifacts/artifact-123/download'
      )
    })

    it('returns null on 404 error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      })

      vi.spyOn(console, 'warn').mockImplementation(() => {})

      const result = await analyzeAPI.downloadArtifact('nonexistent-artifact')

      expect(result).toBe(null)
    })

    it('returns null on network failure', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      vi.spyOn(console, 'warn').mockImplementation(() => {})

      const result = await analyzeAPI.downloadArtifact('artifact-123')

      expect(result).toBe(null)
    })

    it('constructs correct URL with artifact ID', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: async () => 'content',
      })

      await analyzeAPI.downloadArtifact('my-unique-artifact-id')

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8500/api/v1/artifacts/my-unique-artifact-id/download'
      )
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
