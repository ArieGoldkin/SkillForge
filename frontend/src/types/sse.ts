/**
 * SSE Event Types for SkillForge Analysis Workflow
 * Based on: docs/issues/040-sse-endpoint/SSE_SCHEMA.md
 * Version: 1.0
 */

/**
 * Agent stage names - represent individual processing stages
 */
export type AgentStageName =
  | 'extraction'
  | 'embedding'
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

/**
 * Workflow-level stage names - represent workflow-wide events
 * @see docs/issues/040-sse-endpoint/SSE_SCHEMA.md
 */
export type WorkflowStageName = 'workflow' | 'pattern_comparison' | 'metrics'

/**
 * All possible stage names (agent + workflow-level)
 */
export type StageName = AgentStageName | WorkflowStageName

/**
 * Stage status values
 * - pending: Stage hasn't started yet
 * - running: Stage is currently executing
 * - complete: Stage finished successfully
 * - failed: Stage encountered an error
 * - skipped: Stage was skipped (not selected by supervisor)
 */
export type StageStatus = 'pending' | 'running' | 'complete' | 'failed' | 'skipped'

export interface SSEProgressEvent {
  type: 'progress'
  analysis_id: string
  stage: StageName
  status: StageStatus
  timestamp: string
  expected_total_stages?: number
  findings_summary?: string
  insights_count?: number
  confidence_score?: number
  analysis_metadata?: {
    title?: string
    content_type?: 'article' | 'video' | 'repo'
    url?: string
    word_count?: number
  }
  skip_reasons?: Record<string, string> // agent_type -> reason
  success_metrics?: {
    findings_quality?: 'high' | 'medium' | 'low'
    coverage?: 'comprehensive' | 'partial' | 'minimal'
    key_insights?: string[]
  }
  details?: {
    word_count?: number
    agent?: string
    progress_percent?: number
    expected_total_stages?: number
    findings_summary?: string
    insights_count?: number
    confidence_score?: number
    analysis_metadata?: {
      title?: string
      content_type?: 'article' | 'video' | 'repo'
      url?: string
      word_count?: number
    }
    skip_reasons?: Record<string, string>
    success_metrics?: {
      findings_quality?: 'high' | 'medium' | 'low'
      coverage?: 'comprehensive' | 'partial' | 'minimal'
      key_insights?: string[]
    }
    [key: string]: unknown
  }
}

export interface SSECompleteEvent {
  type: 'complete'
  analysis_id: string
  stage: 'artifact_generation' | 'workflow'
  status: 'complete'
  timestamp: string
  artifact_id?: string
  details?: Record<string, unknown>
}

export interface SSEErrorEvent {
  type: 'error'
  analysis_id: string
  stage: string
  status: 'failed'
  timestamp: string
  error?: string // Backend sends error at top level
  details?: {
    // Optional for backward compatibility
    error?: string
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
