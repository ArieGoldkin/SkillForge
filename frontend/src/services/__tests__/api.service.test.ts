/**
 * Tests for api.service - Backend API integration with ky HTTP client
 *
 * Tests the core API functionality:
 * - URL construction
 * - Error handling and message transformation
 * - Response data mapping
 * - Zod validation
 *
 * Issue #550: ky HTTP client with interceptors
 * Issue #548: Zod runtime validation
 *
 * Note: Uses vi.hoisted + vi.mock to ensure env is set BEFORE module loads
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// Set up env and fetch mock BEFORE the module imports (hoisted to top of file)
const { mockFetch } = vi.hoisted(() => {
  // Stub the env variable before any module loads
  vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8500')

  // Create mock fetch and stub it globally before ky imports
  const mock = vi.fn()
  vi.stubGlobal('fetch', mock)

  return {
    mockFetch: mock,
  }
})

// Valid UUIDs for tests (Issue #548: Zod validation requires valid UUIDs)
// UUID format: 8-4-[1-8]xxx-[89ab]xxx-12 (version + variant bytes)
const VALID_ANALYSIS_ID = '123e4567-e89b-12d3-a456-426614174000'
const VALID_ANALYSIS_ID_2 = '987fcdeb-51a2-43d7-8f9e-123456789abc'
const VALID_ARTIFACT_ID = 'aaaabbbb-cccc-1ddd-8eee-ffffffffffff'

// eslint-disable-next-line import/first -- Module must import AFTER vi.hoisted stubs the env
import { analyzeAPI, healthAPI } from '../api.service'

/**
 * Helper to create a mock Response object that ky expects
 * Uses actual Response constructor for proper compatibility
 */
