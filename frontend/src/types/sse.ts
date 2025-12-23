/**
 * SSE Event Types for SkillForge Analysis Workflow
 * Based on: docs/issues/040-sse-endpoint/SSE_SCHEMA.md
 *
 * This file re-exports types from Zod schemas for backward compatibility.
 * Single source of truth: @/schemas/sse and @/schemas/base
 *
 * @deprecated Import directly from @/schemas/sse for runtime validation
 */

// ============================================================================
// Re-export Base Types from Zod Schemas
// ============================================================================

export type {
  AgentStageName,
  WorkflowStageName,
  StageName,
  StageStatus,
  ContentType,
  FindingsQuality,
  Coverage,
} from '@/schemas/base'

// ============================================================================
// Re-export SSE Event Types from Zod Schemas
// ============================================================================

export type {
  SSEEvent,
  SSEProgressEvent,
  SSECompleteEvent,
  SSEErrorEvent,
  AnalysisMetadata,
  SuccessMetrics,
} from '@/schemas/sse'

// ============================================================================
// Re-export Type Guards and Helper Functions
// ============================================================================

export {
  isProgressEvent,
  isCompleteEvent,
  isErrorEvent,
  isFailedStage,
  parseSSEEvent,
} from '@/schemas/sse'
