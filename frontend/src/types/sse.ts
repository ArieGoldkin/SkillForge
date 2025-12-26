/**
 * SSE Type Re-exports
 * Re-exports SSE types from Zod schemas for use across the application
 *
 * This file serves as a convenience layer that consolidates all SSE-related
 * types from both the SSE schema and base schema modules. By importing from
 * this file, components get a single source of truth for SSE types.
 *
 * @module types/sse
 */

// ============================================================================
// SSE Event Types
// ============================================================================

/**
 * Re-export all SSE event types from the SSE schema (single source of truth)
 * These types are inferred from Zod schemas and validated at runtime
 */
export type {
  SSEEvent,
  SSEProgressEvent,
  SSECompleteEvent,
  SSEErrorEvent,
  AnalysisMetadata,
  SuccessMetrics,
} from '@/schemas/sse'

// ============================================================================
// Base Schema Types
// ============================================================================

/**
 * Re-export base schema types used in SSE events
 * These include stage names, statuses, and content types
 */
export type {
  StageName,
  StageStatus,
  AgentStageName,
  WorkflowStageName,
  ContentType,
  FindingsQuality,
  Coverage,
} from '@/schemas/sse'

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Re-export SSE helper functions for event parsing and type guards
 */
export {
  parseSSEEvent,
  isProgressEvent,
  isCompleteEvent,
  isErrorEvent,
  isFailedStage,
} from '@/schemas/sse'
