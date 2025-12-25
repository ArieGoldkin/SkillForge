/**
 * API Response Schemas for SkillForge
 * Provides runtime validation for all API responses using Zod
 *
 * Issue #548: Add Zod Runtime Validation for API Responses
 *
 * @module schemas/api
 */

import { z } from 'zod'

import { logger } from '@/lib/logger'

import { ContentTypeSchema } from './base'

// ============================================================================
// Analysis Status Schema
// ============================================================================

/**
 * Analysis status values matching backend AnalysisStatus enum
 * Includes lifecycle states, failure states, and legacy values
 */
export const AnalysisStatusSchema = z.enum([
  // Lifecycle states
  'pending',
  'extracting',
  'analyzing',
  'generating_artifact',
  'complete',
  // Failure states
  'extraction_failed',
  'analysis_failed',
  'artifact_failed',
  'quality_gate_failed',
  'failed',
  // User actions
  'cancelled',
  // Legacy (backend may still return these)
  'running',
  'in-progress',
  'completed',
])

/**
 * Analysis mode for different processing depths
 */
export const AnalysisModeSchema = z.enum(['quick', 'standard', 'deep_dive'])

/**
 * Search mode for library queries
 */
export const SearchModeSchema = z.enum(['hybrid', 'fulltext', 'semantic'])

// ============================================================================
// API Response Schemas
// ============================================================================

/**
 * POST /api/v1/analyze response
 */
export const AnalyzeResponseSchema = z.object({
  analysis_id: z.string().uuid(),
  sse_endpoint: z.string(),
  status: AnalysisStatusSchema,
  // Additional fields the backend may return
  url: z.string().optional(),
  content_type: z.string().optional(),
})

/**
 * GET /api/v1/analyze/{id} response
 */
export const AnalysisStatusResponseSchema = z.object({
  status: AnalysisStatusSchema,
  artifact_id: z.string().uuid().nullable().optional(),
})

/**
 * Progress event within AnalysisProgressResponse
 */
export const ProgressEventResponseSchema = z.object({
  stage: z.string(),
  status: z.string(),
  progress_data: z.record(z.string(), z.unknown()).nullable(),
  timestamp: z.string(),
})

/**
 * GET /api/v1/analyze/{id}/progress response
 */
export const AnalysisProgressResponseSchema = z.object({
  analysis_id: z.string().uuid(),
  events: z.array(ProgressEventResponseSchema),
})

/**
 * Quality metadata for artifacts
 */
export const QualityMetadataSchema = z.object({
  quality_passed: z.boolean().optional(),
  quality_scores: z
    .record(
      z.string(),
      z.object({
        score: z.number(),
        comment: z.string(),
      })
    )
    .optional(),
  quality_warnings: z.array(z.string()).optional(),
  quality_gate_avg_score: z.number().optional(),
})

/**
 * GET /api/v1/analyze/{id}/artifact response
 * GET /api/v1/artifacts/{id} response
 */
export const ArtifactMetadataResponseSchema = z.object({
  analysis_id: z.string().uuid(),
  artifact_id: z.string().uuid(),
  markdown_content: z.string().nullable().optional(),
  metadata: z.record(z.string(), z.unknown()).optional(),
  artifact_metadata: QualityMetadataSchema.extend({}).catchall(z.unknown()).optional(),
  trace_id: z.string().nullable().optional(),
  download_count: z.number().int().nonnegative().optional(),
  created_at: z.string().optional(),
})

/**
 * POST /api/v1/analyze/{id}/retry response
 */
export const AnalysisRetryResponseSchema = z.object({
  analysis_id: z.string().uuid(),
  status: AnalysisStatusSchema,
  retry_count: z.number().int().nonnegative(),
  sse_endpoint: z.string(),
})

/**
 * POST /api/v1/analyze/{id}/rerun response
 */
export const AnalysisRerunResponseSchema = z.object({
  analysis_id: z.string().uuid(),
  status: AnalysisStatusSchema,
  rerun_count: z.number().int().nonnegative(),
  archived_artifact_id: z.string().uuid().nullable(),
  sse_endpoint: z.string(),
})

/**
 * Full Analysis object (for list endpoints)
 */
