/**
 * SSE Event Types for SkillForge Analysis Workflow
 * Based on: docs/issues/040-sse-endpoint/SSE_SCHEMA.md
 * Version: 1.0
 */

export type StageName =
  | 'extraction'
  | 'supervisor_routing'
  | 'tech_comparison'
  | 'security_audit'
  | 'implementation_planning'
  | 'performance_audit'
  | 'code_quality_audit'
  | 'trends_analysis'
  | 'dependencies_analysis'
  | 'aggregation'
  | 'artifact_generation'

export type StageStatus = 'pending' | 'running' | 'complete' | 'failed'

export interface SSEProgressEvent {
  type: 'progress'
  analysis_id: string
  stage: StageName
  status: StageStatus
  timestamp: string
  details?: {
    word_count?: number
    agent?: string
    progress_percent?: number
    [key: string]: unknown
  }
}

export interface SSECompleteEvent {
  type: 'complete'
  analysis_id: string
  stage: 'artifact_generation'
  status: 'complete'
  timestamp: string
  artifact_id: string
  details?: Record<string, unknown>
}

export interface SSEErrorEvent {
  type: 'error'
  analysis_id: string
  stage: string
  status: 'failed'
  timestamp: string
  details: {
    error: string
    error_code?: string
    [key: string]: unknown
  }
}

export type SSEEvent = SSEProgressEvent | SSECompleteEvent | SSEErrorEvent

/**
 * Type guard to check if an event is a progress event
 */
export function isProgressEvent(event: SSEEvent): event is SSEProgressEvent {
  return event.type === 'progress'
}

/**
 * Type guard to check if an event is a complete event
 */
export function isCompleteEvent(event: SSEEvent): event is SSECompleteEvent {
  return event.type === 'complete'
}

/**
 * Type guard to check if an event is an error event
 */
export function isErrorEvent(event: SSEEvent): event is SSEErrorEvent {
  return event.type === 'error'
}
