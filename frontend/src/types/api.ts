// API type definitions based on backend Pydantic schemas
// Source: docs/INTEGRATION_POINTS.md

export type ContentType = 'article' | 'video' | 'repo'
export type AnalysisStatus =
  | 'pending'
  | 'extracting'
  | 'analyzing'
  | 'running'
  | 'in-progress'
  | 'complete'
  | 'completed' // Backend returns 'completed', normalized to 'complete' in api.service.ts
  | 'failed'
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

export interface ArtifactMetadataResponse {
  analysis_id: string
  artifact_id: string
  markdown_content?: string | null
  metadata?: Record<string, unknown>
  download_count?: number
  created_at?: string
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