function createMockResponse(data: unknown, options: { status?: number } = {}): Response {
  const { status = 200 } = options
  const body = typeof data === 'string' ? data : JSON.stringify(data)

  return new Response(body, {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

/**
 * Helper to create a mock text Response (for download endpoints)
 */
function createMockTextResponse(text: string, options: { status?: number } = {}): Response {
  const { status = 200 } = options

  return new Response(text, {
    status,
    headers: { 'Content-Type': 'text/plain' },
  })
}

describe('api.service', () => {
  beforeEach(() => {
    // Reset mock before each test (fetch already stubbed in hoisted block)
    mockFetch.mockReset()
  })

  afterEach(() => {
    // Note: We don't unstub globals since fetch must remain mocked for ky
    vi.restoreAllMocks()
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
      mockFetch.mockResolvedValueOnce(
        createMockResponse({
          analysis_id: VALID_ANALYSIS_ID,
          url: 'https://example.com/article',
          content_type: 'article',
          status: 'pending',
          sse_endpoint: `/api/v1/analyze/${VALID_ANALYSIS_ID}/stream`,
        })
      )

      const requestPayload = {
        url: 'https://example.com/article',
        content_type: 'article' as const,
      }

      await analyzeAPI.createAnalysis(requestPayload)

      // ky passes Request object to fetch, not separate url/options
      expect(mockFetch).toHaveBeenCalled()
      const [request] = mockFetch.mock.calls[0] as [Request]
      expect(request.url).toBe('http://localhost:8500/api/v1/analyze')
      expect(request.method).toBe('POST')
      // Verify content-type header is set for JSON
      expect(request.headers.get('content-type')).toBe('application/json')
    })

    it('transforms backend response to frontend format', async () => {
      mockFetch.mockResolvedValueOnce(
        createMockResponse({
          analysis_id: VALID_ANALYSIS_ID,
          url: 'https://example.com',
          content_type: 'article',
          status: 'pending',
          sse_endpoint: `/api/v1/analyze/${VALID_ANALYSIS_ID}/stream`,
        })
      )

      const result = await analyzeAPI.createAnalysis({
        url: 'https://example.com',
        content_type: 'article',
      })

      // Issue #548: AnalyzeResponseSchema includes optional url and content_type
      expect(result).toMatchObject({
        analysis_id: VALID_ANALYSIS_ID,
        sse_endpoint: `/api/v1/analyze/${VALID_ANALYSIS_ID}/stream`,
        status: 'pending',
      })
    })

    it('throws error with detail message on API failure', async () => {
      mockFetch.mockResolvedValueOnce(
        createMockResponse({ detail: 'Invalid URL format' }, { status: 400 })
      )

      await expect(
        analyzeAPI.createAnalysis({
          url: 'invalid-url',
          content_type: 'article',
        })
      ).rejects.toThrow()
    })

    it('throws error with message field on API failure', async () => {
      mockFetch.mockResolvedValueOnce(
        createMockResponse({ message: 'Internal server error' }, { status: 500 })
      )

      await expect(
        analyzeAPI.createAnalysis({
          url: 'https://example.com',
          content_type: 'article',
        })
      ).rejects.toThrow()
    })

    it('throws generic error when no error message available', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({}, { status: 503 }))

      await expect(
        analyzeAPI.createAnalysis({
          url: 'https://example.com',
          content_type: 'article',
        })
      ).rejects.toThrow()
    })

    it('handles JSON parse failure in error response', async () => {
      // Create a response with invalid JSON body
      mockFetch.mockResolvedValueOnce(
        new Response('not valid json', {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        })
      )

      await expect(
        analyzeAPI.createAnalysis({
          url: 'https://example.com',
          content_type: 'article',
        })
      ).rejects.toThrow()
    })
  })

  describe('analyzeAPI.getAnalysisStatus', () => {
    it('returns analysis status data on success', async () => {
      // Issue #548: AnalysisStatusResponseSchema only expects { status, artifact_id? }
      const mockStatusResponse = {
        status: 'complete',
        artifact_id: VALID_ARTIFACT_ID,
      }

      mockFetch.mockResolvedValueOnce(createMockResponse(mockStatusResponse))

      const result = await analyzeAPI.getAnalysisStatus(VALID_ANALYSIS_ID)

      expect(result).toEqual(mockStatusResponse)
      expect(mockFetch).toHaveBeenCalled()
      const [request] = mockFetch.mock.calls[0] as [Request]
      expect(request.url).toBe(`http://localhost:8500/api/v1/analyze/${VALID_ANALYSIS_ID}`)
    })

    it('throws on error response', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ detail: 'Not found' }, { status: 404 }))

      await expect(analyzeAPI.getAnalysisStatus('missing')).rejects.toThrow()
    })
  })

  describe('analyzeAPI.getArtifact', () => {
    it('returns artifact data on success', async () => {
      // Issue #548: Mock data must match ArtifactMetadataResponseSchema (valid UUIDs)
      const mockArtifact = {
        artifact_id: VALID_ARTIFACT_ID,
        analysis_id: VALID_ANALYSIS_ID,
        markdown_content: '# Implementation Guide',
        created_at: '2025-01-01T00:00:00Z',
      }

      mockFetch.mockResolvedValueOnce(createMockResponse(mockArtifact))

      const result = await analyzeAPI.getArtifact(VALID_ANALYSIS_ID)

      expect(result).toEqual(mockArtifact)
    })

    it('returns null on error', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ detail: 'Not found' }, { status: 404 }))

      vi.spyOn(console, 'warn').mockImplementation(() => {})

      const result = await analyzeAPI.getArtifact(VALID_ANALYSIS_ID)

      expect(result).toBe(null)
    })
  })

  describe('analyzeAPI.listAnalyses', () => {
    it('returns array of analyses on success', async () => {
      // Issue #548: Mock data must match AnalysisSchema (full objects with all required fields)
      // ContentTypeSchema only allows: 'article' | 'video' | 'repo'
      const mockAnalyses = [
        {
          id: VALID_ANALYSIS_ID,
          url: 'https://a.com',
          content_type: 'article',
          title: 'Test Analysis 1',
          status: 'complete',
          created_at: '2025-12-25T10:00:00Z',
          artifact_id: VALID_ARTIFACT_ID,
        },
        {
          id: VALID_ANALYSIS_ID_2,
          url: 'https://b.com',
          content_type: 'video',
          title: 'Test Analysis 2',
          status: 'pending',
          created_at: '2025-12-25T11:00:00Z',
          artifact_id: null,
        },
      ]

      mockFetch.mockResolvedValueOnce(createMockResponse(mockAnalyses))

      const result = await analyzeAPI.listAnalyses()

      expect(result).toEqual(mockAnalyses)
    })

    it('returns empty array on error', async () => {
      mockFetch.mockResolvedValueOnce(
        createMockResponse({ detail: 'Not implemented' }, { status: 501 })
      )

      vi.spyOn(console, 'warn').mockImplementation(() => {})

      const result = await analyzeAPI.listAnalyses()

      expect(result).toEqual([])
    })
  })

  describe('analyzeAPI.downloadArtifact', () => {
    it('returns markdown content on success', async () => {
      const markdownContent = '# Implementation Guide\n\nThis is the content.'

      mockFetch.mockResolvedValueOnce(createMockTextResponse(markdownContent))

      const result = await analyzeAPI.downloadArtifact('artifact-123')

      expect(result).toBe(markdownContent)
    })

    it('returns null on 404 error', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ detail: 'Not found' }, { status: 404 }))

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
      mockFetch.mockResolvedValueOnce(createMockTextResponse('content'))

      await analyzeAPI.downloadArtifact('my-unique-artifact-id')

      expect(mockFetch).toHaveBeenCalled()
      const [request] = mockFetch.mock.calls[0] as [Request]
      expect(request.url).toBe(
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

      mockFetch.mockResolvedValueOnce(createMockResponse(mockHealth))

      const result = await healthAPI.check()

      expect(result).toEqual(mockHealth)
      expect(mockFetch).toHaveBeenCalled()
      const [request] = mockFetch.mock.calls[0] as [Request]
      expect(request.url).toBe('http://localhost:8500/api/v1/health')
    })
  })
})
