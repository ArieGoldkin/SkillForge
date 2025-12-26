/**
 * API Service for Backend Integration
 *
 * Connects to the FastAPI backend at /api/v1/*
 * Uses ky HTTP client with interceptors (Issue #550)
 * Includes Zod validation for type-safe responses (Issue #548)
 *
 * @module services/api.service
 */

import type {
  Analysis,
  AnalysisProgressResponse,
  AnalysisRerunResponse,
  AnalysisRetryResponse,
  AnalysisStatusResponse,
  AnalyzeRequest,
  AnalyzeResponse,
  ArtifactMetadataResponse,
  LibraryListResponse,
  LibrarySearchParams,
} from '@app-types/api'

import { api, apiRaw, getApiBaseUrl, isHTTPError, safeApi } from '@/lib/api-client'
import { logger } from '@/lib/logger'
import {
  AnalysisListSchema,
  AnalysisProgressResponseSchema,
  AnalysisRerunResponseSchema,
  AnalysisRetryResponseSchema,
  AnalysisStatusResponseSchema,
  AnalyzeResponseSchema,
  ArtifactMetadataResponseSchema,
  HealthResponseSchema,
  LibraryListResponseSchema,
} from '@/schemas/api'

/**
 * Analysis API - connects to real backend
 */
export const analyzeAPI = {
  /**
   * Create a new analysis
   * POST /api/v1/analyze
   */
  createAnalysis: async (request: AnalyzeRequest): Promise<AnalyzeResponse> => {
    const response = await api('api/v1/analyze', AnalyzeResponseSchema, {
      method: 'POST',
      json: request,
    })

    return response
  },

  /**
   * Get analysis status by ID
   * GET /api/v1/analyze/{id}
   */
  getAnalysisStatus: async (id: string): Promise<AnalysisStatusResponse> => {
    return api(`api/v1/analyze/${id}`, AnalysisStatusResponseSchema)
  },

  /**
   * Get progress events for a completed analysis
   * GET /api/v1/analyze/{id}/progress
   */
  getAnalysisProgress: async (id: string): Promise<AnalysisProgressResponse> => {
    return api(`api/v1/analyze/${id}/progress`, AnalysisProgressResponseSchema)
  },

  /**
   * Get latest artifact metadata/content for an analysis
   * GET /api/v1/analyze/{id}/artifact
   */
  getArtifactByAnalysis: async (analysisId: string): Promise<ArtifactMetadataResponse | null> => {
    return safeApi(`api/v1/analyze/${analysisId}/artifact`, ArtifactMetadataResponseSchema)
  },

  /**
   * Get artifact for an analysis
   * GET /api/v1/analyze/{id}/artifact
   */
  getArtifact: async (analysisId: string): Promise<ArtifactMetadataResponse | null> => {
    return safeApi(`api/v1/analyze/${analysisId}/artifact`, ArtifactMetadataResponseSchema)
  },

  /**
   * Get artifact metadata by artifact ID
   * GET /api/v1/artifacts/{artifact_id}
   * Returns artifact metadata including trace_id
   */
  getArtifactById: async (artifactId: string): Promise<ArtifactMetadataResponse | null> => {
    return safeApi(`api/v1/artifacts/${artifactId}`, ArtifactMetadataResponseSchema)
  },

  /**
   * Download artifact markdown content by artifact ID
   * GET /api/v1/artifacts/{artifact_id}/download
   * Returns raw markdown content as string
   */
  downloadArtifact: async (artifactId: string): Promise<string | null> => {
    try {
      const response = await apiRaw(`api/v1/artifacts/${artifactId}/download`)
      return await response.text()
    } catch (error) {
      logger.warn('downloadArtifact failed', {
        artifactId,
        error: error instanceof Error ? error.message : String(error),
        status: isHTTPError(error) ? error.response.status : undefined,
      })
      return null
    }
  },

  /**
   * List all analyses
   * GET /api/v1/analyze
   */
  listAnalyses: async (): Promise<Analysis[]> => {
    const result = await safeApi('api/v1/analyze', AnalysisListSchema)
    return result ?? []
  },

  /**
   * Delete an analysis and related records
   * DELETE /api/v1/analyses/{id}
   */
  deleteAnalysis: async (analysisId: string): Promise<void> => {
    await apiRaw(`api/v1/analyses/${analysisId}`, { method: 'DELETE' })
  },

  /**
   * Get the SSE endpoint URL for streaming progress
   */
  getSSEEndpoint: (analysisId: string): string => {
    return `${getApiBaseUrl()}/api/v1/analyze/${analysisId}/stream`
  },

  /**
   * Retry a failed analysis
   * POST /api/v1/analyze/{id}/retry
   */
  retryAnalysis: async (analysisId: string): Promise<AnalysisRetryResponse> => {
    return api(`api/v1/analyze/${analysisId}/retry`, AnalysisRetryResponseSchema, {
      method: 'POST',
    })
  },

  /**
   * Rerun a completed analysis with latest AI models/prompts
   * POST /api/v1/analyze/{id}/rerun
   */
  rerunAnalysis: async (analysisId: string): Promise<AnalysisRerunResponse> => {
    return api(`api/v1/analyze/${analysisId}/rerun`, AnalysisRerunResponseSchema, {
      method: 'POST',
    })
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
    const endpoint = `api/v1/library${queryString ? `?${queryString}` : ''}`

    return api(endpoint, LibraryListResponseSchema)
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
  check: async () => {
    return api('api/v1/health', HealthResponseSchema)
  },
}

export default analyzeAPI