export const AnalysisSchema = z.object({
  id: z.string().uuid(),
  url: z.string(),
  content_type: ContentTypeSchema,
  title: z.string().nullable(),
  status: AnalysisStatusSchema,
  created_at: z.string(),
  artifact_id: z.string().uuid().nullable(),
})

/**
 * Library search result item
 */
export const LibrarySearchResultSchema = z.object({
  analysis_id: z.string().uuid(),
  url: z.string(),
  title: z.string().nullable(),
  content_type: ContentTypeSchema,
  status: AnalysisStatusSchema,
  tags: z.array(z.string()),
  snippet: z.string().nullable(),
  rank: z.number(),
  created_at: z.string(),
})

/**
 * GET /api/v1/library response
 */
export const LibraryListResponseSchema = z.object({
  items: z.array(LibrarySearchResultSchema),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
})

/**
 * GET /api/v1/health response
 */
export const HealthCheckResponseSchema = z.object({
  status: z.string(),
  version: z.string(),
  environment: z.string(),
  database: z.object({
    status: z.string(),
  }),
})

// Alias for consistency with other schemas
export const HealthResponseSchema = HealthCheckResponseSchema

/**
 * GET /api/v1/analyze (list) response
 */
export const AnalysisListSchema = z.array(AnalysisSchema)

// ============================================================================
// Type Inference - Export TypeScript types from Zod schemas
// ============================================================================

export type AnalysisStatus = z.infer<typeof AnalysisStatusSchema>
export type AnalysisMode = z.infer<typeof AnalysisModeSchema>
export type SearchMode = z.infer<typeof SearchModeSchema>
export type AnalyzeResponse = z.infer<typeof AnalyzeResponseSchema>
export type AnalysisStatusResponse = z.infer<typeof AnalysisStatusResponseSchema>
export type ProgressEventResponse = z.infer<typeof ProgressEventResponseSchema>
export type AnalysisProgressResponse = z.infer<typeof AnalysisProgressResponseSchema>
export type QualityMetadata = z.infer<typeof QualityMetadataSchema>
export type ArtifactMetadataResponse = z.infer<typeof ArtifactMetadataResponseSchema>
export type AnalysisRetryResponse = z.infer<typeof AnalysisRetryResponseSchema>
export type AnalysisRerunResponse = z.infer<typeof AnalysisRerunResponseSchema>
export type Analysis = z.infer<typeof AnalysisSchema>
export type LibrarySearchResult = z.infer<typeof LibrarySearchResultSchema>
export type LibraryListResponse = z.infer<typeof LibraryListResponseSchema>
export type HealthCheckResponse = z.infer<typeof HealthCheckResponseSchema>
export type AnalysisList = z.infer<typeof AnalysisListSchema>

// ============================================================================
// Validation Helper Functions
// ============================================================================

/**
 * Validation result type for API responses
 */
export type ValidationResult<T> =
  | { success: true; data: T }
  | { success: false; error: z.ZodError; data: null }

/**
 * Generic validation function for API responses
 * Logs validation errors with context for debugging
 *
 * @param schema - Zod schema to validate against
 * @param data - Raw data from API response
 * @param context - Context string for logging (e.g., endpoint name)
 * @returns Validated data or throws ZodError
 */
export function validateApiResponse<T>(schema: z.ZodSchema<T>, data: unknown, context: string): T {
  const result = schema.safeParse(data)

  if (!result.success) {
    logger.error('API response validation failed', {
      context,
      validationErrors: result.error.issues,
      receivedData: data,
    })
    throw result.error
  }

  return result.data
}

/**
 * Safe validation function that returns a result object instead of throwing
 * Use this when you want to handle validation errors gracefully
 *
 * @param schema - Zod schema to validate against
 * @param data - Raw data from API response
 * @param context - Context string for logging
 * @returns ValidationResult with success status and data or error
 */
export function safeValidateApiResponse<T>(
  schema: z.ZodSchema<T>,
  data: unknown,
  context: string
): ValidationResult<T> {
  const result = schema.safeParse(data)

  if (!result.success) {
    logger.warn('API response validation failed (safe mode)', {
      context,
      validationErrors: result.error.issues,
      receivedData: data,
    })
    return { success: false, error: result.error, data: null }
  }

  return { success: true, data: result.data }
}
