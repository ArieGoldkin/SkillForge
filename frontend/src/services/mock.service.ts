import type {
  Analysis,
  AnalyzeRequest,
  AnalyzeResponse,
  Artifact,
  TutoringMessage,
  TutoringSession,
  TutoringTopic,
} from '@app-types/api'

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))

export const mockAnalyses: Analysis[] = [
  {
    id: '550e8400-e29b-41d4-a716-446655440000',
    url: 'https://react.dev/reference/rsc/server-components',
    content_type: 'article',
    title: 'Introduction to React Server Components',
    status: 'complete',
    created_at: new Date(Date.now() - 86400000).toISOString(),
    artifact_id: 'artifact-123',
  },
  {
    id: '550e8400-e29b-41d4-a716-446655440001',
    url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    content_type: 'video',
    title: 'Advanced TypeScript Patterns',
    status: 'complete',
    created_at: new Date(Date.now() - 172800000).toISOString(),
    artifact_id: 'artifact-124',
  },
  {
    id: '550e8400-e29b-41d4-a716-446655440002',
    url: 'https://github.com/vercel/next.js',
    content_type: 'repo',
    title: 'Next.js Repository Analysis',
    status: 'complete',
    created_at: new Date(Date.now() - 259200000).toISOString(),
    artifact_id: 'artifact-125',
  },
  {
    id: '550e8400-e29b-41d4-a716-446655440003',
    url: 'https://python.org/docs',
    content_type: 'article',
    title: 'Python Documentation Deep Dive',
    status: 'analyzing',
    created_at: new Date(Date.now() - 3600000).toISOString(),
    artifact_id: null,
  },
]

export const mockAnalysis: Analysis = mockAnalyses[0]

export const mockArtifact: Artifact = {
  id: 'artifact-123',
  analysis_id: '550e8400-e29b-41d4-a716-446655440000',
  markdown_content: `# Implementation Guide: React Server Components

## Overview
React Server Components allow you to write components that render on the server.

## Key Concepts
- Server Components run only on the server
- Client Components run in the browser
- Data fetching happens on the server
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

export const mockTutoringTopics: TutoringTopic[] = [
  { id: 'topic-1', name: 'React Server Components', description: 'Learn how RSC works' },
  {
    id: 'topic-2',
    name: 'Data Fetching Patterns',
    description: 'Async/await in server components',
  },
  {
    id: 'topic-3',
    name: 'Performance Optimization',
    description: 'Optimize rendering and loading',
  },
  { id: 'topic-all', name: 'All Topics', description: 'Overview of all concepts' },
]

export const mockTutoringSession: TutoringSession = {
  id: 'session-456',
  analysis_id: '550e8400-e29b-41d4-a716-446655440000',
  topic_id: 'topic-1',
  status: 'active',
  started_at: new Date().toISOString(),
  completed_at: null,
}

export const mockTutoringMessages: TutoringMessage[] = [
  {
    id: 'msg-1',
    session_id: 'session-456',
    role: 'assistant',
    content: 'Hello! I can help you with React Server Components. What would you like to learn?',
    created_at: new Date(Date.now() - 300000).toISOString(),
  },
  {
    id: 'msg-2',
    session_id: 'session-456',
    role: 'user',
    content: 'How do I fetch data in a Server Component?',
    created_at: new Date(Date.now() - 240000).toISOString(),
  },
]

export const mockAnalyzeAPI = {
  createAnalysis: async (_request: AnalyzeRequest): Promise<AnalyzeResponse> => {
    await delay(500)
    const analysisId = `analysis-${Date.now()}`
    return {
      analysis_id: analysisId,
      sse_endpoint: `/api/v1/analyze/${analysisId}/stream`,
      status: 'pending',
    }
  },
  getAnalysis: async (id: string): Promise<Analysis> => {
    await delay(300)
    return mockAnalyses.find((a) => a.id === id) || mockAnalysis
  },
  getArtifact: async (_id: string): Promise<Artifact> => {
    await delay(300)
    return mockArtifact
  },
  listAnalyses: async (): Promise<Analysis[]> => {
    await delay(400)
    return mockAnalyses
  },
}

export const mockTutoringAPI = {
  getTopics: async (_analysisId: string): Promise<TutoringTopic[]> => {
    await delay(300)
    return mockTutoringTopics
  },
  createSession: async (analysisId: string, topicId?: string): Promise<TutoringSession> => {
    await delay(400)
    return {
      ...mockTutoringSession,
      id: `session-${Date.now()}`,
      analysis_id: analysisId,
      topic_id: topicId,
      started_at: new Date().toISOString(),
    }
  },
  getSession: async (_sessionId: string): Promise<TutoringSession> => {
    await delay(200)
    return mockTutoringSession
  },
  getMessages: async (_sessionId: string): Promise<TutoringMessage[]> => {
    await delay(200)
    return mockTutoringMessages
  },
  sendMessage: async (sessionId: string, content: string): Promise<TutoringMessage> => {
    await delay(600)
    return {
      id: `msg-${Date.now()}`,
      session_id: sessionId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
  },
  endSession: async (sessionId: string): Promise<TutoringSession> => {
    await delay(300)
    return {
      ...mockTutoringSession,
      id: sessionId,
      status: 'completed',
      completed_at: new Date().toISOString(),
    }
  },
}
