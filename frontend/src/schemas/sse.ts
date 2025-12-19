/**
 * SSE Event Schemas for SkillForge Analysis Workflow
 * Provides runtime validation for Server-Sent Events using Zod
 *
 * Based on: docs/issues/040-sse-endpoint/SSE_SCHEMA.md
 *
 * @module schemas/sse
 */

import { z } from 'zod'

import {
  StageNameSchema,
  StageStatusSchema,
  ContentTypeSchema,
  FindingsQualitySchema,
  CoverageSchema,
} from './base'

// ============================================================================
// Nested Object Schemas
// ============================================================================

/**
 * Analysis metadata - optional nested object in progress events
 * Contains information about the content being analyzed
 */
export const AnalysisMetadataSchema = z.object({
  title: z.string().optional(),
  content_type: ContentTypeSchema.optional(),
  url: z.string().optional(), // Not using .url() to allow relative/partial URLs
  word_count: z.number().int().nonnegative().optional(),
})

/**
 * Success metrics - reports on analysis quality
 */
export const SuccessMetricsSchema = z.object({
  findings_quality: FindingsQualitySchema.optional(),
  coverage: CoverageSchema.optional(),
  key_insights: z.array(z.string()).optional(),
})

/**
 * Details object for progress events
 * Uses catchall to allow additional unknown fields from backend
 */
export const ProgressEventDetailsSchema = z
  .object({
    word_count: z.number().optional(),
    agent: z.string().optional(),
    progress_percent: z.number().optional(),
    expected_total_stages: z.number().optional(),
    findings_summary: z.string().optional(),
    insights_count: z.number().optional(),
    confidence_score: z.number().min(0).max(1).optional(),
    analysis_metadata: AnalysisMetadataSchema.optional(),
    skip_reasons: z.record(z.string(), z.string()).optional(),
    success_metrics: SuccessMetricsSchema.optional(),
  })
  .catchall(z.unknown()) // Allow additional unknown fields

// ============================================================================
// SSE Event Schemas
// ============================================================================

/**
 * Progress Event Schema
 * Sent during analysis workflow execution to report stage progress
 */
export const SSEProgressEventSchema = z.object({
  type: z.literal('progress'),
  analysis_id: z.string().uuid(),
  stage: StageNameSchema,
  status: StageStatusSchema,
  timestamp: z.string(), // ISO 8601 format but allowing flexibility
  expected_total_stages: z.number().int().positive().optional(),
  findings_summary: z.string().optional(),
  insights_count: z.number().int().nonnegative().optional(),
  confidence_score: z.number().min(0).max(1).optional(),
  analysis_metadata: AnalysisMetadataSchema.optional(),
  skip_reasons: z.record(z.string(), z.string()).optional(),
  success_metrics: SuccessMetricsSchema.optional(),
  details: ProgressEventDetailsSchema.optional(),
})

/**
 * Complete Event Schema
 * Sent when the entire analysis workflow completes successfully
 */
export const SSECompleteEventSchema = z.object({
  type: z.literal('complete'),
  analysis_id: z.string().uuid(),
  stage: z.enum(['artifact_generation', 'workflow']),
  status: z.literal('complete'),
  timestamp: z.string(),
  trace_id: z.string().optional(), // Langfuse trace ID for feedback submission
  artifact_id: z.string().uuid().optional(),
  details: z.record(z.unknown()).optional(),
})

/**
 * Error Event Schema
 * Sent when an analysis stage fails
 */
export const SSEErrorEventSchema = z.object({
  type: z.literal('error'),
  analysis_id: z.string().uuid(),
  stage: z.string(), // Can be any stage name, allowing flexibility for error events
  status: z.literal('failed'),
  timestamp: z.string(),
  error: z.string().optional(), // Backend sends error at top level
  details: z
    .object({
      error: z.string().optional(),
      error_code: z.string().optional(),
    })
    .catchall(z.unknown())
    .optional(),
})

/**
 * Unified SSE Event Schema - Discriminated Union
 * Uses the 'type' field to determine which event schema to apply
 */
export const SSEEventSchema = z.discriminatedUnion('type', [
  SSEProgressEventSchema,
  SSECompleteEventSchema,
  SSEErrorEventSchema,
])

// ============================================================================
// Type Inference - Export TypeScript types from Zod schemas
// ============================================================================

export type SSEEvent = z.infer<typeof SSEEventSchema>
export type SSEProgressEvent = z.infer<typeof SSEProgressEventSchema>
export type SSECompleteEvent = z.infer<typeof SSECompleteEventSchema>
export type SSEErrorEvent = z.infer<typeof SSEErrorEventSchema>
export type AnalysisMetadata = z.infer<typeof AnalysisMetadataSchema>
export type SuccessMetrics = z.infer<typeof SuccessMetricsSchema>

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Parse and validate SSE event data with detailed error logging
 * Returns validated event or null if validation fails
 *
 * @param data - Raw parsed JSON data from SSE event
 * @returns Validated SSEEvent or null if invalid
 */
export function parseSSEEvent(data: unknown): SSEEvent | null {
  const result = SSEEventSchema.safeParse(data)

  if (!result.success) {
    console.error('[SSE Validation] Invalid event structure:', {
      error: result.error.format(),
      receivedData: data,
    })
    return null
  }

  return result.data
}

/**
 * Type-safe type guard for progress events
 * Uses full schema validation for runtime safety
 */
export function isProgressEvent(event: unknown): event is SSEProgressEvent {
  return SSEProgressEventSchema.safeParse(event).success
}

/**
 * Type-safe type guard for complete events
 * Uses full schema validation for runtime safety
 */
export function isCompleteEvent(event: unknown): event is SSECompleteEvent {
  return SSECompleteEventSchema.safeParse(event).success
}

/**
 * Type-safe type guard for error events
 * Uses full schema validation for runtime safety
 */
export function isErrorEvent(event: unknown): event is SSEErrorEvent {
  return SSEErrorEventSchema.safeParse(event).success
}
