/* eslint-disable max-lines -- SSE schemas require comprehensive type definitions for all event types */
/**
 * SSE Event Schemas for SkillForge Analysis Workflow
 * Provides runtime validation for Server-Sent Events using Zod
 *
 * Based on: docs/issues/040-sse-endpoint/SSE_SCHEMA.md
 *
 * @module schemas/sse
 */

import { z } from 'zod'

import { COMPONENT_CONSTANTS } from '@/lib/constants'
import { logger } from '@/lib/logger'

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
 *
 * Uses .passthrough() to allow additional unknown fields from backend
 * (e.g., agent_type, processing_time_ms, quality_warning, etc.)
 *
 * Issue #442: Progress events can have status: "failed" for individual agents
 * that fail while the workflow continues (fail-open behavior). These events
 * include error and error_code fields at the top level.
 */
export const SSEProgressEventSchema = z
  .object({
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
    // Issue #442: Error fields for failed stages (fail-open - workflow continues)
    error: z.string().optional(),
    error_code: z.string().optional(),
    agent_type: z.string().optional(),
    // Issue #442: Quality metadata for transparency
    quality_warning: z.string().optional(),
    artifact_id: z.string().uuid().optional(),
    markdown_length: z.number().int().nonnegative().optional(),
    // Backend aggregation phase sends these fields
    message: z.string().optional(),
    elapsed_seconds: z.number().optional(),
    // Processing metadata from various stages
    processing_time_ms: z.number().optional(),
  })
  .passthrough() // Allow additional fields from backend

/**
 * Complete Event Schema
 * Sent when the entire analysis workflow completes successfully
 */
export const SSECompleteEventSchema = z
  .object({
    type: z.literal('complete'),
    analysis_id: z.string().uuid(),
    stage: z.enum(['artifact_generation', 'workflow']),
    status: z.literal('complete'),
    timestamp: z.string(),
    trace_id: z.string().optional(), // Langfuse trace ID for feedback submission
    artifact_id: z.string().uuid().optional(),
    details: z.record(z.string(), z.unknown()).optional(),
  })
  .passthrough() // Allow additional fields from backend

/**
 * Error Event Schema
 * Sent when an analysis stage fails
 */
export const SSEErrorEventSchema = z
  .object({
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
  .passthrough() // Allow additional fields from backend

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
 * Zod v4 workaround: Instead of using discriminated union, manually check
 * type field and validate against the appropriate schema
 *
 * @param data - Raw parsed JSON data from SSE event
 * @returns Validated SSEEvent or null if invalid
 */
// eslint-disable-next-line max-lines-per-function -- Each case requires schema validation with error logging
export function parseSSEEvent(data: unknown): SSEEvent | null {
  // Pre-check: Ensure data is an object with a 'type' field
  if (typeof data !== 'object' || data === null || !('type' in data)) {
    logger.error('SSE event validation failed: Invalid data structure', {
      receivedData:
        typeof data === 'string' ? data.substring(0, COMPONENT_CONSTANTS.SIZE_LIMIT_500) : data,
      dataType: typeof data,
    })
    return null
  }

  const eventType = (data as { type?: unknown }).type

  // Select the appropriate schema and validate based on type field
  switch (eventType) {
    case 'progress': {
      const result = SSEProgressEventSchema.safeParse(data)
      if (!result.success) {
        logger.error('SSE event validation failed', {
          eventType,
          validationErrors: result.error.issues,
          receivedData: data,
        })
        return null
      }
      return result.data
    }
    case 'complete': {
      const result = SSECompleteEventSchema.safeParse(data)
      if (!result.success) {
        logger.error('SSE event validation failed', {
          eventType,
          validationErrors: result.error.issues,
          receivedData: data,
        })
        return null
      }
      return result.data
    }
    case 'error': {
      const result = SSEErrorEventSchema.safeParse(data)
      if (!result.success) {
        logger.error('SSE event validation failed', {
          eventType,
          validationErrors: result.error.issues,
          receivedData: data,
        })
        return null
      }
      return result.data
    }
    default:
      logger.error('SSE event validation failed: Unknown event type', {
        eventType,
        receivedData: data,
      })
      return null
  }
}

/**
 * Type-safe type guard for progress events
 * Uses full schema validation for runtime safety
 * Pre-checks type field to avoid Zod v4 discriminated union issues
 */
export function isProgressEvent(event: unknown): event is SSEProgressEvent {
  // Pre-check type field before schema validation (Zod v4 workaround)
  if (typeof event !== 'object' || event === null || !('type' in event)) {
    return false
  }
  if ((event as { type?: unknown }).type !== 'progress') {
    return false
  }
  return SSEProgressEventSchema.safeParse(event).success
}

/**
 * Type-safe type guard for complete events
 * Uses full schema validation for runtime safety
 * Pre-checks type field to avoid Zod v4 discriminated union issues
 */
export function isCompleteEvent(event: unknown): event is SSECompleteEvent {
  // Pre-check type field before schema validation (Zod v4 workaround)
  if (typeof event !== 'object' || event === null || !('type' in event)) {
    return false
  }
  if ((event as { type?: unknown }).type !== 'complete') {
    return false
  }
  return SSECompleteEventSchema.safeParse(event).success
}

/**
 * Type-safe type guard for error events
 * Uses full schema validation for runtime safety
 * Pre-checks type field to avoid Zod v4 discriminated union issues
 */
export function isErrorEvent(event: unknown): event is SSEErrorEvent {
  // Pre-check type field before schema validation (Zod v4 workaround)
  if (typeof event !== 'object' || event === null || !('type' in event)) {
    return false
  }
  if ((event as { type?: unknown }).type !== 'error') {
    return false
  }
  return SSEErrorEventSchema.safeParse(event).success
}
