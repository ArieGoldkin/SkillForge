// API type definitions based on backend Pydantic schemas
// Source: docs/INTEGRATION_POINTS.md

export type ContentType = 'article' | 'video' | 'repo'
export type AnalysisStatus = 'pending' | 'extracting' | 'analyzing' | 'complete' | 'failed'
export type StageStatus = 'pending' | 'running' | 'complete' | 'failed'

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

export interface TutoringSession {
  id: string
  analysis_id: string
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
}

export interface AnalyzeResponse {
  analysis_id: string
  sse_endpoint: string
  status: AnalysisStatus
}

export interface APIError {
  error: {
    code: string
    message: string
    details?: object
  }
}
