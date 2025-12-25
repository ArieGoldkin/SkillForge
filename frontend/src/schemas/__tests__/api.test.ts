/**
 * Unit Tests for API Response Schemas
 * Tests runtime validation for all API endpoint responses using Zod
 *
 * Test Categories:
 * 1. Valid API Responses - All schema types with full and minimal fields
 * 2. Invalid API Responses - Missing required fields, wrong types, invalid UUIDs
 * 3. validateApiResponse helper - Returns validated data on success, throws ZodError on failure
 * 4. safeValidateApiResponse helper - Returns ValidationResult object
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ZodError } from 'zod'

import {
  AnalysisStatusSchema,
  AnalysisModeSchema,
  SearchModeSchema,
  AnalyzeResponseSchema,
  AnalysisStatusResponseSchema,
  ProgressEventResponseSchema,
  AnalysisProgressResponseSchema,
  QualityMetadataSchema,
  ArtifactMetadataResponseSchema,
  AnalysisRetryResponseSchema,
  AnalysisRerunResponseSchema,
  AnalysisSchema,
  LibrarySearchResultSchema,
  LibraryListResponseSchema,
  HealthCheckResponseSchema,
  validateApiResponse,
  safeValidateApiResponse,
  type AnalyzeResponse,
  type QualityMetadata,
  type ArtifactMetadataResponse,
} from '../api'

// ============================================================================
// Test Data Constants
// ============================================================================

const VALID_ANALYSIS_ID = '123e4567-e89b-12d3-a456-426614174000'
const VALID_ARTIFACT_ID = '987fcdeb-51a2-43d7-8f9e-123456789abc'
const VALID_TRACE_ID = 'trace-abc123-def456'
const VALID_TIMESTAMP = '2025-12-19T10:30:00.000Z'
const INVALID_UUID = 'not-a-uuid'

// ============================================================================
// 1. Valid API Responses Tests
// ============================================================================

describe('API Schemas - Valid Responses', () => {
  describe('AnalysisStatusSchema', () => {
    it('should validate all lifecycle status values', () => {
      const lifecycleStatuses = [
        'pending',
        'extracting',
        'analyzing',
        'generating_artifact',
        'complete',
      ]

      lifecycleStatuses.forEach((status) => {
        const result = AnalysisStatusSchema.safeParse(status)
        expect(result.success).toBe(true)
      })
    })

    it('should validate all failure status values', () => {
      const failureStatuses = [
        'extraction_failed',
        'analysis_failed',
        'artifact_failed',
        'quality_gate_failed',
        'failed',
      ]

      failureStatuses.forEach((status) => {
        const result = AnalysisStatusSchema.safeParse(status)
        expect(result.success).toBe(true)
      })
    })

    it('should validate user action status values', () => {
      const result = AnalysisStatusSchema.safeParse('cancelled')
      expect(result.success).toBe(true)
    })

    it('should reject invalid status values', () => {
      const invalidStatuses = ['running', 'in-progress', 'completed', 'invalid', 'unknown']

      invalidStatuses.forEach((status) => {
        const result = AnalysisStatusSchema.safeParse(status)
        expect(result.success).toBe(false)
      })
    })
  })

  describe('AnalysisModeSchema', () => {
    it('should validate all mode values', () => {
      const modes = ['quick', 'standard', 'deep_dive']

      modes.forEach((mode) => {
        const result = AnalysisModeSchema.safeParse(mode)
        expect(result.success).toBe(true)
      })
    })
  })

  describe('SearchModeSchema', () => {
    it('should validate all search mode values', () => {
      const modes = ['hybrid', 'fulltext', 'semantic']

      modes.forEach((mode) => {
        const result = SearchModeSchema.safeParse(mode)
        expect(result.success).toBe(true)
      })
    })
  })

  describe('AnalyzeResponseSchema', () => {
    it('should validate a complete analyze response with all optional fields', () => {
      const validResponse: AnalyzeResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        sse_endpoint: '/api/v1/analyze/123e4567-e89b-12d3-a456-426614174000/sse',
        status: 'pending',
        url: 'https://example.com/article',
        content_type: 'article',
      }

      const result = AnalyzeResponseSchema.safeParse(validResponse)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data).toEqual(validResponse)
      }
    })

    it('should validate a minimal analyze response with only required fields', () => {
      const minimalResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        sse_endpoint: '/api/v1/analyze/123e4567-e89b-12d3-a456-426614174000/sse',
        status: 'pending',
      }

      const result = AnalyzeResponseSchema.safeParse(minimalResponse)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.analysis_id).toBe(VALID_ANALYSIS_ID)
        expect(result.data.status).toBe('pending')
      }
    })
  })

  describe('AnalysisStatusResponseSchema', () => {
    it('should validate a status response with nullable artifact_id', () => {
      const validResponse = {
        status: 'complete',
        artifact_id: null,
      }

      const result = AnalysisStatusResponseSchema.safeParse(validResponse)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.artifact_id).toBeNull()
      }
    })

    it('should validate a status response with valid artifact_id', () => {
      const validResponse = {
        status: 'complete',
        artifact_id: VALID_ARTIFACT_ID,
      }

      const result = AnalysisStatusResponseSchema.safeParse(validResponse)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.artifact_id).toBe(VALID_ARTIFACT_ID)
      }
    })

    it('should validate a minimal status response with only required fields', () => {
      const minimalResponse = {
        status: 'pending',
      }

      const result = AnalysisStatusResponseSchema.safeParse(minimalResponse)
      expect(result.success).toBe(true)
    })
  })

  describe('ProgressEventResponseSchema', () => {
    it('should validate a complete progress event', () => {
      const validEvent = {
        stage: 'extraction',
        status: 'running',
        progress_data: {
          agent: 'extraction_agent',
          progress_percent: 45,
        },
        timestamp: VALID_TIMESTAMP,
      }

      const result = ProgressEventResponseSchema.safeParse(validEvent)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.stage).toBe('extraction')
        expect(result.data.progress_data).toBeDefined()
      }
    })

    it('should validate a progress event with null progress_data', () => {
      const validEvent = {
        stage: 'embedding',
        status: 'pending',
        progress_data: null,
        timestamp: VALID_TIMESTAMP,
      }

      const result = ProgressEventResponseSchema.safeParse(validEvent)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.progress_data).toBeNull()
      }
    })
  })

  describe('AnalysisProgressResponseSchema', () => {
    it('should validate a complete progress response with multiple events', () => {
      const validResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        events: [
          {
            stage: 'extraction',
            status: 'complete',
            progress_data: { findings_count: 5 },
            timestamp: VALID_TIMESTAMP,
          },
          {
            stage: 'embedding',
            status: 'running',
            progress_data: null,
            timestamp: VALID_TIMESTAMP,
          },
        ],
      }

      const result = AnalysisProgressResponseSchema.safeParse(validResponse)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.events).toHaveLength(2)
      }
    })

    it('should validate a progress response with empty events array', () => {
      const validResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        events: [],
      }

      const result = AnalysisProgressResponseSchema.safeParse(validResponse)
      expect(result.success).toBe(true)
    })
  })

  describe('QualityMetadataSchema', () => {
    it('should validate complete quality metadata with all fields', () => {
      const validMetadata: QualityMetadata = {
        quality_passed: true,
        quality_scores: {
          coherence: {
            score: 8.5,
            comment: 'Excellent logical flow',
          },
          relevance: {
            score: 7.2,
            comment: 'Highly relevant to topic',
          },
        },
        quality_warnings: ['Minor formatting issue in section 3'],
        quality_gate_avg_score: 7.85,
      }

      const result = QualityMetadataSchema.safeParse(validMetadata)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.quality_passed).toBe(true)
        expect(result.data.quality_scores).toBeDefined()
      }
    })

    it('should validate minimal quality metadata with no optional fields', () => {
      const minimalMetadata = {}

      const result = QualityMetadataSchema.safeParse(minimalMetadata)
      expect(result.success).toBe(true)
    })
  })

  describe('ArtifactMetadataResponseSchema', () => {
    it('should validate complete artifact metadata with all fields', () => {
      const validResponse: ArtifactMetadataResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        artifact_id: VALID_ARTIFACT_ID,
        markdown_content: '# Introduction to LangGraph\n\nContent here...',
        metadata: {
          title: 'LangGraph Tutorial',
          word_count: 1500,
        },
        artifact_metadata: {
          quality_passed: true,
          quality_scores: {
            depth: {
              score: 8.0,
              comment: 'Comprehensive coverage',
            },
          },
          custom_field: 'allowed due to catchall',
        },
        trace_id: VALID_TRACE_ID,
        download_count: 42,
        created_at: VALID_TIMESTAMP,
      }

      const result = ArtifactMetadataResponseSchema.safeParse(validResponse)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.artifact_id).toBe(VALID_ARTIFACT_ID)
        expect(result.data.download_count).toBe(42)
      }
    })

    it('should validate minimal artifact metadata with only required fields', () => {
      const minimalResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        artifact_id: VALID_ARTIFACT_ID,
      }

      const result = ArtifactMetadataResponseSchema.safeParse(minimalResponse)
      expect(result.success).toBe(true)
    })

    it('should validate artifact metadata with null markdown_content', () => {
      const validResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        artifact_id: VALID_ARTIFACT_ID,
        markdown_content: null,
      }

      const result = ArtifactMetadataResponseSchema.safeParse(validResponse)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.markdown_content).toBeNull()
      }
    })

    it('should validate artifact metadata with null trace_id', () => {
      const validResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        artifact_id: VALID_ARTIFACT_ID,
        trace_id: null,
      }

      const result = ArtifactMetadataResponseSchema.safeParse(validResponse)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.trace_id).toBeNull()
      }
    })

    it('should validate download_count at boundary (0)', () => {
      const validResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        artifact_id: VALID_ARTIFACT_ID,
        download_count: 0,
      }

      const result = ArtifactMetadataResponseSchema.safeParse(validResponse)
      expect(result.success).toBe(true)
    })
  })

  describe('AnalysisRetryResponseSchema', () => {
    it('should validate a complete retry response', () => {
      const validResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        status: 'pending',
        retry_count: 1,
        sse_endpoint: '/api/v1/analyze/123e4567-e89b-12d3-a456-426614174000/sse',
      }

      const result = AnalysisRetryResponseSchema.safeParse(validResponse)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.retry_count).toBe(1)
      }
    })

    it('should validate retry_count at boundary (0)', () => {
      const validResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        status: 'pending',
        retry_count: 0,
        sse_endpoint: '/api/v1/analyze/123e4567-e89b-12d3-a456-426614174000/sse',
      }

      const result = AnalysisRetryResponseSchema.safeParse(validResponse)
      expect(result.success).toBe(true)
    })
  })

  describe('AnalysisRerunResponseSchema', () => {
    it('should validate a complete rerun response with archived artifact', () => {
      const validResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        status: 'pending',
        rerun_count: 2,
        archived_artifact_id: VALID_ARTIFACT_ID,
        sse_endpoint: '/api/v1/analyze/123e4567-e89b-12d3-a456-426614174000/sse',
      }

      const result = AnalysisRerunResponseSchema.safeParse(validResponse)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.rerun_count).toBe(2)
        expect(result.data.archived_artifact_id).toBe(VALID_ARTIFACT_ID)
      }
    })

    it('should validate a rerun response with null archived_artifact_id', () => {
      const validResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        status: 'pending',
        rerun_count: 1,
        archived_artifact_id: null,
        sse_endpoint: '/api/v1/analyze/123e4567-e89b-12d3-a456-426614174000/sse',
      }

      const result = AnalysisRerunResponseSchema.safeParse(validResponse)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.archived_artifact_id).toBeNull()
      }
    })

    it('should validate rerun_count at boundary (0)', () => {
      const validResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        status: 'pending',
        rerun_count: 0,
        archived_artifact_id: null,
        sse_endpoint: '/api/v1/analyze/123e4567-e89b-12d3-a456-426614174000/sse',
      }

      const result = AnalysisRerunResponseSchema.safeParse(validResponse)
      expect(result.success).toBe(true)
    })
  })

  describe('AnalysisSchema', () => {
    it('should validate a complete analysis object', () => {
      const validAnalysis = {
        id: VALID_ANALYSIS_ID,
        url: 'https://example.com/article',
        content_type: 'article',
        title: 'Introduction to LangGraph',
        status: 'complete',
        created_at: VALID_TIMESTAMP,
        artifact_id: VALID_ARTIFACT_ID,
      }

      const result = AnalysisSchema.safeParse(validAnalysis)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.title).toBe('Introduction to LangGraph')
        expect(result.data.artifact_id).toBe(VALID_ARTIFACT_ID)
      }
    })

    it('should validate an analysis with null title and artifact_id', () => {
      const validAnalysis = {
        id: VALID_ANALYSIS_ID,
        url: 'https://example.com/article',
        content_type: 'article',
        title: null,
        status: 'pending',
        created_at: VALID_TIMESTAMP,
        artifact_id: null,
      }

      const result = AnalysisSchema.safeParse(validAnalysis)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.title).toBeNull()
        expect(result.data.artifact_id).toBeNull()
      }
    })

    it('should validate all valid content types', () => {
      const contentTypes = ['article', 'video', 'repo']

      contentTypes.forEach((contentType) => {
        const analysis = {
          id: VALID_ANALYSIS_ID,
          url: 'https://example.com/content',
          content_type: contentType,
          title: null,
          status: 'pending',
          created_at: VALID_TIMESTAMP,
          artifact_id: null,
        }

        const result = AnalysisSchema.safeParse(analysis)
        expect(result.success).toBe(true)
      })
    })
  })

  describe('LibrarySearchResultSchema', () => {
    it('should validate a complete search result', () => {
      const validResult = {
        analysis_id: VALID_ANALYSIS_ID,
        url: 'https://example.com/article',
        title: 'LangGraph Tutorial',
        content_type: 'article',
        status: 'complete',
        tags: ['langgraph', 'multi-agent', 'python'],
        snippet: 'LangGraph is a framework for building multi-agent systems...',
        rank: 0.95,
        created_at: VALID_TIMESTAMP,
      }

      const result = LibrarySearchResultSchema.safeParse(validResult)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.tags).toHaveLength(3)
        expect(result.data.rank).toBe(0.95)
      }
    })

    it('should validate a search result with null title and snippet', () => {
      const validResult = {
        analysis_id: VALID_ANALYSIS_ID,
        url: 'https://example.com/article',
        title: null,
        content_type: 'article',
        status: 'complete',
        tags: [],
        snippet: null,
        rank: 0.75,
        created_at: VALID_TIMESTAMP,
      }

      const result = LibrarySearchResultSchema.safeParse(validResult)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.title).toBeNull()
        expect(result.data.snippet).toBeNull()
        expect(result.data.tags).toEqual([])
      }
    })
  })

  describe('LibraryListResponseSchema', () => {
    it('should validate a complete library list response', () => {
      const validResponse = {
        items: [
          {
            analysis_id: VALID_ANALYSIS_ID,
            url: 'https://example.com/article1',
            title: 'Article 1',
            content_type: 'article',
            status: 'complete',
            tags: ['python'],
            snippet: 'Snippet 1',
            rank: 0.9,
            created_at: VALID_TIMESTAMP,
          },
          {
            analysis_id: '223e4567-e89b-12d3-a456-426614174000',
            url: 'https://example.com/video1',
            title: 'Video Tutorial',
            content_type: 'video',
            status: 'complete',
            tags: ['typescript'],
            snippet: 'Snippet 2',
            rank: 0.85,
            created_at: VALID_TIMESTAMP,
          },
        ],
        total: 42,
        limit: 10,
        offset: 0,
      }

      const result = LibraryListResponseSchema.safeParse(validResponse)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.items).toHaveLength(2)
        expect(result.data.total).toBe(42)
      }
    })

    it('should validate an empty library list response', () => {
      const validResponse = {
        items: [],
        total: 0,
        limit: 10,
        offset: 0,
      }

      const result = LibraryListResponseSchema.safeParse(validResponse)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.items).toEqual([])
        expect(result.data.total).toBe(0)
      }
    })

    it('should validate pagination at boundaries', () => {
      const validResponse = {
        items: [],
        total: 100,
        limit: 1, // minimum positive
        offset: 0, // minimum nonnegative
      }

      const result = LibraryListResponseSchema.safeParse(validResponse)
      expect(result.success).toBe(true)
    })
  })

  describe('HealthCheckResponseSchema', () => {
    it('should validate a complete health check response', () => {
      const validResponse = {
        status: 'healthy',
        version: '1.0.0',
        environment: 'production',
        database: {
          status: 'connected',
        },
      }

      const result = HealthCheckResponseSchema.safeParse(validResponse)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.status).toBe('healthy')
        expect(result.data.database.status).toBe('connected')
      }
    })

    it('should validate a degraded health check response', () => {
      const validResponse = {
        status: 'degraded',
        version: '1.0.0',
        environment: 'development',
        database: {
          status: 'disconnected',
        },
      }

      const result = HealthCheckResponseSchema.safeParse(validResponse)
      expect(result.success).toBe(true)
    })
  })
})

// ============================================================================
// 2. Invalid API Responses Tests
// ============================================================================

describe('API Schemas - Invalid Responses', () => {
  describe('AnalysisStatusSchema - Invalid Cases', () => {
    it('should reject invalid status values', () => {
      const invalidStatuses = ['invalid', 'unknown', 'processing', '']

      invalidStatuses.forEach((status) => {
        const result = AnalysisStatusSchema.safeParse(status)
        expect(result.success).toBe(false)
      })
    })
  })

  describe('AnalyzeResponseSchema - Invalid Cases', () => {
    it('should reject responses missing required analysis_id', () => {
      const invalidResponse = {
        sse_endpoint: '/api/v1/analyze/123/sse',
        status: 'pending',
      }

      const result = AnalyzeResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses missing required sse_endpoint', () => {
      const invalidResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        status: 'pending',
      }

      const result = AnalyzeResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses missing required status', () => {
      const invalidResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        sse_endpoint: '/api/v1/analyze/123/sse',
      }

      const result = AnalyzeResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with invalid UUID for analysis_id', () => {
      const invalidResponse = {
        analysis_id: INVALID_UUID,
        sse_endpoint: '/api/v1/analyze/123/sse',
        status: 'pending',
      }

      const result = AnalyzeResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with invalid status value', () => {
      const invalidResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        sse_endpoint: '/api/v1/analyze/123/sse',
        status: 'invalid_status',
      }

      const result = AnalyzeResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })
  })

  describe('AnalysisStatusResponseSchema - Invalid Cases', () => {
    it('should reject responses missing required status', () => {
      const invalidResponse = {
        artifact_id: VALID_ARTIFACT_ID,
      }

      const result = AnalysisStatusResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with invalid UUID for artifact_id', () => {
      const invalidResponse = {
        status: 'complete',
        artifact_id: INVALID_UUID,
      }

      const result = AnalysisStatusResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })
  })

  describe('ProgressEventResponseSchema - Invalid Cases', () => {
    it('should reject events missing required stage', () => {
      const invalidEvent = {
        status: 'running',
        progress_data: null,
        timestamp: VALID_TIMESTAMP,
      }

      const result = ProgressEventResponseSchema.safeParse(invalidEvent)
      expect(result.success).toBe(false)
    })

    it('should reject events missing required status', () => {
      const invalidEvent = {
        stage: 'extraction',
        progress_data: null,
        timestamp: VALID_TIMESTAMP,
      }

      const result = ProgressEventResponseSchema.safeParse(invalidEvent)
      expect(result.success).toBe(false)
    })

    it('should reject events missing required timestamp', () => {
      const invalidEvent = {
        stage: 'extraction',
        status: 'running',
        progress_data: null,
      }

      const result = ProgressEventResponseSchema.safeParse(invalidEvent)
      expect(result.success).toBe(false)
    })

    it('should reject events missing required progress_data', () => {
      const invalidEvent = {
        stage: 'extraction',
        status: 'running',
        timestamp: VALID_TIMESTAMP,
      }

      const result = ProgressEventResponseSchema.safeParse(invalidEvent)
      expect(result.success).toBe(false)
    })
  })

  describe('AnalysisProgressResponseSchema - Invalid Cases', () => {
    it('should reject responses missing required analysis_id', () => {
      const invalidResponse = {
        events: [],
      }

      const result = AnalysisProgressResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses missing required events', () => {
      const invalidResponse = {
        analysis_id: VALID_ANALYSIS_ID,
      }

      const result = AnalysisProgressResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with invalid UUID for analysis_id', () => {
      const invalidResponse = {
        analysis_id: INVALID_UUID,
        events: [],
      }

      const result = AnalysisProgressResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with invalid events array items', () => {
      const invalidResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        events: [
          {
            stage: 'extraction',
            // missing required fields
          },
        ],
      }

      const result = AnalysisProgressResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })
  })

  describe('QualityMetadataSchema - Invalid Cases', () => {
    it('should reject metadata with non-boolean quality_passed', () => {
      const invalidMetadata = {
        quality_passed: 'true',
      }

      const result = QualityMetadataSchema.safeParse(invalidMetadata)
      expect(result.success).toBe(false)
    })

    it('should reject metadata with invalid quality_scores structure', () => {
      const invalidMetadata = {
        quality_scores: {
          coherence: 'not an object',
        },
      }

      const result = QualityMetadataSchema.safeParse(invalidMetadata)
      expect(result.success).toBe(false)
    })

    it('should reject metadata with quality_scores missing score field', () => {
      const invalidMetadata = {
        quality_scores: {
          coherence: {
            comment: 'Good',
          },
        },
      }

      const result = QualityMetadataSchema.safeParse(invalidMetadata)
      expect(result.success).toBe(false)
    })

    it('should reject metadata with quality_scores missing comment field', () => {
      const invalidMetadata = {
        quality_scores: {
          coherence: {
            score: 8.5,
          },
        },
      }

      const result = QualityMetadataSchema.safeParse(invalidMetadata)
      expect(result.success).toBe(false)
    })

    it('should reject metadata with non-array quality_warnings', () => {
      const invalidMetadata = {
        quality_warnings: 'not an array',
      }

      const result = QualityMetadataSchema.safeParse(invalidMetadata)
      expect(result.success).toBe(false)
    })

    it('should reject metadata with non-number quality_gate_avg_score', () => {
      const invalidMetadata = {
        quality_gate_avg_score: '7.5',
      }

      const result = QualityMetadataSchema.safeParse(invalidMetadata)
      expect(result.success).toBe(false)
    })
  })

  describe('ArtifactMetadataResponseSchema - Invalid Cases', () => {
    it('should reject responses missing required analysis_id', () => {
      const invalidResponse = {
        artifact_id: VALID_ARTIFACT_ID,
      }

      const result = ArtifactMetadataResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses missing required artifact_id', () => {
      const invalidResponse = {
        analysis_id: VALID_ANALYSIS_ID,
      }

      const result = ArtifactMetadataResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with invalid UUID for analysis_id', () => {
      const invalidResponse = {
        analysis_id: INVALID_UUID,
        artifact_id: VALID_ARTIFACT_ID,
      }

      const result = ArtifactMetadataResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with invalid UUID for artifact_id', () => {
      const invalidResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        artifact_id: INVALID_UUID,
      }

      const result = ArtifactMetadataResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with negative download_count', () => {
      const invalidResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        artifact_id: VALID_ARTIFACT_ID,
        download_count: -1,
      }

      const result = ArtifactMetadataResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with non-integer download_count', () => {
      const invalidResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        artifact_id: VALID_ARTIFACT_ID,
        download_count: 3.5,
      }

      const result = ArtifactMetadataResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })
  })

  describe('AnalysisRetryResponseSchema - Invalid Cases', () => {
    it('should reject responses missing required fields', () => {
      const invalidResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        status: 'pending',
      }

      const result = AnalysisRetryResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with invalid UUID for analysis_id', () => {
      const invalidResponse = {
        analysis_id: INVALID_UUID,
        status: 'pending',
        retry_count: 1,
        sse_endpoint: '/api/v1/analyze/123/sse',
      }

      const result = AnalysisRetryResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with negative retry_count', () => {
      const invalidResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        status: 'pending',
        retry_count: -1,
        sse_endpoint: '/api/v1/analyze/123/sse',
      }

      const result = AnalysisRetryResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with non-integer retry_count', () => {
      const invalidResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        status: 'pending',
        retry_count: 1.5,
        sse_endpoint: '/api/v1/analyze/123/sse',
      }

      const result = AnalysisRetryResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })
  })

  describe('AnalysisRerunResponseSchema - Invalid Cases', () => {
    it('should reject responses missing required fields', () => {
      const invalidResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        status: 'pending',
      }

      const result = AnalysisRerunResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with invalid UUID for analysis_id', () => {
      const invalidResponse = {
        analysis_id: INVALID_UUID,
        status: 'pending',
        rerun_count: 1,
        archived_artifact_id: null,
        sse_endpoint: '/api/v1/analyze/123/sse',
      }

      const result = AnalysisRerunResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with invalid UUID for archived_artifact_id', () => {
      const invalidResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        status: 'pending',
        rerun_count: 1,
        archived_artifact_id: INVALID_UUID,
        sse_endpoint: '/api/v1/analyze/123/sse',
      }

      const result = AnalysisRerunResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with negative rerun_count', () => {
      const invalidResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        status: 'pending',
        rerun_count: -1,
        archived_artifact_id: null,
        sse_endpoint: '/api/v1/analyze/123/sse',
      }

      const result = AnalysisRerunResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with non-integer rerun_count', () => {
      const invalidResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        status: 'pending',
        rerun_count: 2.5,
        archived_artifact_id: null,
        sse_endpoint: '/api/v1/analyze/123/sse',
      }

      const result = AnalysisRerunResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })
  })

  describe('AnalysisSchema - Invalid Cases', () => {
    it('should reject analysis missing required id', () => {
      const invalidAnalysis = {
        url: 'https://example.com/article',
        content_type: 'article',
        title: null,
        status: 'pending',
        created_at: VALID_TIMESTAMP,
        artifact_id: null,
      }

      const result = AnalysisSchema.safeParse(invalidAnalysis)
      expect(result.success).toBe(false)
    })

    it('should reject analysis with invalid UUID for id', () => {
      const invalidAnalysis = {
        id: INVALID_UUID,
        url: 'https://example.com/article',
        content_type: 'article',
        title: null,
        status: 'pending',
        created_at: VALID_TIMESTAMP,
        artifact_id: null,
      }

      const result = AnalysisSchema.safeParse(invalidAnalysis)
      expect(result.success).toBe(false)
    })

    it('should reject analysis with invalid UUID for artifact_id', () => {
      const invalidAnalysis = {
        id: VALID_ANALYSIS_ID,
        url: 'https://example.com/article',
        content_type: 'article',
        title: null,
        status: 'pending',
        created_at: VALID_TIMESTAMP,
        artifact_id: INVALID_UUID,
      }

      const result = AnalysisSchema.safeParse(invalidAnalysis)
      expect(result.success).toBe(false)
    })

    it('should reject analysis with invalid content_type', () => {
      const invalidAnalysis = {
        id: VALID_ANALYSIS_ID,
        url: 'https://example.com/article',
        content_type: 'invalid_type',
        title: null,
        status: 'pending',
        created_at: VALID_TIMESTAMP,
        artifact_id: null,
      }

      const result = AnalysisSchema.safeParse(invalidAnalysis)
      expect(result.success).toBe(false)
    })
  })

  describe('LibrarySearchResultSchema - Invalid Cases', () => {
    it('should reject results missing required fields', () => {
      const invalidResult = {
        analysis_id: VALID_ANALYSIS_ID,
        url: 'https://example.com/article',
      }

      const result = LibrarySearchResultSchema.safeParse(invalidResult)
      expect(result.success).toBe(false)
    })

    it('should reject results with invalid UUID for analysis_id', () => {
      const invalidResult = {
        analysis_id: INVALID_UUID,
        url: 'https://example.com/article',
        title: null,
        content_type: 'article',
        status: 'complete',
        tags: [],
        snippet: null,
        rank: 0.8,
        created_at: VALID_TIMESTAMP,
      }

      const result = LibrarySearchResultSchema.safeParse(invalidResult)
      expect(result.success).toBe(false)
    })

    it('should reject results with non-number rank', () => {
      const invalidResult = {
        analysis_id: VALID_ANALYSIS_ID,
        url: 'https://example.com/article',
        title: null,
        content_type: 'article',
        status: 'complete',
        tags: [],
        snippet: null,
        rank: '0.8',
        created_at: VALID_TIMESTAMP,
      }

      const result = LibrarySearchResultSchema.safeParse(invalidResult)
      expect(result.success).toBe(false)
    })

    it('should reject results with non-array tags', () => {
      const invalidResult = {
        analysis_id: VALID_ANALYSIS_ID,
        url: 'https://example.com/article',
        title: null,
        content_type: 'article',
        status: 'complete',
        tags: 'python,langgraph',
        snippet: null,
        rank: 0.8,
        created_at: VALID_TIMESTAMP,
      }

      const result = LibrarySearchResultSchema.safeParse(invalidResult)
      expect(result.success).toBe(false)
    })
  })

  describe('LibraryListResponseSchema - Invalid Cases', () => {
    it('should reject responses missing required fields', () => {
      const invalidResponse = {
        items: [],
        total: 0,
      }

      const result = LibraryListResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with negative total', () => {
      const invalidResponse = {
        items: [],
        total: -1,
        limit: 10,
        offset: 0,
      }

      const result = LibraryListResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with non-positive limit', () => {
      const invalidResponse = {
        items: [],
        total: 0,
        limit: 0,
        offset: 0,
      }

      const result = LibraryListResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with negative offset', () => {
      const invalidResponse = {
        items: [],
        total: 0,
        limit: 10,
        offset: -1,
      }

      const result = LibraryListResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with non-integer total', () => {
      const invalidResponse = {
        items: [],
        total: 10.5,
        limit: 10,
        offset: 0,
      }

      const result = LibraryListResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with invalid items array', () => {
      const invalidResponse = {
        items: [
          {
            analysis_id: INVALID_UUID, // invalid UUID
            url: 'https://example.com/article',
            title: null,
            content_type: 'article',
            status: 'complete',
            tags: [],
            snippet: null,
            rank: 0.8,
            created_at: VALID_TIMESTAMP,
          },
        ],
        total: 1,
        limit: 10,
        offset: 0,
      }

      const result = LibraryListResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })
  })

  describe('HealthCheckResponseSchema - Invalid Cases', () => {
    it('should reject responses missing required fields', () => {
      const invalidResponse = {
        status: 'healthy',
        version: '1.0.0',
      }

      const result = HealthCheckResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })

    it('should reject responses with invalid database structure', () => {
      const invalidResponse = {
        status: 'healthy',
        version: '1.0.0',
        environment: 'production',
        database: {
          // missing status field
          connection_pool: 5,
        },
      }

      const result = HealthCheckResponseSchema.safeParse(invalidResponse)
      expect(result.success).toBe(false)
    })
  })
})

// ============================================================================
// 3. validateApiResponse Helper Tests
// ============================================================================

describe('validateApiResponse helper function', () => {
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    // Spy on console.error to verify error logging
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    // Restore console.error
    consoleErrorSpy.mockRestore()
  })

  describe('Valid response validation', () => {
    it('should return validated data for valid analyze response', () => {
      const validResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        sse_endpoint: '/api/v1/analyze/123/sse',
        status: 'pending',
      }

      const result = validateApiResponse(
        AnalyzeResponseSchema,
        validResponse,
        'POST /api/v1/analyze'
      )

      expect(result).toEqual(validResponse)
      expect(result.analysis_id).toBe(VALID_ANALYSIS_ID)
      expect(consoleErrorSpy).not.toHaveBeenCalled()
    })

    it('should return validated data for valid artifact metadata response', () => {
      const validResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        artifact_id: VALID_ARTIFACT_ID,
        markdown_content: '# Content',
        download_count: 5,
      }

      const result = validateApiResponse(
        ArtifactMetadataResponseSchema,
        validResponse,
        'GET /api/v1/artifacts/{id}'
      )

      expect(result.artifact_id).toBe(VALID_ARTIFACT_ID)
      expect(result.download_count).toBe(5)
      expect(consoleErrorSpy).not.toHaveBeenCalled()
    })

    it('should return validated data for valid library list response', () => {
      const validResponse = {
        items: [],
        total: 0,
        limit: 10,
        offset: 0,
      }

      const result = validateApiResponse(
        LibraryListResponseSchema,
        validResponse,
        'GET /api/v1/library'
      )

      expect(result.items).toEqual([])
      expect(result.total).toBe(0)
      expect(consoleErrorSpy).not.toHaveBeenCalled()
    })

    it('should preserve all fields in validated response', () => {
      const validResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        sse_endpoint: '/api/v1/analyze/123/sse',
        status: 'pending',
        url: 'https://example.com/article',
        content_type: 'article',
      }

      const result = validateApiResponse(
        AnalyzeResponseSchema,
        validResponse,
        'POST /api/v1/analyze'
      )

      expect(result.url).toBe('https://example.com/article')
      expect(result.content_type).toBe('article')
    })
  })

  describe('Invalid response validation', () => {
    it('should throw ZodError for response with invalid UUID', () => {
      const invalidResponse = {
        analysis_id: INVALID_UUID,
        sse_endpoint: '/api/v1/analyze/123/sse',
        status: 'pending',
      }

      expect(() => {
        validateApiResponse(AnalyzeResponseSchema, invalidResponse, 'POST /api/v1/analyze')
      }).toThrow(ZodError)

      expect(consoleErrorSpy).toHaveBeenCalled()
    })

    it('should throw ZodError for response with missing required fields', () => {
      const invalidResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        // missing sse_endpoint and status
      }

      expect(() => {
        validateApiResponse(AnalyzeResponseSchema, invalidResponse, 'POST /api/v1/analyze')
      }).toThrow(ZodError)

      expect(consoleErrorSpy).toHaveBeenCalled()
    })

    it('should throw ZodError for response with wrong field types', () => {
      const invalidResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        artifact_id: VALID_ARTIFACT_ID,
        download_count: 'not a number',
      }

      expect(() => {
        validateApiResponse(
          ArtifactMetadataResponseSchema,
          invalidResponse,
          'GET /api/v1/artifacts/{id}'
        )
      }).toThrow(ZodError)

      expect(consoleErrorSpy).toHaveBeenCalled()
    })

    it('should throw ZodError for response with out-of-range values', () => {
      const invalidResponse = {
        items: [],
        total: -1, // negative not allowed
        limit: 10,
        offset: 0,
      }

      expect(() => {
        validateApiResponse(LibraryListResponseSchema, invalidResponse, 'GET /api/v1/library')
      }).toThrow(ZodError)

      expect(consoleErrorSpy).toHaveBeenCalled()
    })

    it('should throw ZodError for non-object inputs', () => {
      const invalidInputs = [null, undefined, 'string', 123, true, []]

      invalidInputs.forEach((input) => {
        consoleErrorSpy.mockClear()
        expect(() => {
          validateApiResponse(AnalyzeResponseSchema, input, 'POST /api/v1/analyze')
        }).toThrow(ZodError)
        expect(consoleErrorSpy).toHaveBeenCalled()
      })
    })

    it('should log error details when validation fails', () => {
      const invalidResponse = {
        analysis_id: INVALID_UUID,
        sse_endpoint: '/api/v1/analyze/123/sse',
        status: 'pending',
      }

      try {
        validateApiResponse(AnalyzeResponseSchema, invalidResponse, 'POST /api/v1/analyze')
      } catch {
        // Expected to throw
      }

      // The logger.error call includes context, validationErrors, and receivedData
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        '[ERROR] API response validation failed',
        expect.objectContaining({
          context: 'POST /api/v1/analyze',
          receivedData: invalidResponse,
          validationErrors: expect.arrayContaining([
            expect.objectContaining({
              code: 'invalid_format',
              path: ['analysis_id'],
            }),
          ]),
        })
      )
    })
  })
})

// ============================================================================
// 4. safeValidateApiResponse Helper Tests
// ============================================================================

describe('safeValidateApiResponse helper function', () => {
  let consoleWarnSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    // Spy on console.warn to verify warning logging
    consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
  })

  afterEach(() => {
    // Restore console.warn
    consoleWarnSpy.mockRestore()
  })

  describe('Valid response validation', () => {
    it('should return success result for valid analyze response', () => {
      const validResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        sse_endpoint: '/api/v1/analyze/123/sse',
        status: 'pending',
      }

      const result = safeValidateApiResponse(
        AnalyzeResponseSchema,
        validResponse,
        'POST /api/v1/analyze'
      )

      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data).toEqual(validResponse)
        expect(result.data.analysis_id).toBe(VALID_ANALYSIS_ID)
      }
      expect(consoleWarnSpy).not.toHaveBeenCalled()
    })

    it('should return success result for valid health check response', () => {
      const validResponse = {
        status: 'healthy',
        version: '1.0.0',
        environment: 'production',
        database: {
          status: 'connected',
        },
      }

      const result = safeValidateApiResponse(
        HealthCheckResponseSchema,
        validResponse,
        'GET /api/v1/health'
      )

      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.status).toBe('healthy')
      }
    })

    it('should preserve all fields in success result', () => {
      const validResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        artifact_id: VALID_ARTIFACT_ID,
        markdown_content: '# Title\n\nContent',
        download_count: 10,
        trace_id: VALID_TRACE_ID,
      }

      const result = safeValidateApiResponse(
        ArtifactMetadataResponseSchema,
        validResponse,
        'GET /api/v1/artifacts/{id}'
      )

      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.markdown_content).toBe('# Title\n\nContent')
        expect(result.data.download_count).toBe(10)
        expect(result.data.trace_id).toBe(VALID_TRACE_ID)
      }
    })
  })

  describe('Invalid response validation', () => {
    it('should return failure result for response with invalid UUID', () => {
      const invalidResponse = {
        analysis_id: INVALID_UUID,
        sse_endpoint: '/api/v1/analyze/123/sse',
        status: 'pending',
      }

      const result = safeValidateApiResponse(
        AnalyzeResponseSchema,
        invalidResponse,
        'POST /api/v1/analyze'
      )

      expect(result.success).toBe(false)
      if (!result.success) {
        expect(result.data).toBeNull()
        expect(result.error).toBeInstanceOf(ZodError)
        expect(result.error.issues).toHaveLength(1)
        expect(result.error.issues[0].code).toBe('invalid_format')
        expect(result.error.issues[0].path).toEqual(['analysis_id'])
      }
      expect(consoleWarnSpy).toHaveBeenCalled()
    })

    it('should return failure result for response with missing required fields', () => {
      const invalidResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        // missing sse_endpoint and status
      }

      const result = safeValidateApiResponse(
        AnalyzeResponseSchema,
        invalidResponse,
        'POST /api/v1/analyze'
      )

      expect(result.success).toBe(false)
      if (!result.success) {
        expect(result.data).toBeNull()
        expect(result.error).toBeInstanceOf(ZodError)
        expect(result.error.issues.length).toBeGreaterThan(0)
      }
      expect(consoleWarnSpy).toHaveBeenCalled()
    })

    it('should return failure result for response with wrong field types', () => {
      const invalidResponse = {
        items: [],
        total: '100', // should be number
        limit: 10,
        offset: 0,
      }

      const result = safeValidateApiResponse(
        LibraryListResponseSchema,
        invalidResponse,
        'GET /api/v1/library'
      )

      expect(result.success).toBe(false)
      if (!result.success) {
        expect(result.data).toBeNull()
        expect(result.error.issues[0].path).toContain('total')
      }
    })

    it('should return failure result for response with out-of-range values', () => {
      const invalidResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        artifact_id: VALID_ARTIFACT_ID,
        download_count: -5, // negative not allowed
      }

      const result = safeValidateApiResponse(
        ArtifactMetadataResponseSchema,
        invalidResponse,
        'GET /api/v1/artifacts/{id}'
      )

      expect(result.success).toBe(false)
      if (!result.success) {
        expect(result.data).toBeNull()
        expect(result.error.issues[0].path).toContain('download_count')
      }
    })

    it('should return failure result for non-object inputs', () => {
      const invalidInputs = [null, undefined, 'string', 123, true, []]

      invalidInputs.forEach((input) => {
        consoleWarnSpy.mockClear()
        const result = safeValidateApiResponse(AnalyzeResponseSchema, input, 'POST /api/v1/analyze')
        expect(result.success).toBe(false)
        if (!result.success) {
          expect(result.data).toBeNull()
          expect(result.error).toBeInstanceOf(ZodError)
        }
        expect(consoleWarnSpy).toHaveBeenCalled()
      })
    })

    it('should log warning details when validation fails', () => {
      const invalidResponse = {
        analysis_id: INVALID_UUID,
        sse_endpoint: '/api/v1/analyze/123/sse',
        status: 'pending',
      }

      safeValidateApiResponse(AnalyzeResponseSchema, invalidResponse, 'POST /api/v1/analyze')

      // The logger.warn call includes context, validationErrors, and receivedData
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        '[WARN] API response validation failed (safe mode)',
        expect.objectContaining({
          context: 'POST /api/v1/analyze',
          receivedData: invalidResponse,
          validationErrors: expect.arrayContaining([
            expect.objectContaining({
              code: 'invalid_format',
              path: ['analysis_id'],
            }),
          ]),
        })
      )
    })
  })

  describe('Type safety and result discrimination', () => {
    it('should allow type-safe access to data when success is true', () => {
      const validResponse = {
        analysis_id: VALID_ANALYSIS_ID,
        sse_endpoint: '/api/v1/analyze/123/sse',
        status: 'pending',
      }

      const result = safeValidateApiResponse(
        AnalyzeResponseSchema,
        validResponse,
        'POST /api/v1/analyze'
      )

      if (result.success) {
        // TypeScript should know result.data is AnalyzeResponse
        const analysisId: string = result.data.analysis_id
        expect(analysisId).toBe(VALID_ANALYSIS_ID)
      }
    })

    it('should allow type-safe access to error when success is false', () => {
      const invalidResponse = {
        analysis_id: INVALID_UUID,
        sse_endpoint: '/api/v1/analyze/123/sse',
        status: 'pending',
      }

      const result = safeValidateApiResponse(
        AnalyzeResponseSchema,
        invalidResponse,
        'POST /api/v1/analyze'
      )

      if (!result.success) {
        // TypeScript should know result.error is ZodError
        const errorMessage: string = result.error.issues[0].message
        expect(errorMessage).toBeDefined()
        expect(result.data).toBeNull()
      }
    })
  })
})
