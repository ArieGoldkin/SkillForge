/**
 * MSW Request Handlers
 *
 * Issue #551: MSW for Network-Level API Mocking
 *
 * Defines handlers for all API endpoints. These handlers intercept
 * network requests during tests and return mock responses.
 *
 * @module mocks/handlers
 */

import { http, HttpResponse, delay } from 'msw'

import { MOCK_DELAY_CONSTANTS } from '@/lib/constants'

import {
  mockAnalyzeResponse,
  mockAnalysisStatus,
  mockArtifact,
  mockAnalysisList,
  mockAnalysisProgress,
  mockSSEEvents,
  mockHealthCheck,
  mockLibraryList,
} from './factories'

// Base URL for API requests
const API_BASE = 'http://localhost:8500'

/**
 * Default API handlers for happy-path scenarios
 */
export const handlers = [
  // ============================
  // Analysis Endpoints
  // ============================

  // POST /api/v1/analyze - Create new analysis
  http.post(`${API_BASE}/api/v1/analyze`, async ({ request }) => {
    await delay(MOCK_DELAY_CONSTANTS.NETWORK_LATENCY) // Simulate network latency
    const body = (await request.json()) as { url: string; content_type: string }
    return HttpResponse.json(
      mockAnalyzeResponse({ url: body.url, content_type: body.content_type })
    )
  }),

  // GET /api/v1/analyze/:id - Get analysis status
  http.get(`${API_BASE}/api/v1/analyze/:id`, async ({ params }) => {
    await delay(MOCK_DELAY_CONSTANTS.FAST)
    const id = params.id as string

    // Special IDs for testing error scenarios
    if (id === 'not-found') {
      return HttpResponse.json({ detail: 'Analysis not found' }, { status: 404 })
    }
    if (id === 'error-500') {
      return HttpResponse.json({ detail: 'Internal server error' }, { status: 500 })
    }

    return HttpResponse.json(mockAnalysisStatus())
  }),

  // GET /api/v1/analyze/:id/progress - Get progress events
  http.get(`${API_BASE}/api/v1/analyze/:id/progress`, async ({ params }) => {
    await delay(MOCK_DELAY_CONSTANTS.FAST)
    return HttpResponse.json(mockAnalysisProgress(params.id as string))
  }),

  // GET /api/v1/analyze/:id/artifact - Get artifact by analysis
  http.get(`${API_BASE}/api/v1/analyze/:id/artifact`, async () => {
    await delay(MOCK_DELAY_CONSTANTS.FAST)
    return HttpResponse.json(mockArtifact())
  }),

  // GET /api/v1/analyze/:id/stream - SSE streaming endpoint
  http.get(`${API_BASE}/api/v1/analyze/:id/stream`, ({ params }) => {
    const analysisId = params.id as string
    const events = mockSSEEvents(analysisId)
    const encoder = new TextEncoder()

    const stream = new ReadableStream({
      async start(controller) {
        for (const event of events) {
          await delay(MOCK_DELAY_CONSTANTS.SSE_EVENT)
          const data = `data: ${JSON.stringify(event)}\n\n`
          controller.enqueue(encoder.encode(data))
        }
        controller.close()
      },
    })

    return new HttpResponse(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
    })
  }),

  // GET /api/v1/analyze - List all analyses
  http.get(`${API_BASE}/api/v1/analyze`, async () => {
    await delay(MOCK_DELAY_CONSTANTS.NORMAL)
    return HttpResponse.json(mockAnalysisList())
  }),

  // POST /api/v1/analyze/:id/retry - Retry failed analysis
  http.post(`${API_BASE}/api/v1/analyze/:id/retry`, async ({ params }) => {
    await delay(MOCK_DELAY_CONSTANTS.NORMAL)
    const id = params.id as string
    return HttpResponse.json({
      analysis_id: id,
      status: 'pending',
      retry_count: 1,
      sse_endpoint: `/api/v1/analyze/${id}/stream`,
    })
  }),

  // POST /api/v1/analyze/:id/rerun - Rerun completed analysis
  http.post(`${API_BASE}/api/v1/analyze/:id/rerun`, async ({ params }) => {
    await delay(MOCK_DELAY_CONSTANTS.NORMAL)
    const id = params.id as string
    return HttpResponse.json({
      analysis_id: id,
      status: 'pending',
      rerun_count: 1,
      archived_artifact_id: null,
      sse_endpoint: `/api/v1/analyze/${id}/stream`,
    })
  }),

  // DELETE /api/v1/analyses/:id - Delete analysis
  http.delete(`${API_BASE}/api/v1/analyses/:id`, async () => {
    await delay(MOCK_DELAY_CONSTANTS.FAST)
    return new HttpResponse(null, { status: 204 })
  }),

  // ============================
  // Artifact Endpoints
  // ============================

  // GET /api/v1/artifacts/:id - Get artifact metadata
  http.get(`${API_BASE}/api/v1/artifacts/:id`, async () => {
    await delay(MOCK_DELAY_CONSTANTS.FAST)
    return HttpResponse.json(mockArtifact())
  }),

  // GET /api/v1/artifacts/:id/download - Download artifact markdown
  http.get(`${API_BASE}/api/v1/artifacts/:id/download`, async () => {
    await delay(MOCK_DELAY_CONSTANTS.FAST)
    return new HttpResponse(mockArtifact().markdown_content, {
      headers: { 'Content-Type': 'text/markdown' },
    })
  }),

  // ============================
  // Library Endpoints
  // ============================

  // GET /api/v1/library - Search library
  http.get(`${API_BASE}/api/v1/library`, async () => {
    await delay(MOCK_DELAY_CONSTANTS.NORMAL)
    return HttpResponse.json(mockLibraryList())
  }),

  // ============================
  // Health Endpoint
  // ============================

  // GET /api/v1/health - Health check
  http.get(`${API_BASE}/api/v1/health`, async () => {
    await delay(20)
    return HttpResponse.json(mockHealthCheck())
  }),
]

/**
 * Error scenario handlers for testing error handling
 * Use server.use(...errorHandlers.serverError) to override default handlers
 */
export const errorHandlers = {
  notFound: http.get(`${API_BASE}/api/v1/analyze/:id`, () => {
    return HttpResponse.json({ detail: 'Analysis not found' }, { status: 404 })
  }),

  serverError: http.get(`${API_BASE}/api/v1/analyze/:id`, () => {
    return HttpResponse.json({ detail: 'Internal server error' }, { status: 500 })
  }),

  timeout: http.get(`${API_BASE}/api/v1/analyze/:id`, async () => {
    await delay(60000) // 60 second delay to trigger timeout
    return HttpResponse.json({})
  }),

  rateLimited: http.get(`${API_BASE}/api/v1/analyze/:id`, () => {
    return HttpResponse.json(
      { detail: 'Too many requests' },
      {
        status: 429,
        headers: { 'Retry-After': '60' },
      }
    )
  }),

  validationError: http.post(`${API_BASE}/api/v1/analyze`, () => {
    return HttpResponse.json(
      {
        detail: 'Validation error',
        errors: [{ field: 'url', message: 'Invalid URL format' }],
      },
      { status: 422 }
    )
  }),
}
