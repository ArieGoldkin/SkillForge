import type {
  Analysis,
  AnalyzeRequest,
  AnalyzeResponse,
  Artifact,
  TutoringSession,
  TutoringMessage,
} from '@/types/api'

// Mock data for development (until backend is ready)

export const mockAnalysis: Analysis = {
  id: '550e8400-e29b-41d4-a716-446655440000',
  url: 'https://example.com/article',
  content_type: 'article',
  title: 'Introduction to React Server Components',
  status: 'complete',
  created_at: new Date().toISOString(),
  artifact_id: 'artifact-123',
}

export const mockArtifact: Artifact = {
  id: 'artifact-123',
  analysis_id: '550e8400-e29b-41d4-a716-446655440000',
  markdown_content: `# Implementation Guide: React Server Components

## Overview
React Server Components allow you to write components that render on the server...

## Key Concepts
- Server Components run only on the server
- Client Components run in the browser
- Data fetching happens on the server

## Example Code
\`\`\`typescript
async function ServerComponent() {
  const data = await fetch('https://api.example.com/data')
  return <div>{data.title}</div>
}
\`\`\`
`,
  version: 1,
  metadata: {
    topics: ['React', 'Server Components', 'Next.js'],
    complexity: 'intermediate',
    word_count: 1250,
  },
  download_count: 0,
  created_at: new Date().toISOString(),
}

export const mockTutoringSession: TutoringSession = {
  id: 'session-456',
  analysis_id: '550e8400-e29b-41d4-a716-446655440000',
  status: 'active',
  started_at: new Date().toISOString(),
  completed_at: null,
}

export const mockTutoringMessages: TutoringMessage[] = [
  {
    id: 'msg-1',
    session_id: 'session-456',
    role: 'assistant',
    content:
      'Hello! I can help you implement React Server Components. What would you like to learn?',
    created_at: new Date().toISOString(),
  },
]

// Mock API functions (to be replaced with real API calls)

export const mockAnalyzeAPI = {
  createAnalysis: async (_request: AnalyzeRequest): Promise<AnalyzeResponse> => {
    // Simulate network delay
    await new Promise((resolve) => setTimeout(resolve, 500))

    return {
      analysis_id: '550e8400-e29b-41d4-a716-446655440000',
      sse_endpoint: '/api/v1/analyze/550e8400-e29b-41d4-a716-446655440000/stream',
      status: 'pending',
    }
  },

  getAnalysis: async (_id: string): Promise<Analysis> => {
    await new Promise((resolve) => setTimeout(resolve, 300))
    return mockAnalysis
  },

  getArtifact: async (_id: string): Promise<Artifact> => {
    await new Promise((resolve) => setTimeout(resolve, 300))
    return mockArtifact
  },
}

export const mockTutoringAPI = {
  createSession: async (_analysisId: string): Promise<TutoringSession> => {
    await new Promise((resolve) => setTimeout(resolve, 400))
    return mockTutoringSession
  },

  getSession: async (_sessionId: string): Promise<TutoringSession> => {
    await new Promise((resolve) => setTimeout(resolve, 200))
    return mockTutoringSession
  },

  getMessages: async (_sessionId: string): Promise<TutoringMessage[]> => {
    await new Promise((resolve) => setTimeout(resolve, 200))
    return mockTutoringMessages
  },

  sendMessage: async (sessionId: string, content: string): Promise<TutoringMessage> => {
    await new Promise((resolve) => setTimeout(resolve, 600))
    return {
      id: `msg-${Date.now()}`,
      session_id: sessionId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
  },
}
