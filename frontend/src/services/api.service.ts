/**
 * Real API service for backend integration
 * Connects to the FastAPI backend at /api/v1/*
 */

import type {
  Analysis,
  AnalyzeRequest,
  AnalyzeResponse,
  Artifact,
  LibraryListResponse,
  LibrarySearchParams,
} from '@app-types/api'

// API base URL - uses Vite env variable or defaults to localhost:8500
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8500'

/**
 * Generic fetch wrapper with error handling
 */
async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || errorData.message || `API error: ${response.status}`)
  }

  return response.json()
}

/**
 * Analysis API - connects to real backend
 */
export const analyzeAPI = {
  /**
   * Create a new analysis
   * POST /api/v1/analyze
   */
  createAnalysis: async (request: AnalyzeRequest): Promise<AnalyzeResponse> => {
    const response = await apiFetch<{
      analysis_id: string
      url: string
      content_type: string
      status: string
      sse_endpoint: string
    }>('/api/v1/analyze', {
      method: 'POST',
      body: JSON.stringify(request),
    })

    return {
      analysis_id: response.analysis_id,
      sse_endpoint: response.sse_endpoint,
      status: response.status as AnalyzeResponse['status'],
    }
  },

  /**
   * Get analysis by ID
   * GET /api/v1/analyze/{id}
   * Note: Backend returns 501 currently, so this may fail
   */
  getAnalysis: async (id: string): Promise<Analysis | null> => {
    try {
      return await apiFetch<Analysis>(`/api/v1/analyze/${id}`)
    } catch (error) {
      // Backend returns 501 for GET - return null to indicate not available
      console.warn(`getAnalysis not available for ${id}:`, error)
      return null
    }
  },

  /**
   * Get artifact for an analysis
   * GET /api/v1/analyze/{id}/artifact
   * Note: Not yet implemented in backend
   */
  getArtifact: async (analysisId: string): Promise<Artifact | null> => {
    try {
      return await apiFetch<Artifact>(`/api/v1/analyze/${analysisId}/artifact`)
    } catch (error) {
      console.warn(`getArtifact not available for ${analysisId}:`, error)
      return null
    }
  },

  /**
   * Download artifact markdown content by artifact ID
   * GET /api/v1/artifacts/{artifact_id}/download
   * Returns raw markdown content as string
   */
  downloadArtifact: async (artifactId: string): Promise<string | null> => {
    try {
      const url = `${API_BASE_URL}/api/v1/artifacts/${artifactId}/download`
      const response = await fetch(url)

      if (!response.ok) {
        throw new Error(`Failed to download artifact: ${response.status}`)
      }

      return await response.text()
    } catch (error) {
      console.warn(`downloadArtifact failed for ${artifactId}:`, error)
      return null
    }
  },

  /**
   * List all analyses
   * GET /api/v1/analyze
   * Note: Not yet implemented in backend
   */
  listAnalyses: async (): Promise<Analysis[]> => {
    try {
      return await apiFetch<Analysis[]>('/api/v1/analyze')
    } catch (error) {
      console.warn('listAnalyses not available:', error)
      return []
    }
  },

  /**
   * Get the SSE endpoint URL for streaming progress
   */
  getSSEEndpoint: (analysisId: string): string => {
    return `${API_BASE_URL}/api/v1/analyze/${analysisId}/stream`
  },

  /**
   * Search library with full-text, semantic, or hybrid search
   * GET /api/v1/library
   */
  searchLibrary: async (params: LibrarySearchParams = {}): Promise<LibraryListResponse> => {
    const searchParams = new URLSearchParams()
    if (params.query) searchParams.set('query', params.query)
    if (params.content_type) searchParams.set('content_type', params.content_type)
    if (params.status) searchParams.set('status', params.status)
    if (params.search_mode) searchParams.set('search_mode', params.search_mode)
    if (params.limit) searchParams.set('limit', params.limit.toString())
    if (params.offset) searchParams.set('offset', params.offset.toString())

    const queryString = searchParams.toString()
    const endpoint = `/api/v1/library${queryString ? `?${queryString}` : ''}`

    return apiFetch<LibraryListResponse>(endpoint)
  },
}

/**
 * Health check API
 */
export const healthAPI = {
  /**
   * Check backend health
   * GET /api/v1/health
   */
  check: async (): Promise<{
    status: string
    version: string
    environment: string
    database: { status: string }
  }> => {
    return apiFetch('/api/v1/health')
  },
}

export default analyzeAPI
