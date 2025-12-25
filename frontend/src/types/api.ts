// API type definitions based on backend Pydantic schemas
// Source: docs/INTEGRATION_POINTS.md

export type ContentType = 'article' | 'video' | 'repo'

export type AnalysisMode = 'quick' | 'standard' | 'deep_dive'

// Granular analysis status values with semantic meaning
// 'complete' is ONLY set when artifact exists and is valid
export type AnalysisStatus =
  // Lifecycle states
  | 'pending'
  | 'extracting'
  | 'analyzing'
  | 'generating_artifact'
  | 'complete' // Only when artifact exists!
  // Failure states
  | 'extraction_failed'
  | 'analysis_failed'
  | 'artifact_failed' // Workflow done, but no artifact
  | 'quality_gate_failed'
  | 'failed' // Generic fallback
  // User actions
  | 'cancelled'
  // Legacy (for backward compatibility)
  | 'running' // Deprecated - use specific lifecycle states
  | 'in-progress' // Deprecated - use specific lifecycle states
  | 'completed' // Backend returns 'completed', normalized to 'complete' in api.service.ts

export type StageStatus = 'pending' | 'running' | 'complete' | 'failed'

// Helper functions for status checks
export function isFailureStatus(status: AnalysisStatus): boolean {
  return [
    'extraction_failed',
    'analysis_failed',
    'artifact_failed',
    'quality_gate_failed',
    'failed',
  ].includes(status)
}

export function isCompleteStatus(status: AnalysisStatus): boolean {
  return status === 'complete'
}

export interface Analysis {
  id: string
  url: string
  content_type: ContentType
  title: string | null
  status: AnalysisStatus
  created_at: string
  artifact_id: string | null
}

export interface SSEProgressEvent {
  stage: string
  status: StageStatus
  details?: Record<string, unknown>
  timestamp: string
}

export interface Artifact {
  id: string
  analysis_id: string
  markdown_content: string
  version: number
  metadata: {
    topics: string[]
    complexity: 'beginner' | 'intermediate' | 'advanced'
    word_count: number
  }
  download_count: number
  created_at: string
}

export interface TutoringTopic {
  id: string
  name: string
  description?: string
}

export interface TutoringSession {
  id: string
  analysis_id: string
  topic_id?: string
  status: 'active' | 'completed' | 'abandoned'
  started_at: string
  completed_at: string | null
}

export interface TutoringMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

// API Request/Response types
export interface AnalyzeRequest {
  url: string
  content_type?: ContentType
  skill_level?: 'beginner' | 'intermediate' | 'expert'
  analysis_mode?: AnalysisMode
}

export interface AnalyzeResponse {
  analysis_id: string
  sse_endpoint: string
  status: AnalysisStatus
}

export interface AnalysisStatusResponse {
  status: AnalysisStatus
  artifact_id?: string | null
}

export interface ProgressEventResponse {
  stage: string
  status: string
  progress_data: Record<string, unknown> | null
  timestamp: string
}

export interface AnalysisProgressResponse {
  analysis_id: string
  events: ProgressEventResponse[]
}

export interface QualityMetadata {
  quality_passed?: boolean
  quality_scores?: Record<string, { score: number; comment: string }>
  quality_warnings?: string[]
  quality_gate_avg_score?: number
}

export interface ArtifactMetadataResponse {
  analysis_id: string
  artifact_id: string
  markdown_content?: string | null
  metadata?: Record<string, unknown>
  artifact_metadata?: QualityMetadata & Record<string, unknown>
  trace_id?: string | null
  download_count?: number
  created_at?: string
}

export interface AnalysisRetryResponse {
  analysis_id: string
  status: AnalysisStatus
  retry_count: number
  sse_endpoint: string
}

export interface AnalysisRerunResponse {
  analysis_id: string
  status: AnalysisStatus
  rerun_count: number
  archived_artifact_id: string | null
  sse_endpoint: string
}

export interface APIError {
  error: {
    code: string
    message: string
    details?: object
  }
}

// Library Search Types (Issue #75)
export type SearchMode = 'hybrid' | 'fulltext' | 'semantic'

export interface LibrarySearchParams {
  query?: string
  content_type?: ContentType
  status?: AnalysisStatus
  search_mode?: SearchMode
  limit?: number
  offset?: number
}

export interface LibrarySearchResult {
  analysis_id: string
  url: string
  title: string | null
  content_type: ContentType
  status: AnalysisStatus
  tags: string[]
  snippet: string | null
  rank: number
  created_at: string
}

export interface LibraryListResponse {
  items: LibrarySearchResult[]
  total: number
  limit: number
  offset: number
}
